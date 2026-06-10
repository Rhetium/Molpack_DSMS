-- =============================================================
-- Migración 001 — material_comercial + ficha_tecnica
--
-- Cambios:
--   material_comercial: quitar color_base, agregar sector y caracteristica
--   ficha_tecnica:      agregar nombre_local_material
--
-- Ejecutar contra la BD activa (no borra estructura existente):
--   psql -U <usuario> -d <db> -f scripts/migration_001_material_columnas.sql
-- =============================================================

BEGIN;

-- material_comercial
ALTER TABLE material_comercial DROP COLUMN IF EXISTS color_base;
ALTER TABLE material_comercial ADD COLUMN IF NOT EXISTS sector        TEXT;
ALTER TABLE material_comercial ADD COLUMN IF NOT EXISTS caracteristica TEXT;

-- ficha_tecnica
ALTER TABLE ficha_tecnica ADD COLUMN IF NOT EXISTS nombre_local_material TEXT;

COMMIT;
