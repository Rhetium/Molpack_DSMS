ESTADO_BORRADOR = "Borrador"
ESTADO_PRELIMINAR = "Preliminar"
ESTADO_VIGENTE = "Vigente"
ESTADO_OBSOLETO = "Obsoleto"
ESTADO_REVISION = "Revisión"

TRANSACCIONES_PERMITIDAS = {
    ESTADO_BORRADOR: {ESTADO_PRELIMINAR, ESTADO_OBSOLETO},
    ESTADO_PRELIMINAR: {ESTADO_VIGENTE, ESTADO_OBSOLETO},
    ESTADO_VIGENTE: {ESTADO_OBSOLETO},
    ESTADO_OBSOLETO: {ESTADO_REVISION},
    ESTADO_REVISION: {ESTADO_OBSOLETO, ESTADO_PRELIMINAR},
}
ESTADO_ABREVIATURAS = {
    ESTADO_BORRADOR: "BOR",
    ESTADO_PRELIMINAR: "PRE",
    ESTADO_VIGENTE: "VIG",
    ESTADO_OBSOLETO: "OBS",
    ESTADO_REVISION: "REV",
}

KTYPE_MATERIAL_COMERCIAL = "MaterialComercial"
KTYPE_FICHA_TECNICA = "FichaTecnica"
# Futuros k-types:
# KTYPE_NORMA = "Norma"
# KTYPE_INCIDENCIA = "Incidencia"
# KTYPE_PROCESO = "ProcesoManufactura"
# KTYPE_FICHA_COMERCIAL = "FichaComercial"

REL_PERTENECE_A = "pertenece_a"                        # FichaTecnica → MaterialComercial
REL_SE_DERIVA_DE = "se_deriva_de"                      # FichaTecnica → FichaTecnica (versionamiento)
REL_ES_VARIANTE_DE = "es_variante_de"                  # Material → Material
REL_RELACIONADO_CON = "relacionado_con"
REL_SEMANTICAMENTE_SIMILAR = "semanticamente_similar"  # Descubierta por embeddings

# Futuros tipos de relación:
# REL_CUMPLE_NORMA = "cumple_norma"          # Material/Ficha → Norma
# REL_TIENE_INCIDENCIA = "tiene_incidencia"  # Ficha → Incidencia
# REL_FABRICADO_POR = "fabricado_por"        # Material → ProcesoManufactura

RELACIONES_VALIDAS = {
    REL_PERTENECE_A,
    REL_SE_DERIVA_DE,
    REL_ES_VARIANTE_DE,
    REL_RELACIONADO_CON,
    REL_SEMANTICAMENTE_SIMILAR,
}

ACCION_CREACION = "CREACION"
ACCION_CAMBIO_ESTADO = "CAMBIO_ESTADO"
ACCION_MODIFICACION = "MODIFICACION"
ACCION_RELACION_CREADA = "RELACION_CREADA"
ACCION_RELACION_ELIMINADA = "RELACION_ELIMINADA"
ACCION_NUEVA_VERSION = "NUEVA_VERSION"
ACCION_EMBEDDING_GENERADO = "EMBEDDING_GENERADO"

ACCIONES_VALIDAS = {
    ACCION_CREACION,
    ACCION_CAMBIO_ESTADO,
    ACCION_MODIFICACION,
    ACCION_RELACION_CREADA,
    ACCION_RELACION_ELIMINADA,
    ACCION_NUEVA_VERSION,
    ACCION_EMBEDDING_GENERADO,
}

UMBRALES_DUPLICADOS = {
    KTYPE_MATERIAL_COMERCIAL: 0.85,
    KTYPE_FICHA_TECNICA: 0.80,
    # Valores por defecto para k-types futuros
    "_default": 0.85,
}

CAMPOS_CONTENIDO = {
    "profundidad_pilar_valor",
    "profundidad_pilar_tolerancia",
    "profundidad_pilar_unidad",
    "diametro_alveolo_valor",
    "diametro_alveolo_tolerancia",
    "diametro_alveolo_unidad",
    "profundidad_cavidad_valor",
    "profundidad_cavidad_tolerancia",
    "profundidad_cavidad_unidad",
    "diametro_cavidad_valor",
    "diametro_cavidad_tolerancia",
    "diametro_cavidad_unidad",
}
CATEGORIAS_PRODUCTO = {
    "Estuche",
    "Tapa",
    "Separador",
    "Bandeja",
    "Porta vasos",
    "Otro",
}

TIPOS_CONTENIDO = {
    "Huevos",
    "Frutas",
    "Potes de pintura",
    "Vasos",
    "Industrial",
    "Otro",
}