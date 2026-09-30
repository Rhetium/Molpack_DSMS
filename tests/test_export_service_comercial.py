"""
Extracción de campos de la ficha comercial (lógica pura de ExportService).

La ficha comercial es otra vista del mismo K-Item: toma el material
corporativo y un subconjunto de las secciones JSONB de la ficha, y los
formatea como texto legible para el cliente ("300 × 200 × 50 mm",
"50 ± 2 g"), sin microbiología ni plano mecánico.
"""

from types import SimpleNamespace


def _material(**kwargs):
    base = {
        "nombre_corporativo": "Bandeja Huevo 30",
        "contenido": "Huevo",
        "categoria": "Bandejas",
        "sector": "Avícola",
        "caracteristica": "Apilable",
        "material_base": "Pulpa moldeada",
        "capacidad_nominal": "30 unidades",
        "tipo_producto": "Empaque",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _ficha(**kwargs):
    base = {
        "nombre_local_material": "Bandeja 30 huevos CO",
        "caracteristicas": {},
        "caracteristicas_contenido": {},
        "empaque_estiba": {},
        "manejo_disposicion": {},
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


# ── _o_guion ──

def test_o_guion_reemplaza_vacios(export_service):
    assert export_service._o_guion(None) == "—"
    assert export_service._o_guion("") == "—"
    assert export_service._o_guion("   ") == "—"
    assert export_service._o_guion("Kraft") == "Kraft"
    assert export_service._o_guion(30) == "30"


# ── _texto_medida ──

def test_texto_medida_con_tolerancia_y_unidad(export_service):
    datos = {"peso_valor": 50, "peso_tolerancia": 2, "peso_unidad": "g"}
    assert export_service._texto_medida(datos, "peso") == "50 ± 2 g"


def test_texto_medida_sin_tolerancia(export_service):
    datos = {"peso_valor": 50, "peso_unidad": "g"}
    assert export_service._texto_medida(datos, "peso") == "50 g"


def test_texto_medida_nc_tiene_prioridad(export_service):
    datos = {"peso_nc": True, "peso_valor": 50, "peso_unidad": "g"}
    assert export_service._texto_medida(datos, "peso") == "N/C"


def test_texto_medida_sin_valor(export_service):
    assert export_service._texto_medida({}, "peso") == "—"
    assert export_service._texto_medida(None, "peso") == "—"
    assert export_service._texto_medida({"peso_valor": ""}, "peso") == "—"


# ── _texto_dimensiones ──

def test_texto_dimensiones_unidad_comun_se_muestra_una_vez(export_service):
    caract = {
        "dimensiones_largo_valor": 300,
        "dimensiones_largo_unidad": "mm",
        "dimensiones_ancho_valor": 200,
        "dimensiones_ancho_unidad": "mm",
        "dimensiones_alto_valor": 50,
        "dimensiones_alto_unidad": "mm",
    }
    assert export_service._texto_dimensiones(caract) == "300 × 200 × 50 mm"


def test_texto_dimensiones_omite_ejes_sin_valor(export_service):
    caract = {
        "dimensiones_largo_valor": 300,
        "dimensiones_largo_unidad": "mm",
        "dimensiones_ancho_valor": "",
        "dimensiones_alto_valor": 50,
        "dimensiones_alto_unidad": "mm",
    }
    assert export_service._texto_dimensiones(caract) == "300 × 50 mm"


def test_texto_dimensiones_unidades_distintas_se_repiten(export_service):
    caract = {
        "dimensiones_largo_valor": 30,
        "dimensiones_largo_unidad": "cm",
        "dimensiones_alto_valor": 50,
        "dimensiones_alto_unidad": "mm",
    }
    assert export_service._texto_dimensiones(caract) == "30 cm × 50 mm"


def test_texto_dimensiones_vacio(export_service):
    assert export_service._texto_dimensiones({}) == "—"
    assert export_service._texto_dimensiones(None) == "—"


# ── Bloques de campos ──

def test_nombre_comercial_usa_corporativo_y_cae_al_local(export_service):
    ficha = _ficha()
    assert export_service._nombre_comercial(ficha, _material()) == "Bandeja Huevo 30"
    assert export_service._nombre_comercial(ficha, None) == "Bandeja 30 huevos CO"
    assert export_service._nombre_comercial(_ficha(nombre_local_material=None), None) == "—"


def test_campos_identificacion_comercial(export_service):
    ficha = _ficha(caracteristicas={"color": "Blanco"})
    campos = dict(export_service._campos_identificacion_comercial(ficha, _material()))
    assert campos == {
        "Nombre Corporativo": "Bandeja Huevo 30",
        "Nombre Local": "Bandeja 30 huevos CO",
        "Material Base": "Pulpa moldeada",
        "Color": "Blanco",
        "Sector": "Avícola",
        "Contenido": "Huevo",
        "Característica": "Apilable",
        "Capacidad": "30 unidades",
    }


def test_campos_identificacion_comercial_sin_material(export_service):
    """Sin material asociado la ficha sigue exportando, con guiones."""
    campos = dict(export_service._campos_identificacion_comercial(_ficha(), None))
    assert campos["Nombre Corporativo"] == "—"
    assert campos["Sector"] == "—"
    assert campos["Nombre Local"] == "Bandeja 30 huevos CO"


def test_campos_especificaciones_comercial(export_service):
    ficha = _ficha(caracteristicas={
        "dimensiones_largo_valor": 300, "dimensiones_largo_unidad": "mm",
        "dimensiones_ancho_valor": 200, "dimensiones_ancho_unidad": "mm",
        "peso_valor": 50, "peso_tolerancia": 2, "peso_unidad": "g",
    })
    campos = dict(export_service._campos_especificaciones_comercial(ficha))
    assert campos == {"Dimensiones": "300 × 200 mm", "Peso": "50 ± 2 g"}


def test_campos_empaque_comercial(export_service):
    ficha = _ficha(empaque_estiba={
        "tipo_empaque": "Caja corrugada",
        "undidades_empaque": 12,
        "alto_empaque_valor": 400, "alto_empaque_unidad": "mm",
        "empaques_estiba": 40,
        "camas_estiba": 5,
        "empaques_camas_estiba": 8,
    })
    campos = dict(export_service._campos_empaque_comercial(ficha))
    assert campos["Tipo de Empaque"] == "Caja corrugada"
    assert campos["Unidades/Empaque"] == "12"
    assert campos["Alto del Empaque"] == "400 mm"
    assert campos["Peso del Empaque"] == "—"
    assert campos["Empaques/Estiba"] == "40"
    assert campos["Camas/Estiba"] == "5"
    assert campos["Empaques/Cama"] == "8"


def test_campos_empaque_comercial_seccion_vacia(export_service):
    campos = dict(export_service._campos_empaque_comercial(_ficha(empaque_estiba=None)))
    assert set(campos.values()) == {"—"}
