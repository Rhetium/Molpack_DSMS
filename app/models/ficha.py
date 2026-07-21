from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class FichaTecnica(Base):
    """
    Extensión de kitem para fichas técnicas.

    La metadata común (estado, usuarios, fechas) vive en `kitem`. Este modelo
    solo contiene datos de dominio de la ficha más las secciones JSONB.

    Las propiedades `estado_ficha`, `usuario_creador`,
    `usuario_ultima_actualizacion`, `fecha_registro` y `fecha_actualizacion`
    son proxies hacia el kitem asociado, para mantener compatibilidad con el
    código y los schemas que las leen/escriben por su nombre histórico.
    `fecha_registro` mapea a `kitem.fecha_creacion`.

    NOTA: en queries SQL no se puede filtrar por estas propiedades; usar
    `KItem.estado` con un JOIN al kitem.
    """

    __tablename__ = "ficha_tecnica"

    id_ficha = Column(
        UUID(as_uuid=True),
        ForeignKey("kitem.id", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4,
    )

    # FK directa a material (por rendimiento en queries)
    id_material_corporativo = Column(
        UUID(as_uuid=True),
        ForeignKey("material_comercial.id_material_corporativo"),
        nullable=False,
    )

    codigo_ficha_local = Column(Text, nullable=False)
    codigo_material_local = Column(Text, nullable=False)
    nombre_local_material = Column(Text, nullable=True)
    codigo_version = Column(Text, nullable=False)
    pais = Column(Text, nullable=False)

    caracteristicas = Column(JSONB, nullable=True)
    caracteristicas_contenido = Column(JSONB, nullable=True)
    empaque_estiba = Column(JSONB, nullable=True)
    microbiologia = Column(JSONB, nullable=True)
    manejo_disposicion = Column(JSONB, nullable=True)

    # Metadata común vive en kitem (única fuente de verdad).
    kitem = relationship(
        "KItem",
        foreign_keys=[id_ficha],
        lazy="joined",
    )

    # --- Proxies hacia kitem (compatibilidad de lectura/escritura) ---
    @property
    def estado_ficha(self):
        return self.kitem.estado if self.kitem else None

    @estado_ficha.setter
    def estado_ficha(self, valor):
        self.kitem.estado = valor

    @property
    def usuario_creador(self):
        return self.kitem.usuario_creador if self.kitem else None

    @usuario_creador.setter
    def usuario_creador(self, valor):
        self.kitem.usuario_creador = valor

    @property
    def usuario_ultima_actualizacion(self):
        return self.kitem.usuario_ultima_actualizacion if self.kitem else None

    @usuario_ultima_actualizacion.setter
    def usuario_ultima_actualizacion(self, valor):
        self.kitem.usuario_ultima_actualizacion = valor

    @property
    def fecha_registro(self):
        return self.kitem.fecha_creacion if self.kitem else None

    @fecha_registro.setter
    def fecha_registro(self, valor):
        self.kitem.fecha_creacion = valor

    @property
    def fecha_actualizacion(self):
        return self.kitem.fecha_actualizacion if self.kitem else None

    @fecha_actualizacion.setter
    def fecha_actualizacion(self, valor):
        self.kitem.fecha_actualizacion = valor
