from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.fichas_services import FichaService
from app.schemas.ficha import (
    FichaTecnicaSchema,
    FichaTecnicaCreateSchema,
    FichaTecnicaWithMaterialSchema,
)

from app.core.dsms_constants import (
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
)

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
    return await service.buscar_ficha(
        pais=pais, estado_ficha=estado_ficha, tipo_producto=tipo_producto
    )


@router.get("/{id_ficha}", response_model=FichaTecnicaSchema)
async def obtener_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.obtener(id_ficha)


@router.post("/{id_ficha}/aprobar-inicial", response_model=FichaTecnicaSchema)
async def aprobar_inicial(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.cambiar_estado(
        id_ficha, ESTADO_PRELIMINAR, usuario_actualizacion="sistema"
    )


@router.post("/{id_ficha}/publicar", response_model=FichaTecnicaSchema)
async def publicar_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.cambiar_estado(
        id_ficha, ESTADO_VIGENTE, usuario_actualizacion="sistema"
    )


@router.post("/{id_ficha}/archivar", response_model=FichaTecnicaSchema)
async def archivar_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.cambiar_estado(
        id_ficha, ESTADO_OBSOLETO, usuario_actualizacion="sistema"
    )


@router.post("/{id_ficha}/nueva-version", response_model=FichaTecnicaSchema)
async def crear_nueva_version(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    """Crea una nueva versión de la ficha, registrando la relación
    'se_deriva_de' en el grafo de conocimiento del DSMS."""
    return await service.crear_nueva_version(id_ficha, usuario="sistema")