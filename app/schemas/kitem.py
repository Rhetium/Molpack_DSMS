from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class KItemCreateSchema(BaseModel):
    """Schema interno para crear el registro base kitem.
    Normalmente no se usa directo desde la API — los servicios
    de MaterialComercial y FichaTecnica lo crean automáticamente."""

    ktype: str
    nombre: str
    descripcion: str | None = None
    estado: str = "Activo"
    metadata_extra: dict | None = None
    usuario_creador: str


class KItemSchema(BaseModel):
    """Schema de lectura para un k-item base."""

    id: UUID
    ktype: str
    nombre: str
    descripcion: str | None = None
    estado: str
    metadata_extra: dict | None = None
    usuario_creador: str
    usuario_ultima_actualizacion: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class KItemLiteSchema(BaseModel):
    """Schema reducido de k-item para anidar en relaciones."""

    id: UUID
    ktype: str
    nombre: str
    estado: str

    class Config:
        from_attributes = True