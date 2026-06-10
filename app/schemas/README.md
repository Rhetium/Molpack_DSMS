# app/schemas/ — Esquemas Pydantic

Todos los esquemas usan Pydantic v2 con `model_config = ConfigDict(from_attributes=True)`.

| Archivo | Esquemas principales |
|---|---|
| `kitem.py` | `KItemSchema`, `KItemCreateSchema`, `KItemLiteSchema` |
| `material.py` | `MaterialSchema`, `MaterialCreateSchema`, `MaterialUpdateSchema` |
| `ficha.py` | `FichaTecnicaSchema`, `FichaTecnicaCreateSchema`, `FichaTecnicaUpdateSchema`, `CambioEstadoRequest` |
| `kitem_relacion.py` | `KItemRelacionSchema`, `KItemRelacionCreateSchema`, `KItemRelacionDetalleSchema` |
| `kitem_auditoria.py` | `AuditoriaSchema`, `AuditoriaResumenSchema` |
| `anomalia.py` | `AnomaliaRegistroSchema`, `AnalizarFichaRequest`, `ResultadoAnalisis`, `AnomaliaListResponse` |
| `semantic_search.py` | `BusquedaSemanticaRequest`, `BusquedaSemanticaResponse`, `DeteccionDuplicadosRequest/Response` |

## Secciones JSONB en fichas

Los campos JSONB (`caracteristicas`, `caracteristicas_contenido`, etc.) usan `extra="allow"` en el esquema de creación para aceptar cualquier campo sin validación estricta. Esto permite que la forma del contenido varíe por tipo de producto sin requerir migraciones de esquema.

## Patrón AnomaliaResumen

Los endpoints de creación/actualización de fichas y materiales retornan las anomalías detectadas en la misma respuesta, embebidas como `anomalias: list[AnomaliaResumen]`. Esto evita un round-trip adicional desde el frontend.
