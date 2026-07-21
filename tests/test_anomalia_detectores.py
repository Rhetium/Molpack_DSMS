"""
Detectores de anomalías (lógica pura, sin BD ni embeddings).

Cubre:
- D1 _detectar_valores_atipicos (z-score).
- D2 _detectar_unidades_inconsistentes.
- D7 _detectar_rango_categoria (rangos por categoría).
- _tiene_evidencia_dimensional (soporte de D4).
- Helpers: _extraer_vector_numerico, _distancia_euclidiana_normalizada,
  _extraer_valores_campo.
"""

import pytest

from app.core.anomalia_constant import (
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_RANGO_CATEGORIA,
    SEVERIDAD_CRITICA,
    SEVERIDAD_ADVERTENCIA,
)


def _ref(make_ficha, **caract):
    """Ficha de referencia con solo la sección `caracteristicas`."""
    return make_ficha(caracteristicas=dict(caract))


# ── D1: valores atípicos (z-score) ─────────────────────────────────────────

def test_d1_sin_muestras_suficientes_no_detecta(anomalia_service, make_ficha):
    ficha = _ref(make_ficha, peso_valor=999)
    refs = [_ref(make_ficha, peso_valor=50), _ref(make_ficha, peso_valor=51)]  # < 3
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_valor_normal_no_detecta(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50)]  # media 50, std ~1.41
    ficha = _ref(make_ficha, peso_valor=51)  # z ~0.7
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_valor_advertencia(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50)]
    ficha = _ref(make_ficha, peso_valor=53)  # z ~2.12 → advertencia
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert len(anomalias) == 1
    assert anomalias[0].tipo_anomalia == ANOMALIA_VALOR_ATIPICO
    assert anomalias[0].severidad == SEVERIDAD_ADVERTENCIA


def test_d1_valor_critico(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50)]
    ficha = _ref(make_ficha, peso_valor=56)  # z ~4.24 → crítico
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert len(anomalias) == 1
    assert anomalias[0].severidad == SEVERIDAD_CRITICA


def test_d1_std_cero_valor_distinto_es_advertencia(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]  # todos iguales, std=0
    ficha = _ref(make_ficha, peso_valor=51)
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert len(anomalias) == 1
    assert anomalias[0].severidad == SEVERIDAD_ADVERTENCIA


def test_d1_std_cero_mismo_valor_no_detecta(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=50)
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


# ── D2: unidades inconsistentes ────────────────────────────────────────────

def test_d2_unidad_distinta_a_mayoritaria(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_unidad="g") for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=50, peso_unidad="kg")
    anomalias = anomalia_service._detectar_unidades_inconsistentes(ficha, refs)
    assert len(anomalias) == 1
    assert anomalias[0].tipo_anomalia == ANOMALIA_UNIDAD_INCONSISTENTE
    assert anomalias[0].severidad == SEVERIDAD_ADVERTENCIA


def test_d2_misma_unidad_no_detecta(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_unidad="g") for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=50, peso_unidad="g")
    assert anomalia_service._detectar_unidades_inconsistentes(ficha, refs) == []


def test_d2_sin_mayoria_clara_no_detecta(anomalia_service, make_ficha):
    # 50/50 no alcanza el umbral (70%) de unidad mayoritaria.
    refs = [_ref(make_ficha, peso_unidad=u) for u in ("g", "g", "kg", "kg")]
    ficha = _ref(make_ficha, peso_valor=50, peso_unidad="mm")
    assert anomalia_service._detectar_unidades_inconsistentes(ficha, refs) == []


# ── D7: rangos por categoría ───────────────────────────────────────────────

def test_d7_dentro_de_rango_no_detecta(anomalia_service, make_ficha, make_material):
    material = make_material(categoria="Separador")
    ficha = make_ficha(caracteristicas={
        "dimensiones_largo_valor": 298,
        "dimensiones_ancho_valor": 298,
        "dimensiones_alto_valor": 50,
        "peso_valor": 60,
    })
    assert anomalia_service._detectar_rango_categoria(ficha=ficha, material=material) == []


def test_d7_fuera_de_rango_advertencia(anomalia_service, make_ficha, make_material):
    material = make_material(categoria="Separador")
    # largo 500 > 370 pero < 370*2 → advertencia
    ficha = make_ficha(caracteristicas={"dimensiones_largo_valor": 500})
    anomalias = anomalia_service._detectar_rango_categoria(ficha=ficha, material=material)
    assert len(anomalias) == 1
    assert anomalias[0].tipo_anomalia == ANOMALIA_RANGO_CATEGORIA
    assert anomalias[0].severidad == SEVERIDAD_ADVERTENCIA


def test_d7_muy_fuera_de_rango_critico(anomalia_service, make_ficha, make_material):
    material = make_material(categoria="Separador")
    # peso 5 < 35*0.5 = 17.5 → crítico
    ficha = make_ficha(caracteristicas={"peso_valor": 5})
    anomalias = anomalia_service._detectar_rango_categoria(ficha=ficha, material=material)
    assert len(anomalias) == 1
    assert anomalias[0].severidad == SEVERIDAD_CRITICA


def test_d7_categoria_sin_rangos_no_detecta(anomalia_service, make_ficha, make_material):
    material = make_material(categoria="Otro")
    ficha = make_ficha(caracteristicas={"peso_valor": 99999})
    assert anomalia_service._detectar_rango_categoria(ficha=ficha, material=material) == []


def test_d7_valor_no_numerico_se_ignora(anomalia_service, make_ficha, make_material):
    material = make_material(categoria="Separador")
    ficha = make_ficha(caracteristicas={"peso_valor": "N/A"})
    assert anomalia_service._detectar_rango_categoria(ficha=ficha, material=material) == []


# ── _tiene_evidencia_dimensional (soporte D4) ──────────────────────────────

def test_evidencia_dimensional_positiva(anomalia_service, make_ficha):
    # Dimensiones encajan en Bandeja pero NO en Separador (ancho fuera de rango).
    ficha = make_ficha(caracteristicas={
        "dimensiones_largo_valor": 200,
        "dimensiones_ancho_valor": 150,  # < 200 → fuera de Separador
        "dimensiones_alto_valor": 20,
        "peso_valor": 30,
    })
    assert anomalia_service._tiene_evidencia_dimensional(ficha, "Bandeja", "Separador") is True


def test_evidencia_dimensional_negativa(anomalia_service, make_ficha):
    # Dimensiones típicas de Separador → no encajan en Bandeja.
    ficha = make_ficha(caracteristicas={
        "dimensiones_largo_valor": 298,
        "dimensiones_ancho_valor": 298,
        "dimensiones_alto_valor": 50,
        "peso_valor": 60,
    })
    assert anomalia_service._tiene_evidencia_dimensional(ficha, "Bandeja", "Separador") is False


def test_evidencia_dimensional_categoria_sin_rangos(anomalia_service, make_ficha):
    ficha = make_ficha(caracteristicas={"dimensiones_largo_valor": 200})
    assert anomalia_service._tiene_evidencia_dimensional(ficha, "Otro", "Separador") is False


# ── Helpers numéricos ──────────────────────────────────────────────────────

def test_extraer_vector_numerico(anomalia_service, make_ficha):
    ficha = make_ficha(caracteristicas={
        "peso_valor": 50,
        "dimensiones_largo_valor": 100,
        "peso_unidad": "g",          # no es *_valor → se ignora
    })
    vector = anomalia_service._extraer_vector_numerico(ficha)
    assert vector == {"peso_valor": 50.0, "dimensiones_largo_valor": 100.0}


def test_extraer_vector_numerico_excluye_nc(anomalia_service, make_ficha):
    ficha = make_ficha(caracteristicas={"peso_valor": 50, "peso_nc": True})
    assert "peso_valor" not in anomalia_service._extraer_vector_numerico(ficha)


def test_distancia_euclidiana_normalizada(anomalia_service):
    d = anomalia_service._distancia_euclidiana_normalizada(
        {"a": 2.0}, {"a": 0.0}, {"a": 1.0}
    )
    assert d == pytest.approx(2.0)


def test_distancia_sin_campos_comunes_devuelve_none(anomalia_service):
    assert anomalia_service._distancia_euclidiana_normalizada(
        {"a": 1.0}, {"b": 1.0}, {"b": 1.0}
    ) is None


def test_extraer_valores_campo(anomalia_service, make_ficha):
    fichas = [
        _ref(make_ficha, peso_valor=10),
        _ref(make_ficha, peso_valor=20),
        make_ficha(caracteristicas=None),          # sin sección → ignorada
        _ref(make_ficha, otro_campo=5),            # sin el campo → ignorada
    ]
    valores = anomalia_service._extraer_valores_campo(fichas, "caracteristicas", "peso_valor")
    assert valores == [10, 20]
