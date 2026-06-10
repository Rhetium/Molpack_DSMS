# Molpack DSMS

Sistema centralizado de gestión de fichas técnicas y materiales para Molpack Corporation, basado en la arquitectura DSMS (Dataspace Management System).

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI (async) + SQLAlchemy 2.0 + PostgreSQL |
| Vectores | pgvector — embeddings 384D (all-MiniLM-L6-v2) |
| ML | scikit-learn — Isolation Forest |
| Auth | LDAP/Active Directory + JWT |
| Frontend | React 19 + Vite + TanStack Query + Tailwind CSS 4 |

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
Formulario (Zod) → POST /api/<recurso>
  → Service: validar estado, persistir
  → EmbeddingService: generar vector 384D
  → AnomaliaService: detectores 1-6 (z-score + ML)
  → AuditoriaService: registrar acción
  → Respuesta + lista de anomalías
```

### Detección de anomalías

| Detector | Tipo | Descripción |
|---|---|---|
| 1 | `valor_atipico` | Z-score por campo numérico (σ > 2 → advertencia, σ > 3 → crítico) |
| 2 | `unidad_inconsistente` | Unidad fuera de la mayoría (< 70% uso) |
| 3 | `clasificacion_cruzada` | Material en categoría equivocada por similitud semántica |
| 4 | `duplicado_semantico` | Similitud coseno > 0.90 con ficha existente |
| 5 | `perfil_numerico_cruzado` | Perfil numérico inconsistente con la categoría |
| 6 | `atipico_multivariado` | Isolation Forest — combinación de campos inusual |

Los modelos ML se entrenan con `POST /anomalias/entrenar` y se guardan en `app/ml_models/`.

## Scripts de base de datos

```bash
# Crear esquema desde cero
psql -U <user> -d <db> -f scripts/create_tables.sql

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

frontend/src/
├── lib/         cliente Axios + contexto de auth
├── layouts/     shell principal (sidebar)
└── pages/       una carpeta por feature
    ├── fichas/
    ├── materiales/
    ├── anomalias/
    ├── busqueda/
    ├── grafo/
    ├── auditoria/
    └── dashboard/
```
