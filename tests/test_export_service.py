"""
Helpers puros de ExportService: agrupación de propiedades para tablas.

_agrupar_propiedades transforma un dict plano de sección JSONB
(campo_valor / campo_tolerancia / campo_unidad / campo_limite) en un dict
agrupado por prefijo, excluyendo campos no imprimibles.
"""


def test_es_campo_excluido(export_service):
    assert export_service._es_campo_excluido("x_valor", None) is True
    assert export_service._es_campo_excluido("imagenes", {"a": 1}) is True
    assert export_service._es_campo_excluido("peso_nc", True) is True
    assert export_service._es_campo_excluido("algo", [1, 2]) is True
    assert export_service._es_campo_excluido("algo", {"k": "v"}) is True
    assert export_service._es_campo_excluido("peso_valor", 50) is False


def test_agrupar_propiedades_agrupa_por_prefijo(export_service):
    datos = {
        "peso_valor": 50,
        "peso_tolerancia": 2,
        "peso_unidad": "g",
        "color": "rojo",
    }
    resultado = export_service._agrupar_propiedades(datos)
    assert resultado == {
        "peso": {"valor": 50, "tolerancia": 2, "unidad": "g"},
        "color": {"valor": "rojo"},
    }


def test_agrupar_propiedades_excluye_campos_no_imprimibles(export_service):
    datos = {
        "peso_valor": 50,
        "peso_nc": True,             # flag N/C → excluido
        "imagenes": {"foto": "x"},   # imágenes → excluido
        "vacio_valor": None,         # None → excluido
    }
    resultado = export_service._agrupar_propiedades(datos)
    assert resultado == {"peso": {"valor": 50}}


def test_agrupar_propiedades_maneja_limite(export_service):
    datos = {"aerobico_valor": 100, "aerobico_limite": 1000}
    resultado = export_service._agrupar_propiedades(datos)
    assert resultado == {"aerobico": {"valor": 100, "limite": 1000}}


def test_agrupar_propiedades_vacio(export_service):
    assert export_service._agrupar_propiedades({}) == {}
