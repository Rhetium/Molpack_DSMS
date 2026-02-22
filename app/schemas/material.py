from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class MaterialCreateSchema(BaseModel):
    nombre_corporativo: str
    contenido: str | None = None
    categoria: str | None = None
    material_base: str | None = None
    capacidad_nominal: str | None = None
    color_base: str | None = None
    tipo_producto: str | None = None
    estado_material: str
    usuario_creador: str  # NUEVO: necesario para crear el kitem base


class MaterialSchema(BaseModel):
    id_material_corporativo: UUID
    nombre_corporativo: str
    contenido: str | None = None
    categoria: str | None = None
    material_base: str | None = None
    capacidad_nominal: str | None = None
    color_base: str | None = None
    tipo_producto: str | None = None
    estado_material: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class MaterialLiteSchema(BaseModel):
    id_material_corporativo: UUID
    nombre_corporativo: str
    contenido: str | None = None
    categoria: str | None = None
    tipo_producto: str | None = None
    estado_material: str
    capacidad_nominal: str | None = None
    color_base: str | None = None

    class Config:
        from_attributes = True