-- =============================================================
-- Molpack DSMS — DDL completo
-- Genera toda la estructura de la base de datos desde cero.
--
-- Orden de ejecución:
--   1. Extensiones
--   2. kitem                (supertipo universal)
--   3. material_comercial   (extiende kitem)
--   4. ficha_tecnica        (extiende kitem, FK a material_comercial)
--   5. kitem_relacion       (grafo de conocimiento)
--   6. kitem_auditoria      (trazabilidad de cambios)
--   7. anomalia_registro    (repositorio histórico de anomalías)
--   8. Índices adicionales
-- =============================================================

-- -------------------------------------------------------------
-- 0. Extensiones requeridas
-- -------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector (embeddings 384D)


-- -------------------------------------------------------------
-- 1. kitem — Supertipo universal del Dataspace (K-Item)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kitem (
    id                          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ktype                       TEXT            NOT NULL,
    nombre                      TEXT            NOT NULL,
    descripcion                 TEXT,
    estado                      TEXT            NOT NULL DEFAULT 'Activo',
    metadata_extra              JSONB,
    embedding                   VECTOR(384),
    usuario_creador             TEXT            NOT NULL,
    usuario_ultima_actualizacion TEXT           NOT NULL,
    fecha_creacion              TIMESTAMP       NOT NULL DEFAULT NOW(),
    fecha_actualizacion         TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  kitem IS 'Supertipo universal del Dataspace. Cada entidad del sistema (material, ficha, norma) es un k-item.';
COMMENT ON COLUMN kitem.ktype IS 'Tipo de k-item: MaterialComercial, FichaTecnica, etc.';
COMMENT ON COLUMN kitem.embedding IS 'Embedding vectorial 384D (all-MiniLM-L6-v2) para búsqueda semántica por similitud coseno.';

CREATE INDEX IF NOT EXISTS ix_kitem_ktype   ON kitem (ktype);


-- -------------------------------------------------------------
-- 2. material_comercial — K-Type: Material
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS material_comercial (
    id_material_corporativo     UUID            PRIMARY KEY
                                                REFERENCES kitem(id) ON DELETE CASCADE,
    nombre_corporativo          TEXT            NOT NULL,
    contenido                   TEXT,
    categoria                   TEXT,
    sector                      TEXT,
    caracteristica              TEXT,
    material_base               TEXT,
    capacidad_nominal           TEXT,
    tipo_producto               TEXT,
    estado_material             TEXT,
    fecha_creacion              TIMESTAMP,
    fecha_actualizacion         TIMESTAMP
);

COMMENT ON TABLE material_comercial IS 'Extensión de kitem para materiales comerciales de Molpack Corporation.';


-- -------------------------------------------------------------
-- 3. ficha_tecnica — K-Type: Ficha Técnica
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ficha_tecnica (
    id_ficha                    UUID            PRIMARY KEY
                                                REFERENCES kitem(id) ON DELETE CASCADE,
    id_material_corporativo     UUID            NOT NULL
                                                REFERENCES material_comercial(id_material_corporativo),
    codigo_ficha_local          TEXT            NOT NULL,
    codigo_material_local       TEXT            NOT NULL,
    nombre_local_material       TEXT,
    codigo_version              TEXT            NOT NULL,
    usuario_creador             TEXT            NOT NULL,
    usuario_ultima_actualizacion TEXT           NOT NULL,
    estado_ficha                TEXT            NOT NULL,
    fecha_registro              TIMESTAMP       NOT NULL,
    fecha_actualizacion         TIMESTAMP       NOT NULL,
    pais                        TEXT            NOT NULL,

    -- Data Container JSONB (secciones de la ficha técnica)
    caracteristicas             JSONB,
    caracteristicas_contenido   JSONB,
    empaque_estiba              JSONB,
    microbiologia               JSONB,
    manejo_disposicion          JSONB
);

COMMENT ON TABLE  ficha_tecnica IS 'Extensión de kitem para fichas técnicas. Secciones almacenadas como JSONB.';
COMMENT ON COLUMN ficha_tecnica.caracteristicas IS 'Propiedades físicas: dimensiones, peso, ruptura, tiempo de encolado, absorción.';
COMMENT ON COLUMN ficha_tecnica.caracteristicas_contenido IS 'Geometría del contenido: pilar/alvéolo (huevos), cavidad (frutas/vasos/otros).';
COMMENT ON COLUMN ficha_tecnica.empaque_estiba IS 'Configuración de empaque, estiba y unidades.';
COMMENT ON COLUMN ficha_tecnica.microbiologia IS 'Parámetros microbiológicos y metales pesados.';
COMMENT ON COLUMN ficha_tecnica.manejo_disposicion IS 'Manejo, almacenamiento, transporte, vida útil y uso.';


-- -------------------------------------------------------------
-- 4. kitem_relacion — Grafo de conocimiento
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kitem_relacion (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           UUID        NOT NULL REFERENCES kitem(id) ON DELETE CASCADE,
    target_id           UUID        NOT NULL REFERENCES kitem(id) ON DELETE CASCADE,
    tipo_relacion       TEXT        NOT NULL,
    etiqueta            TEXT,
    metadata_relacion   JSONB,
    usuario_creador     TEXT        NOT NULL,
    fecha_creacion      TIMESTAMP   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  kitem_relacion IS 'Grafo dirigido de relaciones semánticas entre k-items.';
COMMENT ON COLUMN kitem_relacion.tipo_relacion IS 'pertenece_a | se_deriva_de | es_variante_de | cumple_norma | relacionado_con';

CREATE INDEX IF NOT EXISTS ix_kitem_relacion_source_id    ON kitem_relacion (source_id);
CREATE INDEX IF NOT EXISTS ix_kitem_relacion_target_id    ON kitem_relacion (target_id);
CREATE INDEX IF NOT EXISTS ix_kitem_relacion_tipo         ON kitem_relacion (tipo_relacion);


-- -------------------------------------------------------------
-- 5. kitem_auditoria — Trazabilidad de cambios
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kitem_auditoria (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    kitem_id        UUID        REFERENCES kitem(id) ON DELETE SET NULL,
    ktype           TEXT        NOT NULL,
    accion          TEXT        NOT NULL,
    estado_anterior TEXT,
    estado_nuevo    TEXT,
    detalles        JSONB,
    usuario         TEXT        NOT NULL,
    fecha           TIMESTAMP   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  kitem_auditoria IS 'Registro de auditoría de todas las acciones sobre k-items.';
COMMENT ON COLUMN kitem_auditoria.kitem_id IS 'UUID del k-item afectado. NULL si el k-item fue eliminado posteriormente.';
COMMENT ON COLUMN kitem_auditoria.accion IS 'creacion | actualizacion | cambio_estado | eliminacion';

CREATE INDEX IF NOT EXISTS ix_kitem_auditoria_kitem_id  ON kitem_auditoria (kitem_id);
CREATE INDEX IF NOT EXISTS ix_kitem_auditoria_accion    ON kitem_auditoria (accion);
CREATE INDEX IF NOT EXISTS ix_kitem_auditoria_fecha     ON kitem_auditoria (fecha);


-- -------------------------------------------------------------
-- 6. anomalia_registro — Repositorio histórico de anomalías
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anomalia_registro (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    kitem_id            UUID        NOT NULL REFERENCES kitem(id) ON DELETE CASCADE,
    ktype               TEXT        NOT NULL,
    tipo_anomalia       TEXT        NOT NULL,
    severidad           TEXT        NOT NULL DEFAULT 'advertencia',
    campo_afectado      TEXT,
    valor_detectado     TEXT,
    valor_esperado      TEXT,
    mensaje             TEXT        NOT NULL,
    detalles            JSONB,
    estado              TEXT        NOT NULL DEFAULT 'pendiente',
    resuelto_por        TEXT,
    fecha_resolucion    TIMESTAMP,
    nota_resolucion     TEXT,
    detectado_por       TEXT        NOT NULL DEFAULT 'sistema',
    usuario_creador     TEXT        NOT NULL,
    fecha_deteccion     TIMESTAMP   NOT NULL DEFAULT NOW(),
    contexto            TEXT        NOT NULL DEFAULT 'creacion'
);

COMMENT ON TABLE  anomalia_registro IS 'Repositorio histórico de anomalías detectadas por el sistema.';
COMMENT ON COLUMN anomalia_registro.tipo_anomalia IS 'valor_atipico | unidad_inconsistente | clasificacion_cruzada | duplicado_semantico | atipico_multivariado';
COMMENT ON COLUMN anomalia_registro.severidad IS 'informativa | advertencia | critica';
COMMENT ON COLUMN anomalia_registro.estado IS 'pendiente | aceptada | descartada | corregida';
COMMENT ON COLUMN anomalia_registro.contexto IS 'creacion | actualizacion | analisis_batch';

CREATE INDEX IF NOT EXISTS ix_anomalia_registro_kitem_id        ON anomalia_registro (kitem_id);
CREATE INDEX IF NOT EXISTS ix_anomalia_registro_tipo_anomalia   ON anomalia_registro (tipo_anomalia);
CREATE INDEX IF NOT EXISTS ix_anomalia_registro_severidad       ON anomalia_registro (severidad);
CREATE INDEX IF NOT EXISTS ix_anomalia_registro_estado          ON anomalia_registro (estado);
CREATE INDEX IF NOT EXISTS ix_anomalia_registro_fecha_deteccion ON anomalia_registro (fecha_deteccion);


-- -------------------------------------------------------------
-- 7. Índice vectorial para búsqueda semántica (pgvector IVFFlat)
-- Crear DESPUÉS de cargar datos iniciales para mejor rendimiento.
-- lists = sqrt(n_filas) aprox. Ajustar según volumen.
-- -------------------------------------------------------------
-- CREATE INDEX ix_kitem_embedding_ivfflat
--     ON kitem USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 50);
