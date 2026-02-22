from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.kitem import KItemLiteSchema


class KItemRelacionCreateSchema(BaseModel):
    """Schema para crear una relación entre dos k-items."""

    source_id: UUID
    target_id: UUID
    tipo_relacion: str
    etiqueta: str | None = None
    metadata_relacion: dict | None = None
    usuario_creador: str


class KItemRelacionSchema(BaseModel):
    """Schema de lectura de una relación."""

    id: UUID
    source_id: UUID
    target_id: UUID
    tipo_relacion: str
    etiqueta: str | None = None
    metadata_relacion: dict | None = None
    usuario_creador: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class KItemRelacionDetalleSchema(BaseModel):
    """Schema de lectura enriquecido con datos de los k-items vinculados."""

    id: UUID
    tipo_relacion: str
    etiqueta: str | None = None
    metadata_relacion: dict | None = None
    source: KItemLiteSchema
    target: KItemLiteSchema
    fecha_creacion: datetime

    class Config:
        from_attributes = True