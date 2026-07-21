"""
Tests de orquestación de FichaService con sesión de BD simulada.

A diferencia de los tests de lógica pura, aquí se ejercita el *flujo* completo
de los métodos que persisten y coordinan colaboradores: `cambiar_estado` y
`actualizar` (que delega en `_modificar_ficha_vigente` / `_modificar_ficha_editable`).

La sesión de BD es una FakeSession cuyo `execute` devuelve resultados
predefinidos en orden; los colaboradores (kitem_service, auditoria, busqueda,
anomalias) son AsyncMock. Así se valida el ramaje de reglas de negocio
(transiciones, bloqueo por anomalías, versionado automático, obsolescencia)
sin necesitar PostgreSQL/pgvector.

Nota: no son tests end-to-end contra una BD real; verifican la coordinación,
no el SQL emitido. Los tests con pgvector real quedan como paso futuro.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.fichas_services as fichas_mod
from app.core.dsms_constants import (
    ESTADO_BORRADOR,
    ESTADO_PRELIMINAR,
    ESTADO_VIGENTE,
    ESTADO_OBSOLETO,
    ACCION_CAMBIO_ESTADO,
    ACCION_MODIFICACION,
)

MANEJO_COMPLETO = {
    "uso": "Uso X", "manejo": "Manejo Y", "almacenamiento": "Seco",
    "transporte": "Terrestre", "vida_util": "12 meses",
}


@pytest.fixture(autouse=True)
def _sin_reentrenamiento(monkeypatch):
    """Evita que las transiciones a Vigente lancen la tarea de fondo de ML
    (que abriría una sesión real de BD)."""
    monkeypatch.setattr(fichas_mod, "_entrenamiento_en_cooldown", lambda: True)


def _ficha_completa(make_ficha, estado, **overrides):
    datos = dict(
        id_ficha=uuid4(),
        id_material_corporativo=uuid4(),
        estado_ficha=estado,
        codigo_material_local="MAT-001",
        pais="CO",
        nombre_local_material="Bandeja X",
        codigo_version="1.0",
        caracteristicas={"color": "verde", "peso_valor": 50},
        manejo_disposicion=dict(MANEJO_COMPLETO),
        empaque_estiba={"tipo_empaque": "Caja"},
    )
    datos.update(overrides)
    return make_ficha(**datos)


# ── cambiar_estado: validación previa a cualquier mutación ─────────────────

async def test_cambiar_estado_transicion_invalida_no_muta(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_BORRADOR)
    svc = make_ficha_service([fake_result([ficha])])

    with pytest.raises(HTTPException) as exc:
        await svc.cambiar_estado(ficha.id_ficha, ESTADO_VIGENTE, "user")

    assert exc.value.status_code == 400
    # Ninguna mutación debe haber ocurrido.
    svc.kitem_service.actualizar_estado_kitem.assert_not_called()
    svc.auditoria.registrar.assert_not_called()
    svc.db_session.commit.assert_not_awaited()


async def test_cambiar_estado_bloquea_con_anomalias_pendientes(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_BORRADOR)
    anomalia_pendiente = object()  # basta con que la lista no esté vacía
    svc = make_ficha_service([
        fake_result([ficha]),               # obtener()
        fake_result([anomalia_pendiente]),  # anomalías pendientes
    ])

    with pytest.raises(HTTPException) as exc:
        await svc.cambiar_estado(ficha.id_ficha, ESTADO_PRELIMINAR, "user")

    assert exc.value.status_code == 400
    assert "pendiente" in exc.value.detail.lower()
    svc.kitem_service.actualizar_estado_kitem.assert_not_called()
    svc.db_session.commit.assert_not_awaited()


# ── cambiar_estado: caminos felices ────────────────────────────────────────

async def test_cambiar_estado_a_preliminar_enriquece_y_analiza(
    make_ficha_service, make_ficha, make_material, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_BORRADOR)
    material = make_material(categoria="Bandeja")
    svc = make_ficha_service([
        fake_result([ficha]),      # obtener()
        fake_result([]),           # anomalías pendientes → ninguna
        fake_result([material]),   # _validar_material() en el bloque Preliminar
        fake_result([]),           # sa_update(KItem) nombre/descripción
    ])

    resultado = await svc.cambiar_estado(ficha.id_ficha, ESTADO_PRELIMINAR, "user")

    assert resultado is ficha
    svc.kitem_service.actualizar_estado_kitem.assert_awaited_once()
    assert svc.kitem_service.actualizar_estado_kitem.await_args.kwargs["nuevo_estado"] == ESTADO_PRELIMINAR
    # Al pasar a Preliminar se regenera el embedding y se corren los detectores.
    svc.busqueda.asignar_embedding.assert_awaited_once()
    svc.anomalias.analizar_ficha.assert_awaited_once()
    assert svc.anomalias.analizar_ficha.await_args.kwargs["contexto"] == "creacion"
    # Auditoría de cambio de estado registrada.
    assert svc.auditoria.registrar.await_args.kwargs["accion"] == ACCION_CAMBIO_ESTADO
    svc.db_session.commit.assert_awaited()


async def test_cambiar_estado_a_vigente_valida_unicidad_y_no_reentrena_en_cooldown(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_PRELIMINAR)
    svc = make_ficha_service([
        fake_result([ficha]),   # obtener()
        fake_result([]),        # _validar_unica_vigente_por_material_pais → no hay otra
        fake_result([]),        # anomalías pendientes → ninguna
    ])

    resultado = await svc.cambiar_estado(ficha.id_ficha, ESTADO_VIGENTE, "user")

    assert resultado is ficha
    assert svc.kitem_service.actualizar_estado_kitem.await_args.kwargs["nuevo_estado"] == ESTADO_VIGENTE
    # No hay enriquecimiento/análisis al pasar a Vigente (solo en Preliminar).
    svc.busqueda.asignar_embedding.assert_not_called()
    svc.db_session.commit.assert_awaited()


# ── _validar_unica_vigente_por_material_pais ───────────────────────────────

async def test_unica_vigente_lanza_si_ya_existe(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_PRELIMINAR)
    otra_vigente = object()
    svc = make_ficha_service([fake_result([otra_vigente])])

    with pytest.raises(HTTPException) as exc:
        await svc._validar_unica_vigente_por_material_pais(ficha)
    assert exc.value.status_code == 400
    assert "vigente" in exc.value.detail.lower()


async def test_unica_vigente_pasa_si_no_existe(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_PRELIMINAR)
    svc = make_ficha_service([fake_result([])])
    # No debe lanzar.
    await svc._validar_unica_vigente_por_material_pais(ficha)


# ── actualizar: reglas por estado ──────────────────────────────────────────

async def test_actualizar_obsoleto_esta_prohibido(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_OBSOLETO)
    svc = make_ficha_service([fake_result([ficha])])

    with pytest.raises(HTTPException) as exc:
        await svc.actualizar(ficha.id_ficha, {"caracteristicas": {"color": "azul"}}, "user")
    assert exc.value.status_code == 400
    assert "obsoleto" in exc.value.detail.lower()
    svc.db_session.commit.assert_not_awaited()


async def test_actualizar_borrador_edita_en_sitio(
    make_ficha_service, make_ficha, fake_result
):
    ficha = _ficha_completa(make_ficha, ESTADO_BORRADOR, caracteristicas={"color": "rojo"})
    svc = make_ficha_service([fake_result([ficha])])

    resultado = await svc.actualizar(
        ficha.id_ficha, {"caracteristicas": {"color": "azul"}}, "user"
    )

    assert resultado is ficha
    assert ficha.caracteristicas == {"color": "azul"}
    # Misma versión: la edición directa no versiona.
    assert ficha.codigo_version == "1.0"
    assert svc.auditoria.registrar.await_args.kwargs["accion"] == ACCION_MODIFICACION
    svc.db_session.commit.assert_awaited()


async def test_actualizar_vigente_crea_version_y_obsoleta_la_anterior(
    make_ficha_service, make_ficha, make_material, fake_result
):
    from types import SimpleNamespace

    vigente = _ficha_completa(make_ficha, ESTADO_VIGENTE, caracteristicas={"color": "rojo"})
    material = make_material(categoria="Bandeja")
    svc = make_ficha_service([
        fake_result([vigente]),    # obtener()
        fake_result([material]),   # _validar_material() para el embedding de la nueva versión
    ])
    # crear_kitem debe devolver un kitem con id UUID real (los schemas de
    # relación validan source_id/target_id como UUID).
    nuevo_kitem_id = uuid4()
    svc.kitem_service.crear_kitem.return_value = SimpleNamespace(id=nuevo_kitem_id)

    nueva = await svc.actualizar(
        vigente.id_ficha, {"caracteristicas": {"color": "azul"}}, "user"
    )

    # La nueva versión hereda el material y aplica la modificación.
    assert nueva.id_material_corporativo == vigente.id_material_corporativo
    assert nueva.caracteristicas == {"color": "azul"}
    # Versión incrementada (1.0 → 2.0) y creada en Preliminar.
    assert nueva.codigo_version == "2.0"
    schema_kitem = svc.kitem_service.crear_kitem.await_args.args[0]
    assert schema_kitem.estado == ESTADO_PRELIMINAR
    # La ficha vigente anterior se marca Obsoleto automáticamente.
    svc.kitem_service.actualizar_estado_kitem.assert_awaited_once()
    call = svc.kitem_service.actualizar_estado_kitem.await_args
    assert call.kwargs["kitem_id"] == vigente.id_ficha
    assert call.kwargs["nuevo_estado"] == ESTADO_OBSOLETO
