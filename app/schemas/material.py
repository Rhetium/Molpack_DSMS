from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class MaterialCreateSchema(BaseModel):
    nombre_corporativo: str
    contenido: str | None = None
    categoria: str | None = None
    sector: str | None = None
    caracteristica: str | None = None
    material_base: str | None = None
    capacidad_nominal: str | None = None
    tipo_producto: str | None = None
    estado_material: str
    # Sobrescrito por el router con la identidad del token JWT.
    usuario_creador: str | None = None


class AnomaliaResumen(BaseModel):
    tipo_anomalia: str
    severidad: str
    campo_afectado: str | None = None
    mensaje: str


class MaterialSchema(BaseModel):
    id_material_corporativo: UUID
    nombre_corporativo: str
    contenido: str | None = None
    categoria: str | None = None
    sector: str | None = None
    caracteristica: str | None = None
    material_base: str | None = None
    capacidad_nominal: str | None = None
    tipo_producto: str | None = None
    estado_material: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    anomalias: list[AnomaliaResumen] | None = None

    class Config:
        from_attributes = True


class MaterialLiteSchema(BaseModel):
    id_material_corporativo: UUID
    nombre_corporativo: str
    contenido: str | None = None
    categoria: str | None = None
    sector: str | None = None
    tipo_producto: str | None = None
    estado_material: str
    capacidad_nominal: str | None = None

    class Config:
        from_attributes = True


class MaterialUpdateSchema(BaseModel):
    nombre_corporativo: str | None = None
    contenido: str | None = None
    categoria: str | None = None
    sector: str | None = None
    caracteristica: str | None = None
    material_base: str | None = None
    capacidad_nominal: str | None = None
    tipo_producto: str | None = None
    estado_material: str | None = None
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    usuario: str | None = None


class CambioEstadoMaterialRequest(BaseModel):
    estado_material: str
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    usuario: str | None = None
