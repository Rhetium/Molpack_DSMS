"""
Detectores de anomalías (lógica pura, sin BD ni embeddings).

Cubre:
- D1 _detectar_valores_atipicos (z-score robusto) y selección de referencia.
- D3 _detectar_duplicados_ficha / _coincidencia_numerica (duplicado por medidas).
- calcular_derivados (gramaje, relación alto/largo).
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
    ANOMALIA_DUPLICADO_SEMANTICO,
    SEVERIDAD_CRITICA,
    SEVERIDAD_ADVERTENCIA,
    NIVEL_MATERIAL,
    NIVEL_FAMILIA,
    NIVEL_CATEGORIA,
    calcular_derivados,
    tolerancia_relativa_derivados,
)


def _ref(make_ficha, **caract):
    """Ficha de referencia con solo la sección `caracteristicas`."""
    return make_ficha(caracteristicas=dict(caract))


# ── D1: valores atípicos (z-score robusto: mediana + MAD) ─────────────────

def test_d1_sin_muestras_suficientes_no_detecta(anomalia_service, make_ficha):
    ficha = _ref(make_ficha, peso_valor=999)
    refs = [_ref(make_ficha, peso_valor=50), _ref(make_ficha, peso_valor=51)]  # < 3
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_valor_normal_no_detecta(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50)]  # mediana 50, escala 1.48
    ficha = _ref(make_ficha, peso_valor=53)  # z ~2.0 < 3.5
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_valor_advertencia(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50)]
    ficha = _ref(make_ficha, peso_valor=56, peso_tolerancia=1)  # z ~4.0 → advertencia
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert len(anomalias) == 1
    assert anomalias[0].tipo_anomalia == ANOMALIA_VALOR_ATIPICO
    assert anomalias[0].severidad == SEVERIDAD_ADVERTENCIA
    assert anomalias[0].campo_afectado == "caracteristicas.peso_valor"


def test_d1_valor_critico(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50)]
    ficha = _ref(make_ficha, peso_valor=60, peso_tolerancia=1)  # z ~6.7 → crítico
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert len(anomalias) == 1
    assert anomalias[0].severidad == SEVERIDAD_CRITICA


def test_d1_referencias_identicas_toleran_diferencia_minima(anomalia_service, make_ficha):
    # MAD = 0: la escala cae al piso del 2% de la mediana (1 g), no a cero.
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=51)
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_referencias_identicas_detectan_diferencia_real(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=54, peso_tolerancia=1)  # escala = 1 g
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert [a.severidad for a in anomalias] == [SEVERIDAD_ADVERTENCIA]
    ficha = _ref(make_ficha, peso_valor=57, peso_tolerancia=1)
    anomalias = anomalia_service._detectar_valores_atipicos(ficha, refs)
    assert [a.severidad for a in anomalias] == [SEVERIDAD_CRITICA]


def test_d1_sin_tolerancia_usa_piso_mayor(anomalia_service, make_ficha):
    # Ruptura 13 → 15 Kgf: sin tolerancia declarada el piso es 5% (0.65), no 2%.
    refs = [_ref(make_ficha, ruptura_valor=13) for _ in range(4)]
    assert anomalia_service._detectar_valores_atipicos(_ref(make_ficha, ruptura_valor=15), refs) == []
    anomalias = anomalia_service._detectar_valores_atipicos(_ref(make_ficha, ruptura_valor=17), refs)
    assert [a.campo_afectado for a in anomalias] == ["caracteristicas.ruptura_valor"]


def test_d1_std_cero_mismo_valor_no_detecta(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=50)
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_tolerancia_declarada_es_piso_de_escala(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]
    ficha = _ref(make_ficha, peso_valor=54, peso_tolerancia=5)  # dentro de ±5 g declarados
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def test_d1_robusto_a_errores_en_la_referencia(anomalia_service, make_ficha):
    # Un error grosero ya cargado (500 g) inflaría la desviación estándar y
    # ocultaría el 70; con mediana + MAD sigue saltando.
    refs = [_ref(make_ficha, peso_valor=v) for v in (48, 50, 52, 50, 500)]
    anomalias = anomalia_service._detectar_valores_atipicos(_ref(make_ficha, peso_valor=70), refs)
    assert len(anomalias) == 1
    assert anomalias[0].severidad == SEVERIDAD_CRITICA


def test_d1_excluye_tiempo_de_encolado(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, tiempo_encolado_valor=5) for _ in range(4)]
    ficha = _ref(make_ficha, tiempo_encolado_valor=120)
    assert anomalia_service._detectar_valores_atipicos(ficha, refs) == []


def _medidas(lado, peso):
    return dict(dimensiones_largo_valor=lado, dimensiones_largo_tolerancia=1,
                dimensiones_ancho_valor=lado, dimensiones_ancho_tolerancia=1,
                peso_valor=peso, peso_tolerancia=1)


def test_d1_detecta_gramaje_incoherente(anomalia_service, make_ficha):
    # Referencias de distintos tamaños con el mismo gramaje (0.0667 g/cm²).
    # La ficha tiene lado y peso dentro de lo visto, pero es grande y liviana:
    # ningún campo destaca por separado, el gramaje sí.
    refs = [_ref(make_ficha, **_medidas(lado, lado * lado / 1500))
            for lado in (270, 285, 300, 315, 330)]
    ficha = _ref(make_ficha, **_medidas(330, 48.6))
    campos = {a.campo_afectado for a in anomalia_service._detectar_valores_atipicos(ficha, refs)}
    assert campos == {"caracteristicas.gramaje_valor"}


def test_d1_detecta_empaque_incoherente(anomalia_service, make_ficha):
    # 140 unidades × 60 g = 8.4 kg; declarar 25 kg delata un error de carga.
    def _ficha(peso_empaque):
        return make_ficha(
            caracteristicas={"peso_valor": 60, "peso_tolerancia": 2, "peso_unidad": "g"},
            empaque_estiba={"undidades_empaque": 140, "peso_empaque_valor": peso_empaque,
                            "peso_empaque_tolerancia": 0.4, "peso_empaque_unidad": "kg"},
        )
    refs = [_ficha(8.4), _ficha(8.6), _ficha(8.5), _ficha(8.7)]
    assert anomalia_service._detectar_valores_atipicos(_ficha(8.5), refs) == []
    campos = {a.campo_afectado for a in anomalia_service._detectar_valores_atipicos(_ficha(25.0), refs)}
    assert campos == {"caracteristicas.coherencia_peso_empaque_valor"}


def test_d1_mensaje_indica_nivel_de_referencia(anomalia_service, make_ficha):
    refs = [_ref(make_ficha, peso_valor=50) for _ in range(4)]
    anomalias = anomalia_service._detectar_valores_atipicos(
        _ref(make_ficha, peso_valor=70), refs, NIVEL_MATERIAL,
    )
    assert "mismo material" in anomalias[0].mensaje
    assert anomalias[0].detalles["nivel_referencia"] == NIVEL_MATERIAL


# ── Selección de referencia por niveles (D1) ───────────────────────────────

def _refs_con_material(make_ficha, especificacion):
    """[(n, material)] → lista de (ficha, material) con n fichas por material."""
    return [(make_ficha(), m) for n, m in especificacion for _ in range(n)]


def test_referencia_mismo_material_si_hay_suficientes(anomalia_service, make_ficha, make_material):
    propio = make_material(id_material_corporativo="A", capacidad_nominal="30")
    otro = make_material(id_material_corporativo="B", capacidad_nominal="30")
    refs = _refs_con_material(make_ficha, [(3, propio), (10, otro)])
    fichas, nivel = anomalia_service._seleccionar_referencia_estadistica(propio, refs)
    assert nivel == NIVEL_MATERIAL
    assert len(fichas) == 3


def test_referencia_familia_por_capacidad(anomalia_service, make_ficha, make_material):
    propio = make_material(id_material_corporativo="A", capacidad_nominal="30")
    misma_cap = make_material(id_material_corporativo="B", capacidad_nominal=" 30 ")
    otra_cap = make_material(id_material_corporativo="C", capacidad_nominal="12")
    refs = _refs_con_material(make_ficha, [(1, propio), (5, misma_cap), (8, otra_cap)])
    fichas, nivel = anomalia_service._seleccionar_referencia_estadistica(propio, refs)
    assert nivel == NIVEL_FAMILIA
    assert len(fichas) == 6


def test_referencia_categoria_como_ultimo_recurso(anomalia_service, make_ficha, make_material):
    propio = make_material(id_material_corporativo="A", capacidad_nominal="No Aplica")
    otro = make_material(id_material_corporativo="B", capacidad_nominal="No Aplica")
    refs = _refs_con_material(make_ficha, [(1, propio), (8, otro)])
    fichas, nivel = anomalia_service._seleccionar_referencia_estadistica(propio, refs)
    assert nivel == NIVEL_CATEGORIA
    assert len(fichas) == 9


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


# ── Variables derivadas ────────────────────────────────────────────────────

def test_calcular_derivados():
    d = calcular_derivados({"dimensiones_largo_valor": 300, "dimensiones_ancho_valor": 200,
                            "dimensiones_alto_valor": 50, "peso_valor": 60})
    assert d["gramaje_valor"] == pytest.approx(0.1)            # 60 g / 600 cm²
    assert d["relacion_alto_largo_valor"] == pytest.approx(50 / 300, abs=1e-4)


def test_calcular_derivados_coherencia_empaque():
    d = calcular_derivados(
        {"peso_valor": 60, "peso_unidad": "g"},
        {"undidades_empaque": 140, "peso_empaque_valor": 8.4, "peso_empaque_unidad": "kg"},
    )
    assert d["coherencia_peso_empaque_valor"] == pytest.approx(1.0)
    # Con unidades no estándar no se calcula (lo reporta el detector de unidades)
    assert "coherencia_peso_empaque_valor" not in calcular_derivados(
        {"peso_valor": 0.06, "peso_unidad": "kg"},
        {"undidades_empaque": 140, "peso_empaque_valor": 8.4, "peso_empaque_unidad": "kg"},
    )


def test_tolerancia_relativa_derivados_suma_componentes():
    t = tolerancia_relativa_derivados({
        "dimensiones_largo_valor": 300, "dimensiones_largo_tolerancia": 3,
        "dimensiones_ancho_valor": 200, "dimensiones_ancho_tolerancia": 2,
        "peso_valor": 60, "peso_tolerancia": 3,
    })
    assert t["gramaje_valor"] == pytest.approx(0.01 + 0.01 + 0.05)


def test_calcular_derivados_omite_lo_no_calculable():
    assert calcular_derivados({"peso_valor": 60, "dimensiones_largo_valor": 300}) == {}
    assert calcular_derivados(None) == {}
    assert "gramaje_valor" not in calcular_derivados({
        "peso_valor": 60, "peso_nc": True,
        "dimensiones_largo_valor": 300, "dimensiones_ancho_valor": 200,
    })


# ── D3: duplicados por coincidencia numérica ───────────────────────────────

_MEDIDAS = dict(
    dimensiones_largo_valor=298, dimensiones_largo_tolerancia=2,
    dimensiones_ancho_valor=298, dimensiones_ancho_tolerancia=2,
    dimensiones_alto_valor=50, dimensiones_alto_tolerancia=1,
    peso_valor=60, peso_tolerancia=2,
)


def test_d3_medidas_iguales_coinciden(anomalia_service, make_ficha):
    a = make_ficha(caracteristicas=dict(_MEDIDAS))
    b = make_ficha(caracteristicas=dict(_MEDIDAS, peso_valor=61, dimensiones_largo_valor=299))
    r = anomalia_service._coincidencia_numerica(a, b)
    assert r is not None
    assert r["campos_coincidentes"][:4] == ["largo", "ancho", "alto", "peso"]


def test_d3_medida_clave_fuera_de_tolerancia_no_coincide(anomalia_service, make_ficha):
    a = make_ficha(caracteristicas=dict(_MEDIDAS))
    b = make_ficha(caracteristicas=dict(_MEDIDAS, peso_valor=64))  # 4 g > ±2 g
    assert anomalia_service._coincidencia_numerica(a, b) is None


def test_d3_falta_medida_clave_no_coincide(anomalia_service, make_ficha):
    a = make_ficha(caracteristicas=dict(_MEDIDAS))
    sin_alto = {k: v for k, v in _MEDIDAS.items() if not k.startswith("dimensiones_alto")}
    assert anomalia_service._coincidencia_numerica(a, make_ficha(caracteristicas=sin_alto)) is None


def test_d3_secundarias_distintas_no_coincide(anomalia_service, make_ficha):
    a = make_ficha(caracteristicas=dict(_MEDIDAS, ruptura_valor=13),
                   caracteristicas_contenido={"profundidad_pilar_valor": 48})
    b = make_ficha(caracteristicas=dict(_MEDIDAS, ruptura_valor=18),
                   caracteristicas_contenido={"profundidad_pilar_valor": 40})
    assert anomalia_service._coincidencia_numerica(a, b) is None


def _servicio_con_similitud(valor):
    from app.services.anomalia_service import AnomaliaService
    svc = AnomaliaService.__new__(AnomaliaService)

    async def _similitud(_a, _b):
        return valor
    svc._similitud_kitems = _similitud
    return svc


async def test_d3_reporta_solo_la_coincidencia_mas_cercana(make_ficha, make_material):
    svc = _servicio_con_similitud(0.9)
    propio = make_material(id_material_corporativo="A")
    otro = make_material(id_material_corporativo="B", nombre_corporativo="Otro")
    ficha = make_ficha(caracteristicas=dict(_MEDIDAS))
    lejana = make_ficha(id_ficha="f1", codigo_ficha_local="F1", caracteristicas=dict(_MEDIDAS, peso_valor=62))
    cercana = make_ficha(id_ficha="f2", codigo_ficha_local="F2", caracteristicas=dict(_MEDIDAS))
    mismo_material = make_ficha(id_ficha="f3", caracteristicas=dict(_MEDIDAS))
    refs = [(lejana, otro), (cercana, otro), (mismo_material, propio)]

    anomalias = await svc._detectar_duplicados_ficha(ficha, propio, refs)
    assert len(anomalias) == 1
    assert anomalias[0].tipo_anomalia == ANOMALIA_DUPLICADO_SEMANTICO
    assert anomalias[0].severidad == SEVERIDAD_CRITICA          # similitud material 0.9
    assert anomalias[0].detalles["kitem_similar_id"] == "f2"


async def test_d3_materiales_poco_similares_es_advertencia(make_ficha, make_material):
    svc = _servicio_con_similitud(0.4)
    ficha = make_ficha(caracteristicas=dict(_MEDIDAS))
    otra = make_ficha(id_ficha="f1", codigo_ficha_local="F1", caracteristicas=dict(_MEDIDAS))
    anomalias = await svc._detectar_duplicados_ficha(
        ficha, make_material(id_material_corporativo="A"),
        [(otra, make_material(id_material_corporativo="B"))],
    )
    assert [a.severidad for a in anomalias] == [SEVERIDAD_ADVERTENCIA]


async def test_d3_mismo_material_nunca_es_duplicado(make_ficha, make_material):
    svc = _servicio_con_similitud(1.0)
    propio = make_material(id_material_corporativo="A")
    otra = make_ficha(id_ficha="f1", caracteristicas=dict(_MEDIDAS))
    assert await svc._detectar_duplicados_ficha(
        make_ficha(caracteristicas=dict(_MEDIDAS)), propio, [(otra, propio)],
    ) == []


# ── D4: clasificación cruzada ──────────────────────────────────────────────

async def test_d4_compara_embedding_guardado_y_reporta_solo_el_mas_parecido(make_material):
    from unittest.mock import AsyncMock
    from app.services.anomalia_service import AnomaliaService
    from app.core.dsms_constants import KTYPE_MATERIAL_COMERCIAL

    svc = AnomaliaService.__new__(AnomaliaService)
    svc.busqueda = AsyncMock()
    svc.busqueda.buscar_similares_a_kitem.return_value = [{"r": 1}, {"r": 2}, {"r": 3}]
    # El primero es de la misma categoría (None); el segundo es el más parecido de otra
    svc._evaluar_similar_clasificacion = AsyncMock(side_effect=[None, "alerta-2", "alerta-3"])

    material = make_material(id_material_corporativo="M1", categoria="Separador")
    assert await svc._detectar_clasificacion_cruzada(material=material) == ["alerta-2"]
    kwargs = svc.busqueda.buscar_similares_a_kitem.call_args.kwargs
    assert kwargs["kitem_id"] == "M1"
    assert kwargs["ktype"] == KTYPE_MATERIAL_COMERCIAL
