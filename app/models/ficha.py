"""
Modelo FichaTecnica — K-Type del Dataspace.

Extiende la tabla kitem usando el mismo UUID como PK y FK.
Los campos JSONB actúan como el "Data Container" del k-item
según la Figura 3 del paper DSMS.

La relación con MaterialComercial se mantiene como FK directa
por rendimiento, y ADEMÁS se registra en kitem_relacion como
relación semántica "pertenece_a".
"""

from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid


class FichaTecnica(Base):
    __tablename__ = "ficha_tecnica"

    # PK que es también FK hacia kitem.id
    id_ficha = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4,
    )

    # FK directa a material (se mantiene por rendimiento en queries)
    id_material_corporativo = Column(
        UUID(as_uuid=True),
        ForeignKey("material_comercial.id_material_corporativo"),
        nullable=False,
    )

    # Metadata específica de la ficha
    codigo_ficha_local = Column(Text, nullable=False)
    codigo_material_local = Column(Text, nullable=False)
    codigo_version = Column(Text, nullable=False)
    usuario_creador = Column(Text, nullable=False)
    usuario_ultima_actualizacion = Column(Text, nullable=False)
    estado_ficha = Column(Text, nullable=False)
    fecha_registro = Column(DateTime, nullable=False)
    fecha_actualizacion = Column(DateTime, nullable=False)
    pais = Column(Text, nullable=False)

    # Data Container (JSONB) — secciones de la ficha técnica
    caracteristicas = Column(JSONB, nullable=True)
    caracteristicas_contenido = Column(JSONB, nullable=True)
    empaque_estiba = Column(JSONB, nullable=True)
    microbiologia = Column(JSONB, nullable=True)
    manejo_disposicion = Column(JSONB, nullable=True)