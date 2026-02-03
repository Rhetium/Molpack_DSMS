from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

class MaterialComercialSchema(BaseModel):
    id_material_corporativo: UUID
    nombre_corporativo: str
    familia: str | None = None
    categoria: str | None = None
    material_base: str | None = None
    capacidad_nominal: str | None = None
    color: str | None = None
    tipo_producto: str | None = None
    estado_matierial: str | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None

    class Config:
        from_attributes = True