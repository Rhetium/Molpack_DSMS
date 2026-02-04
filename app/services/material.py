from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.material import MaterialComercial
from app.schemas.material import MaterialCreateSchema

class MaterialService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def listar(self):
        result = await self.db_session.execute(select(MaterialComercial))
        return result.scalars().all()
    
    async def obtener(self, id_material: UUID):
        result = await self.db_session.execute(
            select(MaterialComercial).where(MaterialComercial.id_material_corporativo == id_material)
        )
        material = result.scalars().first()
        if not material:
            raise HTTPException(status_code=404, detail="Material comercial no encontrado")
        return material
        
    async def crear(self, material_data: MaterialCreateSchema):
        now = datetime.now()

        material = MaterialComercial(
            nombre_corporativo=material_data.nombre_corporativo,
            contenido=material_data.contenido,
            categoria=material_data.categoria,
            material_base=material_data.material_base,
            capacidad_nominal=material_data.capacidad_nominal,
            color_base=material_data.color_base,
            tipo_producto=material_data.tipo_producto,
            estado_material="Activo",
            fecha_creacion=now,
            fecha_actualizacion=now,
        )

        self.db_session.add(material)
        await self.db_session.commit()
        await self.db_session.refresh(material)
        return material