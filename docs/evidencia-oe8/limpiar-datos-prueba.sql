-- Elimina los registros creados por la prueba de integracion OE8.
-- El borrado de kitem arrastra en cascada ficha_tecnica, material_comercial,
-- anomalia_registro, kitem_auditoria y kitem_relacion (ON DELETE CASCADE).
--
-- Ejecutar solo despues de haber tomado las capturas de pantalla:
--   psql -U postgres -d molpack_dsms -f docs/evidencia-oe8/limpiar-datos-prueba.sql

BEGIN;

-- Verificacion previa: deberia listar 2 fichas y 2 materiales
SELECT id, ktype, nombre, estado FROM kitem
WHERE id IN (
    '67b441bb-20c1-460d-955b-108e2e12f0a8',  -- ficha A (OE8-TEST-001)
    'df0c6e27-ee40-470e-9b2e-63ef1ec09f04',  -- ficha B (OE8-TEST-002)
    'f670ba32-6dc4-47aa-b3c0-140a5c65bc17',  -- material A
    'd265f348-db1e-4216-ae86-ae7b27764b28'   -- material B
);

DELETE FROM kitem WHERE id IN (
    '67b441bb-20c1-460d-955b-108e2e12f0a8',
    'df0c6e27-ee40-470e-9b2e-63ef1ec09f04',
    'f670ba32-6dc4-47aa-b3c0-140a5c65bc17',
    'd265f348-db1e-4216-ae86-ae7b27764b28'
);

-- Revisar el resultado antes de confirmar.
-- COMMIT;
ROLLBACK;
