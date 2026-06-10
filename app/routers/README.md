# app/routers/ — Endpoints API

## Mapa de rutas

### Fichas (`/ficha`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/ficha` | Listar todas |
| POST | `/ficha` | Crear (dispara embedding + anomalías) |
| GET | `/ficha/buscar` | Buscar con filtros (país, estado, tipo) |
| GET | `/ficha/{id}` | Detalle |
| PATCH | `/ficha/{id}` | Actualizar secciones JSONB |
| PATCH | `/ficha/{id}/estado` | Cambiar estado (máquina de estados) |
| GET | `/ficha/{id}/rangos-tipicos` | Estadísticas de rangos del mismo material |
| POST | `/ficha/{id}/imagen` | Subir imagen (multipart) |
| GET | `/ficha/{id}/imagen/{tipo}` | Obtener imagen |
| DELETE | `/ficha/{id}/imagen/{tipo}` | Eliminar imagen |

### Materiales (`/material`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/material` | Listar todos |
| POST | `/material` | Crear |
| GET | `/material/{id}` | Detalle |
| PATCH | `/material/{id}` | Actualizar |
| PATCH | `/material/{id}/estado` | Cambiar estado |

### Anomalías (`/anomalias`)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/anomalias/entrenar` | Entrenar Isolation Forest con fichas existentes |
| POST | `/anomalias/analizar/ficha` | Ejecutar detectores sobre una ficha |
| POST | `/anomalias/analizar/material` | Ejecutar detectores sobre un material |
| GET | `/anomalias/` | Listar con filtros (ktype, tipo, severidad, estado) |
| GET | `/anomalias/kitem/{id}` | Anomalías de un k-item |
| PATCH | `/anomalias/{id}/resolver` | Marcar como aceptada/descartada/corregida |

### Búsqueda semántica (`/dsms/semantica`)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/dsms/semantica/buscar` | Búsqueda por texto libre (coseno via pgvector) |
| POST | `/dsms/semantica/duplicados` | Detección de duplicados pre-creación |
| GET | `/dsms/semantica/similares/{id}` | K-items similares a uno dado |
| POST | `/dsms/semantica/reindexar/{id}` | Regenerar embedding de un k-item |
| POST | `/dsms/semantica/reindexar` | Reindexación masiva |
| GET | `/dsms/semantica/estadisticas` | Cobertura de embeddings |

### Grafo (`/dsms`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dsms/kitems` | Listar k-items con filtros |
| GET | `/dsms/kitems/{id}` | Detalle de k-item |
| GET | `/dsms/kitems/{id}/grafo` | Nodo + todas sus relaciones |
| POST | `/dsms/relaciones` | Crear relación semántica |
| GET | `/dsms/kitems/{id}/relaciones` | Relaciones de un k-item |
| DELETE | `/dsms/relaciones/{id}` | Eliminar relación |

### Auditoría (`/dsms/auditoria`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dsms/auditoria/actividad` | Actividad reciente con filtros |
| GET | `/dsms/auditoria/kitem/{id}` | Historial de un k-item |

### Auth (`/auth`)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Login LDAP → JWT |
| GET | `/auth/me` | Usuario autenticado actual |

### Exportación (`/dsms/export`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dsms/export/ficha/{id}/pdf` | Exportar ficha a PDF |
| GET | `/dsms/export/fichas/excel` | Exportar todas las fichas a Excel |
