"""
Modelo MaterialComercial — K-Type del Dataspace.

Extiende la tabla kitem usando el mismo UUID como PK y FK.
Contiene los atributos específicos del dominio de materiales comerciales
de Molpack Corporation.

Patrón: Joined Table Inheritance (supertipo kitem + extensión material_comercial)
"""

from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid


class MaterialComercial(Base):
    __tablename__ = "material_comercial"

    # PK que es también FK hacia kitem.id
    id_material_corporativo = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Atributos específicos del k-type MaterialComercial
    nombre_corporativo = Column(Text, nullable=False)
    contenido = Column(Text, nullable=True)
    categoria = Column(Text, nullable=True)
    material_base = Column(Text, nullable=True)
    capacidad_nominal = Column(Text, nullable=True)
    color_base = Column(Text, nullable=True)
    tipo_producto = Column(Text, nullable=True)
    estado_material = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, nullable=True)
    fecha_actualizacion = Column(DateTime, nullable=True)