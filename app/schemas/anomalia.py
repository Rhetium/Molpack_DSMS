"""
Schemas del módulo de detección de anomalías.

Define los modelos Pydantic para:
- Resultados de análisis (response)
- Resolución de anomalías (request)
- Consulta de anomalías históricas (request/response)
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ========================
# Resultado de un análisis
# ========================

class AnomaliaDetectada(BaseModel):
    """Una anomalía individual detectada durante el análisis."""
    tipo_anomalia: str
    severidad: str = "advertencia"
    campo_afectado: str | None = None
    valor_detectado: str | None = None
    valor_esperado: str | None = None
    mensaje: str
    detalles: dict | None = None


class ResultadoAnalisis(BaseModel):
    """Resultado completo de un análisis de anomalías."""
    kitem_id: UUID
    ktype: str
    total_anomalias: int
    criticas: int = 0
    advertencias: int = 0
    informativas: int = 0
    anomalias: list[AnomaliaDetectada]
    analizado_en: datetime = Field(default_factory=datetime.now)


# ========================
# Request: Analizar
# ========================

class AnalizarFichaRequest(BaseModel):
    """Request para analizar una ficha técnica existente."""
    id_ficha: UUID
    usuario: str


class AnalizarMaterialRequest(BaseModel):
    """Request para analizar un material comercial existente."""
    id_material: UUID
    usuario: str


# ========================
# Request: Resolver anomalía
# ========================

class ResolverAnomaliaRequest(BaseModel):
    """Request para resolver (aceptar/descartar/corregir) una anomalía."""
    estado: str = Field(
        ...,
        description="Nuevo estado: 'aceptada', 'descartada' o 'corregida'",
    )
    nota: str | None = Field(
        None,
        description="Nota explicativa de la resolución",
    )
    usuario: str


# ========================
# Response: Anomalía histórica
# ========================

class AnomaliaRegistroSchema(BaseModel):
    """Schema de respuesta para una anomalía del repositorio histórico."""
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
    """Response para listar anomalías con metadata."""
    total: int
    anomalias: list[AnomaliaRegistroSchema]
    filtros_aplicados: dict | None = None