from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.fichas_services import FichaService
from app.schemas.ficha import (
    AnomaliaResumen,
    FichaTecnicaSchema,
    FichaTecnicaCreateSchema,
    FichaTecnicaWithMaterialSchema,
    FichaTecnicaUpdateSchema,
    FichaVersionSchema,
    CambioEstadoRequest,
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
    ficha = await service.crear(ficha_data)
    resultado = FichaTecnicaSchema.model_validate(ficha)
    if hasattr(ficha,'_anomalias') and ficha._anomalias:
        resultado.anomalias = [
            AnomaliaResumen(
                tipo_anomalia=a.tipo_anomalia,
                severidad=a.severidad,
                campo_afectado=a.campo_afectado,
                mensaje=a.mensaje,
            )
            for a in ficha._anomalias
        ]
    return resultado

@router.get("/buscar", response_model=List[FichaTecnicaWithMaterialSchema])
async def buscar_fichas(
    pais: str | None = None,
    estado_ficha: str | None = None,
    tipo_producto: str | None = None,
    texto: str | None = None,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.buscar_ficha(
        pais=pais, estado_ficha=estado_ficha,
        tipo_producto=tipo_producto, texto=texto,
    )


@router.get("/{id_ficha}", response_model=FichaTecnicaSchema)
async def obtener_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.obtener(id_ficha)


@router.get("/{id_ficha}/versiones", response_model=List[FichaVersionSchema])
async def listar_versiones_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    """Lista todas las versiones del linaje de la ficha (ordenadas por versión)."""
    return await service.listar_versiones(id_ficha)


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
    return await service.crear_nueva_version(id_ficha, usuario="sistema")

@router.patch("/{id_ficha}", response_model=FichaTecnicaSchema)
async def actualizar_ficha(
    id_ficha: UUID,
    datos: FichaTecnicaUpdateSchema,
    service: FichaService = Depends(get_ficha_service),
):
    datos_dict = datos.model_dump(exclude={"usuario_actualizacion"}, exclude_none=True)
    ficha = await service.actualizar(
        id_ficha=id_ficha,
        datos_actualizacion=datos_dict,
        usuario=datos.usuario_actualizacion,
    )
    resultado = FichaTecnicaSchema.model_validate(ficha)
    if hasattr(ficha, '_anomalias') and ficha._anomalias:
        resultado.anomalias = [
            AnomaliaResumen(
                tipo_anomalia=a.tipo_anomalia,
                severidad=a.severidad,
                campo_afectado=a.campo_afectado,
                mensaje=a.mensaje,
            )
            for a in ficha._anomalias
        ]
    return resultado


@router.patch("/{id_ficha}/estado", response_model=FichaTecnicaSchema)
async def cambiar_estado_ficha(
    id_ficha: UUID,
    request: CambioEstadoRequest,
    service: FichaService = Depends(get_ficha_service),
):
    return await service.cambiar_estado(
        id_ficha=id_ficha,
        nuevo_estado=request.nuevo_estado,
        usuario_actualizacion=request.usuario_actualizacion,
    )

@router.get("/{id_material}/rangos-tipicos")
async def obtener_rangos_tipicos(
    id_material: UUID,
    service: FichaService = Depends(get_ficha_service),
):
    """
    Calcula rangos típicos de características basándose en fichas
    existentes del mismo material. Retorna min, max, promedio
    y cantidad de fichas usadas para el cálculo.
    """
    return await service.calcular_rangos_tipicos(id_material)