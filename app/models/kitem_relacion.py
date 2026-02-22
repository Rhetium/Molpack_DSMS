"""
Modelo KItemRelacion — Grafo de conocimiento del Dataspace.

Implementa el concepto de k-item linkage (Sección 2.3.2 del paper DSMS):
- Relaciones genéricas: k-item A "está relacionado con" k-item B
- Relaciones semánticas: k-item A "se deriva de" k-item B

Cada relación conecta dos k-items de cualquier tipo, formando un grafo
dirigido de conocimiento que puede explorarse, consultarse y analizarse.

Tipos de relación predefinidos para Molpack:
- "pertenece_a":      FichaTecnica → MaterialComercial
- "se_deriva_de":     FichaTecnica → FichaTecnica (versionamiento)
- "cumple_norma":     MaterialComercial → Norma (futuro)
- "tiene_incidencia": FichaTecnica → Incidencia (futuro)
- "es_variante_de":   MaterialComercial → MaterialComercial
- "relacionado_con":  relación genérica entre cualquier par de k-items
"""

from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class KItemRelacion(Base):
    __tablename__ = "kitem_relacion"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID del k-item origen de la relación",
    )
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID del k-item destino de la relación",
    )
    tipo_relacion = Column(
        Text,
        nullable=False,
        index=True,
        comment="Tipo semántico de la relación: pertenece_a, se_deriva_de, etc.",
    )
    etiqueta = Column(
        Text,
        nullable=True,
        comment="Descripción legible opcional de la relación",
    )
    metadata_relacion = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Datos adicionales de la relación (ej: contexto, peso, prioridad)",
    )
    usuario_creador = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.now)

    # --- Relaciones ORM ---
    source = relationship(
        "KItem",
        foreign_keys=[source_id],
        back_populates="relaciones_salientes",
    )
    target = relationship(
        "KItem",
        foreign_keys=[target_id],
        back_populates="relaciones_entrantes",
    )

    def __repr__(self):
        return (
            f"<KItemRelacion(source={self.source_id}, "
            f"--[{self.tipo_relacion}]--> "
            f"target={self.target_id})>"
        )