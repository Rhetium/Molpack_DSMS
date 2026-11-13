"""
Generador de datos de prueba para poblar el DSMS a partir de la prueba piloto.

Toma como referencia los valores reales de las fichas piloto (separadores,
estuches, bandejas y porta vasos de pulpa moldeada) y genera:

  - Materiales nuevos: variantes plausibles de las familias piloto.
  - Fichas técnicas en varios países para materiales piloto y nuevos, con
    diferencias notables entre sí pero dentro de lo normal (siempre dentro
    de RANGOS_CATEGORIA y sin valores extremos).
  - Mezcla de estados (Borrador / Preliminar / Vigente) e historial de
    versiones (v1 Obsoleto → v2 Vigente) en parte de las fichas.

Todo pasa por los servicios reales (MaterialService, FichaService), así que
cada registro recibe embedding, relaciones, auditoría y análisis de anomalías
igual que en uso normal. Como los datos generados son normales por
construcción, toda anomalía que salte es un falso positivo: el script las
descarta con una nota y al final muestra el conteo por detector.

Los registros quedan marcados con usuario_creador 'seed.*'. Las fichas piloto
no se modifican.

Uso:
    cd <raíz del proyecto>
    python scripts/seed_datos_prueba.py              # generar e insertar
    python scripts/seed_datos_prueba.py --dry-run    # solo mostrar lo generado
    python scripts/seed_datos_prueba.py --entrenar   # insertar y reentrenar ML
    python scripts/seed_datos_prueba.py --limpiar    # borrar lo generado
"""

import argparse
import asyncio
import logging
import os
import random
import shutil
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy import select, and_, delete, func

from app.core.database import AsyncSessionLocal
from app.core.anomalia_constant import (
    rangos_para_categoria,
    ESTADO_ANOMALIA_PENDIENTE,
    ESTADO_ANOMALIA_DESCARTADA,
)
from app.core.dsms_constants import (
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
)
from app.models.kitem import KItem
from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
from app.models.anomalia import AnomaliaRegistro
from app.schemas.material import MaterialCreateSchema
from app.schemas.ficha import (
    FichaTecnicaCreateSchema,
    CaracteristicasSchema,
    CaracteristicasContenidoSchema,
    EmpaqueEstibaSchema,
    MicrobiologiaSchema,
    ManejoDisposicionSchema,
)
from app.services import fichas_services
from app.services.fichas_services import FichaService
from app.services.material_service import MaterialService
from app.services.anomalia_service import AnomaliaService

SEMILLA = 42
PREFIJO_USUARIO = "seed."
USUARIOS = ["seed.calidad", "seed.ingenieria", "seed.produccion"]
NOTA_DESCARTE = (
    "Seed de prueba: valor generado dentro del rango normal de la familia. "
    "Falso positivo del detector."
)

PAISES = ["VE", "CR", "CO", "EC", "PE", "GT", "PA", "DO", "HN", "MX"]

# Proporción de estados finales para las fichas generadas
DISTRIBUCION_ESTADOS = [
    (ESTADO_VIGENTE, 0.75),
    (ESTADO_PRELIMINAR, 0.15),
    (ESTADO_BORRADOR, 0.10),
]
PROB_NUEVA_VERSION = 0.18  # de las vigentes, cuántas pasan a v2


# ---------------------------------------------------------------------------
# Familias de producto (valores base tomados de la prueba piloto)
# ---------------------------------------------------------------------------
# dims: (largo, ancho, alto) en mm · peso en g · encolado: opciones en min
# empaque: (unidades por bolsa, camas, empaques por cama)

MANEJO_HUEVOS = {
    "uso": "Empaque de huevos de gallina, en granjas de producción avícola",
    "manejo": "Manipular con cuidado. Consulte al fabricante para instrucciones específicas de manejo.",
    "almacenamiento": "El producto debe ser almacenado en tarimas, en un lugar seco, protegido del sol, el polvo, la luz e intemperie",
    "transporte": "Se recomienda no transportar otros productos que afecten la calidad e inocuidad del producto terminado",
    "garantias": "El producto",
}
MANEJO_BANDEJA = {
    "uso": "Bandeja de pulpa moldeada para el empaque de productos agrícolas frescos.",
    "manejo": "Manipular con manos limpias y secas. Evitar contacto con sustancias químicas o humedad excesiva.",
    "almacenamiento": "Almacenar en lugar fresco y seco, temperatura entre 15°C y 30°C, humedad relativa menor al 70%.",
    "transporte": "Transportar en vehículo cerrado y limpio. Proteger de la lluvia y humedad.",
    "inocuidad": "Apto para contacto directo con frutas y verduras frescas.",
}
MANEJO_VASOS = {
    "uso": "Portavasos de pulpa moldeada para el transporte de bebidas",
    "manejo": "Manipular con cuidado. Consulte al fabricante para instrucciones específicas de manejo.",
    "almacenamiento": "El producto debe ser almacenado en tarimas, en un lugar seco, protegido del sol, el polvo, la luz e intemperie",
    "transporte": "Se recomienda no transportar otros productos que afecten la calidad e inocuidad del producto terminado",
    "garantias": "El producto",
}
VIDA_UTIL = [
    "Se recomienda consumir el producto en un periodo no mayor a 6 meses posterior a su fecha de producción",
    "Se recomienda consumir el producto en un periodo no mayor a 12 meses posterior a su fecha de producción",
    "24 meses a partir de la fecha de fabricación, bajo las condiciones de almacenamiento indicadas.",
]
DISPOSICION = (
    "Después de utilizar {obj} la disposición final del producto puede ser de relleno sanitario, "
    "para uso de manualidades o como abono orgánico directo al suelo"
)

FAMILIAS = [
    # --- Materiales piloto (solo se les agregan fichas en otros países) ---
    {"nombre": "Separador 1x30 Universal", "piloto": True, "categoria": "Separador",
     "dims": (298, 298, 50), "peso": 60, "encolado": [5, 15, 30], "ruptura": 13,
     "deflexion": (12, 20), "pilar": 48, "empaque": (140, 6, 10), "n_paises": 4},
    {"nombre": "Separador 1x30 Super Pocket", "piloto": True, "categoria": "Separador",
     "dims": (298, 298, 50), "peso": 64, "encolado": [5, 30], "ruptura": 15,
     "deflexion": (12, 20), "pilar": 48, "empaque": (140, 6, 10), "n_paises": 3},
    {"nombre": "Estuche 1x12 S/Planchar", "piloto": True, "categoria": "Estuche",
     "dims": (300, 250, 50), "peso": 58, "encolado": [5, 30], "alveolo": 45,
     "empaque": (180, 6, 4), "n_paises": 3},
    {"nombre": "Estuche 1x12 con ventana S/I", "piloto": True, "categoria": "Estuche",
     "dims": (300, 250, 55), "peso": 56, "encolado": [5, 15], "alveolo": 45,
     "empaque": (180, 6, 4), "n_paises": 3},
    {"nombre": "Estuche 1x15 con ventana S/I", "piloto": True, "categoria": "Estuche",
     "dims": (350, 250, 70), "peso": 60, "encolado": [0, 15], "alveolo": 45,
     "empaque": (140, 4, 8), "n_paises": 3},
    {"nombre": "Bandeja Biopack 2B", "piloto": True, "categoria": "Bandeja",
     "dims": (210, 155, 15), "peso": 22, "encolado": [90, 120], "cavidad": 12,
     "empaque": (300, 4, 9), "n_paises": 3},
    {"nombre": "Bandeja Biopack 4G", "piloto": True, "categoria": "Bandeja",
     "dims": (260, 155, 30), "peso": 35, "encolado": [90, 120], "cavidad": 26,
     "empaque": (300, 6, 6), "n_paises": 3},
    {"nombre": "Porta Vasos 2 Cav", "piloto": True, "categoria": "Porta vasos",
     "dims": (203, 117, 52), "peso": 36, "encolado": [25], "diam_cavidad": 88,
     "empaque": (600, 4, 11), "n_paises": 3},
    {"nombre": "Porta Vasos 4 Cav", "piloto": True, "categoria": "Porta vasos",
     "dims": (223, 220, 50), "peso": 34, "encolado": [25], "diam_cavidad": 88,
     "empaque": (300, 4, 9), "n_paises": 3},

    # --- Materiales nuevos (variantes de las familias piloto) ---
    {"nombre": "Separador 1x30 Reforzado", "categoria": "Separador", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "30", "caracteristica": "Reforzado",
     "dims": (300, 300, 52), "peso": 74, "encolado": [15, 30], "ruptura": 17,
     "deflexion": (10, 17), "pilar": 50, "empaque": (120, 6, 10), "n_paises": 5},
    {"nombre": "Separador 1x30 Liviano", "categoria": "Separador", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "30", "caracteristica": "No aplica",
     "dims": (296, 296, 46), "peso": 54, "encolado": [5, 15], "ruptura": 12,
     "deflexion": (13, 22), "pilar": 46, "empaque": (160, 6, 10), "n_paises": 4},
    {"nombre": "Separador 1x30 Jumbo", "categoria": "Separador", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "30", "caracteristica": "Huevo jumbo",
     "dims": (310, 310, 56), "peso": 72, "encolado": [15, 30], "ruptura": 16,
     "deflexion": (11, 19), "pilar": 52, "empaque": (120, 6, 9), "n_paises": 4},
    {"nombre": "Separador 1x20 Exportación", "categoria": "Separador", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "20", "caracteristica": "Apilable",
     "dims": (250, 210, 48), "peso": 46, "encolado": [5, 15], "ruptura": 12,
     "deflexion": (12, 20), "pilar": 47, "empaque": (200, 6, 12), "n_paises": 3},
    {"nombre": "Estuche 1x18 S/Planchar", "categoria": "Estuche", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "18", "caracteristica": "No aplica",
     "dims": (400, 300, 68), "peso": 80, "encolado": [15, 30], "alveolo": 46,
     "empaque": (100, 5, 6), "n_paises": 4},
    {"nombre": "Estuche 1x10 con ventana S/I", "categoria": "Estuche", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "10", "caracteristica": "Con ventana",
     "dims": (260, 200, 62), "peso": 48, "encolado": [5, 15], "alveolo": 45,
     "empaque": (200, 6, 5), "n_paises": 4},
    {"nombre": "Estuche 1x12 Planchado Premium", "categoria": "Estuche", "contenido": "Huevos",
     "sector": "Avícola", "capacidad": "12", "caracteristica": "Planchado",
     "dims": (305, 255, 56), "peso": 66, "encolado": [15, 30], "alveolo": 46,
     "empaque": (160, 6, 4), "n_paises": 4},
    {"nombre": "Bandeja Biopack 1B", "categoria": "Bandeja", "contenido": "Frutas y Verduras",
     "sector": "Agrícola", "capacidad": "No Aplica", "caracteristica": "No aplica",
     "dims": (175, 135, 15), "peso": 15, "encolado": [90, 120], "cavidad": 12,
     "empaque": (400, 4, 10), "n_paises": 4},
    {"nombre": "Bandeja Biopack 3B", "categoria": "Bandeja", "contenido": "Frutas y Verduras",
     "sector": "Agrícola", "capacidad": "No Aplica", "caracteristica": "No aplica",
     "dims": (230, 165, 22), "peso": 27, "encolado": [90, 120], "cavidad": 18,
     "empaque": (300, 5, 8), "n_paises": 4},
    {"nombre": "Bandeja Biopack 6G", "categoria": "Bandeja", "contenido": "Frutas y Verduras",
     "sector": "Agrícola", "capacidad": "No Aplica", "caracteristica": "Alta capacidad",
     "dims": (300, 200, 40), "peso": 46, "encolado": [90, 120], "cavidad": 34,
     "empaque": (200, 6, 6), "n_paises": 3},
    {"nombre": "Bandeja Biopack Hongos", "categoria": "Bandeja", "contenido": "Frutas y Verduras",
     "sector": "Agrícola", "capacidad": "No Aplica", "caracteristica": "Con ventilación",
     "dims": (200, 140, 42), "peso": 24, "encolado": [90, 120], "cavidad": 38,
     "empaque": (300, 5, 8), "n_paises": 3},
    {"nombre": "Porta Vasos 4 Cav Reforzado", "categoria": "Porta vasos", "contenido": "Vasos",
     "sector": "Consumo Másivo", "capacidad": "4", "caracteristica": "Reforzado",
     "dims": (225, 222, 55), "peso": 44, "encolado": [25, 30], "diam_cavidad": 90,
     "empaque": (250, 4, 9), "n_paises": 4},
    {"nombre": "Porta Vasos 2 Cav Delivery", "categoria": "Porta vasos", "contenido": "Vasos",
     "sector": "Consumo Másivo", "capacidad": "2", "caracteristica": "Bipartido",
     "dims": (210, 120, 60), "peso": 30, "encolado": [25], "diam_cavidad": 92,
     "empaque": (600, 4, 11), "n_paises": 3},
    {"nombre": "Porta Vasos 4 Cav Café", "categoria": "Porta vasos", "contenido": "Vasos",
     "sector": "Consumo Másivo", "capacidad": "4", "caracteristica": "Vaso térmico",
     "dims": (235, 230, 45), "peso": 38, "encolado": [25, 30], "diam_cavidad": 96,
     "empaque": (300, 4, 9), "n_paises": 3},
]

NOMBRES_LOCALES = {
    "Separador": ["Separador para huevos x{cap}", "Bandeja de huevos x{cap}", "Cubeta de huevos {cap}"],
    "Estuche": ["Estuche de huevos x{cap}", "Caja de huevos {cap} und", "Empaque huevos x{cap}"],
    "Bandeja": ["Bandeja frutas {n}", "Bandeja agrícola {n}", "Bandeja pulpa {n}"],
    "Porta vasos": ["Portavasos {cap} puestos", "Porta bebidas x{cap}", "Bandeja vasos {cap}"],
}
COLORES = {
    "Separador": [("Natural", 0.55), ("Gris", 0.2), ("Verde", 0.1), ("Rosado", 0.08), ("Amarillo", 0.07)],
    "Estuche": [("Natural", 0.6), ("Gris", 0.25), ("Blanco", 0.15)],
    "Bandeja": [("Natural", 0.75), ("Blanco", 0.25)],
    "Porta vasos": [("Natural", 0.8), ("Gris", 0.2)],
}
COLORES_EMPAQUE = ["Transparente", "Transparente", "Negro", "Azul", None]
PREFIJO_CODIGO = {"Separador": "51", "Estuche": "41", "Bandeja": "52", "Porta vasos": "53"}


# ---------------------------------------------------------------------------
# Generación de valores (pura, sin DB)
# ---------------------------------------------------------------------------

def _elegir_ponderado(rng: random.Random, opciones: list[tuple]):
    valores, pesos = zip(*opciones)
    return rng.choices(valores, weights=pesos, k=1)[0]


def _variar(rng: random.Random, base: float, sigma: float, tope: float) -> float:
    """Variación gaussiana relativa, recortada a ±tope para no salir de lo normal."""
    factor = max(1 - tope, min(1 + tope, rng.gauss(1, sigma)))
    return base * factor


def _acotar(valor: float, rango: tuple | None) -> float:
    """Mantiene el valor dentro del rango de categoría con un margen del 3%."""
    if not rango:
        return valor
    minimo, maximo, _ = rango
    margen = (maximo - minimo) * 0.03
    return max(minimo + margen, min(maximo - margen, valor))


def generar_ficha(rng: random.Random, fam: dict) -> dict:
    """Arma las secciones JSONB de una ficha a partir de su familia."""
    cat = fam["categoria"]
    rangos = rangos_para_categoria(cat) or {}
    es_huevo = cat in ("Separador", "Estuche")

    largo, ancho, alto = fam["dims"]
    largo = round(_acotar(_variar(rng, largo, 0.012, 0.03), rangos.get("dimensiones_largo_valor")))
    ancho = round(_acotar(_variar(rng, ancho, 0.012, 0.03), rangos.get("dimensiones_ancho_valor")))
    alto = round(_acotar(_variar(rng, alto, 0.03, 0.07), rangos.get("dimensiones_alto_valor")))
    peso = round(_acotar(_variar(rng, fam["peso"], 0.05, 0.10), rangos.get("peso_valor")))

    caract = {
        "color": _elegir_ponderado(rng, COLORES[cat]),
        "dimensiones_largo_valor": float(largo), "dimensiones_largo_tolerancia": float(rng.choice([1, 2, 2, 3])), "dimensiones_largo_unidad": "mm",
        "dimensiones_ancho_valor": float(ancho), "dimensiones_ancho_tolerancia": float(rng.choice([1, 2, 2, 3])), "dimensiones_ancho_unidad": "mm",
        "dimensiones_alto_valor": float(alto), "dimensiones_alto_tolerancia": 1.0, "dimensiones_alto_unidad": "mm",
        "peso_valor": float(peso), "peso_tolerancia": float(rng.choice([1, 2, 2, 3])), "peso_unidad": "g",
        "tiempo_encolado_valor": float(rng.choice(fam["encolado"])), "tiempo_encolado_unidad": "min",
    }
    if es_huevo and fam.get("ruptura"):
        caract["ruptura_valor"] = float(round(_variar(rng, fam["ruptura"], 0.06, 0.12)))
        caract["ruptura_unidad"] = "Kgf"
    if fam.get("deflexion"):
        interna, externa = fam["deflexion"]
        caract["deflexion_interna_valor"] = float(round(_variar(rng, interna, 0.06, 0.12)))
        caract["deflexion_interna_unidad"] = "mm"
        caract["deflexion_externa_valor"] = float(round(_variar(rng, externa, 0.06, 0.12)))
        caract["deflexion_externa_unidad"] = "mm"
    if cat == "Porta vasos" and rng.random() < 0.6:
        caract["resistencia_valor"] = round(rng.uniform(3.0, 5.0), 1)
        caract["resistencia_unidad"] = "Kgf"
    if cat == "Bandeja" and rng.random() < 0.5:
        caract["porcentaje_absorcion_valor"] = float(rng.choice([15, 18, 20, 22]))
        caract["porcentaje_absorcion_tolerancia"] = 1.0
        caract["porcentaje_absorcion_unidad"] = "%"

    contenido = {}
    if fam.get("pilar"):
        contenido.update(profundidad_pilar_valor=float(round(_variar(rng, fam["pilar"], 0.02, 0.05))),
                         profundidad_pilar_tolerancia=1.0, profundidad_pilar_unidad="mm")
    if fam.get("alveolo"):
        contenido.update(diametro_alveolo_valor=float(round(_variar(rng, fam["alveolo"], 0.015, 0.04))),
                         diametro_alveolo_tolerancia=1.0, diametro_alveolo_unidad="mm")
    if fam.get("cavidad"):
        contenido.update(profundidad_cavidad_valor=float(round(_variar(rng, fam["cavidad"], 0.04, 0.08))),
                         profundidad_cavidad_tolerancia=1.0, profundidad_cavidad_unidad="mm")
    if fam.get("diam_cavidad"):
        contenido.update(diametro_cavidad_valor=float(round(_variar(rng, fam["diam_cavidad"], 0.015, 0.04))),
                         diametro_cavidad_tolerancia=1.0, diametro_cavidad_unidad="mm",
                         profundidad_cavidad_valor=float(round(_variar(rng, alto * 0.8, 0.03, 0.06))),
                         profundidad_cavidad_tolerancia=1.0, profundidad_cavidad_unidad="mm")

    # Empaque: unidades por bolsa con pasos realistas; peso coherente con el peso unitario
    unidades, camas, por_cama = fam["empaque"]
    unidades = max(20, unidades + rng.choice([-20, 0, 0, 0, 20]))
    camas = max(3, camas + rng.choice([-1, 0, 0, 1]))
    peso_bolsa = round(unidades * peso / 1000 * rng.uniform(1.0, 1.04), 2)
    alto_bolsa = round(unidades * alto / 100 * rng.uniform(0.10, 0.13))  # unidades anidadas
    empaque = {
        "tipo_empaque": rng.choice(["Bolsa de polietileno de alta densidad"] * 4 + ["Caja corrugada"]),
        "color_empaque": rng.choice(COLORES_EMPAQUE),
        "undidades_empaque": unidades,
        "camas_estiba": camas,
        "empaques_camas_estiba": por_cama,
        "empaques_estiba": camas * por_cama,
        "alto_empaque_valor": float(max(30, min(95, alto_bolsa))), "alto_empaque_tolerancia": float(rng.choice([1, 2, 3, 5])), "alto_empaque_unidad": "cm",
        "peso_empaque_valor": peso_bolsa, "peso_empaque_tolerancia": round(peso_bolsa * rng.choice([0.03, 0.05, 0.07]), 2), "peso_empaque_unidad": "Kg",
    }

    microbiologia = None
    if cat in ("Bandeja", "Estuche") and rng.random() < 0.45:
        microbiologia = {
            "recuento_aerobico_valor": float(rng.choice([50, 100, 150, 250, 400])), "recuento_aerobico_limite": 1000.0,
            "recuento_moho_valor": float(rng.choice([10, 20, 40, 60])), "recuento_moho_limite": 100.0,
            "coliforme_valor": float(rng.choice([0, 3, 5])), "coliforme_limite": 10.0,
            "cadmio_valor": round(rng.uniform(0.02, 0.2), 2), "cadmio_unidad": "mg/Kg",
            "plomo_valor": round(rng.uniform(0.1, 1.5), 2), "plomo_unidad": "mg/Kg",
        }

    base_manejo = MANEJO_HUEVOS if es_huevo else MANEJO_BANDEJA if cat == "Bandeja" else MANEJO_VASOS
    objeto = {"Separador": "los separadores para huevo", "Estuche": "los estuches",
              "Bandeja": "las bandejas", "Porta vasos": "el portavasos"}[cat]
    manejo = dict(base_manejo, vida_util=rng.choice(VIDA_UTIL), disposicion_pt=DISPOSICION.format(obj=objeto))

    return {
        "caracteristicas": caract,
        "caracteristicas_contenido": contenido or None,
        "empaque_estiba": empaque,
        "microbiologia": microbiologia,
        "manejo_disposicion": manejo,
    }


def planificar(rng: random.Random, paises_ocupados: dict[str, set], codigos_usados: set) -> list[dict]:
    """Decide qué fichas crear: material, país, código, estado final y si versiona."""
    plan = []
    for fam in FAMILIAS:
        ocupados = paises_ocupados.get(fam["nombre"], set())
        disponibles = [p for p in PAISES if p not in ocupados]
        for pais in rng.sample(disponibles, min(fam["n_paises"], len(disponibles))):
            while True:
                codigo = PREFIJO_CODIGO[fam["categoria"]] + f"{rng.randint(0, 999999):06d}"
                if codigo not in codigos_usados:
                    codigos_usados.add(codigo)
                    break
            estado = _elegir_ponderado(rng, DISTRIBUCION_ESTADOS)
            cap = fam.get("capacidad") or fam["nombre"].split("x")[-1].split()[0]
            plan.append({
                "familia": fam,
                "pais": pais,
                "codigo": codigo,
                "nombre_local": rng.choice(NOMBRES_LOCALES[fam["categoria"]]).format(
                    cap=cap, n=fam["nombre"].split()[-1]),
                "estado_final": estado,
                "nueva_version": estado == ESTADO_VIGENTE and rng.random() < PROB_NUEVA_VERSION,
                "usuario": rng.choice(USUARIOS),
                "datos": generar_ficha(rng, fam),
            })
    return plan


# ---------------------------------------------------------------------------
# Persistencia vía servicios
# ---------------------------------------------------------------------------

def _schema_ficha(id_material, item: dict) -> FichaTecnicaCreateSchema:
    d = item["datos"]
    return FichaTecnicaCreateSchema(
        id_material_corporativo=id_material,
        codigo_material_local=item["codigo"],
        nombre_local_material=item["nombre_local"],
        usuario_creador=item["usuario"],
        pais=item["pais"],
        caracteristicas=CaracteristicasSchema(**d["caracteristicas"]),
        caracteristicas_contenido=CaracteristicasContenidoSchema(**d["caracteristicas_contenido"]) if d["caracteristicas_contenido"] else None,
        empaque_estiba=EmpaqueEstibaSchema(**d["empaque_estiba"]),
        microbiologia=MicrobiologiaSchema(**d["microbiologia"]) if d["microbiologia"] else None,
        manejo_disposicion=ManejoDisposicionSchema(**d["manejo_disposicion"]),
    )


async def _descartar_pendientes(session, id_kitem, usuario: str, falsos_positivos: Counter) -> int:
    """Descarta las anomalías pendientes de un k-item generado (son falsos positivos)."""
    result = await session.execute(
        select(AnomaliaRegistro).where(and_(
            AnomaliaRegistro.kitem_id == id_kitem,
            AnomaliaRegistro.estado == ESTADO_ANOMALIA_PENDIENTE,
        ))
    )
    pendientes = result.scalars().all()
    svc = AnomaliaService(session)
    for anomalia in pendientes:
        falsos_positivos[(anomalia.tipo_anomalia, anomalia.severidad)] += 1
        await svc.resolver_anomalia(anomalia.id, ESTADO_ANOMALIA_DESCARTADA, usuario, NOTA_DESCARTE)
    await session.commit()
    return len(pendientes)


async def _contexto_existente():
    """Países con ficha por material y códigos locales ya usados en la DB."""
    async with AsyncSessionLocal() as session:
        materiales = {
            nombre: id_ for id_, nombre in (await session.execute(
                select(MaterialComercial.id_material_corporativo, MaterialComercial.nombre_corporativo)
            )).all()
        }
        filas = (await session.execute(
            select(MaterialComercial.nombre_corporativo, FichaTecnica.pais, FichaTecnica.codigo_material_local)
            .join(FichaTecnica, FichaTecnica.id_material_corporativo == MaterialComercial.id_material_corporativo)
        )).all()
    paises: dict[str, set] = {}
    codigos = set()
    for nombre, pais, codigo in filas:
        paises.setdefault(nombre, set()).add(pais)
        codigos.add(codigo)
    return materiales, paises, codigos


async def crear_materiales(materiales: dict, falsos_positivos: Counter) -> None:
    for fam in FAMILIAS:
        if fam["nombre"] in materiales:
            continue
        if fam.get("piloto"):
            print(f"  ! Material piloto no encontrado, se omite: {fam['nombre']}")
            continue
        async with AsyncSessionLocal() as session:
            material = await MaterialService(session).crear(MaterialCreateSchema(
                nombre_corporativo=fam["nombre"],
                contenido=fam["contenido"],
                categoria=fam["categoria"],
                sector=fam["sector"],
                caracteristica=fam["caracteristica"],
                material_base="Pulpa Moldeada",
                capacidad_nominal=fam["capacidad"],
                tipo_producto="Producto Terminado",
                estado_material="Activo",
                usuario_creador=USUARIOS[1],
            ))
            await _descartar_pendientes(session, material.id_material_corporativo, USUARIOS[1], falsos_positivos)
            materiales[fam["nombre"]] = material.id_material_corporativo
            print(f"  + Material: {fam['nombre']}")


async def crear_ficha(item: dict, id_material, falsos_positivos: Counter) -> str:
    usuario = item["usuario"]
    async with AsyncSessionLocal() as session:
        svc = FichaService(session)
        ficha = await svc.crear(_schema_ficha(id_material, item))
        if item["estado_final"] == ESTADO_BORRADOR:
            return ficha.codigo_ficha_local

        # Al pasar a Preliminar corre el análisis completo de anomalías
        ficha = await svc.cambiar_estado(ficha.id_ficha, ESTADO_PRELIMINAR, usuario)
        if item["estado_final"] == ESTADO_PRELIMINAR:
            # Se dejan sus anomalías pendientes para que el panel tenga casos reales
            return ficha.codigo_ficha_local

        await _descartar_pendientes(session, ficha.id_ficha, usuario, falsos_positivos)
        ficha = await svc.cambiar_estado(ficha.id_ficha, ESTADO_VIGENTE, usuario)

        if item["nueva_version"]:
            # Revisión de especificación: ajuste de peso y tolerancia → v2, v1 queda Obsoleta
            caract = dict(ficha.caracteristicas)
            caract["peso_valor"] = float(caract["peso_valor"] + random.choice([-2, -1, 1, 2]))
            caract["peso_tolerancia"] = float(max(1, caract["peso_tolerancia"] - 1))
            nueva = await svc.actualizar(ficha.id_ficha, {"caracteristicas": caract}, usuario)
            await _descartar_pendientes(session, nueva.id_ficha, usuario, falsos_positivos)
            ficha = await svc.cambiar_estado(nueva.id_ficha, ESTADO_VIGENTE, usuario)
        return ficha.codigo_ficha_local


def respaldar_modelos() -> str | None:
    from app.services.ml_anomalia_service import MODELS_DIR
    pkls = list(MODELS_DIR.glob("*.pkl"))
    if not pkls:
        return None
    destino = MODELS_DIR / f"respaldo_{datetime.now():%Y%m%d_%H%M%S}"
    destino.mkdir()
    for pkl in pkls:
        shutil.copy2(pkl, destino / pkl.name)
    return str(destino)


async def entrenar() -> None:
    from app.services.ml_anomalia_service import MLAnomaliaService
    respaldo = respaldar_modelos()
    if respaldo:
        print(f"\nModelos anteriores respaldados en: {respaldo}")
    async with AsyncSessionLocal() as session:
        resultado = await MLAnomaliaService(session).entrenar_modelos()
    print(f"\n--- Entrenamiento Isolation Forest ({resultado.get('total_fichas_procesadas', 0)} fichas) ---")
    for m in resultado.get("modelos_entrenados", []):
        print(f"  {m['nombre']:<14} n={m['n_fichas']:<4} contamination={m['contamination']:<6} campos={len(m['campos_usados'])}")
    for s in resultado.get("categorias_sin_datos_suficientes", []):
        print(f"  {s['categoria']:<14} sin modelo (n={s['n_fichas']}, mínimo {s['minimo_requerido']})")


async def limpiar() -> None:
    async with AsyncSessionLocal() as session:
        total = await session.scalar(
            select(func.count()).select_from(KItem).where(KItem.usuario_creador.like(f"{PREFIJO_USUARIO}%"))
        )
        # ON DELETE CASCADE arrastra ficha/material, anomalías, auditoría y relaciones
        await session.execute(delete(KItem).where(KItem.usuario_creador.like(f"{PREFIJO_USUARIO}%")))
        await session.commit()
    print(f"Eliminados {total} k-items generados por el seed (usuario '{PREFIJO_USUARIO}*').")


async def main(args) -> None:
    if args.limpiar:
        await limpiar()
        return

    rng = random.Random(SEMILLA)
    random.seed(SEMILLA)
    materiales, paises_ocupados, codigos = await _contexto_existente()
    plan = planificar(rng, paises_ocupados, codigos)

    resumen = Counter(i["estado_final"] for i in plan)
    print(f"\nFichas planificadas: {len(plan)}  {dict(resumen)}  "
          f"(+{sum(i['nueva_version'] for i in plan)} con v2)")

    if args.dry_run:
        for i in plan:
            c = i["datos"]["caracteristicas"]
            print(f"  {i['familia']['nombre']:<32} {i['pais']} {i['codigo']}  "
                  f"{c['dimensiones_largo_valor']:.0f}x{c['dimensiones_ancho_valor']:.0f}x{c['dimensiones_alto_valor']:.0f} mm  "
                  f"{c['peso_valor']:.0f} g  {c['color']:<9} -> {i['estado_final']}{' +v2' if i['nueva_version'] else ''}")
        return

    # El script entrena explícitamente al final; se evita el auto-entrenamiento en background
    fichas_services._entrenamiento_en_cooldown = lambda: True

    falsos_positivos: Counter = Counter()
    print("\nMateriales:")
    await crear_materiales(materiales, falsos_positivos)

    print("\nFichas:")
    errores = []
    for n, item in enumerate(plan, 1):
        nombre = item["familia"]["nombre"]
        if nombre not in materiales:
            continue
        try:
            codigo = await crear_ficha(item, materiales[nombre], falsos_positivos)
            print(f"  [{n:>3}/{len(plan)}] {codigo:<28} {nombre}")
        except Exception as e:
            detalle = getattr(e, "detail", str(e))
            errores.append((nombre, item["pais"], detalle))
            print(f"  [{n:>3}/{len(plan)}] ERROR {nombre} ({item['pais']}): {detalle}")

    print("\n--- Falsos positivos descartados (datos normales marcados como anómalos) ---")
    if not falsos_positivos:
        print("  Ninguno")
    for (tipo, severidad), cantidad in falsos_positivos.most_common():
        print(f"  {tipo:<26} {severidad:<12} {cantidad}")
    if errores:
        print(f"\nErrores: {len(errores)}")

    if args.entrenar:
        await entrenar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera datos de prueba a partir de la prueba piloto.")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo mostrar lo que se generaría")
    grupo.add_argument("--limpiar", action="store_true", help="Borrar todo lo generado por este script")
    parser.add_argument("--entrenar", action="store_true", help="Reentrenar Isolation Forest al terminar")
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main(parser.parse_args()))
