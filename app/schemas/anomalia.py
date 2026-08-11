from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class AnomaliaDetectada(BaseModel):
    tipo_anomalia: str
    severidad: str = "advertencia"
    campo_afectado: str | None = None
    valor_detectado: str | None = None
    valor_esperado: str | None = None
    mensaje: str
    detalles: dict | None = None


class ResultadoAnalisis(BaseModel):
    kitem_id: UUID
    ktype: str
    total_anomalias: int
    criticas: int = 0
    advertencias: int = 0
    informativas: int = 0
    anomalias: list[AnomaliaDetectada]
    analizado_en: datetime = Field(default_factory=datetime.now)

class AnalizarFichaRequest(BaseModel):
    id_ficha: UUID
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    usuario: str | None = None


class AnalizarMaterialRequest(BaseModel):
    id_material: UUID
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    usuario: str | None = None


class ResolverAnomaliaRequest(BaseModel):
    estado: str = Field(
        ...,
        description="Nuevo estado: 'aceptada', 'descartada' o 'corregida'",
    )
    nota: str | None = Field(
        None,
        description="Nota explicativa de la resolución",
    )
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    usuario: str | None = None


class AnomaliaRegistroSchema(BaseModel):
    id: UUID
    kitem_id: UUID
    ktype: str
    tipo_anomalia: str
    severidad: str
    campo_afectado: str | None
    valor_detectado: str | None
    valor_esperado: str | None
    mensaje: str
    detalles: dict | None
    estado: str
    resuelto_por: str | None
    fecha_resolucion: datetime | None
    nota_resolucion: str | None
    detectado_por: str
    usuario_creador: str
    fecha_deteccion: datetime
    contexto: str

    class Config:
        from_attributes = True


class AnomaliaListResponse(BaseModel):
    total: int
    anomalias: list[AnomaliaRegistroSchema]
    filtros_aplicados: dict | None = None