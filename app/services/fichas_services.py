from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
from app.schemas.ficha import FichaTecnicaCreateSchema, FichaTecnicaWithMaterialSchema
from app.schemas.material import MaterialLiteSchema


class FichaService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def listar(self):
        result = await self.db_session.execute(select(FichaTecnica))
        return result.scalars().all()
    
    async def obtener(self,id_ficha: UUID):
        result = await self.db_session.execute(
            select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
        )
        ficha = result.scalars().first()
        if not ficha:
            raise HTTPException(status_code=404, detail="Ficha técnica no encontrada")
        return ficha
    
    async def _validar_material(self, id_material: UUID):
        result = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == id_material
            )
        ) 
        material =  result.scalars().first()
        if not material:
            raise HTTPException(status_code=400, detail="Material comercial no encontrado")
        return material
    
    def _validar_caracteristicas_huevos(self, caracteristicas_contenido: dict | None):
        if not caracteristicas_contenido:
            raise HTTPException(status_code=400, detail="Las características no pueden estar vacías")
        requeridos = ["profundidad_cavidad_valor", "profundidad_cavidad_tolerancia", "profundidad_cavidad_unidad", "diametro_alveolo_valor", "diametro_alveolo_tolerancia", "diametro_alveolo_unidad"]
        faltantes = [campo for campo in requeridos if campo not in caracteristicas_contenido]
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan campos requeridos en características: {', '.join(faltantes)}"
            )
        
    def _validar_caracteristicas_otros(self, caracteristicas_contenido: dict | None):
        if not caracteristicas_contenido:
            raise HTTPException(status_code=400, detail="Las características no pueden estar vacías")
        requeridos = ["profundidad_pilar_valor", "profundidad_pilar_tolerancia", "profundidad_pilar_unidad", "diametro_alveolo_valor", "diametro_alveolo_tolerancia", "diametro_alveolo_unidad"]
        faltantes = [campo for campo in requeridos if campo not in caracteristicas_contenido]
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan campos requeridos en características: {', '.join(faltantes)}"
            )
        
    async def crear(self, ficha_data: FichaTecnicaCreateSchema):
        material = await self._validar_material(ficha_data.id_material_corporativo)

        if material.tipo_producto == "Huevos":
            self._validar_caracteristicas_huevos(ficha_data.caracteristicas_contenido)
        else:
            self._validar_caracteristicas_otros(ficha_data.caracteristicas_contenido)

        now = datetime.now()

        ficha = FichaTecnica(
            id_material_corporativo=ficha_data.id_material_corporativo,
            codigo_ficha_local=ficha_data.codigo_ficha_local,
            codigo_material_local=ficha_data.codigo_material_local,
            codigo_version="1.0",
            usuario_creador=ficha_data.usuario_creador,
            usuario_ultima_actualizacion=ficha_data.usuario_creador,
            estado_ficha="Preliminar",
            fecha_registro=now,
            fecha_actualizacion=now,
            pais=ficha_data.pais,
            caracteristicas=ficha_data.caracteristicas,
            caracteristicas_contenido=ficha_data.caracteristicas_contenido,
            empaque_estiba=ficha_data.empaque_estiba,
            microbiologia=ficha_data.microbiologia,
            manejo_disposicion=ficha_data.manejo_disposicion,
        )

        self.db_session.add(ficha)
        await self.db_session.commit()
        await self.db_session.refresh(ficha)
        return ficha

    async def buscar_ficha(
        self,
        pais: str | None = None,
        estado_ficha: str | None = None,
        tipo_producto: str | None = None,
    ):
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
                    **ficha.__dict__,
                    material=MaterialLiteSchema.model_validate(material),
                )
            )

        return fichas