from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class MaterialComercial(Base):

    __tablename__ = "material_comercial"

    id_material_corporativo = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4,
    )

    nombre_corporativo = Column(Text, nullable=False)
    contenido = Column(Text, nullable=True)
    categoria = Column(Text, nullable=True)
    sector = Column(Text, nullable=True)
    caracteristica = Column(Text, nullable=True)
    material_base = Column(Text, nullable=True)
    capacidad_nominal = Column(Text, nullable=True)
    tipo_producto = Column(Text, nullable=True)


    kitem = relationship(
        "KItem",
        foreign_keys=[id_material_corporativo],
        lazy="joined",
    )


    @property
    def estado_material(self):
        return self.kitem.estado if self.kitem else None

    @estado_material.setter
    def estado_material(self, valor):
        self.kitem.estado = valor

    @property
    def fecha_creacion(self):
        return self.kitem.fecha_creacion if self.kitem else None

    @fecha_creacion.setter
    def fecha_creacion(self, valor):
        self.kitem.fecha_creacion = valor

    @property
    def fecha_actualizacion(self):
        return self.kitem.fecha_actualizacion if self.kitem else None

    @fecha_actualizacion.setter
    def fecha_actualizacion(self, valor):
        self.kitem.fecha_actualizacion = valor
