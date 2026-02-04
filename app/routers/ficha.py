from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.fichas_services import FichaService
from app.schemas.ficha import FichaTecnicaSchema, FichaTecnicaCreateSchema, FichaTecnicaWithMaterialSchema

router = APIRouter(prefix="/ficha", tags=["ficha"])

def get_ficha_service(
    session: AsyncSession = Depends(get_session),
) -> FichaService:
    return FichaService(db_session=session)

@router.get("", response_model=List[FichaTecnicaSchema])
async def listar_fichas(
    service: FichaService = Depends(get_ficha_service),
):
    return await service.listar()

@router.post("", response_model=FichaTecnicaSchema, status_code=201)
async def crear_ficha(
    ficha_data: FichaTecnicaCreateSchema,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.crear(ficha_data)

@router.get("/buscar", response_model=List[FichaTecnicaWithMaterialSchema])
async def buscar_fichas(
    pais: str | None = None,
    estado_ficha: str | None = None,
    tipo_producto: str | None = None,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.buscar_ficha(pais=pais, estado_ficha=estado_ficha, tipo_producto=tipo_producto)

@router.get("/{id_ficha}", response_model=FichaTecnicaSchema)
async def obtener_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.obtener(id_ficha)