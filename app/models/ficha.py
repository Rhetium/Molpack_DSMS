from sqlalchemy import Column, Text, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid

class FichaTecnica(Base):
    __tablename__ = "ficha_tecnica"

    id_ficha = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    id_material_corporativo = Column(
        UUID(as_uuid=True),
        ForeignKey("material_comercial.id_material_corporativo"),
        nullable=False
    )
    codigo_material_local = Column(Text, nullable=False)
    codigo_version = Column(Text, nullable=False)
    usuario_creador = Column(Text, nullable=False)
    usuario_ultima_actualizacion = Column(Text, nullable=False)
    estado_ficha = Column(Text, nullable=False)
    fecha_registro = Column(DateTime, nullable=False)
    fecha_actualizacion = Column(DateTime, nullable=False)
    pais = Column(Text, nullable=False)

    caracteristicas = Column(JSONB, nullable=True)
    caracteristicas_contenido = Column(JSONB, nullable=True)
    empaque_estiba = Column(JSONB, nullable=True)
    microbiologia = Column(JSONB, nullable=True)
    manejo_disposicion = Column(JSONB, nullable=True)