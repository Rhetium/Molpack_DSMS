from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_session
from app.models.material import MaterialComercial
from app.schemas.material import MaterialComercialSchema

router = APIRouter(prefix="/material", tags=["material"])

@router.get("", response_model=List[MaterialComercialSchema])
async def listar_material(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(MaterialComercial))
    material = result.scalars().all()
    return material
