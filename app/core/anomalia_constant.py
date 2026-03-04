"""
Constantes del módulo de detección de anomalías.

Centraliza los tipos, severidades, umbrales y configuraciones
del sistema de detección de anomalías del DSMS.
"""

# ========================
# TIPOS DE ANOMALÍA
# ========================
ANOMALIA_VALOR_ATIPICO = "valor_atipico"
ANOMALIA_UNIDAD_INCONSISTENTE = "unidad_inconsistente"
ANOMALIA_CLASIFICACION_CRUZADA = "clasificacion_cruzada"
ANOMALIA_DUPLICADO_SEMANTICO = "duplicado_semantico"
ANOMALIA_ESTRUCTURA_INVALIDA = "estructura_invalida"
ANOMALIA_PERFIL_CRUZADO = "perfil_numerico_cruzado"

TIPOS_ANOMALIA = {
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_CLASIFICACION_CRUZADA,
    ANOMALIA_DUPLICADO_SEMANTICO,
    ANOMALIA_ESTRUCTURA_INVALIDA,
    ANOMALIA_PERFIL_CRUZADO,
}

# ========================
# SEVERIDADES
# ========================
SEVERIDAD_INFORMATIVA = "informativa"
SEVERIDAD_ADVERTENCIA = "advertencia"
SEVERIDAD_CRITICA = "critica"

# ========================
# ESTADOS DE RESOLUCIÓN
# ========================
ESTADO_ANOMALIA_PENDIENTE = "pendiente"
ESTADO_ANOMALIA_ACEPTADA = "aceptada"
ESTADO_ANOMALIA_DESCARTADA = "descartada"
ESTADO_ANOMALIA_CORREGIDA = "corregida"

ESTADOS_RESOLUCION_VALIDOS = {
    ESTADO_ANOMALIA_ACEPTADA,
    ESTADO_ANOMALIA_DESCARTADA,
    ESTADO_ANOMALIA_CORREGIDA,
}

# ========================
# CONTEXTOS DE DETECCIÓN
# ========================
CONTEXTO_CREACION = "creacion"
CONTEXTO_ACTUALIZACION = "actualizacion"
CONTEXTO_BATCH = "analisis_batch"

# ========================
# UMBRALES DE DETECCIÓN
# ========================

# Z-score: cuántas desviaciones estándar se considera anómalo
# Para fichas con pocas muestras (<10), se usa rango intercuartílico
ZSCORE_ADVERTENCIA = 2.0   # > 2σ → advertencia
ZSCORE_CRITICO = 3.0       # > 3σ → crítico

# Mínimo de muestras para usar estadísticas
MIN_MUESTRAS_ESTADISTICAS = 3

# Duplicado semántico: umbral de similitud coseno
UMBRAL_DUPLICADO_SEMANTICO = 0.90   # > 0.90 → posible duplicado
UMBRAL_DUPLICADO_CRITICO = 0.95     # > 0.95 → casi seguro duplicado

# Clasificación cruzada: umbral para detectar que un material
# "parece" pertenecer a otra categoría
UMBRAL_CLASIFICACION_CRUZADA = 0.85

# Unidad inconsistente: porcentaje mínimo de fichas que usan
# la misma unidad para considerar una unidad como "mayoritaria"
PORCENTAJE_UNIDAD_MAYORITARIA = 0.70  # 70% usa "cm" → "cm" es la norma

# ========================
# CAMPOS NUMÉRICOS ANALIZABLES
# ========================
# Campos de fichas técnicas que pueden tener valores atípicos
# Formato: (campo_valor, campo_unidad, nombre_legible)

CAMPOS_CARACTERISTICAS = [
    ("dimensiones_largo_valor", "dimensiones_largo_unidad", "Largo"),
    ("dimensiones_ancho_valor", "dimensiones_ancho_unidad", "Ancho"),
    ("dimensiones_alto_valor", "dimensiones_alto_unidad", "Alto"),
    ("tiempo_encolado_valor", "tiempo_encolado_unidad", "Tiempo de encolado"),
    ("porcentaje_absorcion_valor", "porcentaje_absorcion_unidad", "Porcentaje de absorción"),
    ("peso_valor", "peso_unidad", "Peso"),
    ("deflexion_interna_valor", "deflexion_interna_unidad", "Deflexión interna"),
    ("deflexion_externa_valor", "deflexion_externa_unidad", "Deflexión externa"),
    ("ruptura_valor", "ruptura_unidad", "Ruptura"),
]

CAMPOS_CONTENIDO = [
    ("profundidad_pilar_valor", "profundidad_pilar_unidad", "Profundidad pilar"),
    ("diametro_alveolo_valor", "diametro_alveolo_unidad", "Diámetro alvéolo"),
    ("profundidad_cavidad_valor", "profundidad_cavidad_unidad", "Profundidad cavidad"),
    ("diametro_cavidad_valor", "diametro_cavidad_unidad", "Diámetro cavidad"),
]

CAMPOS_EMPAQUE = [
    ("alto_empaque_valor", "alto_empaque_unidad", "Alto empaque"),
    ("peso_empaque_valor", "peso_empaque_unidad", "Peso empaque"),
]