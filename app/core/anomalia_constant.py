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

# D1 — z-score robusto: |valor - mediana| / escala, con escala = 1.4826·MAD.
# La mediana y el MAD no se contaminan con los errores ya cargados en la base
# (una media y una desviación estándar sí). 3.5 es el umbral habitual del
# z-score modificado (Iglewicz & Hoaglin).
ZSCORE_ADVERTENCIA = 3.5
ZSCORE_CRITICO = 6.0
FACTOR_MAD = 1.4826
# Piso de la escala: la variación normal nunca se considera menor que la
# tolerancia declarada en la ficha ni que este % de la mediana. Evita que
# fichas idénticas (MAD = 0) conviertan cualquier diferencia en anomalía.
ESCALA_MINIMA_RELATIVA = 0.02
# Campos sin tolerancia declarada (ruptura, deflexión…): suelen ser enteros
# pequeños, donde 1 unidad ya es varios puntos porcentuales.
ESCALA_MINIMA_SIN_TOLERANCIA = 0.05

MIN_MUESTRAS_ESTADISTICAS = 3

# Referencia por niveles: mismo material → misma familia (categoría +
# capacidad nominal) → categoría. Se usa el primer nivel con suficientes fichas.
MIN_MUESTRAS_MATERIAL = 3
MIN_MUESTRAS_FAMILIA = 5
NIVEL_MATERIAL = "material"
NIVEL_FAMILIA = "familia"
NIVEL_CATEGORIA = "categoria"

# tiempo_encolado: parámetro de proceso con pocos valores posibles.
# peso_empaque: depende de cuántas unidades lleva el empaque (varía por país);
# se evalúa su coherencia con el peso unitario (variable derivada).
CAMPOS_EXCLUIDOS_ZSCORE = {"tiempo_encolado_valor", "peso_empaque_valor"}

MIN_MUESTRAS_ML = 5
MODELO_GLOBAL = "global"

# Isolation Forest: score más negativo = más anómalo.
# Una ficha es anómala si su score queda por debajo de este percentil de los
# scores de entrenamiento (umbral calibrado por modelo, guardado en el .pkl).
ML_PERCENTIL_ANOMALIA = 1.0
# Crítica si el score queda esta distancia por debajo del umbral calibrado
ML_SCORE_CRITICO = -0.15

UMBRAL_DUPLICADO_SEMANTICO = 0.90
UMBRAL_DUPLICADO_CRITICO   = 0.95

# D3 para fichas — duplicado = mismo producto bajo otro material: coincidencia
# numérica de las medidas clave dentro de la tolerancia declarada. Los
# embeddings de ficha no sirven aquí: el texto es una plantilla casi idéntica
# para toda la categoría y los números quedan mal representados.
CAMPOS_DUPLICADO_CLAVE = [
    "dimensiones_largo_valor",
    "dimensiones_ancho_valor",
    "dimensiones_alto_valor",
    "peso_valor",
]
CAMPOS_DUPLICADO_SECUNDARIOS = [
    ("caracteristicas", "ruptura_valor"),
    ("caracteristicas", "resistencia_valor"),
    ("caracteristicas_contenido", "profundidad_pilar_valor"),
    ("caracteristicas_contenido", "diametro_alveolo_valor"),
    ("caracteristicas_contenido", "profundidad_cavidad_valor"),
    ("caracteristicas_contenido", "diametro_cavidad_valor"),
]
TOLERANCIA_RELATIVA_DUPLICADO = 0.01   # si la ficha no declara tolerancia
COINCIDENCIA_SECUNDARIA_MINIMA = 0.75  # fracción de campos secundarios que deben coincidir
# Similitud entre los embeddings de los materiales para subir a crítica
UMBRAL_DUPLICADO_MATERIAL_CRITICO = 0.85

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

# Variables derivadas: capturan relaciones entre campos que ningún campo
# muestra por separado (p. ej. "más grande y más liviano").
CAMPOS_DERIVADOS = [
    ("gramaje_valor", "g/cm²", "Gramaje (peso / área)"),
    ("relacion_alto_largo_valor", "", "Relación alto / largo"),
    ("coherencia_peso_empaque_valor", "", "Peso empaque / (unidades × peso unitario)"),
]


def _numero(seccion: dict, campo: str) -> float | None:
    if seccion.get(campo.removesuffix("_valor") + "_nc"):
        return None
    v = seccion.get(campo)
    return float(v) if isinstance(v, (int, float)) and v > 0 else None


def calcular_derivados(
    caracteristicas: dict | None,
    empaque_estiba: dict | None = None,
) -> dict[str, float]:
    """
    Variables derivadas de las medidas declaradas. Devuelve solo lo calculable.

    - Gramaje (g/cm²): en pulpa moldeada es lo que define el producto; una
      ficha con dimensiones y peso plausibles por separado pero incoherentes
      entre sí se ve directamente como un gramaje anormal.
    - Relación alto/largo: forma del producto.
    - Coherencia del empaque: el peso del empaque (kg) debería ser ≈ unidades ×
      peso unitario (g); un valor lejos de 1 delata un error en cualquiera de
      los tres campos.
    """
    c = caracteristicas or {}
    e = empaque_estiba or {}
    largo = _numero(c, "dimensiones_largo_valor")
    ancho = _numero(c, "dimensiones_ancho_valor")
    alto = _numero(c, "dimensiones_alto_valor")
    peso = _numero(c, "peso_valor")

    derivados = {}
    if peso and largo and ancho:
        derivados["gramaje_valor"] = round(peso / (largo * ancho / 100), 5)
    if alto and largo:
        derivados["relacion_alto_largo_valor"] = round(alto / largo, 5)

    peso_empaque = _numero(e, "peso_empaque_valor")
    unidades = e.get("undidades_empaque")
    if (
        peso and peso_empaque and isinstance(unidades, (int, float)) and unidades > 0
        and (c.get("peso_unidad") or "").lower() == "g"
        and (e.get("peso_empaque_unidad") or "").lower() == "kg"
    ):
        derivados["coherencia_peso_empaque_valor"] = round(
            peso_empaque * 1000 / (unidades * peso), 5
        )
    return derivados


def tolerancia_relativa_derivados(
    caracteristicas: dict | None,
    empaque_estiba: dict | None = None,
) -> dict[str, float]:
    """
    Tolerancia relativa de cada variable derivada, propagada desde las
    tolerancias declaradas de los campos que la componen (suma de relativas).
    Sirve de piso a la escala del z-score: el gramaje acumula la incertidumbre
    del peso, el largo y el ancho.
    """
    c = caracteristicas or {}
    e = empaque_estiba or {}

    def _rel(seccion, prefijo):
        valor = _numero(seccion, f"{prefijo}_valor")
        tol = seccion.get(f"{prefijo}_tolerancia")
        if not valor or not isinstance(tol, (int, float)):
            return 0.0
        return abs(tol) / valor

    largo = _rel(c, "dimensiones_largo")
    ancho = _rel(c, "dimensiones_ancho")
    alto = _rel(c, "dimensiones_alto")
    peso = _rel(c, "peso")
    return {
        "gramaje_valor": peso + largo + ancho,
        "relacion_alto_largo_valor": alto + largo,
        "coherencia_peso_empaque_valor": _rel(e, "peso_empaque") + peso,
    }


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