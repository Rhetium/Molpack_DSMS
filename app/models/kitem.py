from sqlalchemy import Column, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import uuid
from datetime import datetime


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


    relaciones_salientes = relationship(
        "KItemRelacion",
        foreign_keys="KItemRelacion.source_id",
        back_populates="source",
        lazy="selectin",
    )

    relaciones_entrantes = relationship(
        "KItemRelacion",
        foreign_keys="KItemRelacion.target_id",
        back_populates="target",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<KItem(id={self.id}, ktype={self.ktype}, nombre={self.nombre})>"