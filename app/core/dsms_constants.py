ESTADO_BORRADOR = "Borrador"
ESTADO_PRELIMINAR = "Preliminar"
ESTADO_VIGENTE = "Vigente"
ESTADO_OBSOLETO = "Obsoleto"

TRANSACCIONES_PERMITIDAS = {
    ESTADO_BORRADOR: {ESTADO_PRELIMINAR},
    ESTADO_PRELIMINAR: {ESTADO_VIGENTE},
    ESTADO_VIGENTE: {ESTADO_OBSOLETO},
    ESTADO_OBSOLETO: set(),
}

ESTADO_ABREVIATURAS = {
    ESTADO_BORRADOR: "BOR",
    ESTADO_PRELIMINAR: "PRE",
    ESTADO_VIGENTE: "VIG",
    ESTADO_OBSOLETO: "OBS",
}

"""
Constantes del Dataspace Management System.

Define los nombres canónicos de k-types y tipos de relación
semántica del grafo de conocimiento de Molpack.
"""

# ========================
# K-TYPES del Dataspace
# ========================
KTYPE_MATERIAL_COMERCIAL = "MaterialComercial"
KTYPE_FICHA_TECNICA = "FichaTecnica"
# Futuros k-types:
# KTYPE_NORMA = "Norma"
# KTYPE_INCIDENCIA = "Incidencia"
# KTYPE_PROCESO = "ProcesoManufactura"
# KTYPE_FICHA_COMERCIAL = "FichaComercial"

# ========================
# TIPOS DE RELACIÓN
# ========================
REL_PERTENECE_A = "pertenece_a"          # FichaTecnica → MaterialComercial
REL_SE_DERIVA_DE = "se_deriva_de"        # FichaTecnica → FichaTecnica (versionamiento)
REL_ES_VARIANTE_DE = "es_variante_de"    # Material → Material
REL_RELACIONADO_CON = "relacionado_con"  # Relación genérica

# Futuros tipos de relación:
# REL_CUMPLE_NORMA = "cumple_norma"          # Material/Ficha → Norma
# REL_TIENE_INCIDENCIA = "tiene_incidencia"  # Ficha → Incidencia
# REL_FABRICADO_POR = "fabricado_por"        # Material → ProcesoManufactura

# Conjunto de relaciones válidas (para validación)
RELACIONES_VALIDAS = {
    REL_PERTENECE_A,
    REL_SE_DERIVA_DE,
    REL_ES_VARIANTE_DE,
    REL_RELACIONADO_CON,
}

# Tipos de acciones de auditoría
ACCION_CREACION = "CREACION"
ACCION_CAMBIO_ESTADO = "CAMBIO_ESTADO"
ACCION_MODIFICACION = "MODIFICACION"
ACCION_RELACION_CREADA = "RELACION_CREADA"
ACCION_RELACION_ELIMINADA = "RELACION_ELIMINADA"
ACCION_NUEVA_VERSION = "NUEVA_VERSION"

# Conjunto de acciones válidas
ACCIONES_VALIDAS = {
    ACCION_CREACION,
    ACCION_CAMBIO_ESTADO,
    ACCION_MODIFICACION,
    ACCION_RELACION_CREADA,
    ACCION_RELACION_ELIMINADA,
    ACCION_NUEVA_VERSION,
}