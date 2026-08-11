# scripts/ — Scripts de base de datos y utilidades

| Archivo | Uso |
|---|---|
| `schema_clean.sql` | **DDL canónico.** Crea toda la estructura desde cero: extensiones, tablas, PK/UNIQUE, índices y FKs. Fuente de verdad para instalaciones nuevas. |
| `truncate_all.sql` | Borra todos los datos sin tocar la estructura. Para limpiar datos de prueba antes de cargar datos reales. |
| `seed_fichas_excel.py` | Importa fichas técnicas desde un `.xlsx` (hoja `Fichas_Tecnicas`) vía `FichaService`, con auditoría y embeddings completos. |

## Uso

```bash
# Crear esquema (solo la primera vez o tras un drop total)
psql -U <user> -d <db> -f scripts/schema_clean.sql

# Limpiar datos (IRREVERSIBLE — hacer backup antes)
psql -U <user> -d <db> -f scripts/truncate_all.sql

# Importar fichas desde Excel
python scripts/seed_fichas_excel.py "ruta/al/archivo.xlsx"
```

## Extensiones requeridas

- `pgcrypto` — `gen_random_uuid()`
- `vector` — pgvector para la columna `embedding VECTOR(384)`

Ambas las instala `schema_clean.sql` con `CREATE EXTENSION IF NOT EXISTS`.

## Índice vectorial

`schema_clean.sql` crea el índice **HNSW** sobre `kitem.embedding`
(`vector_cosine_ops`, `m = 16`, `ef_construction = 64`) como parte del DDL.
No hay que activarlo a mano ni esperar a tener datos cargados.

## Nota sobre migraciones

Las migraciones incrementales `001`–`004` (columnas de material, normalización
de metadata hacia `kitem`, corrección de constraints) ya están aplicadas y
consolidadas dentro de `schema_clean.sql`. Se eliminaron del repositorio;
si necesitás consultarlas, siguen en el historial de git:

```bash
git log --diff-filter=D --name-only -- scripts/
git show <commit>:scripts/migration_002_normalizar_metadata.sql
```
