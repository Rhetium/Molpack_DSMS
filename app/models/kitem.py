"""
Modelo base KItem — Supertipo universal del Dataspace.

Cada objeto de conocimiento en el sistema (material, ficha técnica, norma, incidencia, etc.)
ES un k-item. Esta tabla contiene la metadata común a todos los k-items, según la Figura 3
del paper DSMS de Nahshon et al. (2023):

    K-Item = Metadata + Data Container + Semantic Graph

- Metadata:  almacenada aquí (id, ktype, nombre, descripción, estado, fechas, usuarios)
- Data Container: almacenado en las tablas de extensión (JSONB en ficha_tecnica, etc.)
- Semantic Graph: representado por las relaciones en kitem_relacion

ACTUALIZACIÓN pgvector:
- Se agrega columna `embedding` (vector 384D) para búsqueda semántica.
- El embedding se genera a partir de nombre + descripción + metadata del k-item.
- Permite búsqueda por similitud coseno y detección de duplicados.
"""

from sqlalchemy import Column, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import uuid
from datetime import datetime

# Dimensión del modelo de embeddings.
# 384 = all-MiniLM-L6-v2 (sentence-transformers, local, gratuito)
# Cambiar a 1536 si se migra a OpenAI text-embedding-3-small
EMBEDDING_DIMENSION = 384


class KItem(Base):
    __tablename__ = "kitem"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ktype = Column(
        Text,
        nullable=False,
        index=True,
        comment="Tipo de conocimiento: MaterialComercial, FichaTecnica, etc.",
    )
    nombre = Column(
        Text,
        nullable=False,
        comment="Nombre legible del k-item",
    )
    descripcion = Column(
        Text,
        nullable=True,
        comment="Resumen/summary del k-item (equivale al Summary del paper)",
    )
    estado = Column(
        Text,
        nullable=False,
        default="Activo",
        comment="Estado genérico del ciclo de vida del k-item",
    )
    metadata_extra = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Metadata extensible adicional del k-item",
    )

    # === NUEVO: Embedding vectorial para búsqueda semántica ===
    embedding = Column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,
        comment=(
            "Embedding vectorial del k-item para búsqueda semántica. "
            "Generado a partir de nombre + descripción + metadata contextual. "
            f"Dimensión: {EMBEDDING_DIMENSION} (all-MiniLM-L6-v2)"
        ),
    )

    usuario_creador = Column(Text, nullable=False)
    usuario_ultima_actualizacion = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = Column(DateTime, nullable=False, default=datetime.now)

    # --- Relaciones ORM ---
    # Relaciones donde este k-item es el ORIGEN
    relaciones_salientes = relationship(
        "KItemRelacion",
        foreign_keys="KItemRelacion.source_id",
        back_populates="source",
        lazy="selectin",
    )
    # Relaciones donde este k-item es el DESTINO
    relaciones_entrantes = relationship(
        "KItemRelacion",
        foreign_keys="KItemRelacion.target_id",
        back_populates="target",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<KItem(id={self.id}, ktype={self.ktype}, nombre={self.nombre})>"