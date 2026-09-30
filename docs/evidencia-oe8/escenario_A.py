"""
Prueba de integracion end-to-end DSMS + motor de anomalias (OE8).

Escenario A: bloqueo y desbloqueo de transicion de estado por anomalia
             pendiente (Detector 1, z-score).
Escenario B: el Detector 3 (duplicado semantico) opera sobre la columna
             embedding del kitem via pgvector.

Golpea la app FastAPI real por ASGI con JWT valido, contra PostgreSQL local.
Deja transcripcion completa en el archivo que se pase como argv[1].
"""
import asyncio
import json
import os
import sys
from datetime import datetime

import asyncpg
import httpx
from dotenv import load_dotenv
from sqlalchemy import event

from app.core.database import engine
from app.core.security import crear_token
from app.main import app

load_dotenv()

SALIDA = open(sys.argv[1], "w", encoding="utf-8")
CREADOS = {"materiales": [], "fichas": []}

# Captura de SQL con el operador de pgvector
_sql_capturado, _capturando = [], False


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _cap(conn, cursor, statement, parameters, context, executemany):
    if _capturando:
        _sql_capturado.append(" ".join(statement.split()))


def log(*args):
    texto = " ".join(str(a) for a in args)
    print(texto)
    SALIDA.write(texto + "\n")
    SALIDA.flush()


def titulo(t):
    log("\n" + "=" * 78)
    log(t)
    log("=" * 78)


def paso(n, t):
    log(f"\n--- PASO {n}: {t} ---")


def http(resp, mostrar=None):
    log(f"  HTTP {resp.status_code} {resp.request.method} {resp.request.url.path}")
    try:
        cuerpo = resp.json()
    except Exception:
        log(f"  (cuerpo no JSON, {len(resp.content)} bytes)")
        return None
    if mostrar:
        recorte = {k: cuerpo[k] for k in mostrar if k in cuerpo}
        log("  " + json.dumps(recorte, indent=2, ensure_ascii=False, default=str).replace("\n", "\n  "))
    return cuerpo


async def db():
    return await asyncpg.connect(
        host="127.0.0.1", port=5432, database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"))


async def mostrar_anomalias(con, kitem_id, nota=""):
    filas = await con.fetch("""
        select id, tipo_anomalia, severidad, campo_afectado, valor_detectado,
               valor_esperado, estado, resuelto_por, nota_resolucion,
               fecha_deteccion, fecha_resolucion, contexto, detalles
        from anomalia_registro where kitem_id = $1
        order by fecha_deteccion""", kitem_id)
    log(f"  SQL> select * from anomalia_registro where kitem_id = '{kitem_id}';  {nota}")
    log(f"  ({len(filas)} fila(s))")
    for f in filas:
        log(f"    id              : {f['id']}")
        log(f"    tipo_anomalia   : {f['tipo_anomalia']}")
        log(f"    severidad       : {f['severidad']}")
        log(f"    campo_afectado  : {f['campo_afectado']}")
        log(f"    valor_detectado : {f['valor_detectado']}")
        log(f"    valor_esperado  : {f['valor_esperado']}")
        log(f"    estado          : {f['estado']}")
        log(f"    contexto        : {f['contexto']}")
        log(f"    fecha_deteccion : {f['fecha_deteccion']}")
        if f["resuelto_por"]:
            log(f"    resuelto_por    : {f['resuelto_por']}")
            log(f"    fecha_resolucion: {f['fecha_resolucion']}")
            log(f"    nota_resolucion : {f['nota_resolucion']}")
        det = json.loads(f["detalles"]) if f["detalles"] else {}
        log(f"    detalles        : {json.dumps(det, ensure_ascii=False)}")
        log("")
    return filas


async def mostrar_auditoria(con, kitem_id):
    filas = await con.fetch("""
        select accion, estado_anterior, estado_nuevo, usuario, fecha, detalles
        from kitem_auditoria where kitem_id = $1 order by fecha""", kitem_id)
    log(f"  SQL> select * from kitem_auditoria where kitem_id = '{kitem_id}' order by fecha;")
    log(f"  ({len(filas)} fila(s))")
    log(f"  {'fecha':26} {'accion':18} {'anterior':11} -> {'nuevo':11} {'usuario'}")
    for f in filas:
        log(f"  {str(f['fecha']):26} {f['accion']:18} "
            f"{str(f['estado_anterior'] or '-'):11} -> {str(f['estado_nuevo'] or '-'):11} {f['usuario']}")
    return filas


async def main():
    global _capturando
    headers = {"Authorization": f"Bearer {crear_token({'sub': 'admin', 'nombre': 'admin', 'rol': 'admin'})}"}
    cli = httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                            base_url="http://test", headers=headers, timeout=180)
    con = await db()

    log(f"Prueba de integracion OE8 — {datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"Entorno: PostgreSQL local 5432 / base '{os.getenv('DB_NAME')}' / app FastAPI via ASGI")

    # ════════════════════════════════════════════════════════════════
    titulo("ESCENARIO A — Bloqueo y desbloqueo de transicion de estado")
    # ════════════════════════════════════════════════════════════════

    paso(1, "Crear material comercial de prueba (categoria Separador)")
    r = await cli.post("/api/material", json={
        "nombre_corporativo": "Separador Prueba OE8",
        "contenido": "Huevos", "categoria": "Separador", "sector": "Avicola",
        "caracteristica": "Apilable", "material_base": "Pulpa moldeada",
        "capacidad_nominal": "30 unidades", "tipo_producto": "Empaque",
        "estado_material": "Activo"})
    mat = http(r, ["id_material_corporativo", "nombre_corporativo", "categoria"])
    mat_id = mat["id_material_corporativo"]
    CREADOS["materiales"].append(mat_id)

    log("\n  Referencia estadistica: fichas existentes de categoria 'Separador'")
    ref = await con.fetch("""
        select (f.caracteristicas->>'peso_valor')::float peso
        from ficha_tecnica f join material_comercial m
          on m.id_material_corporativo = f.id_material_corporativo
        where m.categoria = 'Separador' and f.caracteristicas->>'peso_valor' is not null""")
    pesos = [x["peso"] for x in ref]
    media = sum(pesos) / len(pesos)
    std = (sum((p - media) ** 2 for p in pesos) / len(pesos)) ** 0.5
    log(f"  n={len(pesos)}  valores={pesos}")
    log(f"  media={media:.2f} g   desviacion={std:.2f} g")
    log(f"  rango normal (z<2): [{media - 2*std:.1f}, {media + 2*std:.1f}] g")

    PESO_NORMAL, PESO_ATIPICO = 62.0, 220.0
    z = abs(PESO_ATIPICO - media) / std
    log(f"  peso atipico a inyectar: {PESO_ATIPICO} g  ->  z-score esperado = {z:.2f}")

    paso(2, "Crear ficha tecnica en estado Borrador (peso normal)")
    r = await cli.post("/api/ficha", json={
        "id_material_corporativo": mat_id,
        "codigo_material_local": "OE8-TEST-001",
        "nombre_local_material": "Separador prueba integracion OE8",
        "pais": "Venezuela",
        "caracteristicas": {
            "dimensiones_largo_valor": 300, "dimensiones_largo_tolerancia": 2, "dimensiones_largo_unidad": "mm",
            "dimensiones_ancho_valor": 300, "dimensiones_ancho_tolerancia": 2, "dimensiones_ancho_unidad": "mm",
            "dimensiones_alto_valor": 45, "dimensiones_alto_tolerancia": 1, "dimensiones_alto_unidad": "mm",
            "peso_valor": PESO_NORMAL, "peso_tolerancia": 3, "peso_unidad": "g"},
        "empaque_estiba": {"tipo_empaque": "Caja corrugada"},
        "manejo_disposicion": {
            "uso": "Separacion de huevos en estiba.", "manejo": "Manipular en seco.",
            "almacenamiento": "Bodega cubierta.", "transporte": "Camion cerrado.",
            "vida_util": "24 meses."}})
    ficha = http(r, ["id_ficha", "codigo_ficha_local", "estado_ficha"])
    fid = ficha["id_ficha"]
    CREADOS["fichas"].append(fid)
    log(f"\n  Anomalias tras la creacion: {len(ficha.get('anomalias') or [])} "
        f"(la creacion no ejecuta el motor: asigna embedding y devuelve _anomalias=[])")

    paso(3, "Actualizar la ficha con el valor atipico (dispara el motor)")
    log(f"  PATCH caracteristicas.peso_valor: {PESO_NORMAL} -> {PESO_ATIPICO} g")
    r = await cli.patch(f"/api/ficha/{fid}", json={
        "caracteristicas": {
            "dimensiones_largo_valor": 300, "dimensiones_largo_tolerancia": 2, "dimensiones_largo_unidad": "mm",
            "dimensiones_ancho_valor": 300, "dimensiones_ancho_tolerancia": 2, "dimensiones_ancho_unidad": "mm",
            "dimensiones_alto_valor": 45, "dimensiones_alto_tolerancia": 1, "dimensiones_alto_unidad": "mm",
            "peso_valor": PESO_ATIPICO, "peso_tolerancia": 3, "peso_unidad": "g"}})
    cuerpo = http(r)
    anoms = cuerpo.get("anomalias") or []
    log(f"  Respuesta del endpoint: {len(anoms)} anomalia(s) en el campo 'anomalias'")
    for a in anoms:
        log(f"    - [{a['severidad']}] {a['tipo_anomalia']} / {a.get('campo_afectado')}")
        log(f"      {a['mensaje']}")

    paso(4, "Verificar anomalia persistida en estado 'pendiente'")
    filas = await mostrar_anomalias(con, fid, "(esperado: estado=pendiente)")
    pendientes = [f for f in filas if f["estado"] == "pendiente"]

    paso(5, "Intentar transicion Borrador -> Preliminar con anomalia pendiente")
    r = await cli.post(f"/api/ficha/{fid}/aprobar-inicial")
    log(f"  HTTP {r.status_code}  POST /api/ficha/{{id}}/aprobar-inicial")
    log(f"  Cuerpo: {json.dumps(r.json(), ensure_ascii=False)}")
    estado = await con.fetchval("select estado from kitem where id = $1", fid)
    log(f"  Estado de la ficha tras el intento: {estado}  (sin cambios)")
    bloqueo_ok = r.status_code == 400

    paso(6, "Auditoria inmediatamente despues del intento bloqueado")
    aud_tras_bloqueo = await mostrar_auditoria(con, fid)

    paso(7, "Resolver las anomalias pendientes desde el panel")
    for f in pendientes:
        r = await cli.patch(f"/api/anomalias/{f['id']}/resolver", json={
            "estado": "descartada",
            "nota": "Valor verificado con planta: corresponde a un separador reforzado de alto gramaje."})
        c = http(r, ["id", "tipo_anomalia", "estado", "resuelto_por", "nota_resolucion"])

    paso(8, "Verificar el cambio de estado en anomalia_registro")
    await mostrar_anomalias(con, fid, "(esperado: estado=descartada)")

    paso(9, "Reintentar la transicion Borrador -> Preliminar")
    r = await cli.post(f"/api/ficha/{fid}/aprobar-inicial")
    log(f"  HTTP {r.status_code}  POST /api/ficha/{{id}}/aprobar-inicial")
    c = http(r, ["id_ficha", "codigo_ficha_local", "estado_ficha"])
    estado = await con.fetchval("select estado from kitem where id = $1", fid)
    log(f"  Estado de la ficha tras el reintento: {estado}")
    transicion_ok = r.status_code == 200

    paso(10, "Auditoria completa del K-Item (kitem_auditoria)")
    aud_final = await mostrar_auditoria(con, fid)

    log("\n  COMPROBACION sobre el registro del intento bloqueado:")
    log(f"    filas de auditoria antes del reintento : {len(aud_tras_bloqueo)}")
    log(f"    filas de auditoria despues del reintento: {len(aud_final)}")
    cambios_estado = [f for f in aud_final if f["accion"] == "CAMBIO_ESTADO"]
    log(f"    eventos CAMBIO_ESTADO registrados        : {len(cambios_estado)}")

    # ════════════════════════════════════════════════════════════════
    titulo("ESCENARIO B — El Detector 3 opera sobre la columna embedding")
    # ════════════════════════════════════════════════════════════════

    paso(1, "Crear un segundo material casi identico (otro material corporativo)")
    r = await cli.post("/api/material", json={
        "nombre_corporativo": "Separador Prueba OE8 BIS",
        "contenido": "Huevos", "categoria": "Separador", "sector": "Avicola",
        "caracteristica": "Apilable", "material_base": "Pulpa moldeada",
        "capacidad_nominal": "30 unidades", "tipo_producto": "Empaque",
        "estado_material": "Activo"})
    mat2 = http(r, ["id_material_corporativo", "nombre_corporativo"])
    mat2_id = mat2["id_material_corporativo"]
    CREADOS["materiales"].append(mat2_id)

    paso(2, "Crear una ficha gemela (mismas dimensiones, material distinto)")
    r = await cli.post("/api/ficha", json={
        "id_material_corporativo": mat2_id,
        "codigo_material_local": "OE8-TEST-002",
        "nombre_local_material": "Separador prueba integracion OE8",
        "pais": "Venezuela",
        "caracteristicas": {
            "dimensiones_largo_valor": 300, "dimensiones_largo_tolerancia": 2, "dimensiones_largo_unidad": "mm",
            "dimensiones_ancho_valor": 300, "dimensiones_ancho_tolerancia": 2, "dimensiones_ancho_unidad": "mm",
            "dimensiones_alto_valor": 45, "dimensiones_alto_tolerancia": 1, "dimensiones_alto_unidad": "mm",
            "peso_valor": PESO_ATIPICO, "peso_tolerancia": 3, "peso_unidad": "g"},
        "empaque_estiba": {"tipo_empaque": "Caja corrugada"},
        "manejo_disposicion": {
            "uso": "Separacion de huevos en estiba.", "manejo": "Manipular en seco.",
            "almacenamiento": "Bodega cubierta.", "transporte": "Camion cerrado.",
            "vida_util": "24 meses."}})
    ficha2 = http(r, ["id_ficha", "codigo_ficha_local", "estado_ficha"])
    fid2 = ficha2["id_ficha"]
    CREADOS["fichas"].append(fid2)

    paso(3, "Verificar que ambos K-Items tienen embedding en la columna vector")
    for etiqueta, k in (("ficha A", fid), ("ficha B", fid2)):
        fila = await con.fetchrow("""
            select nombre, (embedding is not null) tiene, vector_dims(embedding) dims
            from kitem where id = $1""", k)
        log(f"  {etiqueta}: embedding={'SI' if fila['tiene'] else 'NO'}  "
            f"dimensiones={fila['dims']}  nombre='{fila['nombre']}'")

    log("\n  Similitud coseno entre ambos, calculada en PostgreSQL con pgvector:")
    sim = await con.fetchrow("""
        select 1 - (a.embedding <=> b.embedding) as similitud
        from kitem a, kitem b where a.id = $1 and b.id = $2""", fid, fid2)
    log(f"  SQL> select 1 - (a.embedding <=> b.embedding) from kitem a, kitem b ...")
    log(f"  similitud = {sim['similitud']:.6f}   (umbral Detector 3 para fichas: 0.95)")

    paso(4, "Disparar el motor sobre la ficha B y capturar el SQL emitido")
    _sql_capturado.clear()
    _capturando = True
    r = await cli.patch(f"/api/ficha/{fid2}", json={
        "caracteristicas": {
            "dimensiones_largo_valor": 300, "dimensiones_largo_tolerancia": 2, "dimensiones_largo_unidad": "mm",
            "dimensiones_ancho_valor": 300, "dimensiones_ancho_tolerancia": 2, "dimensiones_ancho_unidad": "mm",
            "dimensiones_alto_valor": 45, "dimensiones_alto_tolerancia": 1, "dimensiones_alto_unidad": "mm",
            "peso_valor": PESO_ATIPICO, "peso_tolerancia": 3, "peso_unidad": "g"}})
    _capturando = False
    http(r, ["id_ficha", "estado_ficha"])

    vectoriales = [q for q in _sql_capturado if "<=>" in q]
    log(f"\n  Consultas SQL emitidas durante el analisis: {len(_sql_capturado)}")
    log(f"  De ellas, con operador de distancia coseno de pgvector (<=>): {len(vectoriales)}")
    for q in vectoriales:
        log(f"\n  {q[:600]}")

    paso(5, "Anomalia de duplicado semantico persistida")
    filas2 = await mostrar_anomalias(con, fid2, "(se busca tipo_anomalia='duplicado_semantico')")
    dups = [f for f in filas2 if f["tipo_anomalia"] == "duplicado_semantico"]
    log(f"  Registros de duplicado semantico: {len(dups)}")
    for d in dups:
        det = json.loads(d["detalles"]) if d["detalles"] else {}
        log(f"    similitud almacenada en detalles: {det.get('similitud')}")
        log(f"    kitem_similar_id                : {det.get('kitem_similar_id')}")
        log(f"    (coincide con ficha A {fid}: "
            f"{str(det.get('kitem_similar_id')) == str(fid)})")

    # ════════════════════════════════════════════════════════════════
    titulo("RESUMEN")
    log(f"  A.5  transicion bloqueada con anomalia pendiente : {'OK' if bloqueo_ok else 'FALLO'}")
    log(f"  A.9  transicion exitosa tras resolver            : {'OK' if transicion_ok else 'FALLO'}")
    log(f"  B.4  el detector usa la columna embedding (<=>)  : {'OK' if vectoriales else 'FALLO'}")
    log(f"  B.5  duplicado semantico registrado              : {'OK' if dups else 'NO DETECTADO'}")
    log("\n  Registros creados (para limpieza):")
    log(f"    materiales: {CREADOS['materiales']}")
    log(f"    fichas    : {CREADOS['fichas']}")

    await con.close()
    await cli.aclose()
    await engine.dispose()
    SALIDA.close()


asyncio.run(main())
