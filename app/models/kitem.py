"""
Modelo base KItem — Supertipo universal del Dataspace.

Cada objeto de conocimiento en el sistema (material, ficha técnica, norma, incidencia, etc.)
ES un k-item. Esta tabla contiene la metadata común a todos los k-items, según la Figura 3
del paper DSMS de Nahshon et al. (2023):

    K-Item = Metadata + Data Container + Semantic Graph

- Metadata:  almacenada aquí (id, ktype, nombre, descripción, estado, fechas, usuarios)
- Data Container: almacenado en las tablas de extensión (JSONB en ficha_tecnica, etc.)
- Semantic Graph: representado por las relaciones en kitem_relacion
"""

from sqlalchemy import Column, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


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