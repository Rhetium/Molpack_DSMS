"""
Integridad de la tabla de transiciones de estado y constantes asociadas.

La máquina de estados documentada es:
    Borrador → Preliminar → Vigente → Obsoleto  (+ Revisión)
Estos tests fijan ese contrato: si alguien altera TRANSACCIONES_PERMITIDAS
por error, la prueba lo detecta.
"""

from app.core.dsms_constants import (
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
    ESTADO_REVISION,
    TRANSACCIONES_PERMITIDAS,
    ESTADO_ABREVIATURAS,
)

TODOS_LOS_ESTADOS = {
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
    ESTADO_REVISION,
}


def test_transiciones_coinciden_con_maquina_documentada():
    assert TRANSACCIONES_PERMITIDAS == {
        ESTADO_BORRADOR: {ESTADO_PRELIMINAR, ESTADO_OBSOLETO},
        ESTADO_PRELIMINAR: {ESTADO_VIGENTE, ESTADO_OBSOLETO},
        ESTADO_VIGENTE: {ESTADO_OBSOLETO},
        ESTADO_OBSOLETO: {ESTADO_REVISION},
        ESTADO_REVISION: {ESTADO_OBSOLETO, ESTADO_PRELIMINAR},
    }


def test_todos_los_estados_tienen_entrada_de_transicion():
    assert set(TRANSACCIONES_PERMITIDAS.keys()) == TODOS_LOS_ESTADOS


def test_todos_los_destinos_son_estados_validos():
    for origen, destinos in TRANSACCIONES_PERMITIDAS.items():
        assert destinos <= TODOS_LOS_ESTADOS, f"Destino inválido desde {origen}"


def test_ningun_estado_transiciona_a_si_mismo():
    for origen, destinos in TRANSACCIONES_PERMITIDAS.items():
        assert origen not in destinos, f"{origen} no debe transicionar a sí mismo"


def test_borrador_no_puede_saltar_directo_a_vigente():
    # Regla de negocio clave: no se publica sin pasar por Preliminar.
    assert ESTADO_VIGENTE not in TRANSACCIONES_PERMITIDAS[ESTADO_BORRADOR]


def test_toda_categoria_de_estado_tiene_abreviatura():
    assert set(ESTADO_ABREVIATURAS.keys()) == TODOS_LOS_ESTADOS
    # Las abreviaturas deben ser únicas (se usan en el código de ficha).
    assert len(set(ESTADO_ABREVIATURAS.values())) == len(ESTADO_ABREVIATURAS)
