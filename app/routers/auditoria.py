from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.security import get_usuario_actual
from app.services.auditoria_service import AuditoriaService
from app.schemas.kitem_auditoria import AuditoriaSchema, AuditoriaResumenSchema

router = APIRouter(
    prefix="/dsms/auditoria",
    tags=["auditoria"],
    dependencies=[Depends(get_usuario_actual)],
)


def get_auditoria_service(
    session: AsyncSession = Depends(get_session),
) -> AuditoriaService:
    return AuditoriaService(db_session=session)


@router.get("/actividad", response_model=List[AuditoriaResumenSchema])
async def actividad_reciente(
    limite: int = 50,
    offset: int = 0,
    ktype: str | None = None,
    accion: str | None = None,
    usuario: str | None = None,
    categoria: str | None = None,
    service: AuditoriaService = Depends(get_auditoria_service),
):
    return await service.obtener_actividad_reciente(
        limite=limite,
        offset=offset,
        ktype=ktype,
        accion=accion,
        usuario=usuario,
        categoria=categoria,
    )


@router.get("/kitem/{kitem_id}", response_model=List[AuditoriaSchema])
async def historial_kitem(
    kitem_id: UUID,
    accion: str | None = None,
    service: AuditoriaService = Depends(get_auditoria_service),
):
    return await service.obtener_historial(
        kitem_id=kitem_id,
        accion=accion,
    )