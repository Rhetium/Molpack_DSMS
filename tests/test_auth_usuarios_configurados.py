"""
Usuarios configurados por entorno (AUTH_USUARIOS): hash PBKDF2 y login sin LDAP.

Garantías:
- El hash nunca contiene la contraseña y cada hash usa una sal distinta.
- Un usuario configurado entra con su contraseña aunque LDAP esté activo
  (no depende del Domain Controller) y no cae a otras vías si falla.
"""

import json

import pytest

from app.services import auth_service
from app.services.auth_service import (
    AuthService,
    LoginRequest,
    hashear_password,
    verificar_password,
)


def test_hash_verifica_solo_la_password_correcta():
    h = hashear_password("Secreta123*", iteraciones=1_000)
    assert "Secreta123*" not in h
    assert verificar_password("Secreta123*", h)
    assert not verificar_password("secreta123*", h)


def test_hash_usa_sal_distinta_cada_vez():
    assert hashear_password("x", iteraciones=1_000) != hashear_password("x", iteraciones=1_000)


@pytest.mark.parametrize("hash_invalido", ["", "texto-plano", "md5$1$a$b", "pbkdf2_sha256$x$y$z"])
def test_hash_malformado_no_autentica(hash_invalido):
    assert not verificar_password("x", hash_invalido)


def test_carga_usuarios_desde_json(monkeypatch):
    monkeypatch.setenv("AUTH_USUARIOS", json.dumps([{"usuario": " Ana@Molpack.net ", "hash": "h"}]))
    assert set(auth_service._cargar_usuarios_configurados()) == {"ana@molpack.net"}


def test_json_invalido_no_carga_usuarios(monkeypatch):
    monkeypatch.setenv("AUTH_USUARIOS", "{no es json")
    assert auth_service._cargar_usuarios_configurados() == {}


@pytest.fixture
def usuario_configurado(monkeypatch):
    usuarios = {"ana@molpack.net": {
        "usuario": "ana@molpack.net",
        "hash": hashear_password("Clave2026!", iteraciones=1_000),
        "nombre": "Ana Pérez",
        "rol": "Administrador",
    }}
    monkeypatch.setattr(auth_service, "USUARIOS_CONFIGURADOS", usuarios)
    # LDAP activo: el usuario configurado no debe depender de él
    monkeypatch.setattr(auth_service, "LDAP_HABILITADO", True)

    async def _ldap_no_debe_llamarse(*_args):
        raise AssertionError("un usuario configurado no consulta LDAP")
    monkeypatch.setattr(AuthService, "_autenticar_ldap", _ldap_no_debe_llamarse)


async def test_login_usuario_configurado(usuario_configurado):
    r = await AuthService().login(LoginRequest(usuario="Ana@Molpack.net", password="Clave2026!"))
    assert r.exito
    assert r.usuario == "ana@molpack.net"
    assert r.rol == "Administrador"
    assert r.iniciales == "AP"
    assert r.email == "ana@molpack.net"


async def test_login_usuario_configurado_password_incorrecta(usuario_configurado):
    r = await AuthService().login(LoginRequest(usuario="ana@molpack.net", password="otra"))
    assert not r.exito
    assert r.mensaje == "Credenciales inválidas."
