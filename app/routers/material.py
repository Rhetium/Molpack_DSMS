from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_session
from app.schemas.material import MaterialSchema, MaterialCreateSchema
from app.services.material import MaterialService

router = APIRouter(prefix="/material", tags=["material"])

def get_material_service(
    session: AsyncSession = Depends(get_session),
) -> MaterialService:
    return MaterialService(db_session=session)

@router.get("", response_model=List[MaterialSchema])
async def listar_materiales(
    service: MaterialService = Depends(get_material_service),
):
    return await service.listar()

@router.get("/{id_material}", response_model=MaterialSchema)
async def obtener_material(
    id_material: UUID,
    service: MaterialService = Depends(get_material_service),
):
    return await service.obtener(id_material)

@router.post("", response_model=MaterialSchema, status_code=201)
async def crear_material(
    material_data: MaterialCreateSchema,
    service: MaterialService = Depends(get_material_service),
):
    return await service.crear(material_data)