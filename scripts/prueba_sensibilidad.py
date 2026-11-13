"""
Prueba de sensibilidad de los detectores de anomalías.

Evalúa cada caso por el flujo real (FichaService.crear → cambiar_estado a
Preliminar → AnomaliaService.analizar_ficha) contra las fichas que ya están en
la base, dentro de una transacción que se revierte al terminar el caso: la
base queda intacta.

Grupos:
  - Control: fichas normales nuevas (mismo generador que seed_datos_prueba.py).
    Todo lo que se detecte aquí es falso positivo.
  - Escenarios: fichas normales a las que se inyecta una anomalía conocida
    con magnitud graduada (peso ×1.25 … ×3, error de digitación, cambio de
    unidad, categoría equivocada, duplicado real, etc.). Se mide si salta el
    detector esperado sobre el campo alterado.

Uso:
    cd <raíz del proyecto>
    python scripts/prueba_sensibilidad.py                     # resumen en consola
    python scripts/prueba_sensibilidad.py --json salida.json  # además guarda el detalle
    python scripts/prueba_sensibilidad.py --n-control 60 --n-escenario 12
"""

import argparse
import asyncio
import copy
import json
import logging
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from seed_datos_prueba import FAMILIAS, generar_ficha, _schema_ficha  # noqa: E402

from sqlalchemy import select, func  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.dsms_constants import ESTADO_PRELIMINAR  # noqa: E402
from app.core.anomalia_constant import (  # noqa: E402
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_DUPLICADO_SEMANTICO,
    ANOMALIA_PERFIL_CRUZADO,
    ANOMALIA_ML_MULTIVARIADO,
    ANOMALIA_RANGO_CATEGORIA,
    ANOMALIA_CLASIFICACION_CRUZADA,
    SEVERIDAD_CRITICA,
)
from app.models.anomalia import AnomaliaRegistro  # noqa: E402
from app.models.ficha import FichaTecnica  # noqa: E402
from app.models.material import MaterialComercial  # noqa: E402
from app.schemas.material import MaterialCreateSchema  # noqa: E402
from app.services.fichas_services import FichaService  # noqa: E402
from app.services.material_service import MaterialService  # noqa: E402

SEMILLA = 2026
USUARIO = "seed.sensibilidad"

DETECTORES = [
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_RANGO_CATEGORIA,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_ML_MULTIVARIADO,
    ANOMALIA_PERFIL_CRUZADO,
    ANOMALIA_CLASIFICACION_CRUZADA,
    ANOMALIA_DUPLICADO_SEMANTICO,
]
ABREV = {
    ANOMALIA_VALOR_ATIPICO: "zscore",
    ANOMALIA_RANGO_CATEGORIA: "rango",
    ANOMALIA_UNIDAD_INCONSISTENTE: "unidad",
    ANOMALIA_ML_MULTIVARIADO: "ml",
    ANOMALIA_PERFIL_CRUZADO: "perfil",
    ANOMALIA_CLASIFICACION_CRUZADA: "clasif",
    ANOMALIA_DUPLICADO_SEMANTICO: "dup",
}
# Detectores que señalan un campo concreto: el acierto exige que sea el alterado
DETECTORES_POR_CAMPO = {ANOMALIA_VALOR_ATIPICO, ANOMALIA_RANGO_CATEGORIA, ANOMALIA_UNIDAD_INCONSISTENTE}

ZSCORE_RANGO = {ANOMALIA_VALOR_ATIPICO, ANOMALIA_RANGO_CATEGORIA}
ESTADISTICOS = {ANOMALIA_VALOR_ATIPICO, ANOMALIA_RANGO_CATEGORIA, ANOMALIA_ML_MULTIVARIADO}


# ---------------------------------------------------------------------------
# Mutaciones (anomalías inyectadas)
# ---------------------------------------------------------------------------

def _escalar(seccion: str, campo: str, factor: float):
    def mutar(datos: dict) -> None:
        datos[seccion][campo] = round(datos[seccion][campo] * factor, 2)
    return mutar


def _cambiar_unidad(campo: str, divisor: float, unidad: str):
    def mutar(datos: dict) -> None:
        c = datos["caracteristicas"]
        c[f"{campo}_valor"] = round(c[f"{campo}_valor"] / divisor, 3)
        c[f"{campo}_unidad"] = unidad
    return mutar


def _incoherente(datos: dict) -> None:
    """Cada valor es plausible por separado, pero la combinación no: más grande y más liviano."""
    c = datos["caracteristicas"]
    c["dimensiones_largo_valor"] = round(c["dimensiones_largo_valor"] * 1.10)
    c["dimensiones_ancho_valor"] = round(c["dimensiones_ancho_valor"] * 1.10)
    c["peso_valor"] = round(c["peso_valor"] * 0.75)


P = "caracteristicas"
ESCENARIOS = [
    # nombre, mutación, campo alterado, detectores esperados
    ("peso x1.25", _escalar(P, "peso_valor", 1.25), "peso_valor", ESTADISTICOS),
    ("peso x1.5", _escalar(P, "peso_valor", 1.5), "peso_valor", ESTADISTICOS),
    ("peso x2", _escalar(P, "peso_valor", 2.0), "peso_valor", ESTADISTICOS),
    ("peso x3", _escalar(P, "peso_valor", 3.0), "peso_valor", ESTADISTICOS),
    ("peso x0.6", _escalar(P, "peso_valor", 0.6), "peso_valor", ESTADISTICOS),
    ("largo x1.15", _escalar(P, "dimensiones_largo_valor", 1.15), "dimensiones_largo_valor", ESTADISTICOS),
    ("largo x1.3", _escalar(P, "dimensiones_largo_valor", 1.3), "dimensiones_largo_valor", ESTADISTICOS),
    ("largo x1.6", _escalar(P, "dimensiones_largo_valor", 1.6), "dimensiones_largo_valor", ESTADISTICOS),
    ("alto x1.5", _escalar(P, "dimensiones_alto_valor", 1.5), "dimensiones_alto_valor", ESTADISTICOS),
    ("alto x2", _escalar(P, "dimensiones_alto_valor", 2.0), "dimensiones_alto_valor", ESTADISTICOS),
    ("digitación ancho /10", _escalar(P, "dimensiones_ancho_valor", 0.1), "dimensiones_ancho_valor", ESTADISTICOS),
    ("digitación peso x10", _escalar(P, "peso_valor", 10), "peso_valor", ESTADISTICOS),
    ("unidad peso g→kg", _cambiar_unidad("peso", 1000, "kg"), "peso_unidad", {ANOMALIA_UNIDAD_INCONSISTENTE}),
    ("unidad largo mm→cm", _cambiar_unidad("dimensiones_largo", 10, "cm"), "dimensiones_largo_unidad", {ANOMALIA_UNIDAD_INCONSISTENTE}),
    ("peso empaque x3", _escalar("empaque_estiba", "peso_empaque_valor", 3.0), "peso_empaque_valor", ESTADISTICOS),
    # El gramaje (peso/área) lo puede detectar el z-score además del ML
    ("combinación incoherente", _incoherente, None, {ANOMALIA_ML_MULTIVARIADO, ANOMALIA_VALOR_ATIPICO}),
]

# Categoría equivocada: valores de una familia cargados en un material de otra categoría
CATEGORIA_ERRONEA = [
    ("Bandeja Biopack 4G", "Separador 1x30 Universal"),
    ("Separador 1x30 Universal", "Bandeja Biopack 3B"),
    ("Estuche 1x18 S/Planchar", "Porta Vasos 4 Cav"),
    ("Porta Vasos 2 Cav", "Estuche 1x12 S/Planchar"),
]
ESPERADOS_CATEGORIA = {ANOMALIA_PERFIL_CRUZADO, ANOMALIA_RANGO_CATEGORIA, ANOMALIA_CLASIFICACION_CRUZADA}

# Material mal categorizado: el nombre y los valores son de una familia, la
# categoría declarada es otra (lo que D4 compara por semántica del material)
MAL_CATEGORIZADO = [
    ("Bandeja Biopack 3B", "Separador"),
    ("Separador 1x30 Reforzado", "Bandeja"),
    ("Estuche 1x10 con ventana S/I", "Porta vasos"),
    ("Porta Vasos 4 Cav Reforzado", "Estuche"),
]


# ---------------------------------------------------------------------------
# Evaluación de un caso dentro de una transacción revertida
# ---------------------------------------------------------------------------

def _codigo(rng: random.Random) -> str:
    return "99" + f"{rng.randint(0, 999999):06d}"


async def _analizar(session, id_material, datos: dict, rng: random.Random) -> list[dict]:
    item = {
        "codigo": _codigo(rng),
        "nombre_local": "Caso de sensibilidad",
        "usuario": USUARIO,
        "pais": "VE",
        "datos": datos,
    }
    svc = FichaService(session)
    ficha = await svc.crear(_schema_ficha(id_material, item))
    await svc.cambiar_estado(ficha.id_ficha, ESTADO_PRELIMINAR, USUARIO)
    filas = (await session.execute(
        select(AnomaliaRegistro).where(AnomaliaRegistro.kitem_id == ficha.id_ficha)
    )).scalars().all()
    return [{"tipo": a.tipo_anomalia, "severidad": a.severidad, "campo": a.campo_afectado or ""} for a in filas]


async def evaluar(id_material, datos: dict, rng: random.Random, material_extra: dict | None = None) -> list[dict]:
    async with AsyncSessionLocal() as session:
        # Los servicios hacen commit; aquí se convierte en flush para poder revertir todo
        session.commit = session.flush
        try:
            if material_extra:
                material = await MaterialService(session).crear(MaterialCreateSchema(**material_extra))
                id_material = material.id_material_corporativo
            return await _analizar(session, id_material, datos, rng)
        finally:
            await session.rollback()


def _acierto(anomalias: list[dict], esperados: set, campo: str | None) -> bool:
    for a in anomalias:
        if a["tipo"] not in esperados:
            continue
        if a["tipo"] in DETECTORES_POR_CAMPO and campo and not a["campo"].endswith(campo):
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args) -> None:
    rng = random.Random(args.semilla)
    familias = {f["nombre"]: f for f in FAMILIAS}

    async with AsyncSessionLocal() as session:
        materiales = {
            nombre: id_ for id_, nombre in (await session.execute(
                select(MaterialComercial.id_material_corporativo, MaterialComercial.nombre_corporativo)
            )).all()
        }
        n_base = await session.scalar(select(func.count()).select_from(FichaTecnica))
    disponibles = [f for f in FAMILIAS if f["nombre"] in materiales]
    print(f"Base de referencia: {n_base} fichas, {len(disponibles)} familias")

    resultados = []

    def registrar(grupo, escenario, familia, anomalias, esperados, campo):
        resultados.append({
            "grupo": grupo,
            "escenario": escenario,
            "familia": familia,
            "anomalias": anomalias,
            "acierto": _acierto(anomalias, esperados, campo) if esperados else None,
        })

    # --- Control: fichas normales ---
    print(f"\nControl ({args.n_control} fichas normales)...")
    for _ in range(args.n_control):
        fam = rng.choice(disponibles)
        anomalias = await evaluar(materiales[fam["nombre"]], generar_ficha(rng, fam), rng)
        registrar("control", "normal", fam["nombre"], anomalias, None, None)

    # --- Escenarios inyectados ---
    for nombre, mutar, campo, esperados in ESCENARIOS:
        print(f"Escenario: {nombre}...")
        for fam in rng.sample(disponibles, min(args.n_escenario, len(disponibles))):
            datos = generar_ficha(rng, fam)
            mutar(datos)
            anomalias = await evaluar(materiales[fam["nombre"]], datos, rng)
            registrar("inyectado", nombre, fam["nombre"], anomalias, esperados, campo)

    print("Escenario: categoría equivocada...")
    for origen, destino in CATEGORIA_ERRONEA:
        for _ in range(max(1, args.n_escenario // len(CATEGORIA_ERRONEA))):
            anomalias = await evaluar(materiales[destino], generar_ficha(rng, familias[origen]), rng)
            registrar("inyectado", "categoría equivocada", f"{origen} → {destino}", anomalias,
                      ESPERADOS_CATEGORIA, None)

    print("Escenario: material mal categorizado...")
    for origen, categoria in MAL_CATEGORIZADO:
        fam = familias[origen]
        for i in range(max(1, args.n_escenario // len(MAL_CATEGORIZADO))):
            material_extra = {
                "nombre_corporativo": f"{fam['nombre']} lote {i + 1}",
                "contenido": fam.get("contenido", "Huevos"), "categoria": categoria,
                "sector": fam.get("sector"), "caracteristica": fam.get("caracteristica"),
                "material_base": "Pulpa Moldeada", "capacidad_nominal": fam.get("capacidad"),
                "tipo_producto": "Producto Terminado", "estado_material": "Activo",
                "usuario_creador": USUARIO,
            }
            anomalias = await evaluar(None, generar_ficha(rng, fam), rng, material_extra=material_extra)
            registrar("inyectado", "material mal categorizado", f"{origen} → {categoria}", anomalias,
                      ESPERADOS_CATEGORIA, None)

    print("Escenario: duplicado real (mismo producto bajo otro material)...")
    for fam in rng.sample(disponibles, min(args.n_escenario, len(disponibles))):
        async with AsyncSessionLocal() as session:
            mat = (await session.execute(select(MaterialComercial).where(
                MaterialComercial.nombre_corporativo == fam["nombre"]))).scalars().first()
            original = (await session.execute(select(FichaTecnica).where(
                FichaTecnica.id_material_corporativo == mat.id_material_corporativo,
                FichaTecnica.codigo_material_local.isnot(None)).limit(1))).scalars().first()
        if not original or not original.caracteristicas:
            continue
        datos = {
            "caracteristicas": {k: v for k, v in original.caracteristicas.items() if k != "imagenes"},
            "caracteristicas_contenido": original.caracteristicas_contenido,
            "empaque_estiba": original.empaque_estiba or generar_ficha(rng, fam)["empaque_estiba"],
            "microbiologia": None,
            "manejo_disposicion": original.manejo_disposicion,
        }
        material_duplicado = {
            "nombre_corporativo": f"{fam['nombre']} (alta duplicada)",
            "contenido": mat.contenido, "categoria": mat.categoria, "sector": mat.sector,
            "caracteristica": mat.caracteristica, "material_base": mat.material_base,
            "capacidad_nominal": mat.capacidad_nominal, "tipo_producto": mat.tipo_producto,
            "estado_material": "Activo", "usuario_creador": USUARIO,
        }
        try:
            anomalias = await evaluar(None, datos, rng, material_extra=material_duplicado)
        except Exception as e:
            print(f"  omitido {fam['nombre']}: {getattr(e, 'detail', e)}")
            continue
        registrar("inyectado", "duplicado real", fam["nombre"], anomalias,
                  {ANOMALIA_DUPLICADO_SEMANTICO}, None)

    imprimir_resumen(resultados)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(resultados, fh, ensure_ascii=False, indent=1)
        print(f"\nDetalle guardado en {args.json}")


def imprimir_resumen(resultados: list[dict]) -> None:
    cab = "".join(f"{ABREV[d]:>8}" for d in DETECTORES)

    print("\n=== Tasa de disparo por detector (% de fichas con al menos una alerta) ===")
    print(f"{'escenario':<26}{'n':>4}{'detecta':>9}{'crít.':>7}{cab}")
    escenarios = list(dict.fromkeys(r["escenario"] for r in resultados))
    for esc in escenarios:
        filas = [r for r in resultados if r["escenario"] == esc]
        n = len(filas)
        dispara = Counter()
        for r in filas:
            for tipo in {a["tipo"] for a in r["anomalias"]}:
                dispara[tipo] += 1
        criticas = sum(any(a["severidad"] == SEVERIDAD_CRITICA for a in r["anomalias"]) for r in filas)
        if filas[0]["acierto"] is None:
            detecta = "  (FP)  "
        else:
            detecta = f"{100 * sum(r['acierto'] for r in filas) / n:>7.0f}%"
        celdas = "".join(f"{100 * dispara[d] / n:>7.0f}%" for d in DETECTORES)
        print(f"{esc:<26}{n:>4}{detecta:>9}{100 * criticas / n:>6.0f}%{celdas}")

    print("\n'detecta' = salta un detector esperado sobre el campo alterado.")
    print("En 'normal' todo disparo es falso positivo.")

    # Sensibilidad vs. especificidad de cada detector, excluyendo duplicados reales
    control = [r for r in resultados if r["grupo"] == "control"]
    inyect = [r for r in resultados if r["grupo"] == "inyectado"]
    print("\n=== Resumen por detector ===")
    print(f"{'detector':<26}{'FP en normales':>16}{'aciertos inyectados':>22}")
    for d in DETECTORES:
        fp = sum(any(a["tipo"] == d for a in r["anomalias"]) for r in control)
        aplicables = [r for r in inyect if r["acierto"] is not None]
        aciertos = sum(any(a["tipo"] == d for a in r["anomalias"]) and r["acierto"] for r in aplicables)
        print(f"{d:<26}{f'{fp}/{len(control)}':>16}{f'{aciertos}/{len(aplicables)}':>22}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba de sensibilidad de los detectores de anomalías.")
    parser.add_argument("--n-control", type=int, default=40, help="Fichas normales de control")
    parser.add_argument("--n-escenario", type=int, default=10, help="Fichas por escenario inyectado")
    parser.add_argument("--semilla", type=int, default=SEMILLA,
                        help="Semilla del generador (calibrar con una, evaluar con otra)")
    parser.add_argument("--json", help="Ruta donde guardar el detalle por caso")
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main(parser.parse_args()))
