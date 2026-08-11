# Molpack DSMS

Sistema centralizado de gestión de fichas técnicas y materiales para Molpack Corporation, basado en la arquitectura DSMS (Dataspace Management System).

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI (async) + SQLAlchemy 2.0 + PostgreSQL |
| Vectores | pgvector — embeddings 384D (all-MiniLM-L6-v2) |
| ML | scikit-learn — Isolation Forest |
| Auth | LDAP/Active Directory + JWT |
| Frontend | React 19 + Vite + React Router 7 + Tailwind CSS 4 (fetching con Axios) |

## Inicio rápido

```bash
# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev        # proxy /api → http://127.0.0.1:8000
```

Variables de entorno requeridas en `.env`:

```
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
LDAP_SERVER, LDAP_BASE_DN, LDAP_BIND_DN, LDAP_GRUPO_AUTORIZADO
JWT_SECRET, JWT_EXPIRATION_HOURS
EMBEDDING_MODEL_NAME
```

## Arquitectura

### K-Item (supertipo universal)

Toda entidad del sistema (`MaterialComercial`, `FichaTecnica`) es un **K-Item**: una fila en `kitem` que centraliza metadatos, embedding vectorial y estado. Las tablas de dominio extienden `kitem` vía FK.

```
kitem
├── material_comercial  (FK → kitem.id)
└── ficha_tecnica       (FK → kitem.id, FK → material_comercial)

kitem_relacion          (grafo dirigido entre k-items)
kitem_auditoria         (log de todas las mutaciones)
anomalia_registro       (repositorio histórico de anomalías)
```

### Máquina de estados — FichaTecnica

```
Borrador → Preliminar → Vigente → Obsoleto ⇆ Revisión
```

Las transiciones permitidas están en `app/core/dsms_constants.py::TRANSACCIONES_PERMITIDAS`.

### Pipeline de creación/actualización

```
Formulario (useState) → POST /api/<recurso>   (Axios + JWT)
  → Service: validar estado, persistir
  → EmbeddingService: generar vector 384D
  → AnomaliaService: detectores 1-7 (z-score + ML)
  → AuditoriaService: registrar acción
  → Respuesta + lista de anomalías
```

### Detección de anomalías

Orden real de los detectores en `AnomaliaService.analizar_ficha`:

| Detector | Tipo | Descripción |
|---|---|---|
| 1 | `valor_atipico` | Z-score por campo numérico (σ ≥ 2 → advertencia, σ ≥ 3 → crítico) |
| 2 | `unidad_inconsistente` | Unidad distinta a la mayoritaria (≥ 70% uso) |
| 3 | `duplicado_semantico` | Similitud coseno ≥ 0.95 con ficha de **otro** material (crítico ≥ 0.98) |
| 4 | `clasificacion_cruzada` | Material en categoría equivocada por similitud semántica (≥ 0.85) |
| 5 | `perfil_numerico_cruzado` | Perfil numérico más cercano a otra categoría (ratio < 0.7) |
| 6 | `atipico_multivariado` | Isolation Forest — combinación de campos inusual |
| 7 | `rango_categoria` | Dimensiones fuera del rango duro esperado por categoría |

Los modelos ML (detector 6) se entrenan con `POST /anomalias/entrenar` y se guardan en `app/ml_models/`.

## Scripts de base de datos

```bash
# Crear esquema desde cero
psql -U <user> -d <db> -f scripts/schema_clean.sql

# Limpiar datos (mantiene estructura)
psql -U <user> -d <db> -f scripts/truncate_all.sql
```

## Estructura del proyecto

```
app/
├── core/        constantes, DB engine, auth, deps
├── models/      ORM (SQLAlchemy)
├── schemas/     Pydantic request/response
├── services/    lógica de negocio
├── routers/     endpoints FastAPI
└── ml_models/   modelos .pkl (Isolation Forest)

frontend/
├── lib/             cliente Axios (api.js) + contexto de auth (auth.jsx)
└── src/
    ├── layouts/     shell principal (sidebar)
    └── pages/       una carpeta por feature
        ├── fichas/
        ├── materiales/
        ├── anomalias/
        ├── busqueda/
        ├── grafo/       (visualización en <canvas>)
        ├── auditoria/
        └── dashboard/
```
