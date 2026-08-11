from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class BusquedaSemanticaRequest(BaseModel):

    texto: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Texto de consulta para buscar k-items similares.",
        examples=["polietileno alta densidad para envases"],
    )
    ktype: str | None = Field(
        default=None,
        description="Filtrar por tipo de k-item (MaterialComercial, FichaTecnica, etc.)",
        examples=["MaterialComercial"],
    )
    estado: str | None = Field(
        default=None,
        description="Filtrar por estado del k-item.",
        examples=["Activo"],
    )
    limite: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Máximo de resultados a retornar.",
    )
    umbral_similitud: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Similitud mínima para incluir en resultados (0.0 = sin filtro).",
    )
    filtro_texto: str | None = None


class DeteccionDuplicadosRequest(BaseModel):

    nombre: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Nombre del k-item candidato.",
        examples=["Polietileno de Alta Densidad HDPE-5502"],
    )
    descripcion: str | None = Field(
        default=None,
        max_length=2000,
        description="Descripción del candidato.",
    )
    ktype: str | None = Field(
        default=None,
        description="Tipo de k-item para filtrar (busca duplicados del mismo tipo).",
        examples=["MaterialComercial"],
    )
    campos_adicionales: dict | None = Field(
        default=None,
        description=(
            "Campos específicos del k-type para enriquecer la comparación. "
            "Ej: {'categoria': 'Resina', 'tipo_producto': 'Polietileno'}"
        ),
    )
    umbral_duplicado: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description=(
            "Similitud mínima para considerar duplicado. "
            "0.85 = conservador, 0.75 = más sensible."
        ),
    )
    limite: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Máximo de duplicados candidatos.",
    )


class ReindexacionMasivaRequest(BaseModel):
    ktype: str | None = Field(
        default=None,
        description="Filtrar por tipo (None = todos los k-items).",
    )
    solo_sin_embedding: bool = Field(
        default=True,
        description="Si True, solo procesa k-items que no tienen embedding.",
    )
    batch_size: int = Field(
        default=64,
        ge=8,
        le=256,
        description="Tamaño del lote para procesamiento.",
    )

class KItemBusquedaSchema(BaseModel):

    id: UUID
    ktype: str
    nombre: str
    descripcion: str | None = None
    estado: str
    metadata_extra: dict | None = None
    usuario_creador: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class ResultadoBusquedaSchema(BaseModel):

    kitem: KItemBusquedaSchema
    similitud: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similitud coseno con la consulta (1.0 = idéntico).",
    )


class BusquedaSemanticaResponse(BaseModel):

    consulta: str
    total_resultados: int
    resultados: list[ResultadoBusquedaSchema]
    filtros_aplicados: dict = Field(
        default_factory=dict,
        description="Filtros aplicados a la búsqueda.",
    )


class DeteccionDuplicadosResponse(BaseModel):

    nombre_candidato: str
    hay_duplicados: bool = Field(
        description="True si se encontraron posibles duplicados sobre el umbral.",
    )
    total_duplicados: int
    umbral_utilizado: float
    duplicados: list[ResultadoBusquedaSchema]
    recomendacion: str = Field(
        description="Recomendación para el usuario.",
    )


class ReindexacionResponse(BaseModel):

    procesados: int
    ktype: str
    solo_sin_embedding: bool
    dimension_embedding: int


class EstadisticasEmbeddingKtype(BaseModel):

    ktype: str
    total: int
    con_embedding: int
    cobertura_pct: float


class EstadisticasEmbeddingResponse(BaseModel):

    total_kitems: int
    con_embedding: int
    sin_embedding: int
    cobertura_pct: float
    dimension_embedding: int
    modelo_embedding: str
    desglose_por_ktype: list[EstadisticasEmbeddingKtype]