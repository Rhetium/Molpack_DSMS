-- =============================================================
-- Molpack DSMS — Limpiar todos los datos
--
-- Borra TODOS los registros sin eliminar tablas, índices ni constraints.
-- Útil para resetear datos de prueba antes de insertar datos reales.
--
-- ADVERTENCIA: Esta operación es IRREVERSIBLE.
-- Hacer backup antes si es necesario:
--   pg_dump -U <usuario> -d <db> --data-only -f backup_datos.sql
-- =============================================================

BEGIN;

-- Truncar en orden correcto (hijos antes que padres)
-- CASCADE cubre cualquier dependencia restante automáticamente.
TRUNCATE TABLE
    anomalia_registro,
    kitem_auditoria,
    kitem_relacion,
    ficha_tecnica,
    material_comercial,
    kitem
RESTART IDENTITY CASCADE;

COMMIT;
