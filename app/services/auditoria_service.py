from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kitem_auditoria import KItemAuditoria
from app.models.material import MaterialComercial
from app.models.ficha import FichaTecnica


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
        limite: int = 25,
        offset: int = 0,
        ktype: str | None = None,
        accion: str | None = None,
        usuario: str | None = None,
        categoria: str | None = None,
    ) -> list[KItemAuditoria]:
        query = select(KItemAuditoria)
        conditions = []

        if ktype:
            conditions.append(KItemAuditoria.ktype == ktype)
        if accion:
            conditions.append(KItemAuditoria.accion == accion)
        if usuario:
            conditions.append(KItemAuditoria.usuario == usuario)

        if categoria:
            # IDs de materiales que pertenecen a la categoría
            mat_ids_q = select(MaterialComercial.id_material_corporativo).where(
                MaterialComercial.categoria == categoria
            )
            mat_ids = (await self.db_session.execute(mat_ids_q)).scalars().all()

            # IDs de fichas vinculadas a esos materiales
            ficha_ids_q = select(FichaTecnica.id_ficha).where(
                FichaTecnica.id_material_corporativo.in_(mat_ids)
            )
            ficha_ids = (await self.db_session.execute(ficha_ids_q)).scalars().all()

            all_ids = list(mat_ids) + list(ficha_ids)
            if not all_ids:
                return []
            conditions.append(KItemAuditoria.kitem_id.in_(all_ids))

        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(KItemAuditoria.fecha.desc()).offset(offset).limit(limite)
        result = await self.db_session.execute(query)
        return result.scalars().all()