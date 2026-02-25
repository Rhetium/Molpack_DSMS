"""
Servicio de Búsqueda Semántica — Motor de búsqueda por similitud del Dataspace.

Responsabilidades:
1. Búsqueda semántica: encontrar k-items similares a un texto o a otro k-item
2. Detección de duplicados: prevenir creación de k-items redundantes
3. Asignación de embeddings: generar y almacenar embeddings en k-items
4. Reindexación masiva: regenerar embeddings para k-items existentes

Referencia DSMS (Nahshon et al., 2023):
- Implementa "Semantic Search" de la Sección 2.3.4
- Habilita descubrimiento de conocimiento sin relaciones explícitas
- Prerequisito para detección de anomalías (Integration Level 4)

Integración con arquitectura existente:
- Usa KItem como supertipo universal (todo pasa por kitem)
- Registra acciones de auditoría via AuditoriaService
- Compatible con filtros por ktype y estado
"""

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
    """Servicio central de búsqueda semántica del DSMS."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.auditoria = AuditoriaService(db_session)

    # =========================================================
    # 1. ASIGNACIÓN DE EMBEDDINGS
    # =========================================================

    async def asignar_embedding(
        self,
        kitem_id: UUID,
        campos_adicionales: dict | None = None,
        usuario: str = "sistema",
    ) -> KItem:
        """
        Genera y almacena el embedding de un k-item.

        Se llama automáticamente desde los servicios de dominio
        (MaterialService, FichaService) al crear o actualizar un k-item.

        Args:
            kitem_id: UUID del k-item.
            campos_adicionales: Campos específicos del k-type para enriquecer
                                el texto del embedding (categoría, tipo_producto, etc.)
            usuario: Usuario que ejecuta la acción (para auditoría).

        Returns:
            El k-item actualizado con su embedding.
        """
        result = await self.db_session.execute(
            select(KItem).where(KItem.id == kitem_id)
        )
        kitem = result.scalars().first()
        if not kitem:
            raise HTTPException(status_code=404, detail="K-Item no encontrado")

        # Construir texto representativo y generar embedding
        texto = construir_texto_embedding(
            ktype=kitem.ktype,
            nombre=kitem.nombre,
            descripcion=kitem.descripcion,
            metadata_extra=kitem.metadata_extra,
            campos_adicionales=campos_adicionales,
        )
        embedding = generar_embedding(texto)

        # Almacenar embedding en la columna vectorial
        kitem.embedding = embedding
        kitem.fecha_actualizacion = datetime.now()
        self.db_session.add(kitem)
        await self.db_session.flush()

        # Auditoría
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

    # =========================================================
    # 2. BÚSQUEDA SEMÁNTICA
    # =========================================================

    async def buscar_por_texto(
        self,
        texto_consulta: str,
        ktype: str | None = None,
        estado: str | None = None,
        limite: int = 10,
        umbral_similitud: float = 0.0,
    ) -> list[dict]:
        """
        Búsqueda semántica: encuentra k-items similares a un texto libre.

        Usa similitud coseno via pgvector (operador <=>).
        La distancia coseno va de 0 (idénticos) a 2 (opuestos).
        Similitud = 1 - distancia.

        Args:
            texto_consulta: Texto libre para buscar.
            ktype: Filtrar por tipo de k-item (MaterialComercial, FichaTecnica, etc.)
            estado: Filtrar por estado del k-item.
            limite: Máximo de resultados.
            umbral_similitud: Similitud mínima (0.0 a 1.0). Resultados con
                              similitud menor se excluyen.

        Returns:
            Lista de dicts con kitem y similitud, ordenados por relevancia.
        """
        # Generar embedding del texto de consulta
        embedding_consulta = generar_embedding(texto_consulta)

        # Construir query con pgvector cosine distance
        # La distancia coseno en pgvector: kitem.embedding <=> query_vector
        # Similitud = 1 - distancia
        conditions = [KItem.embedding.isnot(None)]
        if ktype:
            conditions.append(KItem.ktype == ktype)
        if estado:
            conditions.append(KItem.estado == estado)

        # pgvector cosine distance operator: <=>
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

        # Filtrar por umbral y formatear respuesta
        resultados = []
        for kitem, similitud in filas:
            similitud_float = float(similitud)
            if similitud_float >= umbral_similitud:
                resultados.append({
                    "kitem": kitem,
                    "similitud": round(similitud_float, 4),
                })

        logger.info(
            f"Búsqueda semántica: '{texto_consulta[:80]}' → "
            f"{len(resultados)} resultados (ktype={ktype}, umbral={umbral_similitud})"
        )
        return resultados

    async def buscar_similares_a_kitem(
        self,
        kitem_id: UUID,
        ktype: str | None = None,
        limite: int = 10,
        umbral_similitud: float = 0.0,
    ) -> list[dict]:
        """
        Encuentra k-items similares a uno existente.

        Útil para:
        - Exploración del dataspace ("¿qué se parece a este material?")
        - Descubrimiento de relaciones semánticas implícitas
        - Input para detección de anomalías

        Args:
            kitem_id: UUID del k-item de referencia.
            ktype: Filtrar resultados por tipo (puede buscar similares entre tipos diferentes).
            limite: Máximo de resultados.
            umbral_similitud: Similitud mínima para incluir.

        Returns:
            Lista de dicts con kitem y similitud (excluyendo el k-item de referencia).
        """
        # Obtener embedding del k-item de referencia
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

        # Buscar similares excluyendo el propio k-item
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

    # =========================================================
    # 3. DETECCIÓN DE DUPLICADOS
    # =========================================================

    async def detectar_duplicados(
        self,
        nombre: str,
        descripcion: str | None = None,
        ktype: str | None = None,
        campos_adicionales: dict | None = None,
        umbral_duplicado: float = 0.85,
        limite: int = 5,
    ) -> list[dict]:
        """
        Detecta posibles duplicados ANTES de crear un nuevo k-item.

        Se invoca desde el frontend durante el registro guiado para
        alertar al usuario si ya existe un material/ficha similar.

        El umbral por defecto (0.85) es conservador: solo alerta cuando
        la similitud es alta. Se puede ajustar por k-type.

        Umbrales recomendados:
        - MaterialComercial: 0.85 (nombres de producto suelen ser únicos)
        - FichaTecnica: 0.80 (fichas del mismo material son naturalmente similares)

        Args:
            nombre: Nombre del nuevo k-item candidato.
            descripcion: Descripción del candidato.
            ktype: Tipo de k-item (para filtrar entre el mismo tipo).
            campos_adicionales: Campos específicos del k-type.
            umbral_duplicado: Similitud mínima para considerar duplicado.
            limite: Máximo de duplicados candidatos.

        Returns:
            Lista de posibles duplicados con similitud.
            Lista vacía si no hay duplicados sospechosos.
        """
        # Construir texto representativo del candidato
        texto_candidato = construir_texto_embedding(
            ktype=ktype or "General",
            nombre=nombre,
            descripcion=descripcion,
            campos_adicionales=campos_adicionales,
        )

        # Buscar similares con umbral alto
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

    # =========================================================
    # 4. REINDEXACIÓN
    # =========================================================

    async def reindexar_kitem(
        self,
        kitem_id: UUID,
        campos_adicionales: dict | None = None,
        usuario: str = "sistema",
    ) -> KItem:
        """
        Regenera el embedding de un k-item específico.

        Útil cuando se actualiza el nombre, descripción o campos
        de un k-item existente.
        """
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
        """
        Regenera embeddings para múltiples k-items.

        Útil para:
        - Migración inicial (cuando se activa pgvector por primera vez)
        - Reindexación después de cambiar modelo de embeddings
        - Generar embeddings para k-items que no los tienen

        Args:
            ktype: Filtrar por tipo (None = todos).
            solo_sin_embedding: Si True, solo procesa k-items sin embedding.
            batch_size: Tamaño del lote para procesamiento.
            usuario: Usuario para auditoría.

        Returns:
            Dict con estadísticas del proceso.
        """
        # Seleccionar k-items a procesar
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

        # Generar textos para todos los k-items
        textos = []
        for kitem in kitems:
            texto = construir_texto_embedding(
                ktype=kitem.ktype,
                nombre=kitem.nombre,
                descripcion=kitem.descripcion,
                metadata_extra=kitem.metadata_extra,
            )
            textos.append(texto)

        # Generar embeddings en batch (eficiente)
        logger.info(f"Generando embeddings para {len(textos)} k-items (batch={batch_size})")
        embeddings = generar_embeddings_batch(textos, batch_size=batch_size)

        # Asignar embeddings a cada k-item
        for kitem, embedding in zip(kitems, embeddings):
            kitem.embedding = embedding
            kitem.fecha_actualizacion = datetime.now()
            self.db_session.add(kitem)

        await self.db_session.flush()

        # Auditoría: registrar reindexación masiva (un solo evento resumen)
        await self.auditoria.registrar(
            kitem_id=kitems[0].id,  # Referencia al primer k-item del lote
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

    # =========================================================
    # 5. ESTADÍSTICAS
    # =========================================================

    async def obtener_estadisticas(self) -> dict:
        """
        Retorna estadísticas del estado de embeddings en el dataspace.
        Útil para monitoreo y para el dashboard del frontend.
        """
        # Total k-items
        total_result = await self.db_session.execute(
            select(func.count(KItem.id))
        )
        total = total_result.scalar()

        # K-items con embedding
        con_embedding_result = await self.db_session.execute(
            select(func.count(KItem.id)).where(KItem.embedding.isnot(None))
        )
        con_embedding = con_embedding_result.scalar()

        # Desglose por ktype
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