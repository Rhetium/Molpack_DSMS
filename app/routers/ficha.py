from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_session
from app.models.ficha import FichaTecnica
from app.schemas.ficha import FichaTecnicaSchema

router = APIRouter(prefix="/ficha", tags=["ficha"])

@router.get("", response_model=List[FichaTecnicaSchema])
async def listar_fichas(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(FichaTecnica))
    fichas = result.scalars().all()
    return fichas

@router.get("/{id_ficha}", response_model=FichaTecnicaSchema)
async def obtener_ficha(
    id_ficha: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
    )
    ficha = result.scalars().first()
    if ficha is None:
        raise HTTPException(status_code=404, detail="Ficha técnica no encontrada")
    return ficha