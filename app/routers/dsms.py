"""
Router del Grafo de Conocimiento (Knowledge Graph).

Expone la API para explorar y gestionar el dataspace:
- Listar y consultar k-items
- Crear y consultar relaciones semánticas
- Explorar el grafo de un k-item (sus conexiones)

Equivale a la funcionalidad de "Data Exploration" del paper DSMS (Sección 2.3.4).
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.kitem_service import KItemService
from app.schemas.kitem import KItemSchema, KItemLiteSchema
from app.schemas.kitem_relacion import (
    KItemRelacionCreateSchema,
    KItemRelacionSchema,
    KItemRelacionDetalleSchema,
)

router = APIRouter(prefix="/dsms", tags=["dataspace"])


def get_kitem_service(
    session: AsyncSession = Depends(get_session),
) -> KItemService:
    return KItemService(db_session=session)


# ========================
# K-Items
# ========================

@router.get("/kitems", response_model=List[KItemSchema])
async def listar_kitems(
    ktype: str | None = None,
    estado: str | None = None,
    service: KItemService = Depends(get_kitem_service),
):
    """Lista todos los k-items del dataspace con filtros opcionales."""
    return await service.listar_kitems(ktype=ktype, estado=estado)


@router.get("/kitems/{kitem_id}", response_model=KItemSchema)
async def obtener_kitem(
    kitem_id: UUID,
    service: KItemService = Depends(get_kitem_service),
):
    """Obtiene un k-item por su UUID."""
    return await service.obtener_kitem(kitem_id)


@router.get("/kitems/{kitem_id}/grafo")
async def obtener_grafo_kitem(
    kitem_id: UUID,
    service: KItemService = Depends(get_kitem_service),
):
    """
    Devuelve el grafo de un k-item: el nodo central con todas sus
    relaciones y los k-items conectados.
    Implementa la exploración de grafo del DSMS.
    """
    return await service.obtener_grafo_kitem(kitem_id)


# ========================
# Relaciones Semánticas
# ========================

@router.post("/relaciones", response_model=KItemRelacionSchema, status_code=201)
async def crear_relacion(
    data: KItemRelacionCreateSchema,
    service: KItemService = Depends(get_kitem_service),
):
    """Crea una relación semántica entre dos k-items del dataspace."""
    return await service.crear_relacion(data)


@router.get(
    "/kitems/{kitem_id}/relaciones",
    response_model=List[KItemRelacionDetalleSchema],
)
async def obtener_relaciones(
    kitem_id: UUID,
    tipo_relacion: str | None = None,
    direccion: str = "ambas",
    service: KItemService = Depends(get_kitem_service),
):
    """
    Obtiene las relaciones de un k-item.
    - direccion: 'salientes', 'entrantes', o 'ambas'
    - tipo_relacion: filtrar por tipo (ej: 'pertenece_a', 'se_deriva_de')
    """
    relaciones = await service.obtener_relaciones_de_kitem(
        kitem_id=kitem_id,
        tipo_relacion=tipo_relacion,
        direccion=direccion,
    )
    # Convertir a schema con detalle
    resultado = []
    for rel in relaciones:
        resultado.append(
            KItemRelacionDetalleSchema(
                id=rel.id,
                tipo_relacion=rel.tipo_relacion,
                etiqueta=rel.etiqueta,
                metadata=rel.metadata,
                source=KItemLiteSchema.model_validate(rel.source),
                target=KItemLiteSchema.model_validate(rel.target),
                fecha_creacion=rel.fecha_creacion,
            )
        )
    return resultado


@router.delete("/relaciones/{relacion_id}", status_code=204)
async def eliminar_relacion(
    relacion_id: UUID,
    service: KItemService = Depends(get_kitem_service),
):
    """Elimina una relación semántica del grafo."""
    await service.eliminar_relacion(relacion_id)