from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class AuditoriaSchema(BaseModel):
    """Schema de lectura para un evento de auditoría."""

    id: UUID
    kitem_id: UUID | None = None
    ktype: str
    accion: str
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    detalles: dict | None = None
    usuario: str
    fecha: datetime

    class Config:
        from_attributes = True


class AuditoriaResumenSchema(BaseModel):
    """Schema resumido para listados de auditoría."""

    id: UUID
    kitem_id: UUID | None = None
    ktype: str
    accion: str
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    usuario: str
    fecha: datetime

    class Config:
        from_attributes = True