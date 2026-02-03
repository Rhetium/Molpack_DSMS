from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

class FichaTecnicaSchema(BaseModel):
    id_ficha: UUID
    id_material_corporativo: UUID
    codigo_material_local: str | None = None
    codigo_version: str | None = None
    usuario_creador: str | None = None
    usuario_ultima_actualizacion: str | None = None
    estado_ficha: str | None = None
    fecha_registro: datetime | None = None
    fecha_actualizacion: datetime | None = None
    pais: str | None = None

    caracteristicas: dict | None = None
    caracteristicas_contenido: dict | None = None
    empaque_estiba: dict | None = None
    microbiologia: dict | None = None
    manejo_disposicion: dict | None = None

    class Config:
        from_attributes = True
