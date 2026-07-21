from uuid import UUID
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialComercial
from app.schemas.material import MaterialCreateSchema
from app.schemas.kitem import KItemCreateSchema
from app.services.kitem_service import KItemService
from app.services.semantic_search_service import BusquedaSemanticaService
from app.services.anomalia_service import AnomaliaService

from app.core.dsms_constants import (
    KTYPE_MATERIAL_COMERCIAL,
    ACCION_MODIFICACION,
)


class MaterialService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.kitem_service = KItemService(db_session)
        self.busqueda = BusquedaSemanticaService(db_session)
        self.anomalia_service = AnomaliaService(db_session)

    def _campos_embedding(self, material: MaterialComercial) -> dict:
        return {
            "categoria": material.categoria,
            "tipo_producto": material.tipo_producto,
            "contenido": material.contenido,
            "material_base": material.material_base,
            "sector": material.sector,
            "caracteristica": material.caracteristica,
        }

    async def listar(self) -> list[MaterialComercial]:
        result = await self.db_session.execute(select(MaterialComercial))
        return result.scalars().all()

    async def obtener(self, id_material: UUID) -> MaterialComercial:
        result = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == id_material
            )
        )
        material = result.scalars().first()
        if not material:
            raise HTTPException(
                status_code=404, detail="Material comercial no encontrado"
            )
        return material

    async def crear(self, material_data: MaterialCreateSchema) -> MaterialComercial:
        kitem = await self.kitem_service.crear_kitem(
            KItemCreateSchema(
                ktype=KTYPE_MATERIAL_COMERCIAL,
                nombre=material_data.nombre_corporativo,
                descripcion=(
                    f"Material comercial: {material_data.nombre_corporativo} "
                    f"({material_data.categoria or 'sin categoría'}) - "
                    f"{material_data.tipo_producto or 'sin tipo'}"
                ),
                estado=material_data.estado_material,
                metadata_extra={
                    "categoria": material_data.categoria,
                    "tipo_producto": material_data.tipo_producto,
                    "material_base": material_data.material_base,
                },
                usuario_creador=material_data.usuario_creador,
            )
        )

        material = MaterialComercial(
            id_material_corporativo=kitem.id,
            nombre_corporativo=material_data.nombre_corporativo,
            contenido=material_data.contenido,
            categoria=material_data.categoria,
            sector=material_data.sector,
            caracteristica=material_data.caracteristica,
            material_base=material_data.material_base,
            capacidad_nominal=material_data.capacidad_nominal,
            tipo_producto=material_data.tipo_producto,
        )
        # estado y fechas viven en kitem (única fuente de verdad)
        material.kitem = kitem
        self.db_session.add(material)
        await self.db_session.flush()

        await self.busqueda.asignar_embedding(
            kitem_id=material.id_material_corporativo,
            campos_adicionales=self._campos_embedding(material),
            usuario=material_data.usuario_creador,
        )

        await self.db_session.commit()
        await self.db_session.refresh(material)

        try:
            resultado_anomalias = await self.anomalia_service.analizar_material(
                id_material=material.id_material_corporativo,
                usuario=material_data.usuario_creador,
                contexto="creacion",
            )
            await self.db_session.commit()
            material._anomalias = resultado_anomalias.anomalias
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Error en analisis de anomalías para material {material.id_material_corporativo}: {e}"
            )
            material._anomalias = []

        return material

    async def actualizar(
        self,
        id_material: UUID,
        datos_actualizacion: dict,
        usuario: str,
    ) -> MaterialComercial:
        material = await self.obtener(id_material)
        now = datetime.now()

        campos_validos = {
            "nombre_corporativo",
            "contenido",
            "categoria",
            "sector",
            "caracteristica",
            "material_base",
            "capacidad_nominal",
            "tipo_producto",
            "estado_material",
        }

        cambios = {}
        for campo, valor in datos_actualizacion.items():
            if campo in campos_validos and valor is not None:
                valor_anterior = getattr(material, campo)
                if valor_anterior != valor:
                    setattr(material, campo, valor)
                    cambios[campo] = {"anterior": valor_anterior, "nuevo": valor}

        if not cambios:
            return material

        material.fecha_actualizacion = now
        self.db_session.add(material)
        await self.db_session.flush()

        kitem = await self.kitem_service.obtener_kitem(id_material)
        kitem.usuario_ultima_actualizacion = usuario
        kitem.fecha_actualizacion = now

        if "nombre_corporativo" in cambios:
            kitem.nombre = material.nombre_corporativo

        kitem.descripcion = (
            f"Material comercial: {material.nombre_corporativo} "
            f"({material.categoria or 'sin categoría'}) - "
            f"{material.tipo_producto or 'sin tipo'}"
        )

        kitem.metadata_extra = {
            "categoria": material.categoria,
            "tipo_producto": material.tipo_producto,
            "material_base": material.material_base,
        }

        self.db_session.add(kitem)
        await self.db_session.flush()

        await self.kitem_service.auditoria.registrar(
            kitem_id=id_material,
            ktype=KTYPE_MATERIAL_COMERCIAL,
            accion=ACCION_MODIFICACION,
            usuario=usuario,
            detalles={
                "campos_modificados": list(cambios.keys()),
                "cambios": cambios,
            },
        )

        await self.busqueda.asignar_embedding(
            kitem_id=id_material,
            campos_adicionales=self._campos_embedding(material),
            usuario=usuario,
        )

        await self.db_session.commit()
        await self.db_session.refresh(material)

        try:
            resultado_anomalias = await self.anomalia_service.analizar_material(
                id_material=material.id_material_corporativo,
                usuario=usuario,
                contexto="actualizacion",
            )
            await self.db_session.commit()
            material._anomalias = resultado_anomalias.anomalias
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Error en analisis de anomalías para material {material.id_material_corporativo}: {e}"
            )
            material._anomalias = []

        return material
