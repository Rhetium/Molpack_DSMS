"""
Helpers de configuración de anomalías: rangos_para_categoria y normalización.

rangos_para_categoria debe ser tolerante a mayúsculas/espacios: 'Porta vasos',
'Portavasos' y 'PORTA VASOS' son la misma categoría. Un lookup exacto
desactivaría silenciosamente el detector D7.
"""

import pytest

from app.core.anomalia_constant import (
    rangos_para_categoria,
    _normalizar_categoria,
    RANGOS_CATEGORIA,
)


def test_categoria_conocida_devuelve_rangos():
    rangos = rangos_para_categoria("Separador")
    assert rangos is not None
    assert "dimensiones_largo_valor" in rangos


@pytest.mark.parametrize("grafia", ["Porta vasos", "Portavasos", "PORTA VASOS", "  porta   vasos "])
def test_lookup_tolerante_a_mayusculas_y_espacios(grafia):
    assert rangos_para_categoria(grafia) is RANGOS_CATEGORIA["Porta vasos"] or \
        rangos_para_categoria(grafia) == RANGOS_CATEGORIA["Porta vasos"]


def test_categoria_desconocida_devuelve_none():
    assert rangos_para_categoria("Categoria Inexistente") is None


@pytest.mark.parametrize("valor", [None, ""])
def test_categoria_vacia_devuelve_none(valor):
    assert rangos_para_categoria(valor) is None


def test_normalizar_quita_espacios_y_baja_caja():
    assert _normalizar_categoria("Porta Vasos") == "portavasos"
    assert _normalizar_categoria("  BANDEJA ") == "bandeja"
    assert _normalizar_categoria(None) == ""


def test_rangos_bien_formados():
    # Cada rango debe ser (min, max, unidad) con min < max.
    for categoria, campos in RANGOS_CATEGORIA.items():
        for campo, tupla in campos.items():
            assert len(tupla) == 3, f"{categoria}.{campo}"
            minimo, maximo, unidad = tupla
            assert minimo < maximo, f"{categoria}.{campo}: min >= max"
            assert isinstance(unidad, str) and unidad
