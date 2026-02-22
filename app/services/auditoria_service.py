"""
Servicio de Auditoría — Trazabilidad automática del Dataspace.

Este servicio es INTERNO — no se llama desde la API directamente.
Los servicios de dominio (FichaService, MaterialService, KItemService)
lo usan para registrar eventos automáticamente.

Implementa el requisito de "Provenance and traceability" del paper DSMS:
cada acción relevante queda documentada de forma inmutable.
"""

from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kitem_auditoria import KItemAuditoria


class AuditoriaService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def registrar(
        self,
        kitem_id: UUID,
        ktype: str,
        accion: str,
        usuario: str,
        estado_anterior: str | None = None,
        estado_nuevo: str | None = None,
        detalles: dict | None = None,
    ) -> KItemAuditoria:
        """
        Registra un evento de auditoría.
        Usado internamente por los servicios de dominio.
        """
        evento = KItemAuditoria(
            kitem_id=kitem_id,
            ktype=ktype,
            accion=accion,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            detalles=detalles,
            usuario=usuario,
            fecha=datetime.now(),
        )
        self.db_session.add(evento)
        await self.db_session.flush()
        return evento

    async def obtener_historial(
        self,
        kitem_id: UUID,
        accion: str | None = None,
    ) -> list[KItemAuditoria]:
        """Obtiene el historial de auditoría de un k-item."""
        query = select(KItemAuditoria).where(
            KItemAuditoria.kitem_id == kitem_id
        )
        if accion:
            query = query.where(KItemAuditoria.accion == accion)
        query = query.order_by(KItemAuditoria.fecha.desc())
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def obtener_actividad_reciente(
        self,
        limite: int = 50,
        ktype: str | None = None,
        accion: str | None = None,
        usuario: str | None = None,
    ) -> list[KItemAuditoria]:
        """Obtiene la actividad reciente del dataspace con filtros opcionales."""
        query = select(KItemAuditoria)
        conditions = []
        if ktype:
            conditions.append(KItemAuditoria.ktype == ktype)
        if accion:
            conditions.append(KItemAuditoria.accion == accion)
        if usuario:
            conditions.append(KItemAuditoria.usuario == usuario)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(KItemAuditoria.fecha.desc()).limit(limite)
        result = await self.db_session.execute(query)
        return result.scalars().all()