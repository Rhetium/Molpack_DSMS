# app/ — Backend FastAPI

## Módulos

| Módulo | Responsabilidad |
|---|---|
| `core/` | Configuración transversal: DB engine, constantes, auth, deps |
| `models/` | Modelos ORM (SQLAlchemy 2.0 async) |
| `schemas/` | Esquemas Pydantic v2 (request/response) |
| `services/` | Lógica de negocio — una clase por dominio |
| `routers/` | Endpoints FastAPI — capa delgada sobre services |
| `ml_models/` | Archivos `.pkl` de Isolation Forest (generados en runtime) |

## Convenciones

- Toda mutación pasa por `KItemService` antes del servicio de dominio; esto garantiza que el embedding y la auditoría se generen siempre.
- Los routers no contienen lógica: validan la request con Pydantic y delegan al service correspondiente.
- Los servicios son stateless; reciben `AsyncSession` por inyección en cada request.
- Los esquemas usan `model_config = ConfigDict(from_attributes=True)` para ser compatibles con ORM objects via `model_validate`.

## Orden de dependencias

```
routers → services → models
                   ↘ schemas (solo para tipado de entrada/salida)
```
