from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.anomalia_service import AnomaliaService
from app.services.ml_anomalia_service import MLAnomaliaService
from app.schemas.anomalia import (
    AnalizarFichaRequest,
    AnalizarMaterialRequest,
    ResultadoAnalisis,
    ResolverAnomaliaRequest,
    AnomaliaRegistroSchema,
    AnomaliaListResponse,
)
from app.core.anomalia_constant import ESTADOS_RESOLUCION_VALIDOS
from app.core.security import get_usuario_actual, get_usuario_nombre

router = APIRouter(
    prefix="/anomalias",
    tags=["Anomalías"],
    dependencies=[Depends(get_usuario_actual)],
)


def get_anomalia_service(session: AsyncSession = Depends(get_session)) -> AnomaliaService:
    return AnomaliaService(db_session=session)


@router.get("/debug/{id_ficha}")
async def debug_detectores(
    id_ficha: UUID,
    service: AnomaliaService = Depends(get_anomalia_service),
):
    return await service.analizar_debug(id_ficha)


@router.post("/entrenar")
async def entrenar_modelos_ml(
    session: AsyncSession = Depends(get_session),
):
    svc = MLAnomaliaService(db_session=session)
    return await svc.entrenar_modelos()


@router.post("/analizar/ficha", response_model=ResultadoAnalisis)
async def analizar_ficha(
    request: AnalizarFichaRequest,
    service: AnomaliaService = Depends(get_anomalia_service),
    usuario: str = Depends(get_usuario_nombre),
):
    return await service.analizar_ficha(
        id_ficha=request.id_ficha,
        usuario=usuario,
    )


@router.post("/analizar/material", response_model=ResultadoAnalisis)
async def analizar_material(
    request: AnalizarMaterialRequest,
    service: AnomaliaService = Depends(get_anomalia_service),
    usuario: str = Depends(get_usuario_nombre),
):
    return await service.analizar_material(
        id_material=request.id_material,
        usuario=usuario,
    )


@router.get("/", response_model=AnomaliaListResponse)
async def listar_anomalias(
    ktype: str | None = None,
    tipo_anomalia: str | None = None,
    severidad: str | None = None,
    estado: str | None = None,
    limite: int = 50,
    service: AnomaliaService = Depends(get_anomalia_service),
):
    registros = await service.listar_anomalias(
        ktype=ktype,
        tipo_anomalia=tipo_anomalia,
        severidad=severidad,
        estado=estado,
        limite=limite,
    )

    filtros = {}
    if ktype:
        filtros["ktype"] = ktype
    if tipo_anomalia:
        filtros["tipo_anomalia"] = tipo_anomalia
    if severidad:
        filtros["severidad"] = severidad
    if estado:
        filtros["estado"] = estado

    return AnomaliaListResponse(
        total=len(registros),
        anomalias=[
            AnomaliaRegistroSchema.model_validate(r) for r in registros
        ],
        filtros_aplicados=filtros if filtros else None,
    )


@router.get("/kitem/{kitem_id}", response_model=AnomaliaListResponse)
async def anomalias_por_kitem(
    kitem_id: UUID,
    estado: str | None = None,
    service: AnomaliaService = Depends(get_anomalia_service),
):
    registros = await service.listar_anomalias(
        kitem_id=kitem_id,
        estado=estado,
    )
    return AnomaliaListResponse(
        total=len(registros),
        anomalias=[
            AnomaliaRegistroSchema.model_validate(r) for r in registros
        ],
    )


@router.patch("/{id_anomalia}/resolver", response_model=AnomaliaRegistroSchema)
async def resolver_anomalia(
    id_anomalia: UUID,
    request: ResolverAnomaliaRequest,
    service: AnomaliaService = Depends(get_anomalia_service),
    usuario: str = Depends(get_usuario_nombre),
):
    if request.estado not in ESTADOS_RESOLUCION_VALIDOS:
        from fastapi import HTTPException
        raise HTTPException(
            400,
            f"Estado inválido. Valores permitidos: "
            f"{', '.join(ESTADOS_RESOLUCION_VALIDOS)}",
        )

    registro = await service.resolver_anomalia(
        id_anomalia=id_anomalia,
        nuevo_estado=request.estado,
        usuario=usuario,
        nota=request.nota,
    )
    await service.db_session.commit()
    await service.db_session.refresh(registro)
    return AnomaliaRegistroSchema.model_validate(registro)
