"""
Máquina de estados de FichaTecnica: FichaService._validar_transicion_estado.

Método puro: dado (estado_actual, nuevo_estado), no hace nada si la
transición es válida y lanza HTTPException 400 si no lo es.
"""

import pytest
from fastapi import HTTPException

from app.core.dsms_constants import (
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
    ESTADO_REVISION,
    TRANSACCIONES_PERMITIDAS,
)

ESTADOS = [
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
    ESTADO_REVISION,
]

TRANSICIONES_VALIDAS = [
    (origen, destino)
    for origen, destinos in TRANSACCIONES_PERMITIDAS.items()
    for destino in destinos
]

TRANSICIONES_INVALIDAS = [
    (origen, destino)
    for origen in ESTADOS
    for destino in ESTADOS
    if destino not in TRANSACCIONES_PERMITIDAS.get(origen, set())
]


@pytest.mark.parametrize("origen,destino", TRANSICIONES_VALIDAS)
def test_transiciones_validas_no_lanzan(ficha_service, origen, destino):
    # No debe lanzar excepción alguna.
    ficha_service._validar_transicion_estado(origen, destino)


@pytest.mark.parametrize("origen,destino", TRANSICIONES_INVALIDAS)
def test_transiciones_invalidas_lanzan_400(ficha_service, origen, destino):
    with pytest.raises(HTTPException) as exc:
        ficha_service._validar_transicion_estado(origen, destino)
    assert exc.value.status_code == 400
    assert "no permitida" in exc.value.detail.lower()


def test_estado_desconocido_no_permite_transicion(ficha_service):
    # Un estado no registrado no tiene destinos permitidos → siempre 400.
    with pytest.raises(HTTPException) as exc:
        ficha_service._validar_transicion_estado("EstadoInexistente", ESTADO_VIGENTE)
    assert exc.value.status_code == 400


def test_borrador_a_vigente_esta_prohibido(ficha_service):
    with pytest.raises(HTTPException):
        ficha_service._validar_transicion_estado(ESTADO_BORRADOR, ESTADO_VIGENTE)


def test_vigente_a_borrador_esta_prohibido(ficha_service):
    with pytest.raises(HTTPException):
        ficha_service._validar_transicion_estado(ESTADO_VIGENTE, ESTADO_BORRADOR)
