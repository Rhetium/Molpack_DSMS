"""
Modelo AnomaliaRegistro — Repositorio histórico de anomalías detectadas.

Almacena cada anomalía encontrada durante la creación, actualización
o análisis batch de k-items en el DSMS. Permite:
- Trazabilidad de eventos anómalos
- Revisión por supervisores
- Alimentar mejora continua de modelos
- Reportes de calidad de datos
"""

from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid
from datetime import datetime


class AnomaliaRegistro(Base):
    __tablename__ = "anomalia_registro"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # K-Item que disparó la anomalía
    kitem_id = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID del k-item donde se detectó la anomalía",
    )
    ktype = Column(
        Text,
        nullable=False,
        comment="Tipo de k-item: MaterialComercial, FichaTecnica",
    )

    # Clasificación
    tipo_anomalia = Column(
        Text,
        nullable=False,
        index=True,
        comment=(
            "Tipo: valor_atipico, unidad_inconsistente, "
            "clasificacion_cruzada, duplicado_semantico, estructura_invalida"
        ),
    )
    severidad = Column(
        Text,
        nullable=False,
        default="advertencia",
        index=True,
        comment="Severidad: informativa, advertencia, critica",
    )

    # Detalle
    campo_afectado = Column(
        Text,
        nullable=True,
        comment="Campo específico donde se detectó la anomalía",
    )
    valor_detectado = Column(
        Text,
        nullable=True,
        comment="Valor que disparó la anomalía",
    )
    valor_esperado = Column(
        Text,
        nullable=True,
        comment="Rango o valor esperado (ej: '28.0 - 32.0 cm')",
    )
    mensaje = Column(
        Text,
        nullable=False,
        comment="Mensaje explicativo para el usuario",
    )
    detalles = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Metadata adicional: stats, similitud, categorías, etc.",
    )

    # Estado de resolucion
    estado = Column(
        Text,
        nullable=False,
        default="pendiente",
        index=True,
        comment="Estado: pendiente, aceptada, descartada, corregida",
    )
    resuelto_por = Column(Text, nullable=True)
    fecha_resolucion = Column(DateTime, nullable=True)
    nota_resolucion = Column(Text, nullable=True)

    # Metadata
    detectado_por = Column(
        Text,
        nullable=False,
        default="sistema",
        comment="'sistema' (automático) o usuario que reportó",
    )
    usuario_creador = Column(
        Text,
        nullable=False,
        comment="Usuario que estaba operando cuando se detectó",
    )
    fecha_deteccion = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        index=True,
    )
    contexto = Column(
        Text,
        nullable=False,
        default="creacion",
        comment="Contexto: creacion, actualizacion, analisis_batch",
    )

    def __repr__(self):
        return (
            f"<AnomaliaRegistro(kitem={self.kitem_id}, "
            f"tipo={self.tipo_anomalia}, "
            f"severidad={self.severidad}, "
            f"estado={self.estado})>"
        )