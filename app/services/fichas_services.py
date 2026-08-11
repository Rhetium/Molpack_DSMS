import asyncio
import logging
import time
from pathlib import Path
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
from app.models.anomalia import AnomaliaRegistro
from app.models.kitem import KItem
from app.schemas.ficha import (
    FichaTecnicaCreateSchema,
    FichaTecnicaWithMaterialSchema,
    FichaTecnicaSchema,
)
from app.schemas.material import MaterialLiteSchema
from app.schemas.kitem import KItemCreateSchema
from app.schemas.kitem_relacion import KItemRelacionCreateSchema
from app.services.kitem_service import KItemService
from app.services.auditoria_service import AuditoriaService
from app.core.utils import nombre_pais_a_iso

from app.services.semantic_search_service import BusquedaSemanticaService
from app.services.anomalia_service import AnomaliaService
from app.routers.imagenes import clonar_imagenes_ficha

from app.core.dsms_constants import (
    ESTADO_REVISION,
    KTYPE_FICHA_TECNICA,
    REL_PERTENECE_A,
    REL_SE_DERIVA_DE,
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
    ESTADO_ABREVIATURAS,
    TRANSACCIONES_PERMITIDAS,
    ACCION_CAMBIO_ESTADO,
    ACCION_NUEVA_VERSION,
    ACCION_MODIFICACION,
)
from app.core.anomalia_constant import MIN_MUESTRAS_ML

logger = logging.getLogger(__name__)

_bg_tasks: set = set()

_COOLDOWN_FILE = Path(__file__).parent.parent / "ml_models" / ".last_training"

_COOLDOWN_SEGUNDOS = 3600  # 1 hora


def _entrenamiento_en_cooldown() -> bool:
    if not _COOLDOWN_FILE.exists():
        return False
    try:
        ultimo = float(_COOLDOWN_FILE.read_text().strip())
        return (time.time() - ultimo) < _COOLDOWN_SEGUNDOS
    except (ValueError, OSError):
        return False


def _registrar_entrenamiento() -> None:
    _COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _COOLDOWN_FILE.write_text(str(time.time()))


async def _ejecutar_entrenamiento_bg() -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.ml_anomalia_service import MLAnomaliaService

    try:
        async with AsyncSessionLocal() as session:
            total = await session.scalar(
                select(func.count())
                .select_from(FichaTecnica)
                .join(KItem, FichaTecnica.id_ficha == KItem.id)
                .where(KItem.estado == ESTADO_VIGENTE)
            )
            if (total or 0) < MIN_MUESTRAS_ML:
                logger.info(
                    f"[ML] Auto-entrenamiento omitido: solo {total} fichas "
                    f"Vigentes (mínimo {MIN_MUESTRAS_ML})."
                )
                return

            ml = MLAnomaliaService(session)
            resultado = await ml.entrenar_modelos()
            _registrar_entrenamiento()
            modelos = len(resultado.get("modelos_entrenados", []))
            logger.info(
                f"[ML] Auto-entrenamiento completado: {total} fichas, "
                f"{modelos} modelos entrenados."
            )
    except Exception:
        logger.exception("[ML] Error durante auto-entrenamiento en background.")

class FichaService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.kitem_service = KItemService(db_session)
        self.auditoria = AuditoriaService(db_session)
        self.busqueda = BusquedaSemanticaService(db_session)
        self.anomalias = AnomaliaService(db_session)

    def _validar_transicion_estado(self, estado_actual: str, nuevo_estado: str) -> None:
        permitidos = TRANSACCIONES_PERMITIDAS.get(estado_actual, set())
        if nuevo_estado not in permitidos:
            raise HTTPException(
                status_code=400,
                detail=f"Transicion de estado no permitida: {estado_actual} -> {nuevo_estado}",
            )

    def _validar_para_preliminar(self, ficha: FichaTecnica) -> None:
        faltantes = []

        if not ficha.codigo_material_local:
            faltantes.append("Código de material local")
        if not ficha.pais:
            faltantes.append("País")
        if not ficha.nombre_local_material:
            faltantes.append("Nombre local del material")
        if not ficha.caracteristicas:
            faltantes.append("Características físicas")

        md = ficha.manejo_disposicion or {}
        for campo, etiqueta in [
            ("uso", "Uso"), ("manejo", "Manejo"),
            ("almacenamiento", "Almacenamiento"), ("transporte", "Transporte"),
            ("vida_util", "Vida útil"),
        ]:
            if not md.get(campo):
                faltantes.append(f"Manejo y disposición → {etiqueta}")

        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Campos obligatorios incompletos para pasar a Preliminar: "
                    + ", ".join(faltantes)
                ),
            )

    def _validar_para_vigente(self, ficha: FichaTecnica) -> None:
        self._validar_para_preliminar(ficha)
        emp = ficha.empaque_estiba or {}
        if not emp or not emp.get("tipo_empaque"):
            raise HTTPException(
                status_code=400,
                detail="No se pueden publicar fichas sin tipo de empaque definido.",
            )

    async def _validar_unica_vigente_por_material_pais(self, ficha: FichaTecnica) -> None:
        query = (
            select(FichaTecnica)
            .join(KItem, FichaTecnica.id_ficha == KItem.id)
            .where(
                and_(
                    FichaTecnica.id_material_corporativo == ficha.id_material_corporativo,
                    FichaTecnica.pais == ficha.pais,
                    KItem.estado == ESTADO_VIGENTE,
                    FichaTecnica.id_ficha != ficha.id_ficha,
                )
            )
        )
        result = await self.db_session.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Ya existe una ficha vigente para este material y pais. "
                    "Solo puede haber una ficha vigente por material y pais."
                ),
            )

    async def _validar_material(self, id_material: UUID) -> MaterialComercial:
        result = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == id_material
            )
        )
        material = result.scalars().first()
        if not material:
            raise HTTPException(
                status_code=400, detail="Material comercial no encontrado"
            )
        return material

    def _validar_contenido_por_tipo(
        self,
        caracteristicas_contenido: dict | None,
    ) -> None:
        if not caracteristicas_contenido:
            return

        datos = (
            caracteristicas_contenido.model_dump()
            if hasattr(caracteristicas_contenido, "model_dump")
            else caracteristicas_contenido
        )

        tiene_algun_valor = any(
            v is not None
            for k, v in datos.items()
            if k.endswith("_valor")
        )

        if not tiene_algun_valor:
            return
        
    async def _validar_codigo_material_local_unico(
        self, id_material: UUID, pais: str, codigo_material_local: str,
    ) -> None:
        query = select(FichaTecnica).where(
            and_(
                FichaTecnica.id_material_corporativo == id_material,
                FichaTecnica.pais == pais,
                FichaTecnica.codigo_material_local == codigo_material_local,
            )
        )
        result = await self.db_session.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Ya existe una ficha con el mismo codigo de material local "
                    "para este material y pais."
                ),
            )


    def _generar_codigo_ficha(
        self, codigo_material_local: str, pais: str,
        estado_ficha: str, codigo_version: str,
    ) -> str:
        abreviatura_estado = ESTADO_ABREVIATURAS.get(estado_ficha, "UNK")
        pais_norm = pais.upper()
        return f"FT-{codigo_material_local}-{pais_norm}-{abreviatura_estado}-V{codigo_version}"

    def _incrementar_version_simple(self, codigo_version: str) -> str:
        try:
            major = int(float(codigo_version))
            return f"{major + 1}.0"
        except (ValueError, TypeError):
            return "2.0"


    async def listar(self) -> list[FichaTecnica]:
        result = await self.db_session.execute(select(FichaTecnica))
        return result.scalars().all()

    async def obtener(self, id_ficha: UUID) -> FichaTecnica:
        result = await self.db_session.execute(
            select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
        )
        ficha = result.scalars().first()
        if not ficha:
            raise HTTPException(status_code=404, detail="Ficha tecnica no encontrada")
        return ficha

    async def listar_versiones(self, id_ficha: UUID) -> list[FichaTecnica]:
        ficha = await self.obtener(id_ficha)

        if not ficha.codigo_material_local:
            return [ficha]

        result = await self.db_session.execute(
            select(FichaTecnica).where(
                and_(
                    FichaTecnica.id_material_corporativo == ficha.id_material_corporativo,
                    FichaTecnica.pais == ficha.pais,
                    FichaTecnica.codigo_material_local == ficha.codigo_material_local,
                )
            )
        )
        versiones = result.scalars().all()

        def _clave_version(f: FichaTecnica) -> float:
            try:
                return float(f.codigo_version)
            except (TypeError, ValueError):
                return 0.0

        return sorted(versiones, key=_clave_version)

    async def crear(self, ficha_data: FichaTecnicaCreateSchema):
        material = await self._validar_material(ficha_data.id_material_corporativo)

        if material.estado_material == "Inactivo":
            raise HTTPException(
                status_code=400,
                detail="No se pueden crear fichas técnicas para materiales inactivos.",
            )

        self._validar_contenido_por_tipo(
            caracteristicas_contenido=ficha_data.caracteristicas_contenido,
        )
        version_inicial = "1.0"
        estado_inicial = ESTADO_BORRADOR

        codigo_local = ficha_data.codigo_material_local or ""
        pais_iso = nombre_pais_a_iso(ficha_data.pais) if ficha_data.pais else ""

        if codigo_local:
            await self._validar_codigo_material_local_unico(
                id_material=ficha_data.id_material_corporativo,
                pais=pais_iso,
                codigo_material_local=codigo_local,
            )

        label_codigo = codigo_local or "BORRADOR"
        label_pais   = pais_iso   or "XX"
        codigo_ficha_local = self._generar_codigo_ficha(
            estado_ficha=estado_inicial,
            codigo_material_local=label_codigo,
            pais=label_pais,
            codigo_version=version_inicial,
        )

        kitem = await self.kitem_service.crear_kitem(
            KItemCreateSchema(
                ktype=KTYPE_FICHA_TECNICA,
                nombre=f"Ficha Tecnica - {label_codigo} ({label_pais})",
                descripcion=f"Ficha tecnica v{version_inicial} para material {label_codigo} en {label_pais}",
                estado=estado_inicial,
                metadata_extra={
                    "codigo_ficha_local": codigo_ficha_local,
                    "pais": label_pais,
                    "version": version_inicial,
                },
                usuario_creador=ficha_data.usuario_creador,
            )
        )

        ficha = FichaTecnica(
            id_ficha=kitem.id,
            id_material_corporativo=ficha_data.id_material_corporativo,
            codigo_ficha_local=codigo_ficha_local,
            codigo_material_local=codigo_local,
            nombre_local_material=ficha_data.nombre_local_material,
            codigo_version=version_inicial,
            pais=pais_iso,
            caracteristicas=ficha_data.caracteristicas.model_dump() if ficha_data.caracteristicas else None,
            caracteristicas_contenido=ficha_data.caracteristicas_contenido.model_dump() if ficha_data.caracteristicas_contenido else None,
            empaque_estiba=ficha_data.empaque_estiba.model_dump() if ficha_data.empaque_estiba else None,
            microbiologia=ficha_data.microbiologia.model_dump() if ficha_data.microbiologia else None,
            manejo_disposicion=ficha_data.manejo_disposicion.model_dump() if ficha_data.manejo_disposicion else None,
        )

        ficha.kitem = kitem
        self.db_session.add(ficha)

        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_data.id_material_corporativo,
                tipo_relacion=REL_PERTENECE_A,
                etiqueta=f"Ficha {codigo_ficha_local} pertenece a material {ficha_data.codigo_material_local}",
                usuario_creador=ficha_data.usuario_creador,
            )
        )

        await self.busqueda.asignar_embedding(
            kitem_id=ficha.id_ficha,
            campos_adicionales={
                "tipo_producto": material.tipo_producto, 
                "estado_ficha": ficha.estado_ficha,
            },
            usuario=ficha_data.usuario_creador,
        )

        await self.db_session.commit()
        await self.db_session.refresh(ficha)

        ficha._anomalias = []
        return ficha

    async def buscar_ficha(
        self,
        pais: str | None = None,
        estado_ficha: str | None = None,
        tipo_producto: str | None = None,
        texto: str | None = None,
    ) -> list[FichaTecnicaWithMaterialSchema]:
        from sqlalchemy import or_
        query = (
            select(FichaTecnica, MaterialComercial)
            .join(MaterialComercial)
            .join(KItem, FichaTecnica.id_ficha == KItem.id)
        )

        conditions = []
        if pais:
            conditions.append(FichaTecnica.pais == pais)
        if estado_ficha:
            conditions.append(KItem.estado == estado_ficha)
        if tipo_producto:
            conditions.append(MaterialComercial.tipo_producto == tipo_producto)
        if texto:
            patron = f"%{texto}%"
            conditions.append(or_(
                FichaTecnica.codigo_ficha_local.ilike(patron),
                FichaTecnica.codigo_material_local.ilike(patron),
                FichaTecnica.nombre_local_material.ilike(patron),
                FichaTecnica.pais.ilike(patron),
                MaterialComercial.nombre_corporativo.ilike(patron),
                MaterialComercial.categoria.ilike(patron),
            ))
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db_session.execute(query)
        rows = result.all()

        fichas: list[FichaTecnicaWithMaterialSchema] = []
        for ficha, material in rows:
            fichas.append(
                FichaTecnicaWithMaterialSchema(
                    **FichaTecnicaSchema.model_validate(ficha).model_dump(),
                    material=MaterialLiteSchema.model_validate(material),
                )
            )
        return fichas

    async def cambiar_estado(
        self, id_ficha: UUID, nuevo_estado: str, usuario_actualizacion: str,
    ):
        """Cambia estado de ficha con auditoría en ambos niveles (ficha + kitem)."""
        ficha = await self.obtener(id_ficha)
        estado_anterior = ficha.estado_ficha

        self._validar_transicion_estado(ficha.estado_ficha, nuevo_estado)

        if nuevo_estado == ESTADO_PRELIMINAR:
            self._validar_para_preliminar(ficha)
        elif nuevo_estado == ESTADO_VIGENTE:
            self._validar_para_vigente(ficha)
            await self._validar_unica_vigente_por_material_pais(ficha)

        # Validar que no haya anomalias pendientes
        result_anomalias = await self.db_session.execute(
            select(AnomaliaRegistro).where(
                and_(AnomaliaRegistro.kitem_id == id_ficha,
                     AnomaliaRegistro.estado == "pendiente")
            )
        )

        anomalias_pendientes = result_anomalias.scalars().all()
        if anomalias_pendientes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede cambiar el estado: hay {len(anomalias_pendientes)} "
                    f"anomalía(s) pendiente(s) por resolver. Resuélvelas antes de continuar."
                ),
            )

        ficha.codigo_ficha_local = self._generar_codigo_ficha(
            codigo_material_local=ficha.codigo_material_local or "BORRADOR",
            pais=ficha.pais or "XX",
            estado_ficha=nuevo_estado,
            codigo_version=ficha.codigo_version,
        )
        self.db_session.add(ficha)

        await self.kitem_service.actualizar_estado_kitem(
            kitem_id=ficha.id_ficha,
            nuevo_estado=nuevo_estado,
            usuario=usuario_actualizacion,
        )

        await self.auditoria.registrar(
            kitem_id=ficha.id_ficha,
            ktype=KTYPE_FICHA_TECNICA,
            accion=ACCION_CAMBIO_ESTADO,
            usuario=usuario_actualizacion,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            detalles={
                "codigo_ficha_local": ficha.codigo_ficha_local,
                "codigo_material_local": ficha.codigo_material_local,
                "pais": ficha.pais,
                "version": ficha.codigo_version,
                "transicion": f"{estado_anterior} -> {nuevo_estado}",
            },
        )

        if nuevo_estado == ESTADO_PRELIMINAR:
            try:
                material = await self._validar_material(ficha.id_material_corporativo)

                caract = ficha.caracteristicas or {}
                campos_embedding = {
                    "material": material.nombre_corporativo,
                    "categoria": material.categoria or "",
                    "contenido": material.contenido or "",
                    "material_base": material.material_base or "",
                    "tipo_producto": material.tipo_producto or "",
                    "pais": ficha.pais,
                    "color": caract.get("color", ""),
                    "largo_mm": caract.get("dimensiones_largo_valor", ""),
                    "ancho_mm": caract.get("dimensiones_ancho_valor", ""),
                    "alto_mm": caract.get("dimensiones_alto_valor", ""),
                    "peso_g": caract.get("peso_valor", ""),
                }

                campos_embedding = {k: v for k, v in campos_embedding.items() if v not in (None, "", 0)}

                from sqlalchemy import update as sa_update
                from app.models.kitem import KItem as KItemModel
                nombre_rico = (
                    f"Ficha: {material.nombre_corporativo} "
                    f"- {ficha.codigo_material_local} ({ficha.pais})"
                )
                desc_rica = (
                    f"Ficha técnica {ficha.codigo_version} de "
                    f"{material.nombre_corporativo} "
                    f"(categoría: {material.categoria}, "
                    f"contenido: {material.contenido}). "
                    f"Código local: {ficha.codigo_material_local}, país: {ficha.pais}."
                )
                await self.db_session.execute(
                    sa_update(KItemModel)
                    .where(KItemModel.id == ficha.id_ficha)
                    .values(nombre=nombre_rico, descripcion=desc_rica)
                )

                await self.busqueda.asignar_embedding(
                    kitem_id=ficha.id_ficha,
                    campos_adicionales=campos_embedding,
                    usuario=usuario_actualizacion,
                )
                await self.anomalias.analizar_ficha(
                    id_ficha=ficha.id_ficha,
                    usuario=usuario_actualizacion,
                    contexto="creacion",
                )
            except HTTPException:
                raise
            except Exception as exc:
                logger.error(
                    f"Error al enriquecer/analizar la ficha {ficha.id_ficha} "
                    "al pasar a Preliminar; la transición fue revertida.",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "No se pudo completar el análisis de la ficha al pasar "
                        "a Preliminar; la transición fue revertida. "
                        "Intenta nuevamente o contacta al administrador."
                    ),
                ) from exc

        await self.db_session.commit()
        await self.db_session.refresh(ficha)

        if nuevo_estado == ESTADO_VIGENTE and not _entrenamiento_en_cooldown():
            task = asyncio.create_task(_ejecutar_entrenamiento_bg())
            _bg_tasks.add(task)
            task.add_done_callback(_bg_tasks.discard)

        return ficha

    async def crear_nueva_version(self, id_ficha: UUID, usuario: str):

        ficha_origen = await self.obtener(id_ficha)

        nueva_version = self._incrementar_version_simple(ficha_origen.codigo_version)
        estado_inicial = ESTADO_BORRADOR

        codigo_ficha_local = self._generar_codigo_ficha(
            estado_ficha=estado_inicial,
            codigo_material_local=ficha_origen.codigo_material_local,
            pais=ficha_origen.pais,
            codigo_version=nueva_version,
        )

        kitem = await self.kitem_service.crear_kitem(
            KItemCreateSchema(
                ktype=KTYPE_FICHA_TECNICA,
                nombre=f"Ficha Tecnica - {ficha_origen.codigo_material_local} ({ficha_origen.pais}) v{nueva_version}",
                descripcion=f"Nueva version ({nueva_version}) derivada de {ficha_origen.codigo_ficha_local}",
                estado=estado_inicial,
                metadata_extra={
                    "codigo_ficha_local": codigo_ficha_local,
                    "pais": ficha_origen.pais,
                    "version": nueva_version,
                    "version_origen": ficha_origen.codigo_version,
                    "ficha_origen_id": str(ficha_origen.id_ficha),
                },
                usuario_creador=usuario,
            )
        )

        nueva_ficha = FichaTecnica(
            id_ficha=kitem.id,
            id_material_corporativo=ficha_origen.id_material_corporativo,
            codigo_ficha_local=codigo_ficha_local,
            codigo_material_local=ficha_origen.codigo_material_local,
            nombre_local_material=ficha_origen.nombre_local_material,
            codigo_version=nueva_version,
            pais=ficha_origen.pais,

            caracteristicas=clonar_imagenes_ficha(
                ficha_origen.id_ficha, kitem.id, ficha_origen.caracteristicas
            ),
            caracteristicas_contenido=ficha_origen.caracteristicas_contenido,
            empaque_estiba=ficha_origen.empaque_estiba,
            microbiologia=ficha_origen.microbiologia,
            manejo_disposicion=ficha_origen.manejo_disposicion,
        )

        nueva_ficha.kitem = kitem
        self.db_session.add(nueva_ficha)

        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_origen.id_ficha,
                tipo_relacion=REL_SE_DERIVA_DE,
                etiqueta=f"v{nueva_version} se deriva de v{ficha_origen.codigo_version}",
                usuario_creador=usuario,
            )
        )

        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_origen.id_material_corporativo,
                tipo_relacion=REL_PERTENECE_A,
                etiqueta=f"Ficha {codigo_ficha_local} pertenece a material {ficha_origen.codigo_material_local}",
                usuario_creador=usuario,
            )
        )

        await self.auditoria.registrar(
            kitem_id=ficha_origen.id_ficha,
            ktype=KTYPE_FICHA_TECNICA,
            accion=ACCION_NUEVA_VERSION,
            usuario=usuario,
            detalles={
                "nueva_ficha_id": str(kitem.id),
                "nueva_version": nueva_version,
                "nuevo_codigo_ficha": codigo_ficha_local,
                "version_origen": ficha_origen.codigo_version,
            },
        )

        await self.db_session.commit()
        await self.db_session.refresh(nueva_ficha)
        return nueva_ficha


    SECCIONES_EDITABLES = {
        "caracteristicas",
        "caracteristicas_contenido",
        "empaque_estiba",
        "microbiologia",
        "manejo_disposicion",
    }

    CAMPOS_ESCALARES_EDITABLES = {
        "nombre_local_material",
        "codigo_material_local",
        "pais",
    }


    async def actualizar(
        self,
        id_ficha: UUID,
        datos_actualizacion: dict,
        usuario: str,
    ) -> FichaTecnica:
        ficha = await self.obtener(id_ficha)

        if ficha.estado_ficha == ESTADO_OBSOLETO:
            raise HTTPException(
                status_code=400,
                detail="No se puede modificar una ficha en estado Obsoleto.",
            )

        if ficha.estado_ficha in (ESTADO_VIGENTE, ESTADO_REVISION):
            return await self._modificar_ficha_vigente(
                ficha_vigente=ficha,
                datos_actualizacion=datos_actualizacion,
                usuario=usuario,
            )

        return await self._modificar_ficha_editable(
            ficha=ficha,
            datos_actualizacion=datos_actualizacion,
            usuario=usuario,
        )

    async def _modificar_ficha_editable(
        self,
        ficha: FichaTecnica,
        datos_actualizacion: dict,
        usuario: str,
    ) -> FichaTecnica:
        nuevo_pais = datos_actualizacion.get("pais")
        if nuevo_pais:
            nuevo_pais = nombre_pais_a_iso(nuevo_pais)
            datos_actualizacion["pais"] = nuevo_pais

        nuevo_codigo = datos_actualizacion.get("codigo_material_local")
        cambia_codigo = bool(nuevo_codigo) and nuevo_codigo != ficha.codigo_material_local
        cambia_pais = bool(nuevo_pais) and nuevo_pais != ficha.pais
        if cambia_codigo or cambia_pais:
            if ficha.estado_ficha != ESTADO_BORRADOR:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "El código de material local y el país solo pueden "
                        "modificarse en estado Borrador."
                    ),
                )
            codigo_final = nuevo_codigo or ficha.codigo_material_local
            if codigo_final:
                await self._validar_codigo_material_local_unico(
                    id_material=ficha.id_material_corporativo,
                    pais=(nuevo_pais or ficha.pais) or "",
                    codigo_material_local=codigo_final,
                )

        cambios = {}

        for campo, valor in datos_actualizacion.items():
            if (
                campo not in self.SECCIONES_EDITABLES
                and campo not in self.CAMPOS_ESCALARES_EDITABLES
            ):
                continue
            if valor is None:
                continue

            valor_anterior = getattr(ficha, campo)
            if valor_anterior != valor:
                setattr(ficha, campo, valor)
                cambios[campo] = {
                    "anterior": valor_anterior,
                    "nuevo": valor,
                }

        if not cambios:
            return ficha  
        if "caracteristicas_contenido" in cambios:
            self._validar_contenido_por_tipo(
                    caracteristicas_contenido=ficha.caracteristicas_contenido,
            )

        ficha.usuario_ultima_actualizacion = usuario
        ficha.fecha_actualizacion = datetime.now()
        self.db_session.add(ficha)

        ficha.codigo_ficha_local = self._generar_codigo_ficha(
            codigo_material_local=ficha.codigo_material_local or "BORRADOR",
            pais=ficha.pais or "XX",
            estado_ficha=ficha.estado_ficha,
            codigo_version=ficha.codigo_version,
        )

        kitem = await self.kitem_service.obtener_kitem(ficha.id_ficha)
        kitem.usuario_ultima_actualizacion = usuario
        kitem.fecha_actualizacion = datetime.now()
        self.db_session.add(kitem)

        await self.auditoria.registrar(
            kitem_id=ficha.id_ficha,
            ktype=KTYPE_FICHA_TECNICA,
            accion=ACCION_MODIFICACION,
            usuario=usuario,
            detalles={
                "tipo_modificacion": "edicion_directa",
                "estado_ficha": ficha.estado_ficha,
                "version": ficha.codigo_version,
                "secciones_modificadas": list(cambios.keys()),
                "cambios": cambios,
            },
        )

        await self.db_session.commit()
        await self.db_session.refresh(ficha)

        try:
            resultado_anomalias = await self.anomalias.analizar_ficha(
                id_ficha=ficha.id_ficha,
                usuario=usuario,
                contexto="actualizacion",
            )
            await self.db_session.commit()  # Commit para persistir anomalías detectadas
            ficha._anomalias = resultado_anomalias.anomalias  # Agregar anomalías al objeto ficha para respuesta
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error al analizar anomalías para ficha {ficha.id_ficha}: {e}")
            ficha._anomalias = []  # Respuesta sin anomalías si falla el análisis

        return ficha

    async def _modificar_ficha_vigente(
        self,
        ficha_vigente: FichaTecnica,
        datos_actualizacion: dict,
        usuario: str,
    ) -> FichaTecnica:

        nueva_version = self._incrementar_version_simple(ficha_vigente.codigo_version)
        estado_inicial = ESTADO_PRELIMINAR

        codigo_ficha_local = self._generar_codigo_ficha(
            estado_ficha=estado_inicial,
            codigo_material_local=ficha_vigente.codigo_material_local,
            pais=ficha_vigente.pais,
            codigo_version=nueva_version,
        )

        kitem = await self.kitem_service.crear_kitem(
            KItemCreateSchema(
                ktype=KTYPE_FICHA_TECNICA,
                nombre=f"Ficha Tecnica - {ficha_vigente.codigo_material_local} ({ficha_vigente.pais}) v{nueva_version}",
                descripcion=f"Nueva version ({nueva_version}) derivada de {ficha_vigente.codigo_ficha_local} por modificacion",
                estado=estado_inicial,
                metadata_extra={
                    "codigo_ficha_local": codigo_ficha_local,
                    "pais": ficha_vigente.pais,
                    "version": nueva_version,
                    "version_origen": ficha_vigente.codigo_version,
                    "ficha_origen_id": str(ficha_vigente.id_ficha),
                    "motivo": "modificacion_ficha_vigente",
                },
                usuario_creador=usuario,
            )
        )

        secciones = {
            "caracteristicas": ficha_vigente.caracteristicas,
            "caracteristicas_contenido": ficha_vigente.caracteristicas_contenido,
            "empaque_estiba": ficha_vigente.empaque_estiba,
            "microbiologia": ficha_vigente.microbiologia,
            "manejo_disposicion": ficha_vigente.manejo_disposicion,
        }

        cambios_aplicados = {}
        for campo, valor in datos_actualizacion.items():
            if campo in self.SECCIONES_EDITABLES and valor is not None:
                cambios_aplicados[campo] = {
                    "anterior": secciones.get(campo),
                    "nuevo": valor,
                }
                secciones[campo] = valor

        nombre_local = ficha_vigente.nombre_local_material
        nuevo_nombre_local = datos_actualizacion.get("nombre_local_material")
        if nuevo_nombre_local and nuevo_nombre_local != nombre_local:
            cambios_aplicados["nombre_local_material"] = {
                "anterior": nombre_local,
                "nuevo": nuevo_nombre_local,
            }
            nombre_local = nuevo_nombre_local

        if "caracteristicas_contenido" in cambios_aplicados:
            self._validar_contenido_por_tipo(
                    caracteristicas_contenido=secciones["caracteristicas_contenido"],
            )

        nueva_ficha = FichaTecnica(
            id_ficha=kitem.id,
            id_material_corporativo=ficha_vigente.id_material_corporativo,
            codigo_ficha_local=codigo_ficha_local,
            codigo_material_local=ficha_vigente.codigo_material_local,
            nombre_local_material=nombre_local,
            codigo_version=nueva_version,
            pais=ficha_vigente.pais,

            caracteristicas=clonar_imagenes_ficha(
                ficha_vigente.id_ficha, kitem.id, secciones["caracteristicas"]
            ),
            caracteristicas_contenido=secciones["caracteristicas_contenido"],
            empaque_estiba=secciones["empaque_estiba"],
            microbiologia=secciones["microbiologia"],
            manejo_disposicion=secciones["manejo_disposicion"],
        )
        nueva_ficha.kitem = kitem
        self.db_session.add(nueva_ficha)

        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_vigente.id_ficha,
                tipo_relacion=REL_SE_DERIVA_DE,
                etiqueta=f"v{nueva_version} se deriva de v{ficha_vigente.codigo_version} (modificacion)",
                usuario_creador=usuario,
            )
        )

        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_vigente.id_material_corporativo,
                tipo_relacion=REL_PERTENECE_A,
                etiqueta=f"Ficha {codigo_ficha_local} pertenece a material {ficha_vigente.codigo_material_local}",
                usuario_creador=usuario,
            )
        )

        estado_anterior = ficha_vigente.estado_ficha
        await self.kitem_service.actualizar_estado_kitem(
            kitem_id=ficha_vigente.id_ficha,
            nuevo_estado=ESTADO_OBSOLETO,
            usuario=usuario,
        )

        await self.auditoria.registrar(
            kitem_id=ficha_vigente.id_ficha,
            ktype=KTYPE_FICHA_TECNICA,
            accion=ACCION_CAMBIO_ESTADO,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=ESTADO_OBSOLETO,
            detalles={
                "motivo": "Reemplazada por nueva version",
                "nueva_version_id": str(kitem.id),
                "nueva_version": nueva_version,
            },
        )

        await self.auditoria.registrar(
            kitem_id=kitem.id,
            ktype=KTYPE_FICHA_TECNICA,
            accion=ACCION_NUEVA_VERSION,
            usuario=usuario,
            detalles={
                "tipo_modificacion": "modificacion_ficha_vigente",
                "version_origen": ficha_vigente.codigo_version,
                "nueva_version": nueva_version,
                "secciones_modificadas": list(cambios_aplicados.keys()),
                "cambios": cambios_aplicados,
            },
        )

        await self.db_session.commit()
        await self.db_session.refresh(nueva_ficha)

        nueva_ficha_id = nueva_ficha.id_ficha
        try:
            material = await self._validar_material(nueva_ficha.id_material_corporativo)
            caract = nueva_ficha.caracteristicas or {}
            campos_embedding = {
                "material": material.nombre_corporativo,
                "categoria": material.categoria or "",
                "contenido": material.contenido or "",
                "material_base": material.material_base or "",
                "tipo_producto": material.tipo_producto or "",
                "pais": nueva_ficha.pais,
                "largo_mm": caract.get("dimensiones_largo_valor", ""),
                "ancho_mm": caract.get("dimensiones_ancho_valor", ""),
                "alto_mm": caract.get("dimensiones_alto_valor", ""),
                "peso_g": caract.get("peso_valor", ""),
            }
            campos_embedding = {k: v for k, v in campos_embedding.items() if v not in (None, "", 0)}
            await self.busqueda.asignar_embedding(
                kitem_id=nueva_ficha_id,
                campos_adicionales=campos_embedding,
                usuario=usuario,
            )

            resultado_anomalias = await self.anomalias.analizar_ficha(
                id_ficha=nueva_ficha_id,
                usuario=usuario,
                contexto="actualizacion",
            )
            await self.db_session.commit() 
            nueva_ficha._anomalias = resultado_anomalias.anomalias
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error al analizar anomalías para ficha {nueva_ficha_id}: {e}")
            nueva_ficha._anomalias = []

        return nueva_ficha
    
    async def calcular_rangos_tipicos(self, id_material: UUID) -> dict:
        """Calcula rangos típicos de las fichas de un material."""
        query = (
            select(FichaTecnica)
            .join(KItem, FichaTecnica.id_ficha == KItem.id)
            .where(
                and_(
                    FichaTecnica.id_material_corporativo == id_material,
                    KItem.estado.in_([ESTADO_VIGENTE, ESTADO_PRELIMINAR]),
                )
            )
        )
        result = await self.db_session.execute(query)
        fichas = result.scalars().all()

        if len(fichas) < 2:
            return {"fuente": "sin_datos", "total_fichas": len(fichas), "rangos": {}}

        rangos = {}
        campos_numericos = [
            "dimensiones_largo_valor", "dimensiones_ancho_valor",
            "dimensiones_alto_valor", "peso_valor", "ruptura_valor",
            "profundidad_pilar_valor", "diametro_alveolo_valor",
            "profundidad_cavidad_valor", "diametro_cavidad_valor",
        ]

        for campo in campos_numericos:
            valores = []
            for ficha in fichas:
                seccion = "caracteristicas" if "dimensiones" in campo or campo in (
                    "peso_valor", "ruptura_valor"
                ) else "caracteristicas_contenido"
                datos = getattr(ficha, seccion)
                if datos and campo in datos and datos[campo] is not None:
                    valores.append(float(datos[campo]))

            if len(valores) >= 2:
                rangos[campo] = {
                    "min": round(min(valores), 2),
                    "max": round(max(valores), 2),
                    "promedio": round(sum(valores) / len(valores), 2),
                    "muestras": len(valores),
                }

        return {
            "fuente": "calculado",
            "total_fichas": len(fichas),
            "rangos": rangos,
        }