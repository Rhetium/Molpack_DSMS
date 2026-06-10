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


@router.get("/kitems", response_model=List[KItemSchema])
async def listar_kitems(
    ktype: str | None = None,
    estado: str | None = None,
    service: KItemService = Depends(get_kitem_service),
):
    return await service.listar_kitems(ktype=ktype, estado=estado)


@router.get("/kitems/{kitem_id}", response_model=KItemSchema)
async def obtener_kitem(
    kitem_id: UUID,
    service: KItemService = Depends(get_kitem_service),
):
    return await service.obtener_kitem(kitem_id)


@router.get("/kitems/{kitem_id}/grafo")
async def obtener_grafo_kitem(
    kitem_id: UUID,
    service: KItemService = Depends(get_kitem_service),
):
    return await service.obtener_grafo_kitem(kitem_id)


@router.post("/relaciones", response_model=KItemRelacionSchema, status_code=201)
async def crear_relacion(
    data: KItemRelacionCreateSchema,
    service: KItemService = Depends(get_kitem_service),
):
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
    relaciones = await service.obtener_relaciones_de_kitem(
        kitem_id=kitem_id,
        tipo_relacion=tipo_relacion,
        direccion=direccion,
    )
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
    await service.eliminar_relacion(relacion_id)