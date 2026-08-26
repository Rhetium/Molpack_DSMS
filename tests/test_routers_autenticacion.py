"""
Tests de la capa HTTP: autenticación y origen de la identidad.

Estos tests NO requieren base de datos. Verifican dos garantías:

1. **Cobertura de autenticación**: todo endpoint de la API exige un token JWT
   válido, salvo los explícitamente declarados públicos (`POST /auth/login`).
   El test recorre el esquema OpenAPI real de la aplicación, así que un router
   nuevo queda cubierto automáticamente sin tocar este archivo.

2. **Origen de la identidad**: el usuario que se registra en la auditoría
   proviene del token JWT y NUNCA del cuerpo de la petición. Un cliente que
   envíe `usuario_creador: "otro.usuario"` no debe poder atribuirse acciones
   a nombre de un tercero.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import crear_token
from app.routers.ficha import get_ficha_service
from app.routers.material import get_material_service


# Prefijo bajo el que app/main.py monta todos los routers.
API = "/api"

# Rutas que deben permanecer accesibles sin token, con su justificación.
RUTAS_PUBLICAS = {
    (f"{API}/auth/login", "post"),  # No puede exigir token: es quien lo emite.
}

METODOS_CON_CUERPO = {"post", "patch", "put"}

UUID_CERO = "00000000-0000-0000-0000-000000000000"


def _rutas_de_la_app():
    """Extrae (ruta, método) de todos los endpoints del esquema OpenAPI."""
    for ruta, operaciones in app.openapi()["paths"].items():
        for metodo in operaciones:
            if metodo in ("get", "post", "patch", "put", "delete"):
                yield ruta, metodo


def _url_concreta(ruta: str) -> str:
    """Sustituye los parámetros de path por valores sintácticamente válidos."""
    for parametro in (
        "{id_ficha}", "{id_material}", "{kitem_id}",
        "{relacion_id}", "{id_anomalia}",
    ):
        ruta = ruta.replace(parametro, UUID_CERO)
    return ruta.replace("{tipo}", "foto_producto")


@pytest.fixture
def cliente():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def token_valido():
    return crear_token({
        "usuario": "usuario.del.token",
        "nombre": "Usuario Del Token",
        "rol": "Administrador",
    })


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "ruta,metodo",
    [(r, m) for r, m in _rutas_de_la_app() if (r, m) not in RUTAS_PUBLICAS],
)
def test_endpoint_exige_autenticacion(cliente, ruta, metodo):
    """Sin token, todo endpoint no público responde 401."""
    kwargs = {"json": {}} if metodo in METODOS_CON_CUERPO else {}
    respuesta = getattr(cliente, metodo)(_url_concreta(ruta), **kwargs)

    assert respuesta.status_code == 401, (
        f"{metodo.upper()} {ruta} respondió {respuesta.status_code} sin token; "
        f"se esperaba 401. ¿Falta 'dependencies=[Depends(get_usuario_actual)]' "
        f"en el router?"
    )


@pytest.mark.parametrize("ruta,metodo", sorted(RUTAS_PUBLICAS))
def test_ruta_publica_no_exige_token(cliente, ruta, metodo):
    """El login debe seguir siendo accesible sin credenciales previas."""
    respuesta = getattr(cliente, metodo)(ruta, json={"usuario": "x", "password": "y"})
    assert respuesta.status_code != 401


def test_token_invalido_es_rechazado(cliente):
    respuesta = cliente.get(
        f"{API}/auth/me",
        headers={"Authorization": "Bearer token.falsificado.xxx"},
    )
    assert respuesta.status_code == 401
    assert "inválido" in respuesta.json()["detail"].lower()


def test_token_valido_es_aceptado(cliente, token_valido):
    respuesta = cliente.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {token_valido}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"] == "usuario.del.token"


class _ServicioEspia:
    """Captura la identidad con la que el router invoca al servicio.

    Interrumpe el flujo con un 418 que transporta el usuario capturado, para
    no depender de la base de datos ni de la validación del response_model.
    """

    def __init__(self):
        self.usuario_recibido = None

    def _capturar(self, usuario):
        self.usuario_recibido = usuario
        raise HTTPException(status_code=418, detail=usuario)

    async def crear(self, datos):
        self._capturar(datos.usuario_creador)

    async def cambiar_estado(self, id_ficha, nuevo_estado, usuario_actualizacion):
        self._capturar(usuario_actualizacion)

    async def actualizar(self, id_ficha, datos_actualizacion, usuario):
        self._capturar(usuario)


def test_crear_ficha_ignora_el_usuario_del_cuerpo(cliente, token_valido):
    """El cuerpo declara otro usuario; debe prevalecer el del token."""
    espia = _ServicioEspia()
    app.dependency_overrides[get_ficha_service] = lambda: espia

    respuesta = cliente.post(
        f"{API}/ficha",
        headers={"Authorization": f"Bearer {token_valido}"},
        json={
            "id_material_corporativo": UUID_CERO,
            "usuario_creador": "atacante.suplantador",
        },
    )

    assert respuesta.status_code == 418
    assert espia.usuario_recibido == "usuario.del.token"


def test_cambio_de_estado_usa_el_usuario_del_token(cliente, token_valido):
    espia = _ServicioEspia()
    app.dependency_overrides[get_ficha_service] = lambda: espia

    respuesta = cliente.patch(
        f"{API}/ficha/{UUID_CERO}/estado",
        headers={"Authorization": f"Bearer {token_valido}"},
        json={
            "nuevo_estado": "Preliminar",
            "usuario_actualizacion": "atacante.suplantador",
        },
    )

    assert respuesta.status_code == 418
    assert espia.usuario_recibido == "usuario.del.token"


def test_actualizar_ficha_usa_el_usuario_del_token(cliente, token_valido):
    espia = _ServicioEspia()
    app.dependency_overrides[get_ficha_service] = lambda: espia

    respuesta = cliente.patch(
        f"{API}/ficha/{UUID_CERO}",
        headers={"Authorization": f"Bearer {token_valido}"},
        json={
            "nombre_local_material": "Cambio",
            "usuario_actualizacion": "atacante.suplantador",
        },
    )

    assert respuesta.status_code == 418
    assert espia.usuario_recibido == "usuario.del.token"


def test_crear_material_ignora_el_usuario_del_cuerpo(cliente, token_valido):
    espia = _ServicioEspia()
    app.dependency_overrides[get_material_service] = lambda: espia

    respuesta = cliente.post(
        f"{API}/material",
        headers={"Authorization": f"Bearer {token_valido}"},
        json={
            "nombre_corporativo": "Material de prueba",
            "estado_material": "Activo",
            "usuario_creador": "atacante.suplantador",
        },
    )

    assert respuesta.status_code == 418
    assert espia.usuario_recibido == "usuario.del.token"


def test_transicion_no_se_atribuye_a_sistema(cliente, token_valido):
    """Regresión: los endpoints semánticos usaban usuario='sistema' fijo."""
    espia = _ServicioEspia()
    app.dependency_overrides[get_ficha_service] = lambda: espia

    respuesta = cliente.post(
        f"{API}/ficha/{UUID_CERO}/publicar",
        headers={"Authorization": f"Bearer {token_valido}"},
    )

    assert respuesta.status_code == 418
    assert espia.usuario_recibido != "sistema"
    assert espia.usuario_recibido == "usuario.del.token"
