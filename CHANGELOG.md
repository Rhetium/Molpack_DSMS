# CHANGELOG

## [Unreleased]

### Añadido
- **`material_comercial`**: nuevas columnas `sector` (TEXT) y `caracteristica` (TEXT). Disponibles en formularios de creación/edición y en el detalle del material.
- **`ficha_tecnica`**: nueva columna `nombre_local_material` (TEXT). Visible en Paso 0 del wizard de creación y en el header del detalle de ficha.
- **`scripts/migration_001_material_columnas.sql`**: script de migración para aplicar los cambios sobre una BD existente (`ALTER TABLE` con `IF NOT EXISTS / IF EXISTS`).

### Eliminado
- **`color_base`** de `material_comercial` — ahora el color se registra en `caracteristicas.color` de la ficha técnica.

---

### Añadido (sesión anterior)
- **ML — Detección multivariada** (`MLAnomaliaService`): Isolation Forest entrenado con fichas existentes. Modelo global + modelos por categoría (≥5 fichas). Pipeline: `SimpleImputer → StandardScaler → IsolationForest`. Endpoint `POST /anomalias/entrenar`.
- **N/C en microbiología**: Los 9 parámetros microbiológicos (recuento aeróbico, moho, coliformes, E. coli, salmonella, cadmio, plomo, mercurio, cromo) ahora soportan marcado N/C desde el wizard de fichas.
- **Scripts de BD**: `scripts/create_tables.sql` (DDL completo idempotente) y `scripts/truncate_all.sql` (limpieza de datos de prueba).
- **READMEs por módulo**: Documentación técnica en `app/`, `app/core/`, `app/models/`, `app/routers/`, `app/schemas/`, `app/services/`, `app/ml_models/`, `frontend/src/`, `scripts/`.

### Corregido
- **Layout Paso 2 (Contenido)**: El campo "Calibre/Tamaño" se montaba sobre el dropdown de unidad de "Peso del contenido". Corregido cambiando `grid-cols-3` a `grid-cols-2` (máximo 2 campos visibles simultáneamente).
- **Navegación post-creación**: Al confirmar "agregar imágenes" tras crear una ficha, redirigía al wizard de creación en lugar del detalle. Ahora navega a `/fichas/{id}?tab=imagenes` y el detalle inicializa la tab desde el query param.
- **Vista de detalle — filtrado de campos**: `agruparCampos()` ahora omite claves `_nc`, valores booleanos y strings vacíos. Los campos marcados N/C y los campos irrelevantes al tipo de producto ya no aparecen en la tabla de detalle.
- **Imágenes en detalle**: La tab de imágenes en `FichaDetallePage` ahora permite subir y eliminar imágenes (antes estaba en modo solo lectura).

---

## [2026-03-27] — Auth and fixes (`561f0faa`)

### Añadido
- Autenticación LDAP/Active Directory con fallback JWT.
- `AuthService` y router `/auth` (login + `/auth/me`).
- Protección de rutas en el frontend con `AuthProvider`.

---

## [2026-03-06] — Módulo de Grafos y Cambios de Atributos (`d4bff11d`)

### Añadido
- Router `/dsms` para exploración del grafo: listar k-items, obtener grafo de un nodo, crear/eliminar relaciones.
- `KItemService`: CRUD de k-items y relaciones semánticas.
- Frontend `GrafoPage`: visualización interactiva del grafo de conocimiento.
- Cambio de estado de materiales desde el frontend (`PATCH /material/{id}/estado`).

---

## [2026-03-04] — Front y Módulo de Grafos (`07dd4de9`)

### Añadido
- Layout principal con sidebar de navegación (`MainLayout.jsx`).
- Páginas de fichas: lista, detalle, crear, editar.
- Páginas de materiales: lista, detalle, crear, editar.
- `FichaCrearPage`: wizard de 5 pasos con validación Zod.
- Página de búsqueda semántica (`BusquedaPage`).
- Página de auditoría (`AuditoriaPage`).

---

## [2026-02-24] — Embedding Module (`34e9a294`)

### Añadido
- `EmbeddingService`: generación de vectores 384D con `sentence-transformers/all-MiniLM-L6-v2`.
- Columna `embedding VECTOR(384)` en `kitem` (pgvector).
- `BusquedaSemanticaService`: búsqueda coseno, detección de duplicados, reindexación.
- Router `/dsms/semantica` con endpoints de búsqueda y estadísticas.

---

## [2026-02-22] — Modificaciones DSMS (`6f1de2b2`)

### Añadido
- `AnomaliaService`: detectores 1-5 (z-score, unidades, clasificación cruzada, duplicados semánticos, perfil cruzado).
- `AuditoriaService` + router `/dsms/auditoria`.
- `ExportService`: exportación a PDF y Excel.
- Router `/dsms/export`.

---

## [2026-02-04] — DSMS v1 (`220ac988`)

### Añadido
- Esquema de BD completo: `kitem`, `material_comercial`, `ficha_tecnica`, `kitem_relacion`, `kitem_auditoria`, `anomalia_registro`.
- Modelos ORM SQLAlchemy 2.0 (async).
- Esquemas Pydantic v2 para todos los modelos.
- `FichaService` y `MaterialService` con lógica de máquina de estados.
- Routers `/ficha` y `/material`.

---

## [2026-02-03] — InitialDev (`fc2b9285`)

### Añadido
- Estructura inicial del proyecto FastAPI + React.
- Configuración de entorno: `.env`, `requirements.txt`, `vite.config.js`.
- `app/main.py` con registro de routers.
