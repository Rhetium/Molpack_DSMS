"""
Servicio KItem — Gestión del grafo de conocimiento del Dataspace.

ACTUALIZADO con auditoría automática: cada creación de k-item,
cambio de estado, creación/eliminación de relación queda registrada
en kitem_auditoria para trazabilidad completa.
"""

from uuid import UUID
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.kitem import KItem
from app.models.kitem_relacion import KItemRelacion
from app.schemas.kitem import KItemCreateSchema, KItemSchema, KItemLiteSchema
from app.schemas.kitem_relacion import (
    KItemRelacionCreateSchema,
    KItemRelacionSchema,
    KItemRelacionDetalleSchema,
)
from app.services.auditoria_service import AuditoriaService
from app.core.dsms_constants import (
    RELACIONES_VALIDAS,
    ACCION_CREACION,
    ACCION_CAMBIO_ESTADO,
    ACCION_RELACION_CREADA,
    ACCION_RELACION_ELIMINADA,
)

class KItemService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.auditoria = AuditoriaService(db_session)

    # =========================================
    # Operaciones de K-Items base
    # =========================================

    async def crear_kitem(self, data: KItemCreateSchema) -> KItem:
        """Crea un registro base kitem y registra el evento de auditoría."""
        now = datetime.now()
        kitem = KItem(
            ktype=data.ktype,
            nombre=data.nombre,
            descripcion=data.descripcion,
            estado=data.estado,
            metadata_extra=data.metadata_extra,
            usuario_creador=data.usuario_creador,
            usuario_ultima_actualizacion=data.usuario_creador,
            fecha_creacion=now,
            fecha_actualizacion=now,
        )
        self.db_session.add(kitem)
        await self.db_session.flush()

        # Auditoría: registrar creación
        await self.auditoria.registrar(
            kitem_id=kitem.id,
            ktype=data.ktype,
            accion=ACCION_CREACION,
            usuario=data.usuario_creador,
            estado_nuevo=data.estado,
            detalles={
                "nombre": data.nombre,
                "descripcion": data.descripcion,
            },
        )

        return kitem

    async def obtener_kitem(self, kitem_id: UUID) -> KItem:
        """Obtiene un k-item por su ID."""
        result = await self.db_session.execute(
            select(KItem).where(KItem.id == kitem_id)
        )
        kitem = result.scalars().first()
        if not kitem:
            raise HTTPException(status_code=404, detail="K-Item no encontrado")
        return kitem

    async def listar_kitems(
        self,
        ktype: str | None = None,
        estado: str | None = None,
    ) -> list[KItem]:
        """Lista k-items con filtros opcionales por tipo y estado."""
        query = select(KItem)
        conditions = []
        if ktype:
            conditions.append(KItem.ktype == ktype)
        if estado:
            conditions.append(KItem.estado == estado)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(KItem.fecha_creacion.desc())
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def actualizar_estado_kitem(
        self,
        kitem_id: UUID,
        nuevo_estado: str,
        usuario: str,
    ) -> KItem:
        """Actualiza el estado de un k-item y registra la transición."""
        kitem = await self.obtener_kitem(kitem_id)
        estado_anterior = kitem.estado

        kitem.estado = nuevo_estado
        kitem.usuario_ultima_actualizacion = usuario
        kitem.fecha_actualizacion = datetime.now()
        self.db_session.add(kitem)
        await self.db_session.flush()

        # Auditoría: registrar cambio de estado
        await self.auditoria.registrar(
            kitem_id=kitem_id,
            ktype=kitem.ktype,
            accion=ACCION_CAMBIO_ESTADO,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            detalles={
                "nombre": kitem.nombre,
                "transicion": f"{estado_anterior} -> {nuevo_estado}",
            },
        )

        return kitem

    # =========================================
    # Operaciones de Relaciones (Grafo)
    # =========================================

    async def crear_relacion(self, data: KItemRelacionCreateSchema) -> KItemRelacion:
        """Crea una relación semántica y registra el evento de auditoría."""

        if data.tipo_relacion not in RELACIONES_VALIDAS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Tipo de relacion '{data.tipo_relacion}' no valido. "
                    f"Tipos validos: {', '.join(sorted(RELACIONES_VALIDAS))}"
                ),
            )

        source = await self.obtener_kitem(data.source_id)
        target = await self.obtener_kitem(data.target_id)

        if data.source_id == data.target_id:
            raise HTTPException(
                status_code=400,
                detail="Un k-item no puede tener una relacion consigo mismo.",
            )

        query = select(KItemRelacion).where(
            and_(
                KItemRelacion.source_id == data.source_id,
                KItemRelacion.target_id == data.target_id,
                KItemRelacion.tipo_relacion == data.tipo_relacion,
            )
        )
        result = await self.db_session.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="Ya existe una relacion de este tipo entre estos k-items.",
            )

        relacion = KItemRelacion(
            source_id=data.source_id,
            target_id=data.target_id,
            tipo_relacion=data.tipo_relacion,
            etiqueta=data.etiqueta,
            metadata_relacion=data.metadata_relacion,
            usuario_creador=data.usuario_creador,
            fecha_creacion=datetime.now(),
        )
        self.db_session.add(relacion)
        await self.db_session.flush()

        # Auditoría: registrar en AMBOS k-items involucrados
        detalle_relacion = {
            "relacion_id": str(relacion.id),
            "tipo_relacion": data.tipo_relacion,
            "source_nombre": source.nombre,
            "target_nombre": target.nombre,
            "etiqueta": data.etiqueta,
        }

        await self.auditoria.registrar(
            kitem_id=data.source_id,
            ktype=source.ktype,
            accion=ACCION_RELACION_CREADA,
            usuario=data.usuario_creador,
            detalles={
                **detalle_relacion,
                "direccion": "saliente",
                "conectado_a": str(data.target_id),
            },
        )

        await self.auditoria.registrar(
            kitem_id=data.target_id,
            ktype=target.ktype,
            accion=ACCION_RELACION_CREADA,
            usuario=data.usuario_creador,
            detalles={
                **detalle_relacion,
                "direccion": "entrante",
                "conectado_a": str(data.source_id),
            },
        )

        return relacion

    async def obtener_relaciones_de_kitem(
        self,
        kitem_id: UUID,
        tipo_relacion: str | None = None,
        direccion: str = "ambas",
    ) -> list[KItemRelacion]:
        """Obtiene las relaciones de un k-item."""
        conditions = []

        if direccion == "salientes":
            conditions.append(KItemRelacion.source_id == kitem_id)
        elif direccion == "entrantes":
            conditions.append(KItemRelacion.target_id == kitem_id)
        else:
            conditions.append(
                or_(
                    KItemRelacion.source_id == kitem_id,
                    KItemRelacion.target_id == kitem_id,
                )
            )

        if tipo_relacion:
            conditions.append(KItemRelacion.tipo_relacion == tipo_relacion)

        query = (
            select(KItemRelacion)
            .options(
                selectinload(KItemRelacion.source),
                selectinload(KItemRelacion.target),
            )
            .where(and_(*conditions))
            .order_by(KItemRelacion.fecha_creacion.desc())
        )

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def obtener_grafo_kitem(self, kitem_id: UUID) -> dict:
        """Devuelve el grafo completo de un k-item con sus relaciones."""
        kitem = await self.obtener_kitem(kitem_id)
        relaciones = await self.obtener_relaciones_de_kitem(kitem_id)

        relaciones_detalle = []
        for rel in relaciones:
            relaciones_detalle.append(
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

        return {
            "kitem": KItemSchema.model_validate(kitem),
            "relaciones": relaciones_detalle,
            "total_relaciones": len(relaciones_detalle),
        }

    async def eliminar_relacion(self, relacion_id: UUID) -> None:
        """Elimina una relación y registra el evento de auditoría."""
        result = await self.db_session.execute(
            select(KItemRelacion)
            .options(
                selectinload(KItemRelacion.source),
                selectinload(KItemRelacion.target),
            )
            .where(KItemRelacion.id == relacion_id)
        )
        relacion = result.scalars().first()
        if not relacion:
            raise HTTPException(status_code=404, detail="Relacion no encontrada")

        detalle = {
            "relacion_id": str(relacion.id),
            "tipo_relacion": relacion.tipo_relacion,
            "source_nombre": relacion.source.nombre,
            "target_nombre": relacion.target.nombre,
            "etiqueta": relacion.etiqueta,
        }

        await self.auditoria.registrar(
            kitem_id=relacion.source_id,
            ktype=relacion.source.ktype,
            accion=ACCION_RELACION_ELIMINADA,
            usuario="sistema",
            detalles={**detalle, "direccion": "saliente"},
        )

        await self.auditoria.registrar(
            kitem_id=relacion.target_id,
            ktype=relacion.target.ktype,
            accion=ACCION_RELACION_ELIMINADA,
            usuario="sistema",
            detalles={**detalle, "direccion": "entrante"},
        )

        await self.db_session.delete(relacion)
        await self.db_session.flush()