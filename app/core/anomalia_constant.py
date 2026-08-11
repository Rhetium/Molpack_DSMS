ANOMALIA_RANGO_CATEGORIA = "rango_categoria"
ANOMALIA_VALOR_ATIPICO = "valor_atipico"
ANOMALIA_UNIDAD_INCONSISTENTE = "unidad_inconsistente"
ANOMALIA_CLASIFICACION_CRUZADA = "clasificacion_cruzada"
ANOMALIA_DUPLICADO_SEMANTICO = "duplicado_semantico"
ANOMALIA_ESTRUCTURA_INVALIDA = "estructura_invalida"
ANOMALIA_PERFIL_CRUZADO = "perfil_numerico_cruzado"
ANOMALIA_ML_MULTIVARIADO = "atipico_multivariado"

TIPOS_ANOMALIA = {
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_CLASIFICACION_CRUZADA,
    ANOMALIA_DUPLICADO_SEMANTICO,
    ANOMALIA_ESTRUCTURA_INVALIDA,
    ANOMALIA_PERFIL_CRUZADO,
    ANOMALIA_ML_MULTIVARIADO,
    ANOMALIA_RANGO_CATEGORIA,
}

SEVERIDAD_INFORMATIVA = "informativa"
SEVERIDAD_ADVERTENCIA = "advertencia"
SEVERIDAD_CRITICA = "critica"

ESTADO_ANOMALIA_PENDIENTE = "pendiente"
ESTADO_ANOMALIA_ACEPTADA = "aceptada"
ESTADO_ANOMALIA_DESCARTADA = "descartada"
ESTADO_ANOMALIA_CORREGIDA = "corregida"

ESTADOS_RESOLUCION_VALIDOS = {
    ESTADO_ANOMALIA_ACEPTADA,
    ESTADO_ANOMALIA_DESCARTADA,
    ESTADO_ANOMALIA_CORREGIDA,
}

CONTEXTO_CREACION = "creacion"
CONTEXTO_ACTUALIZACION = "actualizacion"
CONTEXTO_BATCH = "analisis_batch"

# z-score: umbral en desviaciones estándar
ZSCORE_ADVERTENCIA = 2.0
ZSCORE_CRITICO = 3.0 

MIN_MUESTRAS_ESTADISTICAS = 3

MIN_MUESTRAS_ML = 5
MODELO_GLOBAL = "global"

# Isolation Forest: score más negativo = más anómalo
ML_SCORE_CRITICO = -0.15
ML_SCORE_ADVERTENCIA = -0.05

UMBRAL_DUPLICADO_SEMANTICO = 0.90
UMBRAL_DUPLICADO_CRITICO   = 0.95

UMBRAL_DUPLICADO_FICHA     = 0.95
UMBRAL_DUPLICADO_FICHA_CRITICO = 0.98

UMBRAL_CLASIFICACION_CRUZADA = 0.85

PORCENTAJE_UNIDAD_MAYORITARIA = 0.70

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
    ("resistencia_valor", "resistencia_unidad", "Resistencia"),
]

CAMPOS_CONTENIDO = [
    ("profundidad_pilar_valor", "profundidad_pilar_unidad", "Profundidad pilar"),
    ("diametro_alveolo_valor", "diametro_alveolo_unidad", "Diámetro alvéolo"),
    ("profundidad_cavidad_valor", "profundidad_cavidad_unidad", "Profundidad cavidad"),
    ("diametro_cavidad_valor", "diametro_cavidad_unidad", "Diámetro cavidad"),
    ("ancho_cavidad_valor", "ancho_cavidad_unidad", "Ancho cavidad"),
    ("largo_cavidad_valor", "largo_cavidad_unidad", "Largo cavidad"),
]

CAMPOS_EMPAQUE = [
    ("alto_empaque_valor", "alto_empaque_unidad", "Alto empaque"),
    ("peso_empaque_valor", "peso_empaque_unidad", "Peso empaque"),
]


RANGOS_CATEGORIA: dict[str, dict[str, tuple]] = {
    "Separador": {
        "dimensiones_largo_valor": (200, 370, "mm"),
        "dimensiones_ancho_valor": (200, 370, "mm"),
        "dimensiones_alto_valor":  (30,  70,  "mm"),
        "peso_valor":              (35, 110,  "g"),
    },
    "Porta vasos": {
        "dimensiones_largo_valor": (140, 290, "mm"),
        "dimensiones_alto_valor":  (30,  75,  "mm"),
        "peso_valor":              (15,  65,  "g"),
    },
    "Estuche": {
        "dimensiones_largo_valor": (220, 450, "mm"),
        "dimensiones_ancho_valor": (170, 340, "mm"),
        "dimensiones_alto_valor":  (30,  95,  "mm"),
        "peso_valor":              (35,  95,  "g"),
    },
    "Bandeja": {
        "dimensiones_largo_valor": (140, 350, "mm"),
        "dimensiones_ancho_valor": (100, 230, "mm"),
        "dimensiones_alto_valor":  (3,   50,  "mm"),
        "peso_valor":              (8,   60,  "g"),
    },
}

def _normalizar_categoria(categoria: str) -> str:
    """Clave de comparación de categorías: minúsculas y sin espacios."""
    return "".join((categoria or "").lower().split())


_RANGOS_POR_CATEGORIA_NORM = {
    _normalizar_categoria(cat): rangos for cat, rangos in RANGOS_CATEGORIA.items()
}


def rangos_para_categoria(categoria: str | None) -> dict | None:
    """
    Rangos D7 de una categoría, tolerante a mayúsculas y espacios:
    'Porta vasos', 'Portavasos' y 'PORTA VASOS' son la misma categoría.
    El catálogo ya registra varias grafías, por lo que un lookup exacto
    desactivaba silenciosamente el detector. Devuelve None si la
    categoría no tiene rangos definidos.
    """
    if not categoria:
        return None
    return _RANGOS_POR_CATEGORIA_NORM.get(_normalizar_categoria(categoria))