-- =============================================================
-- Migración 002 — Normalizar metadata hacia kitem
--
-- Elimina las columnas de metadata común duplicadas en las tablas
-- hijas, dejando a `kitem` como única fuente de verdad.
--
--   material_comercial:  estado_material, fecha_creacion, fecha_actualizacion
--   ficha_tecnica:       usuario_creador, usuario_ultima_actualizacion,
--                        estado_ficha, fecha_registro, fecha_actualizacion
--
-- ANTES de eliminar, reconcilia los valores hacia kitem para no
-- perder datos que pudieran haber divergido (en particular
-- estado_material, que el servicio de update NO sincronizaba con
-- kitem.estado — ver material_service.actualizar()).
--
-- Ejecutar contra la BD activa:
--   psql -U <usuario> -d <db> -f scripts/migration_002_normalizar_metadata.sql
--
-- REQUISITO: aplicar el refactor de código (modelos/servicios/schemas)
-- en el mismo despliegue. Tras esta migración la app fallará si el
-- código sigue leyendo las columnas eliminadas.
--
-- Reversible solo restaurando desde backup: hacer dump antes de correr.
-- =============================================================

BEGIN;

-- -------------------------------------------------------------
-- 1. Reconciliar material_comercial -> kitem
--    estado_material es la fuente autoritativa (el update directo del
--    material lo modificaba sin tocar kitem.estado).
-- -------------------------------------------------------------
UPDATE kitem k
SET estado              = m.estado_material,
    fecha_creacion      = LEAST(k.fecha_creacion,
                                COALESCE(m.fecha_creacion, k.fecha_creacion)),
    fecha_actualizacion = GREATEST(k.fecha_actualizacion,
                                   COALESCE(m.fecha_actualizacion, k.fecha_actualizacion))
FROM material_comercial m
WHERE k.id = m.id_material_corporativo;

-- -------------------------------------------------------------
-- 2. Reconciliar ficha_tecnica -> kitem
--    fecha_registro es la fecha de creación de la ficha.
-- -------------------------------------------------------------
UPDATE kitem k
SET estado                        = f.estado_ficha,
    usuario_creador               = f.usuario_creador,
    usuario_ultima_actualizacion  = f.usuario_ultima_actualizacion,
    fecha_creacion                = f.fecha_registro,
    fecha_actualizacion           = GREATEST(k.fecha_actualizacion, f.fecha_actualizacion)
FROM ficha_tecnica f
WHERE k.id = f.id_ficha;

-- -------------------------------------------------------------
-- 3. Eliminar columnas redundantes
-- -------------------------------------------------------------
ALTER TABLE material_comercial
    DROP COLUMN IF EXISTS estado_material,
    DROP COLUMN IF EXISTS fecha_creacion,
    DROP COLUMN IF EXISTS fecha_actualizacion;

ALTER TABLE ficha_tecnica
    DROP COLUMN IF EXISTS usuario_creador,
    DROP COLUMN IF EXISTS usuario_ultima_actualizacion,
    DROP COLUMN IF EXISTS estado_ficha,
    DROP COLUMN IF EXISTS fecha_registro,
    DROP COLUMN IF EXISTS fecha_actualizacion;

-- (La BD ya tiene idx_kitem_estado sobre kitem(estado); no se crea otro.)

COMMIT;
