# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Molpack DSMS** (Dataspace Management System) is a knowledge management system for technical materials and specifications. It features semantic search (via pgvector + sentence-transformers), state-machine-driven workflows for technical datasheets, anomaly detection, audit trails, and a knowledge graph. Code and docstrings are primarily in **Spanish**.

## Commands

### Backend (FastAPI)
```bash
# Run dev server
uvicorn app.main:app --reload

# Install dependencies
pip install -r requirements.txt
```

### Tests (pytest)
```bash
# Install dev/test dependencies (runtime + pytest)
pip install -r requirements-dev.txt

# Run the unit test suite (fast, no DB required)
pytest

# Run a single file or filter by name
pytest tests/test_ficha_service_transiciones.py
pytest -k "transicion"
```
Tests live in `tests/`, in two layers:
- **Pure domain logic** — FichaTecnica state machine, field-completeness
  validations, code/version generation, anomaly detectors (z-score, category
  ranges, unit consistency). Services are instantiated via `__new__` to bypass
  DB/embedding setup; ORM entities are `SimpleNamespace` stubs.
- **Service orchestration** (`test_ficha_service_flujo.py`) — `cambiar_estado`
  and `actualizar` flows exercised against a `FakeSession` (whose `execute`
  returns predefined results in order) with mocked collaborators. This validates
  the business branching (transition rules, blocking on pending anomalies,
  automatic versioning + obsolescence) without PostgreSQL/pgvector.

Factories and fakes live in `tests/conftest.py`. Full end-to-end tests against a
real pgvector database are not yet present.

### Frontend (React + Vite)
```bash
cd frontend

# Dev server (proxies /api to http://127.0.0.1:8000)
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

## Architecture

### Stack
- **Backend**: FastAPI (async) + SQLAlchemy 2.0 + PostgreSQL + pgvector
- **Frontend**: React 19 + React Router 7 + Tailwind CSS 4. Data fetching is done with **Axios + `useState`/`useEffect`** (client in `frontend/lib/api.js`); forms use plain `useState` + native `<form>`. NOTE: `@tanstack/react-query` is in `package.json` but **not actually used** — only `QueryClientProvider` is mounted in `App.jsx`. Do not assume it is wired. (`react-hook-form`, `@hookform/resolvers`, `zod` and `sonner` were declared but never imported; they have been uninstalled.)
- **Auth**: LDAP/Active Directory (ldap3) with JWT fallback
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`, 384-dim vectors via pgvector)

### Backend structure (`app/`)
- `main.py` — FastAPI app entry point, router registration
- `core/` — Database engine (`database.py`), JWT utils (`security.py`), dependency injection (`deps.py`), business-rule constants (`dsms_constants.py`, `anomalia_constant.py`)
- `models/` — SQLAlchemy ORM models (see K-Item pattern below)
- `schemas/` — Pydantic request/response schemas
- `services/` — Business logic (one service per domain)
- `routers/` — FastAPI route handlers (thin layer over services)

### Frontend structure
- `frontend/lib/api.js` — Axios client with JWT interceptors; all API calls go through here (note: `lib/` is OUTSIDE `src/`)
- `frontend/lib/auth.jsx` — React Context for auth state (`useAuth` → `{ user, cargando, login, logout }`)
- `frontend/src/layouts/MainLayout.jsx` — Sidebar + main content shell
- `pages/` — Route-level components (one directory per feature: `fichas/`, `materiales/`, `anomalias/`, `busqueda/`, `grafo/`, `auditoria/`, `dashboard/`)

### Core design patterns

**K-Item universal type**: All domain entities (`MaterialComercial`, `FichaTecnica`, and future types) are backed by a `KItem` row. `KItem` holds metadata, a JSON data blob, and a pgvector embedding. Inter-entity relationships live in `KItemRelacion`; every mutation is logged to `KItemAuditoria`.

**State machine for FichaTecnica**: Strict transitions — `Borrador → Preliminar → Vigente → Obsoleto` (plus `Revisión`). State-change rules are enforced in `fichas_services.py`; the constants live in `dsms_constants.py`.

**Semantic pipeline**: On create/update, `embedding_service.py` generates a 384-dim embedding and stores it in the `KItem` pgvector column. `semantic_search_service.py` runs cosine-similarity queries. `anomalia_service.py` uses z-score outlier detection plus duplicate detection against existing embeddings.

**Data flow (create/update)**:
```
Frontend form (useState; validation happens server-side)
  → POST /api/<resource>
  → Service: validate state rules, persist via SQLAlchemy
  → EmbeddingService: generate + store vector
  → AnomaliaService: detect anomalies
  → AuditoriaService: log action
  → Return result + anomaly list to frontend
```

### Environment variables (`.env`)
| Variable | Purpose |
|---|---|
| `DB_HOST/PORT/NAME/USER/PASSWORD` | PostgreSQL connection |
| `LDAP_SERVER`, `LDAP_BASE_DN`, `LDAP_BIND_DN`, `LDAP_GRUPO_AUTORIZADO` | Active Directory auth |
| `JWT_SECRET`, `JWT_EXPIRATION_HOURS` | Token config |
| `EMBEDDING_MODEL_NAME` | Sentence-transformers model name |
