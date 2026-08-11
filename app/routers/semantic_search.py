from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.security import get_usuario_actual, get_usuario_nombre
from app.services.semantic_search_service import BusquedaSemanticaService
from app.schemas.semantic_search import (
    BusquedaSemanticaRequest,
    BusquedaSemanticaResponse,
    DeteccionDuplicadosRequest,
    DeteccionDuplicadosResponse,
    ReindexacionMasivaRequest,
    ReindexacionResponse,
    EstadisticasEmbeddingResponse,
    ResultadoBusquedaSchema,
    KItemBusquedaSchema,
)

router = APIRouter(
    prefix="/dsms/semantica",
    tags=["búsqueda semántica"],
    dependencies=[Depends(get_usuario_actual)],
)


def get_busqueda_service(
    session: AsyncSession = Depends(get_session),
) -> BusquedaSemanticaService:
    return BusquedaSemanticaService(db_session=session)


@router.post(
    "/buscar",
    response_model=BusquedaSemanticaResponse,
    summary="Búsqueda semántica por texto libre",
    description=(
        "Encuentra k-items del dataspace semánticamente similares al texto de consulta. "
        "Usa embeddings vectoriales y similitud coseno via pgvector. "
        "Permite filtrar por ktype y estado."
    ),
)
async def buscar_semanticamente(
    request: BusquedaSemanticaRequest,
    service: BusquedaSemanticaService = Depends(get_busqueda_service),
):
    resultados_raw = await service.buscar_por_texto(
        texto_consulta=request.texto,
        ktype=request.ktype,
        estado=request.estado,
        limite=request.limite,
        umbral_similitud=request.umbral_similitud,
        filtro_texto=request.filtro_texto,
    )

    resultados = [
        ResultadoBusquedaSchema(
            kitem=KItemBusquedaSchema.model_validate(r["kitem"]),
            similitud=r["similitud"],
        )
        for r in resultados_raw
    ]

    filtros = {}
    if request.ktype:
        filtros["ktype"] = request.ktype
    if request.estado:
        filtros["estado"] = request.estado
    if request.umbral_similitud > 0:
        filtros["umbral_similitud"] = request.umbral_similitud
    if request.filtro_texto:
        filtros["filtro_texto"] = request.filtro_texto

    return BusquedaSemanticaResponse(
        consulta=request.texto,
        total_resultados=len(resultados),
        resultados=resultados,
        filtros_aplicados=filtros,
    )



@router.post(
    "/duplicados",
    response_model=DeteccionDuplicadosResponse,
    summary="Detectar posibles duplicados antes de crear un k-item",
    description=(
        "Verifica si ya existe un k-item similar al que se pretende crear. "
        "Diseñado para invocarse desde el formulario de registro guiado "
        "del frontend, previniendo redundancia en el dataspace."
    ),
)
async def detectar_duplicados(
    request: DeteccionDuplicadosRequest,
    service: BusquedaSemanticaService = Depends(get_busqueda_service),
):
    resultados_raw = await service.detectar_duplicados(
        nombre=request.nombre,
        descripcion=request.descripcion,
        ktype=request.ktype,
        campos_adicionales=request.campos_adicionales,
        umbral_duplicado=request.umbral_duplicado,
        limite=request.limite,
    )

    duplicados = [
        ResultadoBusquedaSchema(
            kitem=KItemBusquedaSchema.model_validate(r["kitem"]),
            similitud=r["similitud"],
        )
        for r in resultados_raw
    ]

    hay_duplicados = len(duplicados) > 0

    if hay_duplicados:
        mejor_similitud = duplicados[0].similitud
        if mejor_similitud >= 0.95:
            recomendacion = (
                "⚠️ ALTA PROBABILIDAD DE DUPLICADO: Ya existe un k-item "
                "prácticamente idéntico. Revise el existente antes de crear uno nuevo."
            )
        elif mejor_similitud >= 0.85:
            recomendacion = (
                "⚡ POSIBLE DUPLICADO: Se encontraron k-items muy similares. "
                "Verifique si alguno corresponde al que desea crear."
            )
        else:
            recomendacion = (
                "ℹ️ SIMILITUD MODERADA: Se encontraron k-items relacionados. "
                "Puede proceder con la creación si confirma que es diferente."
            )
    else:
        recomendacion = (
            "✅ SIN DUPLICADOS: No se encontraron k-items similares. "
            "Puede proceder con la creación."
        )

    return DeteccionDuplicadosResponse(
        nombre_candidato=request.nombre,
        hay_duplicados=hay_duplicados,
        total_duplicados=len(duplicados),
        umbral_utilizado=request.umbral_duplicado,
        duplicados=duplicados,
        recomendacion=recomendacion,
    )



@router.get(
    "/similares/{kitem_id}",
    response_model=List[ResultadoBusquedaSchema],
    summary="Encontrar k-items similares a uno existente",
    description=(
        "Busca k-items semánticamente similares a un k-item de referencia. "
        "Útil para exploración del dataspace y descubrimiento de relaciones implícitas."
    ),
)
async def buscar_similares(
    kitem_id: UUID,
    ktype: str | None = None,
    limite: int = 10,
    umbral_similitud: float = 0.0,
    service: BusquedaSemanticaService = Depends(get_busqueda_service),
):
    resultados_raw = await service.buscar_similares_a_kitem(
        kitem_id=kitem_id,
        ktype=ktype,
        limite=limite,
        umbral_similitud=umbral_similitud,
    )

    return [
        ResultadoBusquedaSchema(
            kitem=KItemBusquedaSchema.model_validate(r["kitem"]),
            similitud=r["similitud"],
        )
        for r in resultados_raw
    ]



@router.post(
    "/reindexar/{kitem_id}",
    response_model=dict,
    summary="Regenerar embedding de un k-item",
    description="Regenera el embedding vectorial de un k-item específico.",
)
async def reindexar_kitem(
    kitem_id: UUID,
    service: BusquedaSemanticaService = Depends(get_busqueda_service),
    usuario: str = Depends(get_usuario_nombre),
):
    kitem = await service.reindexar_kitem(
        kitem_id=kitem_id,
        usuario=usuario,
    )
    return {
        "mensaje": f"Embedding regenerado para '{kitem.nombre}'",
        "kitem_id": str(kitem.id),
        "ktype": kitem.ktype,
    }


@router.post(
    "/reindexar",
    response_model=ReindexacionResponse,
    summary="Reindexación masiva de embeddings",
    description=(
        "Genera embeddings para múltiples k-items. "
        "Útil para migración inicial o reindexación después de cambiar modelo."
    ),
)
async def reindexar_masivo(
    request: ReindexacionMasivaRequest,
    service: BusquedaSemanticaService = Depends(get_busqueda_service),
    usuario: str = Depends(get_usuario_nombre),
):
    resultado = await service.reindexar_masivo(
        ktype=request.ktype,
        solo_sin_embedding=request.solo_sin_embedding,
        batch_size=request.batch_size,
        usuario=usuario,
    )
    return ReindexacionResponse(**resultado)



@router.get(
    "/estadisticas",
    response_model=EstadisticasEmbeddingResponse,
    summary="Estadísticas de embeddings del dataspace",
    description=(
        "Retorna el estado de cobertura de embeddings: total de k-items, "
        "cuántos tienen embedding, desglose por ktype."
    ),
)
async def obtener_estadisticas(
    service: BusquedaSemanticaService = Depends(get_busqueda_service),
):
    return await service.obtener_estadisticas()