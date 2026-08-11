from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.kitem import KItemLiteSchema


class KItemRelacionCreateSchema(BaseModel):

    source_id: UUID
    target_id: UUID
    tipo_relacion: str
    etiqueta: str | None = None
    metadata_relacion: dict | None = None
    # Sobrescrito por el router con la identidad del token JWT.
    usuario_creador: str | None = None


class KItemRelacionSchema(BaseModel):

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

    id: UUID
    tipo_relacion: str
    etiqueta: str | None = None
    metadata_relacion: dict | None = None
    source: KItemLiteSchema
    target: KItemLiteSchema
    fecha_creacion: datetime

    class Config:
        from_attributes = True