"""
Normalización de países: nombre_pais_a_iso.

Acepta códigos ISO-2 directos (lo que envía el frontend) y nombres legibles
(datos legados / scripts de carga). Devuelve siempre ISO-2 o lanza 400.
"""

import pytest
from fastapi import HTTPException

from app.core.utils import nombre_pais_a_iso


@pytest.mark.parametrize("entrada,esperado", [
    ("CO", "CO"),
    ("co", "CO"),
    ("US", "US"),
    ("Colombia", "CO"),
    ("Mexico", "MX"),
])
def test_convierte_a_iso2(entrada, esperado):
    assert nombre_pais_a_iso(entrada) == esperado


def test_recorta_espacios(*_):
    assert nombre_pais_a_iso("  CO  ") == "CO"


@pytest.mark.parametrize("invalido", ["Xyzzy123", "Pais Inexistente"])
def test_nombre_invalido_lanza_400(invalido):
    with pytest.raises(HTTPException) as exc:
        nombre_pais_a_iso(invalido)
    assert exc.value.status_code == 400
