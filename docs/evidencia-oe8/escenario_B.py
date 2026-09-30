"""
Escenario B (v2) — Detector 3 sobre la columna embedding del K-Item.

La v1 no disparo porque los embeddings estaban en etapas distintas: el texto
que se vectoriza solo se enriquece en la transicion Borrador -> Preliminar.
Aqui se lleva la ficha B a la misma etapa que la A antes de comparar.
"""
import asyncio
import json
import os
import sys

import asyncpg
import httpx
from dotenv import load_dotenv
from sqlalchemy import event

from app.core.database import engine
from app.core.security import crear_token
from app.main import app

load_dotenv()
SALIDA = open(sys.argv[1], "w", encoding="utf-8")

MAT_A, MAT_B = sys.argv[2], sys.argv[3]
FICHA_A, FICHA_B = sys.argv[4], sys.argv[5]

_sql, _cap = [], False


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _c(conn, cursor, statement, parameters, context, executemany):
    if _cap:
        _sql.append(" ".join(statement.split()))


def log(*a):
    t = " ".join(str(x) for x in a)
    print(t)
    SALIDA.write(t + "\n")
    SALIDA.flush()


def paso(n, t):
    log(f"\n--- PASO B.{n}: {t} ---")


async def main():
    global _cap
    headers = {"Authorization": f"Bearer {crear_token({'sub': 'admin', 'nombre': 'admin', 'rol': 'admin'})}"}
    cli = httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                            base_url="http://test", headers=headers, timeout=180)
    con = await asyncpg.connect(host="127.0.0.1", port=5432, database=os.getenv("DB_NAME"),
                                user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"))

    log("ESCENARIO B — El Detector 3 usa el vector semantico del K-Item")
    log("=" * 78)

    paso(1, "Igualar la denominacion comercial de ambos materiales")
    log("  Los dos materiales siguen siendo K-Items distintos (UUID distinto);")
    log("  solo se iguala el nombre para forzar la maxima similitud semantica.")
    r = await cli.patch(f"/api/material/{MAT_B}", json={"nombre_corporativo": "Separador Prueba OE8"})
    log(f"  HTTP {r.status_code}  material B -> nombre_corporativo='Separador Prueba OE8'")
    for etiqueta, m in (("A", MAT_A), ("B", MAT_B)):
        n = await con.fetchval("select nombre_corporativo from material_comercial where id_material_corporativo=$1", m)
        log(f"    material {etiqueta}: {m}  nombre='{n}'")

    paso(2, "Resolver las anomalias pendientes de la ficha B para poder avanzarla")
    pend = await con.fetch("select id, tipo_anomalia, campo_afectado from anomalia_registro "
                           "where kitem_id=$1 and estado='pendiente'", FICHA_B)
    log(f"  {len(pend)} anomalia(s) pendiente(s)")
    for p in pend:
        r = await cli.patch(f"/api/anomalias/{p['id']}/resolver", json={
            "estado": "descartada", "nota": "Ficha de prueba del escenario B (OE8)."})
        log(f"    HTTP {r.status_code}  {p['tipo_anomalia']:16} {p['campo_afectado']} -> descartada")

    paso(3, "Llevar la ficha B a Preliminar (recalcula el embedding enriquecido)")
    _sql.clear()
    _cap = True
    r = await cli.post(f"/api/ficha/{FICHA_B}/aprobar-inicial")
    _cap = False
    log(f"  HTTP {r.status_code}  POST /api/ficha/{{id}}/aprobar-inicial")
    estado = await con.fetchval("select estado from kitem where id=$1", FICHA_B)
    log(f"  Estado de la ficha B: {estado}")

    paso(4, "Texto vectorizado y similitud coseno calculada por pgvector")
    for etiqueta, k in (("A", FICHA_A), ("B", FICHA_B)):
        f = await con.fetchrow("select nombre, descripcion, vector_dims(embedding) d from kitem where id=$1", k)
        log(f"  ficha {etiqueta} (dim={f['d']})")
        log(f"    nombre     : {f['nombre']}")
        log(f"    descripcion: {f['descripcion']}")
    sim = await con.fetchval("""select 1 - (a.embedding <=> b.embedding)
                                from kitem a, kitem b where a.id=$1 and b.id=$2""", FICHA_A, FICHA_B)
    log(f"\n  SQL> select 1 - (a.embedding <=> b.embedding) from kitem a, kitem b")
    log(f"       where a.id='{FICHA_A}' and b.id='{FICHA_B}';")
    log(f"  similitud = {sim:.6f}    umbral Detector 3 (fichas) = 0.95    "
        f"{'SUPERA EL UMBRAL' if sim >= 0.95 else 'por debajo del umbral'}")

    paso(5, "SQL emitido por el Detector 3 durante el analisis")
    vec = [q for q in _sql if "<=>" in q]
    log(f"  Consultas con el operador de distancia coseno de pgvector: {len(vec)}")
    if vec:
        log(f"\n  {vec[0][:700]}")
    log("\n  Lectura: el detector no recalcula vectores en Python. Ordena y filtra")
    log("  con 'kitem.embedding <=> :vector_referencia' — la columna embedding de")
    log("  la tabla kitem — y deriva la similitud como 1 - distancia_coseno.")

    paso(6, "Anomalia de duplicado semantico en anomalia_registro")
    filas = await con.fetch("""
        select id, tipo_anomalia, severidad, mensaje, estado, detalles, fecha_deteccion
        from anomalia_registro where kitem_id=$1 and tipo_anomalia='duplicado_semantico'
        order by fecha_deteccion desc""", FICHA_B)
    log(f"  SQL> select * from anomalia_registro where kitem_id='{FICHA_B}'")
    log(f"         and tipo_anomalia='duplicado_semantico';")
    log(f"  ({len(filas)} fila(s))")
    for f in filas:
        det = json.loads(f["detalles"]) if f["detalles"] else {}
        log(f"    id             : {f['id']}")
        log(f"    tipo_anomalia  : {f['tipo_anomalia']}")
        log(f"    severidad      : {f['severidad']}")
        log(f"    estado         : {f['estado']}")
        log(f"    fecha_deteccion: {f['fecha_deteccion']}")
        log(f"    mensaje        : {f['mensaje']}")
        log(f"    detalles       : {json.dumps(det, ensure_ascii=False, indent=2)}")
        log(f"    -> similitud almacenada en el payload: {det.get('similitud')}")
        log(f"    -> kitem_similar_id == ficha A: {str(det.get('kitem_similar_id')) == str(FICHA_A)}")

    log("\n" + "=" * 78)
    log(f"  B.4 similitud coseno via pgvector : {sim:.6f}")
    log(f"  B.5 SQL usa kitem.embedding (<=>) : {'OK' if vec else 'FALLO'}")
    log(f"  B.6 duplicado_semantico registrado: {'OK' if filas else 'NO DETECTADO'}")

    await con.close()
    await cli.aclose()
    await engine.dispose()
    SALIDA.close()


asyncio.run(main())
