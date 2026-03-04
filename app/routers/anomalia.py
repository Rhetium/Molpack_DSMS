"""
Router de Anomalías — Endpoints API para detección y gestión.

Endpoints:
- POST /anomalias/analizar/ficha     → Analizar ficha técnica
- POST /anomalias/analizar/material  → Analizar material comercial
- GET  /anomalias/                   → Listar anomalías históricas
- GET  /anomalias/{id}               → Obtener anomalía por ID
- GET  /anomalias/kitem/{kitem_id}   → Anomalías de un k-item
- PATCH /anomalias/{id}/resolver     → Resolver anomalía
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.anomalia_service import AnomaliaService
from app.schemas.anomalia import (
    AnalizarFichaRequest,
    AnalizarMaterialRequest,
    ResultadoAnalisis,
    ResolverAnomaliaRequest,
    AnomaliaRegistroSchema,
    AnomaliaListResponse,
)
from app.core.anomalia_constant import ESTADOS_RESOLUCION_VALIDOS

router = APIRouter(prefix="/anomalias", tags=["Anomalías"])


def get_anomalia_service(session: AsyncSession = Depends(get_session)) -> AnomaliaService:
    return AnomaliaService(db_session=session)


# ========================
# Análisis
# ========================

@router.post(
    "/analizar/ficha",
    response_model=ResultadoAnalisis,
    summary="Analizar ficha técnica en busca de anomalías",
    description=(
        "Ejecuta todos los detectores sobre una ficha técnica: "
        "valores atípicos, unidades inconsistentes, duplicados semánticos "
        "y clasificación cruzada. Las anomalías encontradas se persisten "
        "en el repositorio histórico."
    ),
)
async def analizar_ficha(
    request: AnalizarFichaRequest,
    service: AnomaliaService = Depends(get_anomalia_service),
):
    return await service.analizar_ficha(
        id_ficha=request.id_ficha,
        usuario=request.usuario,
    )


@router.post(
    "/analizar/material",
    response_model=ResultadoAnalisis,
    summary="Analizar material comercial en busca de anomalías",
    description=(
        "Ejecuta detectores de duplicados semánticos y clasificación "
        "cruzada sobre un material comercial."
    ),
)
async def analizar_material(
    request: AnalizarMaterialRequest,
    service: AnomaliaService = Depends(get_anomalia_service),
):
    return await service.analizar_material(
        id_material=request.id_material,
        usuario=request.usuario,
    )


# ========================
# Consulta de historial
# ========================

@router.get(
    "/",
    response_model=AnomaliaListResponse,
    summary="Listar anomalías históricas",
    description="Consulta el repositorio de anomalías con filtros opcionales.",
)
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


@router.get(
    "/kitem/{kitem_id}",
    response_model=AnomaliaListResponse,
    summary="Anomalías de un k-item específico",
)
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


# ========================
# Resolución
# ========================

@router.patch(
    "/{id_anomalia}/resolver",
    response_model=AnomaliaRegistroSchema,
    summary="Resolver una anomalía",
    description=(
        "Marca una anomalía como aceptada (el valor es correcto), "
        "descartada (falso positivo) o corregida (se modificó el registro)."
    ),
)
async def resolver_anomalia(
    id_anomalia: UUID,
    request: ResolverAnomaliaRequest,
    service: AnomaliaService = Depends(get_anomalia_service),
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
        usuario=request.usuario,
        nota=request.nota,
    )
    await service.db_session.commit()
    await service.db_session.refresh(registro)
    return AnomaliaRegistroSchema.model_validate(registro)