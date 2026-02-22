"""
Servicio FichaTecnica — Con auditoría integrada.

La auditoría de creación y relaciones se maneja automáticamente
desde KItemService. Este servicio agrega auditoría para:
- Cambios de estado específicos de ficha (Borrador → Preliminar, etc.)
- Creación de nuevas versiones
"""

from uuid import UUID
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
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

from app.core.dsms_constants import (
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
)

class FichaService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.kitem_service = KItemService(db_session)
        self.auditoria = AuditoriaService(db_session)

    # -------------------------
    # Validaciones de estado
    # -------------------------

    def _validar_transicion_estado(self, estado_actual: str, nuevo_estado: str) -> None:
        permitidos = TRANSACCIONES_PERMITIDAS.get(estado_actual, set())
        if nuevo_estado not in permitidos:
            raise HTTPException(
                status_code=400,
                detail=f"Transicion de estado no permitida: {estado_actual} -> {nuevo_estado}",
            )

    def _validar_para_preliminar(self, ficha: FichaTecnica) -> None:
        if not ficha.caracteristicas:
            raise HTTPException(
                status_code=400,
                detail="No se pueden aprobar fichas sin caracteristicas definidas.",
            )
        if not ficha.caracteristicas_contenido:
            raise HTTPException(
                status_code=400,
                detail="No se pueden aprobar fichas sin caracteristicas de contenido definidas.",
            )

    def _validar_para_vigente(self, ficha: FichaTecnica) -> None:
        self._validar_para_preliminar(ficha)
        if not ficha.empaque_estiba:
            raise HTTPException(
                status_code=400,
                detail="No se pueden publicar fichas sin informacion de empaque y estiba.",
            )

    async def _validar_unica_vigente_por_material_pais(self, ficha: FichaTecnica) -> None:
        query = select(FichaTecnica).where(
            and_(
                FichaTecnica.id_material_corporativo == ficha.id_material_corporativo,
                FichaTecnica.pais == ficha.pais,
                FichaTecnica.estado_ficha == ESTADO_VIGENTE,
                FichaTecnica.id_ficha != ficha.id_ficha,
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

    # -------------------------
    # Validaciones de dominio
    # -------------------------

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

    def _validar_caracteristicas_huevos(self, caracteristicas_contenido: dict | None) -> None:
        if not caracteristicas_contenido:
            raise HTTPException(
                status_code=400, detail="Las caracteristicas no pueden estar vacias"
            )
        requeridos = [
            "profundidad_cavidad_valor",
            "profundidad_cavidad_tolerancia",
            "profundidad_cavidad_unidad",
            "diametro_alveolo_valor",
            "diametro_alveolo_tolerancia",
            "diametro_alveolo_unidad",
        ]
        faltantes = [c for c in requeridos if c not in caracteristicas_contenido]
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail="Faltan campos requeridos en caracteristicas: " + ", ".join(faltantes),
            )

    def _validar_caracteristicas_otros(self, caracteristicas_contenido: dict | None) -> None:
        if not caracteristicas_contenido:
            raise HTTPException(
                status_code=400, detail="Las caracteristicas no pueden estar vacias"
            )
        requeridos = [
            "profundidad_pilar_valor",
            "profundidad_pilar_tolerancia",
            "profundidad_pilar_unidad",
            "diametro_alveolo_valor",
            "diametro_alveolo_tolerancia",
            "diametro_alveolo_unidad",
        ]
        faltantes = [c for c in requeridos if c not in caracteristicas_contenido]
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail="Faltan campos requeridos en caracteristicas: " + ", ".join(faltantes),
            )

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

    # -------------------------
    # Utilidades
    # -------------------------

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

    # -------------------------
    # Operaciones públicas
    # -------------------------

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

    async def crear(self, ficha_data: FichaTecnicaCreateSchema):
        """
        Crea una ficha técnica con integración completa al DSMS.
        La auditoría de creación y relación se maneja desde KItemService.
        """
        material = await self._validar_material(ficha_data.id_material_corporativo)

        if material.tipo_producto == "Huevos":
            self._validar_caracteristicas_huevos(ficha_data.caracteristicas_contenido)
        else:
            self._validar_caracteristicas_otros(ficha_data.caracteristicas_contenido)

        now = datetime.now()
        version_inicial = "1.0"
        estado_inicial = ESTADO_BORRADOR
        pais_iso = nombre_pais_a_iso(ficha_data.pais)

        await self._validar_codigo_material_local_unico(
            id_material=ficha_data.id_material_corporativo,
            pais=pais_iso,
            codigo_material_local=ficha_data.codigo_material_local,
        )

        codigo_ficha_local = self._generar_codigo_ficha(
            estado_ficha=estado_inicial,
            codigo_material_local=ficha_data.codigo_material_local,
            pais=pais_iso,
            codigo_version=version_inicial,
        )

        # PASO 1: Crear kitem base (auditoría de CREACION automática)
        kitem = await self.kitem_service.crear_kitem(
            KItemCreateSchema(
                ktype=KTYPE_FICHA_TECNICA,
                nombre=f"Ficha Tecnica - {ficha_data.codigo_material_local} ({pais_iso})",
                descripcion=f"Ficha tecnica v{version_inicial} para material {ficha_data.codigo_material_local} en {pais_iso}",
                estado=estado_inicial,
                metadata_extra={
                    "codigo_ficha_local": codigo_ficha_local,
                    "pais": pais_iso,
                    "version": version_inicial,
                },
                usuario_creador=ficha_data.usuario_creador,
            )
        )

        # PASO 2: Crear la ficha técnica
        ficha = FichaTecnica(
            id_ficha=kitem.id,
            id_material_corporativo=ficha_data.id_material_corporativo,
            codigo_ficha_local=codigo_ficha_local,
            codigo_material_local=ficha_data.codigo_material_local,
            codigo_version=version_inicial,
            usuario_creador=ficha_data.usuario_creador,
            usuario_ultima_actualizacion=ficha_data.usuario_creador,
            estado_ficha=estado_inicial,
            fecha_registro=now,
            fecha_actualizacion=now,
            pais=pais_iso,
            caracteristicas=ficha_data.caracteristicas,
            caracteristicas_contenido=ficha_data.caracteristicas_contenido,
            empaque_estiba=ficha_data.empaque_estiba,
            microbiologia=ficha_data.microbiologia,
            manejo_disposicion=ficha_data.manejo_disposicion,
        )
        self.db_session.add(ficha)

        # PASO 3: Relación "pertenece_a" (auditoría de RELACION_CREADA automática)
        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_data.id_material_corporativo,
                tipo_relacion=REL_PERTENECE_A,
                etiqueta=f"Ficha {codigo_ficha_local} pertenece a material {ficha_data.codigo_material_local}",
                usuario_creador=ficha_data.usuario_creador,
            )
        )

        await self.db_session.commit()
        await self.db_session.refresh(ficha)
        return ficha

    async def buscar_ficha(
        self,
        pais: str | None = None,
        estado_ficha: str | None = None,
        tipo_producto: str | None = None,
    ) -> list[FichaTecnicaWithMaterialSchema]:
        query = select(FichaTecnica, MaterialComercial).join(MaterialComercial)

        conditions = []
        if pais:
            conditions.append(FichaTecnica.pais == pais)
        if estado_ficha:
            conditions.append(FichaTecnica.estado_ficha == estado_ficha)
        if tipo_producto:
            conditions.append(MaterialComercial.tipo_producto == tipo_producto)
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

        ficha.estado_ficha = nuevo_estado
        ficha.usuario_ultima_actualizacion = usuario_actualizacion
        ficha.fecha_actualizacion = datetime.now()
        self.db_session.add(ficha)

        # Sincronizar estado en kitem base (auditoría de CAMBIO_ESTADO automática)
        await self.kitem_service.actualizar_estado_kitem(
            kitem_id=ficha.id_ficha,
            nuevo_estado=nuevo_estado,
            usuario=usuario_actualizacion,
        )

        # Auditoría adicional a nivel de ficha con detalles específicos
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

        await self.db_session.commit()
        await self.db_session.refresh(ficha)
        return ficha

    async def crear_nueva_version(self, id_ficha: UUID, usuario: str):
        """
        Crea nueva versión con trazabilidad completa:
        - Auditoría de NUEVA_VERSION en la ficha origen
        - Auditoría de CREACION en la nueva ficha (automática desde KItemService)
        - Relación "se_deriva_de" en el grafo (automática desde KItemService)
        """
        ficha_origen = await self.obtener(id_ficha)

        nueva_version = self._incrementar_version_simple(ficha_origen.codigo_version)
        now = datetime.now()
        estado_inicial = ESTADO_BORRADOR

        codigo_ficha_local = self._generar_codigo_ficha(
            estado_ficha=estado_inicial,
            codigo_material_local=ficha_origen.codigo_material_local,
            pais=ficha_origen.pais,
            codigo_version=nueva_version,
        )

        # PASO 1: Crear kitem base (auditoría de CREACION automática)
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

        # PASO 2: Crear la nueva ficha
        nueva_ficha = FichaTecnica(
            id_ficha=kitem.id,
            id_material_corporativo=ficha_origen.id_material_corporativo,
            codigo_ficha_local=codigo_ficha_local,
            codigo_material_local=ficha_origen.codigo_material_local,
            codigo_version=nueva_version,
            usuario_creador=usuario,
            usuario_ultima_actualizacion=usuario,
            estado_ficha=estado_inicial,
            fecha_registro=now,
            fecha_actualizacion=now,
            pais=ficha_origen.pais,
            caracteristicas=ficha_origen.caracteristicas,
            caracteristicas_contenido=ficha_origen.caracteristicas_contenido,
            empaque_estiba=ficha_origen.empaque_estiba,
            microbiologia=ficha_origen.microbiologia,
            manejo_disposicion=ficha_origen.manejo_disposicion,
        )
        self.db_session.add(nueva_ficha)

        # PASO 3: Relación "se_deriva_de" (auditoría de RELACION_CREADA automática)
        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_origen.id_ficha,
                tipo_relacion=REL_SE_DERIVA_DE,
                etiqueta=f"v{nueva_version} se deriva de v{ficha_origen.codigo_version}",
                usuario_creador=usuario,
            )
        )

        # PASO 4: Relación "pertenece_a" con el material
        await self.kitem_service.crear_relacion(
            KItemRelacionCreateSchema(
                source_id=kitem.id,
                target_id=ficha_origen.id_material_corporativo,
                tipo_relacion=REL_PERTENECE_A,
                etiqueta=f"Ficha {codigo_ficha_local} pertenece a material {ficha_origen.codigo_material_local}",
                usuario_creador=usuario,
            )
        )

        # Auditoría: registrar NUEVA_VERSION en la ficha ORIGEN
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