from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid
from datetime import datetime

class KItemAuditoria(Base):
    __tablename__ = "kitem_auditoria"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    kitem_id = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="UUID del k-item afectado.  NULL si el k-item fue eliminado.",
    )
    ktype = Column(
        Text,
        nullable=False,
        comment="Tipo de conocimiento auditado: MaterialComercial, FichaTecnica, etc.",
    )
    accion = Column(
        Text,
        nullable=False,
        index=True,
        comment="Tipo de acción auditada: creación, actualización, eliminación",
    )
    estado_anterior = Column(
        Text,
        nullable=True,
        comment="Estado del k-item antes de la acción (ej: 'Activo', 'Obsoleto'). NULL si no aplica.",
    )
    estado_nuevo = Column(
        Text,
        nullable=True,
        comment="Estado del k-item después de la acción (ej: 'Activo', 'Obsoleto'). NULL si no aplica.",
    )
    detalles = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Detalles adicionales del cambio en formato JSON (ej: campos modificados, valores anteriores/nuevos)",
    )
    usuario = Column(
        Text,
        nullable=False,
        comment="Usuario que realizó la acción auditada",
    )
    fecha = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        index=True,
        comment="Fecha y hora en que se realizó la acción auditada",
    )

    def __repr__(self):
        return (
            f"<KItemAuditoria(kitem={self.kitem_id}, "
            f"accion={self.accion}, "
            f"usuario={self.usuario}, "
            f"fecha={self.fecha})>"
        )