-- =============================================================
-- Migración 003 — Corrección de dos bugs de esquema
--
-- BUG 1: material_comercial.capacidad_nominal quedó NOT NULL en la BD,
--        pero el modelo (MaterialComercial) y MaterialCreateSchema la
--        tratan como opcional. Crear un material sin capacidad_nominal
--        fallaba con NotNullViolation (HTTP 500). Se relaja a NULLABLE
--        para alinear la BD con el modelo y el DDL.
--
-- BUG 2: el CHECK constraint chk_tipo_anomalia estaba desactualizado:
--        solo permitía 6 de los 8 valores que el detector de anomalías
--        emite. Faltaban:
--          - 'rango_categoria'      (detector D7 por rango de categoría)
--          - 'atipico_multivariado' (detector ML Isolation Forest)
--        Al dispararse cualquiera de esos detectores, el INSERT en
--        anomalia_registro violaba el constraint (HTTP 500) y abortaba
--        el flujo (p. ej. al pasar una ficha a Preliminar).
--
-- Ejecutar contra la BD activa:
--   psql -U <usuario> -d <db> -f scripts/migration_003_fix_constraints.sql
-- =============================================================

BEGIN;

-- BUG 1 — capacidad_nominal pasa a opcional
ALTER TABLE material_comercial
    ALTER COLUMN capacidad_nominal DROP NOT NULL;

-- BUG 2 — recrear chk_tipo_anomalia con el conjunto completo de valores
ALTER TABLE anomalia_registro
    DROP CONSTRAINT IF EXISTS chk_tipo_anomalia;

ALTER TABLE anomalia_registro
    ADD CONSTRAINT chk_tipo_anomalia CHECK (
        tipo_anomalia IN (
            'valor_atipico',
            'unidad_inconsistente',
            'clasificacion_cruzada',
            'duplicado_semantico',
            'estructura_invalida',
            'perfil_numerico_cruzado',
            'atipico_multivariado',
            'rango_categoria'
        )
    );

COMMIT;
