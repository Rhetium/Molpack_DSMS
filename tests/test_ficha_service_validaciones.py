"""
Validaciones de completitud y utilidades de FichaService.

Cubre:
- _validar_para_preliminar: campos obligatorios para avanzar a Preliminar.
- _validar_para_vigente: además exige tipo de empaque.
- _generar_codigo_ficha: formato del código de ficha.
- _incrementar_version_simple: incremento de versión mayor.
- _validar_contenido_por_tipo: tolerancia de secciones de contenido vacías.
"""

import pytest
from fastapi import HTTPException

from app.core.dsms_constants import (
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
)

MANEJO_COMPLETO = {
    "uso": "Uso X",
    "manejo": "Manejo Y",
    "almacenamiento": "Lugar seco",
    "transporte": "Terrestre",
    "vida_util": "12 meses",
}


def _ficha_preliminar_completa(make_ficha, **overrides):
    datos = dict(
        codigo_material_local="MAT-001",
        pais="CO",
        nombre_local_material="Bandeja X",
        caracteristicas={"color": "verde"},
        manejo_disposicion=dict(MANEJO_COMPLETO),
    )
    datos.update(overrides)
    return make_ficha(**datos)


# ── _validar_para_preliminar ───────────────────────────────────────────────

def test_preliminar_completa_no_lanza(ficha_service, make_ficha):
    ficha = _ficha_preliminar_completa(make_ficha)
    ficha_service._validar_para_preliminar(ficha)


@pytest.mark.parametrize("campo,esperado", [
    ("codigo_material_local", "Código de material local"),
    ("pais", "País"),
    ("nombre_local_material", "Nombre local del material"),
    ("caracteristicas", "Características físicas"),
])
def test_preliminar_falta_campo_escalar(ficha_service, make_ficha, campo, esperado):
    ficha = _ficha_preliminar_completa(make_ficha, **{campo: None})
    with pytest.raises(HTTPException) as exc:
        ficha_service._validar_para_preliminar(ficha)
    assert exc.value.status_code == 400
    assert esperado in exc.value.detail


def test_preliminar_falta_campo_de_manejo(ficha_service, make_ficha):
    manejo_incompleto = dict(MANEJO_COMPLETO)
    del manejo_incompleto["vida_util"]
    ficha = _ficha_preliminar_completa(make_ficha, manejo_disposicion=manejo_incompleto)
    with pytest.raises(HTTPException) as exc:
        ficha_service._validar_para_preliminar(ficha)
    assert "Vida útil" in exc.value.detail


def test_preliminar_reporta_todos_los_faltantes_juntos(ficha_service, make_ficha):
    ficha = make_ficha()  # todo vacío
    with pytest.raises(HTTPException) as exc:
        ficha_service._validar_para_preliminar(ficha)
    detalle = exc.value.detail
    assert "Código de material local" in detalle
    assert "País" in detalle
    assert "Manejo y disposición" in detalle


# ── _validar_para_vigente ──────────────────────────────────────────────────

def test_vigente_requiere_tipo_empaque(ficha_service, make_ficha):
    # Ficha completa para preliminar pero sin empaque → falla en vigente.
    ficha = _ficha_preliminar_completa(make_ficha, empaque_estiba=None)
    with pytest.raises(HTTPException) as exc:
        ficha_service._validar_para_vigente(ficha)
    assert "empaque" in exc.value.detail.lower()


def test_vigente_completa_no_lanza(ficha_service, make_ficha):
    ficha = _ficha_preliminar_completa(
        make_ficha, empaque_estiba={"tipo_empaque": "Caja"}
    )
    ficha_service._validar_para_vigente(ficha)


def test_vigente_tambien_exige_completitud_de_preliminar(ficha_service, make_ficha):
    # Con empaque pero sin nombre local → debe fallar por la regla de preliminar.
    ficha = _ficha_preliminar_completa(
        make_ficha,
        nombre_local_material=None,
        empaque_estiba={"tipo_empaque": "Caja"},
    )
    with pytest.raises(HTTPException):
        ficha_service._validar_para_vigente(ficha)


# ── _generar_codigo_ficha ──────────────────────────────────────────────────

def test_generar_codigo_ficha_formato(ficha_service):
    codigo = ficha_service._generar_codigo_ficha(
        codigo_material_local="MAT-001",
        pais="co",
        estado_ficha=ESTADO_BORRADOR,
        codigo_version="1.0",
    )
    assert codigo == "FT-MAT-001-CO-BOR-V1.0"


def test_generar_codigo_ficha_estados(ficha_service):
    assert ficha_service._generar_codigo_ficha("M", "CO", ESTADO_PRELIMINAR, "2.0").endswith("-PRE-V2.0")
    assert ficha_service._generar_codigo_ficha("M", "CO", ESTADO_VIGENTE, "3.0").endswith("-VIG-V3.0")


def test_generar_codigo_ficha_estado_desconocido_usa_unk(ficha_service):
    codigo = ficha_service._generar_codigo_ficha("M", "CO", "EstadoRaro", "1.0")
    assert "-UNK-" in codigo


# ── _incrementar_version_simple ────────────────────────────────────────────

@pytest.mark.parametrize("actual,esperado", [
    ("1.0", "2.0"),
    ("2.0", "3.0"),
    ("3.5", "4.0"),   # int(float("3.5")) = 3 → 4.0
    ("10.0", "11.0"),
])
def test_incrementar_version(ficha_service, actual, esperado):
    assert ficha_service._incrementar_version_simple(actual) == esperado


@pytest.mark.parametrize("invalido", ["", "abc", None])
def test_incrementar_version_invalida_cae_a_2(ficha_service, invalido):
    assert ficha_service._incrementar_version_simple(invalido) == "2.0"


# ── _validar_contenido_por_tipo ────────────────────────────────────────────

def test_contenido_none_es_valido(ficha_service):
    ficha_service._validar_contenido_por_tipo(None)  # no lanza


def test_contenido_todo_vacio_es_tolerado(ficha_service):
    # Sección presente pero sin ningún *_valor → se ignora sin error.
    ficha_service._validar_contenido_por_tipo(
        {"profundidad_pilar_valor": None, "diametro_alveolo_valor": None}
    )


def test_contenido_con_algun_valor_es_valido(ficha_service):
    ficha_service._validar_contenido_por_tipo({"profundidad_pilar_valor": 12.5})
