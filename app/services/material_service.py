"""
Servicio MaterialComercial — Refactorizado para DSMS.

Al crear un material, se crea automáticamente su kitem base
en la tabla kitem, asegurando que todo material es un k-item
del dataspace y puede participar en el grafo de conocimiento.
"""

from uuid import UUID
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialComercial
from app.schemas.material import MaterialCreateSchema
from app.schemas.kitem import KItemCreateSchema
from app.services.kitem_service import KItemService
from app.core.dsms_constants import KTYPE_MATERIAL_COMERCIAL


class MaterialService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.kitem_service = KItemService(db_session)

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

    async def crear(self, material_data: MaterialCreateSchema):
        """
        Crea un material comercial con integración al DSMS:
        1. Crea el kitem base
        2. Crea el material comercial con el mismo UUID
        """
        now = datetime.now()

        # --- PASO 1: Crear el kitem base ---
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

        # --- PASO 2: Crear el material con el mismo UUID ---
        material = MaterialComercial(
            id_material_corporativo=kitem.id,  # MISMO UUID que el kitem
            nombre_corporativo=material_data.nombre_corporativo,
            contenido=material_data.contenido,
            categoria=material_data.categoria,
            material_base=material_data.material_base,
            capacidad_nominal=material_data.capacidad_nominal,
            color_base=material_data.color_base,
            tipo_producto=material_data.tipo_producto,
            estado_material=material_data.estado_material,
            fecha_creacion=now,
            fecha_actualizacion=now,
        )

        self.db_session.add(material)
        await self.db_session.commit()
        await self.db_session.refresh(material)
        return material