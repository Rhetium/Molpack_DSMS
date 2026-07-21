-- =============================================================
-- Molpack DSMS — DDL canónico (fiel a la base de datos real)
--
-- Este script se generó a partir del esquema REAL de producción
-- (pg_dump --schema-only) y es la fuente de verdad para instalaciones
-- nuevas. Refleja el estado tras las migraciones 002/003/004.
--
-- Notas importantes (diferencias frente a versiones antiguas del script):
--   - Timestamps: timestamptz (timestamp WITH time zone).
--   - Extensiones: pgcrypto (para gen_random_uuid) + vector (pgvector).
--   - Índice vectorial: HNSW (no IVFFlat).
--   - kitem_relacion tiene UNIQUE(source_id, target_id, tipo_relacion).
--   - FKs con nombres explícitos y ON DELETE definido.
--   - Metadata común (estado, usuarios, fechas) vive solo en kitem;
--     material_comercial y ficha_tecnica NO la duplican (migración 002).
--
-- Orden: extensiones → tablas → PK/UNIQUE → índices → FKs.
-- (Las FKs se agregan al final, por eso el orden de las tablas es libre.)
-- =============================================================

-- -------------------------------------------------------------
-- 0. Extensiones
-- -------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector (embeddings 384D, HNSW)


-- -------------------------------------------------------------
-- 1. kitem — Supertipo universal (única fuente de verdad de metadata)
-- -------------------------------------------------------------
CREATE TABLE kitem (
    id                           uuid        DEFAULT gen_random_uuid() NOT NULL,
    ktype                        text        NOT NULL,
    nombre                       text        NOT NULL,
    descripcion                  text,
    estado                       text        DEFAULT 'Activo'::text NOT NULL,
    metadata_extra               jsonb       DEFAULT '{}'::jsonb,
    usuario_creador              text        NOT NULL,
    usuario_ultima_actualizacion text        NOT NULL,
    fecha_creacion               timestamptz DEFAULT now() NOT NULL,
    fecha_actualizacion          timestamptz DEFAULT now() NOT NULL,
    embedding                    vector(384)
);


-- -------------------------------------------------------------
-- 2. material_comercial — K-Type: Material (solo datos de dominio)
-- -------------------------------------------------------------
CREATE TABLE material_comercial (
    id_material_corporativo uuid NOT NULL,
    nombre_corporativo      text NOT NULL,
    contenido               text,
    categoria               text,
    material_base           text,
    capacidad_nominal       text,
    tipo_producto           text,
    sector                  text,
    caracteristica          text
);


-- -------------------------------------------------------------
-- 3. ficha_tecnica — K-Type: Ficha Técnica (solo datos de dominio)
-- -------------------------------------------------------------
CREATE TABLE ficha_tecnica (
    id_ficha                  uuid NOT NULL,
    id_material_corporativo   uuid NOT NULL,
    codigo_ficha_local        text NOT NULL,
    codigo_material_local     text NOT NULL,
    codigo_version            text NOT NULL,
    pais                      text NOT NULL,
    caracteristicas           jsonb,
    caracteristicas_contenido jsonb,
    empaque_estiba            jsonb,
    microbiologia             jsonb,
    manejo_disposicion        jsonb,
    nombre_local_material     text
);


-- -------------------------------------------------------------
-- 4. kitem_relacion — Grafo de conocimiento
-- -------------------------------------------------------------
CREATE TABLE kitem_relacion (
    id                uuid        DEFAULT gen_random_uuid() NOT NULL,
    source_id         uuid        NOT NULL,
    target_id         uuid        NOT NULL,
    tipo_relacion     text        NOT NULL,
    etiqueta          text,
    metadata_relacion jsonb       DEFAULT '{}'::jsonb,
    usuario_creador   text        NOT NULL,
    fecha_creacion    timestamptz DEFAULT now() NOT NULL
);


-- -------------------------------------------------------------
-- 5. kitem_auditoria — Trazabilidad de cambios
-- -------------------------------------------------------------
CREATE TABLE kitem_auditoria (
    id              uuid        DEFAULT gen_random_uuid() NOT NULL,
    kitem_id        uuid,
    ktype           text        NOT NULL,
    accion          text        NOT NULL,
    estado_anterior text,
    estado_nuevo    text,
    detalles        jsonb       DEFAULT '{}'::jsonb,
    usuario         text        NOT NULL,
    fecha           timestamptz DEFAULT now() NOT NULL
);


-- -------------------------------------------------------------
-- 6. anomalia_registro — Repositorio histórico de anomalías
-- -------------------------------------------------------------
CREATE TABLE anomalia_registro (
    id               uuid        DEFAULT gen_random_uuid() NOT NULL,
    kitem_id         uuid        NOT NULL,
    ktype            text        NOT NULL,
    tipo_anomalia    text        NOT NULL,
    severidad        text        DEFAULT 'advertencia'::text NOT NULL,
    campo_afectado   text,
    valor_detectado  text,
    valor_esperado   text,
    mensaje          text        NOT NULL,
    detalles         jsonb       DEFAULT '{}'::jsonb,
    estado           text        DEFAULT 'pendiente'::text NOT NULL,
    resuelto_por     text,
    fecha_resolucion timestamptz,
    nota_resolucion  text,
    detectado_por    text        DEFAULT 'sistema'::text NOT NULL,
    usuario_creador  text        NOT NULL,
    fecha_deteccion  timestamptz DEFAULT now() NOT NULL,
    contexto         text        DEFAULT 'creacion'::text NOT NULL,
    CONSTRAINT chk_contexto      CHECK (contexto IN ('creacion', 'actualizacion', 'analisis_batch')),
    CONSTRAINT chk_estado        CHECK (estado IN ('pendiente', 'aceptada', 'descartada', 'corregida')),
    CONSTRAINT chk_severidad     CHECK (severidad IN ('informativa', 'advertencia', 'critica')),
    CONSTRAINT chk_tipo_anomalia CHECK (tipo_anomalia IN (
        'valor_atipico', 'unidad_inconsistente', 'clasificacion_cruzada',
        'duplicado_semantico', 'estructura_invalida', 'perfil_numerico_cruzado',
        'atipico_multivariado', 'rango_categoria'
    ))
);


-- =============================================================
-- Llaves primarias y únicas
-- =============================================================
ALTER TABLE kitem              ADD CONSTRAINT kitem_pkey              PRIMARY KEY (id);
ALTER TABLE material_comercial ADD CONSTRAINT material_comercial_pkey PRIMARY KEY (id_material_corporativo);
ALTER TABLE ficha_tecnica      ADD CONSTRAINT ficha_tecnica_pkey      PRIMARY KEY (id_ficha);
ALTER TABLE kitem_relacion     ADD CONSTRAINT kitem_relacion_pkey     PRIMARY KEY (id);
ALTER TABLE kitem_auditoria    ADD CONSTRAINT kitem_auditoria_pkey    PRIMARY KEY (id);
ALTER TABLE anomalia_registro  ADD CONSTRAINT anomalia_registro_pkey  PRIMARY KEY (id);

-- Evita relaciones duplicadas en el grafo
ALTER TABLE kitem_relacion
    ADD CONSTRAINT uq_krel_source_target_tipo UNIQUE (source_id, target_id, tipo_relacion);


-- =============================================================
-- Índices
-- =============================================================
-- kitem
CREATE INDEX idx_kitem_ktype        ON kitem USING btree (ktype);
CREATE INDEX idx_kitem_estado       ON kitem USING btree (estado);
CREATE INDEX idx_kitem_ktype_estado ON kitem USING btree (ktype, estado);
CREATE INDEX idx_kitem_fecha        ON kitem USING btree (fecha_creacion DESC);

-- Índice vectorial HNSW para búsqueda semántica (similitud coseno)
CREATE INDEX idx_kitem_embedding_hnsw
    ON kitem USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- kitem_auditoria
CREATE INDEX idx_auditoria_kitem   ON kitem_auditoria USING btree (kitem_id);
CREATE INDEX idx_auditoria_accion  ON kitem_auditoria USING btree (accion);
CREATE INDEX idx_auditoria_ktype   ON kitem_auditoria USING btree (ktype);
CREATE INDEX idx_auditoria_usuario ON kitem_auditoria USING btree (usuario);
CREATE INDEX idx_auditoria_fecha   ON kitem_auditoria USING btree (fecha DESC);

-- anomalia_registro
CREATE INDEX idx_anomalia_kitem     ON anomalia_registro USING btree (kitem_id);
CREATE INDEX idx_anomalia_ktype     ON anomalia_registro USING btree (ktype);
CREATE INDEX idx_anomalia_tipo      ON anomalia_registro USING btree (tipo_anomalia);
CREATE INDEX idx_anomalia_severidad ON anomalia_registro USING btree (severidad);
CREATE INDEX idx_anomalia_estado    ON anomalia_registro USING btree (estado);
CREATE INDEX idx_anomalia_fecha     ON anomalia_registro USING btree (fecha_deteccion DESC);


-- =============================================================
-- Llaves foráneas
-- =============================================================
ALTER TABLE material_comercial
    ADD CONSTRAINT fk_material_kitem FOREIGN KEY (id_material_corporativo)
        REFERENCES kitem(id) ON DELETE CASCADE;

ALTER TABLE ficha_tecnica
    ADD CONSTRAINT fk_ficha_kitem FOREIGN KEY (id_ficha)
        REFERENCES kitem(id) ON DELETE CASCADE;
ALTER TABLE ficha_tecnica
    ADD CONSTRAINT fk_ficha_material FOREIGN KEY (id_material_corporativo)
        REFERENCES material_comercial(id_material_corporativo);

ALTER TABLE kitem_relacion
    ADD CONSTRAINT fk_krel_source FOREIGN KEY (source_id)
        REFERENCES kitem(id) ON DELETE CASCADE;
ALTER TABLE kitem_relacion
    ADD CONSTRAINT fk_krel_target FOREIGN KEY (target_id)
        REFERENCES kitem(id) ON DELETE CASCADE;

ALTER TABLE kitem_auditoria
    ADD CONSTRAINT fk_auditoria_kitem FOREIGN KEY (kitem_id)
        REFERENCES kitem(id) ON DELETE SET NULL;

ALTER TABLE anomalia_registro
    ADD CONSTRAINT anomalia_registro_kitem_id_fkey FOREIGN KEY (kitem_id)
        REFERENCES kitem(id) ON DELETE CASCADE;
