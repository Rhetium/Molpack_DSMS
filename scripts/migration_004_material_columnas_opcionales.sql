-- =============================================================
-- Migración 004 — material_comercial: columnas de dominio opcionales
--
-- Cierra la misma familia de bugs que migration_003 (capacidad_nominal):
-- estas columnas eran NOT NULL en la BD viva (drift heredado), pero el
-- modelo SQLAlchemy las declara nullable=True y MaterialCreateSchema las
-- trata como opcionales (str | None = None). Crear un material sin alguna
-- de ellas fallaba con NotNullViolation (HTTP 500).
--
-- Se relajan a NULLABLE para alinear la BD con el modelo, el schema y
-- schema_clean.sql (que ya las define sin NOT NULL).
--
-- Ejecutar contra la BD activa:
--   psql -U <usuario> -d <db> -f scripts/migration_004_material_columnas_opcionales.sql
-- =============================================================

BEGIN;

ALTER TABLE material_comercial ALTER COLUMN contenido      DROP NOT NULL;
ALTER TABLE material_comercial ALTER COLUMN categoria      DROP NOT NULL;
ALTER TABLE material_comercial ALTER COLUMN material_base  DROP NOT NULL;
ALTER TABLE material_comercial ALTER COLUMN tipo_producto  DROP NOT NULL;

COMMIT;
