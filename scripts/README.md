# scripts/ — Scripts de base de datos

| Archivo | Uso |
|---|---|
| `create_tables.sql` | Crea toda la estructura desde cero (extensiones, tablas, índices). Idempotente con `IF NOT EXISTS`. |
| `truncate_all.sql` | Borra todos los datos sin tocar la estructura. Para limpiar datos de prueba antes de cargar datos reales. |

## Uso

```bash
# Crear esquema (solo la primera vez o tras un drop total)
psql -U <user> -d <db> -f scripts/create_tables.sql

# Limpiar datos (IRREVERSIBLE — hacer backup antes)
psql -U <user> -d <db> -f scripts/truncate_all.sql
```

## Extensiones requeridas

- `uuid-ossp` — `uuid_generate_v4()`
- `vector` — pgvector para columna `embedding VECTOR(384)`

Ambas se instalan automáticamente por `create_tables.sql` con `CREATE EXTENSION IF NOT EXISTS`.

## Índice vectorial

El índice IVFFlat para búsqueda semántica está comentado en `create_tables.sql`. Activarlo después de cargar datos iniciales ajustando `lists = sqrt(n_filas)`.
