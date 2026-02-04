from sqlalchemy import Column, Text, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid

class MaterialComercial(Base):
    __tablename__ = "material_comercial"

    id_material_corporativo = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    nombre_corporativo = Column(String, nullable=False)
    contenido = Column(Text, nullable=True)
    categoria = Column(Text, nullable=True)
    material_base = Column(Text, nullable=True)
    capacidad_nominal = Column(Text, nullable=True)
    color_base = Column(Text, nullable=True)
    tipo_producto = Column(Text, nullable=True)
    estado_material = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, nullable=True)
    fecha_actualizacion = Column(DateTime, nullable=True)
