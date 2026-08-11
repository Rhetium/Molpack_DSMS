# Reporte Técnico — Molpack DSMS

> Documento de referencia del sistema tal como está implementado en el código.
> Pensado para contrastar contra el tomo de trabajo de grado y verificar que la
> descripción escrita coincide con la realidad del software.
>
> Fecha de generación: 2026-07-09 · Rama: `Development`

---

## 1. Resumen del sistema

**Molpack DSMS** (*Dataspace Management System*) es un sistema de gestión del
conocimiento para materiales técnicos y sus fichas de especificación en Molpack
Corporation. Combina:

- Un **modelo de datos universal tipo "K-Item"** (supertipo único para todas las
  entidades de conocimiento).
- **Búsqueda semántica** mediante embeddings vectoriales (pgvector +
  sentence-transformers).
- Un **flujo de trabajo dirigido por máquina de estados** para las fichas técnicas.
- **Detección de anomalías** híbrida (estadística + reglas + Machine Learning).
- **Trazabilidad / auditoría** inmutable de todas las mutaciones.
- Un **grafo de conocimiento** de relaciones entre entidades.

El código y las docstrings están redactados principalmente en **español**.

### Fundamento teórico

La arquitectura se basa explícitamente en el paper de **DSMS de Nahshon et al.
(2023)**, citado directamente en las docstrings del código
([app/models/kitem.py](../app/models/kitem.py),
[app/models/kitem_relacion.py](../app/models/kitem_relacion.py),
[app/services/embedding_service.py](../app/services/embedding_service.py),
[app/services/semantic_search_service.py](../app/services/semantic_search_service.py),
[app/services/auditoria_service.py](../app/services/auditoria_service.py)). Los conceptos del paper mapeados al
código son:

| Concepto del paper (Nahshon et al., 2023) | Implementación en el código |
|---|---|
| **K-Item = Metadata + Data Container + Semantic Graph** (Fig. 3) | Tabla `kitem` (metadata) + tablas de extensión JSONB (data container) + `kitem_relacion` (grafo) |
| **K-Item linkage** (Sec. 2.3.2) | Modelo `KItemRelacion` (grafo dirigido) |
| **Semantic Search** (Sec. 2.3.4) | `BusquedaSemanticaService` + columna `embedding` pgvector |
| **Integration Level 4** (detección de anomalías) | `AnomaliaService` + `MLAnomaliaService` |
| **Provenance and traceability** | `AuditoriaService` + tabla `kitem_auditoria` |

---

## 2. Stack tecnológico

### Backend (Python) — `requirements.txt`

| Categoría | Tecnología | Versión | Rol |
|---|---|---|---|
| Framework web | **FastAPI** | 0.115.0 | API REST asíncrona |
| Servidor ASGI | **uvicorn[standard]** | 0.30.0 | Servidor de aplicación |
| ORM | **SQLAlchemy** | 2.0.36 | Mapeo objeto-relacional (modo async) |
| Driver BD | **asyncpg** | 0.30.0 | Conexión asíncrona a PostgreSQL |
| Validación | **Pydantic** | 2.9.0 | Schemas request/response |
| Config | **python-dotenv** | 1.0.1 | Variables de entorno (`.env`) |
| Países | **pycountry** | 22.3.5 | Normalización de países a ISO-2 |
| ML | **scikit-learn** | 1.5.0 | Isolation Forest, pipeline de preprocesado |
| Persistencia ML | **joblib** | 1.4.2 | Serialización de modelos `.pkl` |
| Vectores | **pgvector** | 0.3.6 | Tipo `Vector` + distancia coseno en PostgreSQL |
| Embeddings | **sentence-transformers** | 3.0.1 | Modelo `all-MiniLM-L6-v2` (384D) |
| Numérico | **numpy** | ≥1.26.0 | Álgebra vectorial |
| Auth (implícito) | **PyJWT**, **ldap3** | — | JWT (HS256) y LDAP/Active Directory |
| Exportación (implícito) | **reportlab**, **pypdf**, **openpyxl** | — | Generación de PDF y Excel |

> Base de datos: **PostgreSQL** con la extensión **pgvector** habilitada.

### Frontend (JavaScript) — `frontend/package.json`

| Tecnología | Versión | Rol |
|---|---|---|
| **React** | 19.2 | Librería de UI |
| **Vite** | 7.3 | Build tool / dev server |
| **React Router DOM** | 7.13 | Enrutamiento SPA |
| **Axios** | 1.13 | **Cliente HTTP real** (con interceptores JWT) — mecanismo de fetching en uso |
| **Tailwind CSS** | 4.2 | Estilos utilitarios |
| **lucide-react** | 0.575 | Iconografía |
| **ESLint** | 9.39 | Linting |
| **TanStack React Query** | 5.90 | ⚠️ Declarada; solo se monta el `QueryClientProvider` — **sus hooks no se usan** |

> **Verificado en código (importante para el tomo):** el fetching de datos se hace
> con **Axios + `useState`/`useEffect`** en cada página; los formularios con
> `useState` y `<form>` nativo. `@tanstack/react-query` figura como dependencia
> pero **no está integrada** en el código (ver Sección 10).
>
> `react-hook-form`, `@hookform/resolvers`, `zod` y `sonner` también estaban
> declaradas sin ningún uso; se desinstalaron en la limpieza de dependencias.

### Testing

| Tecnología | Versión | Rol |
|---|---|---|
| **pytest** | 9.1.1 | Framework de pruebas unitarias |
| **pytest-asyncio** | 1.4.0 | Soporte para pruebas `async` |

---

## 3. Estructura del proyecto

```
app/
├── main.py            Punto de entrada FastAPI, registro de routers + auth global
├── core/              Infraestructura transversal
│   ├── database.py        Engine async + sessionmaker + Base declarativa
│   ├── security.py        JWT (HS256) + RateLimiter en memoria
│   ├── deps.py            Inyección de dependencias
│   ├── utils.py           nombre_pais_a_iso (normalización de países)
│   ├── dsms_constants.py  Estados, transiciones, tipos de relación, acciones
│   └── anomalia_constant.py  Umbrales, campos, rangos por categoría
├── models/            ORM SQLAlchemy (patrón K-Item)
│   ├── kitem.py           Supertipo universal (+ columna embedding 384D)
│   ├── material.py        MaterialComercial (extensión de kitem)
│   ├── ficha.py           FichaTecnica (extensión de kitem)
│   ├── kitem_relacion.py  Grafo dirigido de conocimiento
│   ├── kitem_auditoria.py Log inmutable de mutaciones
│   └── anomalia.py        Repositorio histórico de anomalías
├── schemas/           Pydantic (request/response)
├── services/          Lógica de negocio (un servicio por dominio)
│   ├── kitem_service.py         CRUD de k-items + relaciones + auditoría
│   ├── material_service.py      Dominio de materiales
│   ├── fichas_services.py       Dominio de fichas + máquina de estados
│   ├── embedding_service.py     Generación de embeddings (funciones puras)
│   ├── semantic_search_service.py  Búsqueda semántica + duplicados
│   ├── anomalia_service.py      Orquestador de 7 detectores
│   ├── ml_anomalia_service.py   Isolation Forest (entrenamiento + predicción)
│   ├── auditoria_service.py     Registro de auditoría (interno)
│   ├── auth_service.py          Login LDAP + fallback local
│   └── export_service.py        PDF (reportlab/pypdf) + Excel (openpyxl)
├── routers/           Endpoints FastAPI (capa fina sobre servicios)
└── ml_models/         Modelos Isolation Forest serializados (.pkl)

frontend/
├── lib/           Cliente Axios (interceptores JWT) + contexto de auth  (¡fuera de src/!)
│   ├── api.js
│   └── auth.jsx
└── src/
    ├── layouts/   MainLayout (sidebar + shell)
    └── pages/     Una carpeta por feature: fichas, materiales, anomalias,
                   busqueda, grafo, auditoria, dashboard, auth, dev

scripts/       SQL de esquema + migraciones + seed
tests/         Pruebas unitarias (pytest)
```

---

## 4. Modelo de datos

### 4.1 Patrón K-Item (supertipo/subtipo)

Todas las entidades de conocimiento son un **K-Item**. La tabla `kitem`
centraliza la metadata común; las tablas de dominio la extienden mediante una
**clave foránea que es a la vez clave primaria** (herencia de tabla por
delegación / *joined-table inheritance* manual).

```
              ┌─────────────────────────────┐
              │           kitem             │  ← supertipo universal
              │  id (PK, UUID)              │
              │  ktype, nombre, descripcion │
              │  estado                     │
              │  metadata_extra (JSONB)     │
              │  embedding (Vector 384)     │  ← pgvector
              │  usuario_creador / _actual. │
              │  fecha_creacion / _actual.  │
              └──────────────┬──────────────┘
                 ┌───────────┴───────────┐
     ┌───────────▼──────────┐   ┌────────▼─────────────┐
     │  material_comercial  │   │    ficha_tecnica     │
     │  id → kitem.id (PK/FK)│  │  id_ficha → kitem.id │
     │  nombre_corporativo  │   │  id_material → material
     │  categoria, contenido│   │  codigo_*, pais, ver.│
     │  material_base, ...  │   │  5 secciones JSONB   │
     └──────────────────────┘   └──────────────────────┘
```

**Detalle clave — "única fuente de verdad":** el estado, los usuarios y las
fechas viven **solo** en `kitem`. Los modelos de dominio exponen esos campos como
**propiedades proxy** (`estado_ficha`, `estado_material`, `fecha_registro`,
etc.) que leen/escriben sobre `self.kitem`. Esto evita duplicar el estado del
ciclo de vida en dos tablas. (Ver [app/models/ficha.py](../app/models/ficha.py)
líneas 61-99 y [app/models/material.py](../app/models/material.py) líneas 44-67.)

### 4.2 Tablas

| Tabla | Rol | Campos destacados |
|---|---|---|
| `kitem` | Supertipo universal | `embedding` (Vector 384), `metadata_extra` (JSONB), estado, auditoría |
| `material_comercial` | Materiales (extiende kitem) | categoria, contenido, material_base, tipo_producto, sector |
| `ficha_tecnica` | Fichas (extiende kitem) | codigo_ficha_local, codigo_version, pais + 5 secciones JSONB |
| `kitem_relacion` | Grafo dirigido | source_id, target_id, tipo_relacion, metadata_relacion (JSONB) |
| `kitem_auditoria` | Log inmutable | accion, estado_anterior/nuevo, detalles (JSONB), usuario, fecha |
| `anomalia_registro` | Historial de anomalías | tipo_anomalia, severidad, estado, campo/valor detectado, detalles (JSONB) |

Las 5 secciones JSONB de `ficha_tecnica` son: `caracteristicas`,
`caracteristicas_contenido`, `empaque_estiba`, `microbiologia`,
`manejo_disposicion`.

### 4.3 Grafo de conocimiento — tipos de relación

Definidos en [app/core/dsms_constants.py](../app/core/dsms_constants.py):

| Relación | Semántica | Origen → Destino |
|---|---|---|
| `pertenece_a` | Ficha pertenece a un material | FichaTecnica → MaterialComercial |
| `se_deriva_de` | Versionamiento | FichaTecnica → FichaTecnica |
| `es_variante_de` | Variante de material | Material → Material |
| `relacionado_con` | Relación genérica | cualquier par |
| `semanticamente_similar` | Descubierta por embeddings | cualquier par |

---

## 5. Patrones de diseño y arquitectura

| Patrón | Dónde | Descripción |
|---|---|---|
| **Arquitectura por capas** | routers → services → models | Routers finos; toda la lógica de negocio en la capa de servicios |
| **Service Layer** | `app/services/` | Un servicio por dominio, orquestando persistencia + colaboradores |
| **Supertipo/Subtipo (K-Item)** | `models/` | Herencia de tabla por FK-que-es-PK |
| **Propiedades Proxy** | `ficha.py`, `material.py` | `estado_ficha`/`estado_material` delegan en `kitem` |
| **Inyección de dependencias** | FastAPI `Depends` | Sesión de BD y servicios inyectados por request |
| **Singleton** | `embedding_service.get_embedding_model()` | El modelo de embeddings se carga una sola vez en memoria |
| **Strategy / detectores intercambiables** | `AnomaliaService` (7 detectores) | Cada detector es un método independiente compuesto en el orquestador |
| **Máquina de estados** | `fichas_services.py` + `TRANSACCIONES_PERMITIDAS` | Transiciones estrictas validadas centralmente |
| **Caché** | `MLAnomaliaService._cache` + archivo cooldown | Evita recargar modelos y reentrenar en exceso |
| **Tareas en segundo plano** | `asyncio.create_task` | Reentrenamiento ML al publicar una ficha (no bloquea la request) |
| **Auditoría transversal** | `AuditoriaService` (interno) | Registro automático desde los servicios de dominio |

### Flujo de datos (crear/actualizar)

```
Formulario React (estado con useState)
  → POST/PATCH /api/<recurso>   (Axios + JWT)
    → Router (valida auth, delega)
      → Service: valida reglas de estado, persiste vía SQLAlchemy
        → EmbeddingService: genera y almacena vector 384D
        → AnomaliaService: ejecuta detectores 1-7
        → AuditoriaService: registra la acción
      ← Respuesta + lista de anomalías
```

---

## 6. Algoritmos implementados

Esta es la sección de mayor interés para el tomo. Cada algoritmo está descrito
tal como aparece en el código, con sus parámetros exactos.

### 6.1 Embeddings semánticos

- **Modelo:** `all-MiniLM-L6-v2` (sentence-transformers), local, gratuito,
  licencia Apache 2.0. Dimensión **384**.
- **Construcción del texto** (`construir_texto_embedding`): concatena
  `[KTYPE] nombre`, descripción, campos adicionales del k-type
  (`clave: valor | ...`) y metadata útil (`tags`, `keywords`, `sector`,
  `aplicacion`, `notas`).
- **Normalización:** los embeddings se generan con
  `normalize_embeddings=True` (vectores unitarios → el producto punto equivale
  a la similitud coseno).
- **Batch:** `generar_embeddings_batch` con `batch_size=64` para reindexación
  masiva.
- Referencia: [app/services/embedding_service.py](../app/services/embedding_service.py).

### 6.2 Similitud coseno / búsqueda vectorial

- En BD se usa el operador **coseno de pgvector**:
  `KItem.embedding.cosine_distance(vector)`, y la similitud se calcula como
  **`similitud = 1 − distancia_coseno`**.
- Los resultados se ordenan por distancia ascendente y se filtran por
  `umbral_similitud`.
- Fuera de BD existe `calcular_similitud_coseno` (numpy):
  `dot(a,b) / (‖a‖·‖b‖)`.
- Referencia: [app/services/semantic_search_service.py](../app/services/semantic_search_service.py) líneas 121-277.

### 6.3 Detección de anomalías — 7 detectores

Orquestados en `AnomaliaService.analizar_ficha`
([app/services/anomalia_service.py](../app/services/anomalia_service.py)):

**D1 — Valor atípico (Z-score).**
Compara cada campo numérico contra las fichas de la misma categoría.
- Requiere `MIN_MUESTRAS_ESTADISTICAS = 3` fichas de referencia.
- Media y **varianza poblacional** (`Σ(v−μ)² / N`), `σ = √varianza`.
- `z = |valor − μ| / σ`. Umbrales: `z ≥ 3.0` → **crítica**, `z ≥ 2.0` →
  **advertencia**, si no → normal.
- Caso `σ = 0` (todos los valores iguales): si el nuevo difiere → advertencia.

**D2 — Unidad inconsistente.**
Detecta cuando la unidad usada no coincide con la mayoritaria del histórico.
- Requiere ≥3 muestras. Se activa si la unidad mayoritaria tiene
  `≥ PORCENTAJE_UNIDAD_MAYORITARIA = 70%` de uso y la ficha usa otra distinta.

**D3 — Duplicado semántico.**
Busca k-items casi idénticos por similitud coseno.
- Fichas: `UMBRAL_DUPLICADO_FICHA = 0.95` (advertencia),
  `UMBRAL_DUPLICADO_FICHA_CRITICO = 0.98` (crítica).
- Materiales: `0.90` / `0.95`.
- Para fichas se **excluyen** las del mismo material (es normal que sean
  similares); solo alerta si materiales distintos son casi idénticos.

**D4 — Clasificación cruzada.**
Un material parece pertenecer a otra categoría.
- Señal semántica: similitud `≥ UMBRAL_CLASIFICACION_CRUZADA = 0.85` con
  materiales de otra categoría.
- Señal dimensional (`_tiene_evidencia_dimensional`): si las dimensiones de la
  ficha **encajan** en la categoría sugerida y **no** en la declarada, sube la
  severidad a crítica.

**D5 — Perfil numérico cruzado.**
Compara el vector numérico de la ficha contra los **centroides** de cada
categoría usando **distancia euclidiana normalizada por σ**:
`d = √( Σ((vᵢ − cᵢ)/σᵢ)² / n )`.
- Si otra categoría está `>30%` más cerca (`ratio < 0.7`) → advertencia;
  `ratio < 0.4` → crítica.

**D6 — Isolation Forest (multivariado).** Ver 6.4.

**D7 — Rango por categoría.**
Valida dimensiones contra rangos duros predefinidos por categoría (no requiere
histórico). Categorías con rangos: **Separador, Porta vasos, Estuche, Bandeja**
([app/core/anomalia_constant.py](../app/core/anomalia_constant.py) líneas 106-135).
- Fuera de rango → advertencia; muy fuera (`valor < min·0.5` o `valor > max·2`)
  → crítica.
- El lookup de categoría es **tolerante a mayúsculas/espacios**
  (`rangos_para_categoria`): "Porta vasos", "Portavasos" y "PORTA VASOS" son
  equivalentes.

### 6.4 Isolation Forest (ML multivariado)

[app/services/ml_anomalia_service.py](../app/services/ml_anomalia_service.py):

- **Pipeline scikit-learn:** `SimpleImputer(strategy="mean")` →
  `StandardScaler` → `IsolationForest(n_estimators=100, contamination=…,
  random_state=42)`.
- **Contaminación adaptativa:** `contamination = clip(1/n, 0.05, 0.10)`.
- **Selección de columnas:** solo se usan campos con **≥30% de datos no nulos**
  (evita imputar sobre columnas casi vacías).
- **Vector de features:** longitud fija con todos los campos numéricos de
  `caracteristicas + contenido + empaque`; `NaN` donde falta dato o está marcado
  N/C.
- **Modelos:** uno **global** (todas las fichas) + uno **por categoría** cuando
  esa categoría alcanza `MIN_MUESTRAS_ML = 5` fichas. Prioridad en predicción:
  categoría → global → sin modelo.
- **Score:** `decision_function` (más negativo = más anómalo). Umbrales:
  `≤ ML_SCORE_CRITICO = −0.15` → crítica; `≤ ML_SCORE_ADVERTENCIA = −0.05`.
- **Persistencia:** `joblib.dump` en `app/ml_models/*.pkl`; caché en memoria por
  request.
- **Reentrenamiento automático:** al publicar una ficha a **Vigente**, se lanza
  una tarea de fondo (`asyncio.create_task`) con **cooldown de 1 hora**
  (archivo `.last_training`).

### 6.5 Normalización de países

`nombre_pais_a_iso` ([app/core/utils.py](../app/core/utils.py)): acepta código
ISO-2 directo o nombre legible (búsqueda difusa con pycountry
`search_fuzzy`); devuelve siempre ISO-2 o lanza HTTP 400.

---

## 7. Máquina de estados — FichaTecnica

Definida en [app/core/dsms_constants.py](../app/core/dsms_constants.py) y
aplicada en [app/services/fichas_services.py](../app/services/fichas_services.py).

```
   ┌──────────┐   ┌────────────┐   ┌─────────┐   ┌──────────┐
   │ Borrador │──▶│ Preliminar │──▶│ Vigente │──▶│ Obsoleto │
   └────┬─────┘   └─────┬──────┘   └────┬────┘   └────┬─────┘
        │               │               │            │
        └──▶ Obsoleto ◀─┘               └─▶ Obsoleto  ▼
                                              ┌──────────┐
        Revisión ⇄ {Obsoleto, Preliminar} ◀──│ Revisión │
                                              └──────────┘
```

**Transiciones permitidas (`TRANSACCIONES_PERMITIDAS`):**

| Estado actual | Estados destino permitidos |
|---|---|
| Borrador | Preliminar, Obsoleto |
| Preliminar | Vigente, Obsoleto |
| Vigente | Obsoleto |
| Obsoleto | Revisión |
| Revisión | Obsoleto, Preliminar |

**Reglas de negocio asociadas:**

- **No se puede saltar** de Borrador directo a Vigente (debe pasar por
  Preliminar).
- **Validación de completitud** al avanzar:
  - A *Preliminar*: exige código local, país, nombre local, características
    físicas y los 5 campos de manejo (uso, manejo, almacenamiento, transporte,
    vida útil).
  - A *Vigente*: todo lo anterior **más** tipo de empaque definido.
- **Unicidad:** solo puede existir **una ficha Vigente por material + país**.
- **Bloqueo por anomalías:** no se cambia de estado si hay anomalías
  **pendientes** sin resolver.
- **Al pasar a Preliminar:** se regenera el embedding con datos ricos y se
  ejecutan los detectores (antes del commit, para que un fallo revierta la
  transición).
- **Edición de una ficha Vigente:** no se edita en sitio; se **crea una nueva
  versión** (en Preliminar) y la anterior pasa **automáticamente a Obsoleto**,
  con relación `se_deriva_de` en el grafo.
- **Versionado:** `_incrementar_version_simple` sube la versión mayor
  (`1.0 → 2.0`, `3.5 → 4.0`).
- **Código de ficha:** formato
  `FT-{codigo_local}-{PAIS}-{ABREV_ESTADO}-V{version}` (p. ej.
  `FT-MAT-001-CO-BOR-V1.0`).

---

## 8. Seguridad y autenticación

[app/core/security.py](../app/core/security.py) y
[app/services/auth_service.py](../app/services/auth_service.py):

- **JWT** firmado con **HS256**, expiración configurable (default **8 horas**).
  El payload incluye usuario, nombre, rol, iniciales, email, `iat`, `exp`.
- **Autenticación híbrida:** primero **LDAP / Active Directory** (librería
  `ldap3`: bind de servicio → búsqueda por `sAMAccountName` → bind del usuario →
  verificación de grupo autorizado → extracción de rol); si LDAP no está
  configurado o falla, **fallback a usuarios locales**.
- **Rate limiting en memoria** (`RateLimiter`): máx. **5 intentos fallidos** por
  IP en ventana de **60 s**; tras excederlos, bloqueo de **300 s** (HTTP 429).
- **Protección global:** en [app/main.py](../app/main.py) todos los routers de
  datos llevan `Depends(get_usuario_actual)`. Excepciones: `/auth/login`
  (público) y el `GET` de imágenes (se sirve vía `<img src>` sin header
  Authorization).

> Nota de seguridad: `JWT_SECRET` y los usuarios locales tienen valores por
> defecto de desarrollo y deben configurarse por entorno en producción.

---

## 9. API REST — inventario de endpoints

| Prefijo (router) | Endpoints |
|---|---|
| `/auth` | `POST /login`, `GET /me`, `POST /refresh` |
| `/material` | `GET ""`, `GET /{id}`, `POST ""`, `PATCH /{id}`, `PATCH /{id}/estado` |
| `/ficha` | `GET ""`, `POST ""`, `GET /buscar`, `GET /{id}`, `GET /{id}/versiones`, `POST /{id}/aprobar-inicial`, `POST /{id}/publicar`, `POST /{id}/archivar`, `POST /{id}/nueva-version`, `PATCH /{id}`, `PATCH /{id}/estado`, `GET /{id}/rangos-tipicos` |
| `/ficha` (imágenes) | `POST /{id}/imagen`, `GET /{id}/imagen/{tipo}`, `DELETE /{id}/imagen/{tipo}` |
| `/dsms` | `GET /kitems`, `GET /kitems/{id}`, `GET /kitems/{id}/grafo`, `POST /relaciones`, `GET /relaciones...`, `DELETE /relaciones/{id}` |
| `/dsms/semantica` | búsqueda por texto, similares, detección de duplicados, reindexación, estadísticas |
| `/dsms/auditoria` | `GET /actividad`, `GET /kitem/{id}` |
| `/anomalias` | `GET /debug/{id}`, `POST /entrenar`, `POST /analizar/ficha`, `POST /analizar/material`, `GET /`, `GET /kitem/{id}`, `PATCH /{id}/resolver` |
| `/dsms/export` | `GET /ficha/{id}/pdf`, `GET /fichas/excel` |

---

## 10. Frontend

> Esta sección se corrigió tras auditar el código: **difiere de lo que afirmaban
> los README** (ver 10.5). Todo lo aquí descrito está verificado en los archivos
> `.jsx` reales.

### 10.1 Base

- **SPA React 19** servida por **Vite 7**, con proxy de `/api` al backend
  (`http://127.0.0.1:8000`).
- **Enrutamiento** con **React Router 7** ([frontend/src/App.jsx](../frontend/src/App.jsx)):
  rutas públicas (`/login`) y protegidas mediante el componente
  `RutaProtegida` (redirige a `/login` si no hay usuario).
- Los archivos de infraestructura están en **`frontend/lib/`** (fuera de `src/`),
  no en `src/lib/`.

### 10.2 Fetching de datos — Axios (no TanStack Query)

- **Cliente HTTP** centralizado en [frontend/lib/api.js](../frontend/lib/api.js):
  instancia de Axios con `baseURL = /api` e **interceptores**:
  - *request*: inyecta `Authorization: Bearer <token>` leyendo
    `localStorage['dsms_token']`.
  - *response*: ante un **401** limpia el token/usuario y redirige a `/login`.
- **Cada página obtiene sus datos** con `useState` + `useEffect` llamando a
  `api.get/post/patch/delete` (patrón visible en las 17 páginas, p. ej.
  [MaterialesPage.jsx](../frontend/src/pages/materiales/MaterialesPage.jsx)).
  El filtrado de listas se hace en cliente con `Array.filter`.
- **TanStack Query:** se crea un `QueryClient` y se envuelve la app en
  `<QueryClientProvider>` en `App.jsx`, **pero no se usa ninguno de sus hooks**
  (`useQuery`, `useMutation`, etc.). Es infraestructura montada, no utilizada.

### 10.3 Formularios y autenticación

- **Formularios:** manejados con **`useState` y `<form>`/`onSubmit` nativos**,
  con funciones propias `handleSubmit` (p. ej. `MaterialCrearPage.jsx`,
  `FichaCrearPage.jsx`, `LoginPage.jsx`). **No se usa React Hook Form ni Zod**;
  la validación fuerte de datos vive en el backend (Pydantic + reglas de
  servicio).
- **Autenticación:** Context API propio en
  [frontend/lib/auth.jsx](../frontend/lib/auth.jsx) (`AuthProvider` + `useAuth`).
  Guarda `dsms_token` y `dsms_user` en `localStorage` y verifica la expiración
  **decodificando el payload del JWT en el cliente** (`atob` del segmento
  central). Expone `{ user, cargando, login, logout }`.

### 10.4 Páginas y componentes destacados

- `fichas/` — asistente por pasos (`PasosFicha.jsx`), crear/editar/detalle
  (tabs por sección), imágenes (`ImagenesFicha.jsx`), y un `AsistenteIA.jsx`.
  Manejo de campos "N/C" persistidos como `{campo_nc: true}` en el JSONB.
- `materiales/`, `anomalias/`, `busqueda/` (búsqueda semántica), `auditoria/`,
  `dashboard/`, `auth/` (login), `dev/` (panel de depuración de anomalías).
- `grafo/` — **visualización propia del grafo de conocimiento dibujada sobre un
  `<canvas>` 2D** ([GrafoPage.jsx](../frontend/src/pages/grafo/GrafoPage.jsx)):
  render manual de nodos (Categoría / Material / Ficha, coloreados por estado) y
  enlaces (`pertenece_a`, `se_deriva_de`), con zoom. **No usa librería de
  grafos** (d3, vis.js, etc.).
- **Estilos:** Tailwind CSS 4. **Iconos:** lucide-react. **Notificaciones:** no
  hay librería de toasts; los mensajes de error/éxito se renderizan inline en
  cada página con `useState`. **Store global:** no hay; solo Context de auth +
  `useState` local por componente.

### 10.5 Discrepancias corregidas respecto a los README

| Afirmación previa (README/tomo) | Realidad del código |
|---|---|
| "Server state con TanStack Query (`useQuery`, `useMutation`)" | Solo el Provider montado; fetching real con **Axios + useState/useEffect** |
| "Formularios con React Hook Form + Zod" | `useState` + `<form>` nativo; **RHF/Zod no se importan** |
| `useAuth` expone `{ …, isAuthenticated }` | Expone `{ user, cargando, login, logout }` (no hay `isAuthenticated`) |
| `lib/` dentro de `src/` | Está en `frontend/lib/` (fuera de `src/`) |

---

## 11. Exportación de documentos

[app/services/export_service.py](../app/services/export_service.py):

- **PDF:** se genera un *overlay* con reportlab y, opcionalmente, se combina
  **sobre una plantilla PDF** del usuario con pypdf (`merge_page`). Incluye
  cabecera, información del material, imágenes (foto de producto y plano
  mecánico), tablas de características, empaque, microbiología y manejo.
- **Excel:** con openpyxl, ~80 columnas (definidas en `_EXCEL_HEADERS`) con
  estilos corporativos (verde Molpack `#044926`).
- **Restricción:** solo se exportan fichas en estado **Preliminar** o
  **Vigente**.

---

## 12. Pruebas (calidad del software)

Suite en `tests/` ejecutable con `pytest` (config en `pytest.ini`). **111
pruebas**, todas verdes, en ~6 s, **sin requerir base de datos**.

| Archivo | Nº | Cubre |
|---|---|---|
| `test_dsms_constants.py` | 6 | Integridad de la tabla de transiciones |
| `test_ficha_service_transiciones.py` | 28 | Máquina de estados (válidas/ inválidas) |
| `test_ficha_service_validaciones.py` | 23 | Completitud, generación de código/versión |
| `test_ficha_service_flujo.py` | 9 | Orquestación con sesión de BD simulada |
| `test_anomalia_detectores.py` | 22 | Z-score, unidades, rangos, distancia |
| `test_anomalia_constant.py` | 10 | Rangos por categoría / normalización |
| `test_utils_pais.py` | 8 | Normalización de países a ISO-2 |
| `test_export_service.py` | 5 | Agrupación de propiedades para tablas |

**Estrategia:** dos capas. (1) *Lógica pura* — servicios instanciados con
`__new__` para saltar la carga de BD/embeddings, con stubs `SimpleNamespace`.
(2) *Orquestación de servicio* — `FakeSession` (cuyo `execute` devuelve
resultados predefinidos) + colaboradores `AsyncMock`, para validar el ramaje de
negocio sin PostgreSQL/pgvector. **Pendiente:** pruebas end-to-end contra una BD
pgvector real.

---

## 13. Tabla de verificación para el tomo

Puntos concretos a contrastar con lo escrito en el trabajo de grado:

- [ ] El sistema se describe como **DSMS basado en Nahshon et al. (2023)**.
- [ ] Patrón **K-Item** (Metadata + Data Container + Semantic Graph).
- [ ] Modelo de datos: 6 tablas (kitem, material, ficha, relación, auditoría,
      anomalía).
- [ ] Estado/usuarios/fechas centralizados en `kitem` (propiedades proxy).
- [ ] Embeddings: **all-MiniLM-L6-v2**, **384 dimensiones**, pgvector, coseno.
- [ ] Máquina de estados con **5 estados** y transiciones estrictas.
- [ ] Regla "una sola ficha Vigente por material + país".
- [ ] **7 detectores** de anomalías (Z-score, unidades, duplicado, clasificación
      cruzada, perfil numérico, Isolation Forest, rango por categoría).
- [ ] Z-score con umbrales **σ>2 / σ>3**; Isolation Forest con
      **n_estimators=100, contaminación 5–10%**.
- [ ] Auditoría inmutable de todas las mutaciones (provenance).
- [ ] Auth **JWT (HS256, 8h) + LDAP/AD** con fallback local y rate limiting.
- [ ] Frontend **React 19 + Vite + React Router 7 + Tailwind 4**, con fetching
      vía **Axios + useState/useEffect** (⚠️ **no** TanStack Query / RHF / Zod:
      están en `package.json` pero sin integrar — corregir si el tomo dice lo
      contrario).
- [ ] Exportación a **PDF (con plantilla)** y **Excel**.
- [ ] Grafo de conocimiento con 5 tipos de relación (visualización en `<canvas>`).

> **Nota de fidelidad:** este reporte se generó leyendo directamente el código
> fuente. Si algún punto del tomo difiere de lo aquí descrito, la discrepancia
> está en la redacción del tomo, no en el reporte — conviene revisar el archivo
> citado en cada caso.
```
