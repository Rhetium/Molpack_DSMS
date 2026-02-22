"""
Router de Auditoría — API de trazabilidad del Dataspace.

Permite consultar:
- Historial completo de un k-item específico
- Actividad reciente del dataspace con filtros
- Eventos por tipo de acción, usuario o k-type
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.auditoria_service import AuditoriaService
from app.schemas.kitem_auditoria import AuditoriaSchema, AuditoriaResumenSchema

router = APIRouter(prefix="/dsms/auditoria", tags=["auditoria"])


def get_auditoria_service(
    session: AsyncSession = Depends(get_session),
) -> AuditoriaService:
    return AuditoriaService(db_session=session)


@router.get("/actividad", response_model=List[AuditoriaResumenSchema])
async def actividad_reciente(
    limite: int = 50,
    ktype: str | None = None,
    accion: str | None = None,
    usuario: str | None = None,
    service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Actividad reciente del dataspace.
    Filtros opcionales: ktype, accion, usuario.
    """
    return await service.obtener_actividad_reciente(
        limite=limite,
        ktype=ktype,
        accion=accion,
        usuario=usuario,
    )


@router.get("/kitem/{kitem_id}", response_model=List[AuditoriaSchema])
async def historial_kitem(
    kitem_id: UUID,
    accion: str | None = None,
    service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Historial completo de un k-item: todas las acciones que lo afectaron,
    en orden cronológico inverso (más reciente primero).
    """
    return await service.obtener_historial(
        kitem_id=kitem_id,
        accion=accion,
    )