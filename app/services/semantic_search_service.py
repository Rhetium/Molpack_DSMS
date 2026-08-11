from uuid import UUID
from datetime import datetime
import logging

from fastapi import HTTPException
from sqlalchemy import select, text, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kitem import KItem, EMBEDDING_DIMENSION
from app.services.embedding_service import (
    construir_texto_embedding,
    generar_embedding,
    generar_embeddings_batch,
)
from app.services.auditoria_service import AuditoriaService
from app.core.dsms_constants import ACCION_EMBEDDING_GENERADO

logger = logging.getLogger(__name__)


class BusquedaSemanticaService:

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.auditoria = AuditoriaService(db_session)

    async def asignar_embedding(
        self,
        kitem_id: UUID,
        campos_adicionales: dict | None = None,
        usuario: str = "sistema",
    ) -> KItem:

        result = await self.db_session.execute(
            select(KItem).where(KItem.id == kitem_id)
        )
        kitem = result.scalars().first()
        if not kitem:
            raise HTTPException(status_code=404, detail="K-Item no encontrado")

        texto = construir_texto_embedding(
            ktype=kitem.ktype,
            nombre=kitem.nombre,
            descripcion=kitem.descripcion,
            metadata_extra=kitem.metadata_extra,
            campos_adicionales=campos_adicionales,
        )
        embedding = generar_embedding(texto)

        kitem.embedding = embedding
        kitem.fecha_actualizacion = datetime.now()
        self.db_session.add(kitem)
        await self.db_session.flush()

        await self.auditoria.registrar(
            kitem_id=kitem_id,
            ktype=kitem.ktype,
            accion=ACCION_EMBEDDING_GENERADO,
            usuario=usuario,
            detalles={
                "texto_embedding_chars": len(texto),
                "embedding_dimension": EMBEDDING_DIMENSION,
                "campos_adicionales_keys": list(campos_adicionales.keys())
                if campos_adicionales
                else [],
            },
        )

        logger.info(
            f"Embedding asignado a kitem {kitem_id} "
            f"({kitem.ktype}: {kitem.nombre[:50]})"
        )
        return kitem

    async def buscar_por_texto(
        self,
        texto_consulta: str,
        ktype: str | None = None,
        estado: str | None = None,
        limite: int = 10,
        umbral_similitud: float = 0.0,
        filtro_texto: str | None = None,
    ) -> list[dict]:
        from sqlalchemy import or_

        embedding_consulta = generar_embedding(texto_consulta)

        conditions = [KItem.embedding.isnot(None)]
        if ktype:
            conditions.append(KItem.ktype == ktype)
        if estado:
            conditions.append(KItem.estado == estado)

        if filtro_texto:
            patron = f"%{filtro_texto}%"
            conditions.append(
                or_(
                    KItem.nombre.ilike(patron),
                    KItem.descripcion.ilike(patron),
                )
            )

        distancia = KItem.embedding.cosine_distance(embedding_consulta)

        query = (
            select(
                KItem,
                (1 - distancia).label("similitud"),
            )
            .where(and_(*conditions))
            .order_by(distancia.asc())
            .limit(limite)
        )

        result = await self.db_session.execute(query)
        filas = result.all()

        resultados = []
        for kitem, similitud in filas:
            similitud_float = float(similitud)
            if similitud_float >= umbral_similitud:
                resultados.append({
                    "kitem": kitem,
                    "similitud": round(similitud_float, 4),
                })

        logger.info(
            f"Búsqueda híbrida: '{texto_consulta[:80]}' "
            f"(filtro_texto='{filtro_texto}') → "
            f"{len(resultados)} resultados"
        )
        return resultados


    async def buscar_similares_a_kitem(
        self,
        kitem_id: UUID,
        ktype: str | None = None,
        limite: int = 10,
        umbral_similitud: float = 0.0,
    ) -> list[dict]:

        result = await self.db_session.execute(
            select(KItem).where(KItem.id == kitem_id)
        )
        kitem_ref = result.scalars().first()
        if not kitem_ref:
            raise HTTPException(status_code=404, detail="K-Item no encontrado")
        if kitem_ref.embedding is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El k-item '{kitem_ref.nombre}' no tiene embedding. "
                    "Genere el embedding primero con POST /dsms/semantica/reindexar/{kitem_id}"
                ),
            )

        conditions = [
            KItem.embedding.isnot(None),
            KItem.id != kitem_id,
        ]
        if ktype:
            conditions.append(KItem.ktype == ktype)

        distancia = KItem.embedding.cosine_distance(kitem_ref.embedding)

        query = (
            select(
                KItem,
                (1 - distancia).label("similitud"),
            )
            .where(and_(*conditions))
            .order_by(distancia.asc())
            .limit(limite)
        )

        result = await self.db_session.execute(query)
        filas = result.all()

        resultados = []
        for kitem, similitud in filas:
            similitud_float = float(similitud)
            if similitud_float >= umbral_similitud:
                resultados.append({
                    "kitem": kitem,
                    "similitud": round(similitud_float, 4),
                })

        return resultados

    async def detectar_duplicados(
        self,
        nombre: str,
        descripcion: str | None = None,
        ktype: str | None = None,
        campos_adicionales: dict | None = None,
        umbral_duplicado: float = 0.85,
        limite: int = 5,
    ) -> list[dict]:

        texto_candidato = construir_texto_embedding(
            ktype=ktype or "General",
            nombre=nombre,
            descripcion=descripcion,
            campos_adicionales=campos_adicionales,
        )

        resultados = await self.buscar_por_texto(
            texto_consulta=texto_candidato,
            ktype=ktype,
            limite=limite,
            umbral_similitud=umbral_duplicado,
        )

        if resultados:
            logger.warning(
                f"Posibles duplicados detectados para '{nombre}': "
                f"{len(resultados)} con similitud >= {umbral_duplicado}"
            )

        return resultados

    async def reindexar_kitem(
        self,
        kitem_id: UUID,
        campos_adicionales: dict | None = None,
        usuario: str = "sistema",
    ) -> KItem:

        return await self.asignar_embedding(
            kitem_id=kitem_id,
            campos_adicionales=campos_adicionales,
            usuario=usuario,
        )

    async def reindexar_masivo(
        self,
        ktype: str | None = None,
        solo_sin_embedding: bool = True,
        batch_size: int = 64,
        usuario: str = "sistema",
    ) -> dict:

        conditions = []
        if ktype:
            conditions.append(KItem.ktype == ktype)
        if solo_sin_embedding:
            conditions.append(KItem.embedding.is_(None))

        query = select(KItem)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(KItem.fecha_creacion.asc())

        result = await self.db_session.execute(query)
        kitems = result.scalars().all()

        if not kitems:
            return {
                "procesados": 0,
                "mensaje": "No hay k-items pendientes de indexación.",
            }

        textos = []
        for kitem in kitems:
            texto = construir_texto_embedding(
                ktype=kitem.ktype,
                nombre=kitem.nombre,
                descripcion=kitem.descripcion,
                metadata_extra=kitem.metadata_extra,
            )
            textos.append(texto)

        logger.info(f"Generando embeddings para {len(textos)} k-items (batch={batch_size})")
        embeddings = generar_embeddings_batch(textos, batch_size=batch_size)

        for kitem, embedding in zip(kitems, embeddings):
            kitem.embedding = embedding
            kitem.fecha_actualizacion = datetime.now()
            self.db_session.add(kitem)

        await self.db_session.flush()


        await self.auditoria.registrar(
            kitem_id=kitems[0].id,
            ktype=ktype or "TODOS",
            accion=ACCION_EMBEDDING_GENERADO,
            usuario=usuario,
            detalles={
                "tipo_operacion": "reindexacion_masiva",
                "total_procesados": len(kitems),
                "ktype_filtro": ktype,
                "solo_sin_embedding": solo_sin_embedding,
                "batch_size": batch_size,
                "embedding_dimension": EMBEDDING_DIMENSION,
            },
        )

        logger.info(f"Reindexación completada: {len(kitems)} k-items procesados")
        return {
            "procesados": len(kitems),
            "ktype": ktype or "todos",
            "solo_sin_embedding": solo_sin_embedding,
            "dimension_embedding": EMBEDDING_DIMENSION,
        }

    async def obtener_estadisticas(self) -> dict:

        total_result = await self.db_session.execute(
            select(func.count(KItem.id))
        )
        total = total_result.scalar()

        con_embedding_result = await self.db_session.execute(
            select(func.count(KItem.id)).where(KItem.embedding.isnot(None))
        )
        con_embedding = con_embedding_result.scalar()

        desglose_result = await self.db_session.execute(
            select(
                KItem.ktype,
                func.count(KItem.id).label("total"),
                func.count(KItem.embedding).label("con_embedding"),
            ).group_by(KItem.ktype)
        )
        desglose = [
            {
                "ktype": row.ktype,
                "total": row.total,
                "con_embedding": row.con_embedding,
                "cobertura_pct": round(
                    (row.con_embedding / row.total * 100) if row.total > 0 else 0, 1
                ),
            }
            for row in desglose_result.all()
        ]

        return {
            "total_kitems": total,
            "con_embedding": con_embedding,
            "sin_embedding": total - con_embedding,
            "cobertura_pct": round(
                (con_embedding / total * 100) if total > 0 else 0, 1
            ),
            "dimension_embedding": EMBEDDING_DIMENSION,
            "modelo_embedding": "all-MiniLM-L6-v2",
            "desglose_por_ktype": desglose,
        }