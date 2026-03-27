"""
Módulo de Autenticación — LDAP/Active Directory + usuarios locales.

Configuración:
    Editar las variables LDAP_* abajo con los datos del Active Directory
    de Molpack Corporation. Mientras no estén configuradas, el sistema
    usa autenticación local (usuarios hardcodeados para desarrollo).

Integración:
    1. Copiar este archivo a app/services/auth_service.py
    2. Copiar auth_router.py a app/routers/auth.py
    3. Registrar en main.py: app.include_router(auth_router)
    4. Configurar las variables LDAP_* con los datos del AD de Molpack

Dependencias:
    pip install python-ldap  (para Linux)
    pip install ldap3        (multiplataforma, recomendado)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN LDAP — Editar con datos de Molpack
# ============================================================

# Dirección del servidor Active Directory
# Ejemplo: "ldap://dc01.molpack.local" o "ldaps://dc01.molpack.net:636"
LDAP_SERVER = os.getenv("LDAP_SERVER", "")

# DN base del dominio
# Ejemplo: "DC=molpack,DC=net"
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "")

# DN del usuario de servicio para buscar usuarios (bind account)
# Ejemplo: "CN=svc_dsms,OU=Service Accounts,DC=molpack,DC=net"
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")

# Grupo de AD que tiene acceso al sistema
# Ejemplo: "CN=DSMS_Users,OU=Groups,DC=molpack,DC=net"
LDAP_GRUPO_AUTORIZADO = os.getenv("LDAP_GRUPO_AUTORIZADO", "")

# Filtro para buscar usuarios
# {username} será reemplazado con el usuario ingresado
LDAP_USER_FILTER = os.getenv("LDAP_USER_FILTER", "(sAMAccountName={username})")

# ¿Usar SSL? (ldaps://)
LDAP_USE_SSL = os.getenv("LDAP_USE_SSL", "false").lower() == "true"

# ¿Está configurado LDAP?
LDAP_HABILITADO = bool(LDAP_SERVER and LDAP_BASE_DN)


# ============================================================
# USUARIOS LOCALES (desarrollo / fallback)
# ============================================================

USUARIOS_LOCALES = {
    "marco.agrusa": {
        "password": "molpack2025",
        "nombre": "Marco Agrusa",
        "rol": "Administrador",
        "email": "marcoagrusa@gmail.com",
    },
    "admin": {
        "password": "admin",
        "nombre": "Administrador",
        "rol": "Administrador",
        "email": "admin@molpack.net",
    },
    "demo": {
        "password": "demo",
        "nombre": "Usuario Demo",
        "rol": "Consultor",
        "email": "demo@molpack.net",
    },
}


# ============================================================
# SCHEMAS
# ============================================================

class LoginRequest(BaseModel):
    usuario: str
    password: str


class LoginResponse(BaseModel):
    exito: bool
    usuario: Optional[str] = None
    nombre: Optional[str] = None
    rol: Optional[str] = None
    email: Optional[str] = None
    iniciales: Optional[str] = None
    metodo: Optional[str] = None  # "ldap" o "local"
    mensaje: Optional[str] = None


# ============================================================
# SERVICIO DE AUTENTICACIÓN
# ============================================================

class AuthService:
    """
    Servicio de autenticación híbrido: LDAP + local.
    
    Flujo:
    1. Si LDAP está configurado, intenta autenticar contra AD
    2. Si LDAP falla o no está configurado, intenta autenticación local
    3. El usuario admin siempre puede autenticarse localmente
    """

    async def login(self, request: LoginRequest) -> LoginResponse:
        """Intenta autenticar al usuario."""
        usuario = request.usuario.strip().lower()
        password = request.password

        if not usuario or not password:
            return LoginResponse(exito=False, mensaje="Usuario y contraseña son obligatorios.")

        # Siempre permitir admin local
        if usuario == "admin":
            return self._autenticar_local(usuario, password)

        # Intentar LDAP primero si está configurado
        if LDAP_HABILITADO:
            resultado = await self._autenticar_ldap(usuario, password)
            if resultado.exito:
                return resultado
            # Si LDAP falla, intentar local como fallback
            logger.info(f"LDAP falló para {usuario}, intentando autenticación local.")

        # Autenticación local
        return self._autenticar_local(usuario, password)

    def _autenticar_local(self, usuario: str, password: str) -> LoginResponse:
        """Autenticación contra usuarios locales hardcodeados."""
        user_data = USUARIOS_LOCALES.get(usuario)
        if not user_data or user_data["password"] != password:
            return LoginResponse(
                exito=False,
                mensaje="Credenciales inválidas.",
            )

        nombre = user_data["nombre"]
        partes = nombre.split()
        iniciales = "".join([p[0].upper() for p in partes[:2]]) if partes else "U"

        return LoginResponse(
            exito=True,
            usuario=usuario,
            nombre=nombre,
            rol=user_data["rol"],
            email=user_data.get("email"),
            iniciales=iniciales,
            metodo="local",
            mensaje="Autenticación local exitosa.",
        )

    async def _autenticar_ldap(self, usuario: str, password: str) -> LoginResponse:
        """
        Autenticación contra Active Directory via LDAP.
        
        Flujo:
        1. Conectar al AD con la cuenta de servicio (bind)
        2. Buscar el usuario por sAMAccountName
        3. Intentar bind con las credenciales del usuario
        4. Verificar membresía en grupo autorizado
        5. Extraer nombre, email, rol del AD
        """
        try:
            import ldap3
            from ldap3 import Server, Connection, ALL, SUBTREE
        except ImportError:
            logger.warning("ldap3 no instalado. pip install ldap3")
            return LoginResponse(exito=False, mensaje="Módulo LDAP no disponible.")

        try:
            # Paso 1: Conectar con cuenta de servicio
            server = Server(LDAP_SERVER, use_ssl=LDAP_USE_SSL, get_info=ALL)

            # Bind con cuenta de servicio para buscar
            conn = Connection(
                server,
                user=LDAP_BIND_DN,
                password=LDAP_BIND_PASSWORD,
                auto_bind=True,
            )

            # Paso 2: Buscar usuario
            filtro = LDAP_USER_FILTER.replace("{username}", usuario)
            conn.search(
                search_base=LDAP_BASE_DN,
                search_filter=filtro,
                search_scope=SUBTREE,
                attributes=[
                    "cn", "displayName", "mail", "memberOf",
                    "sAMAccountName", "department", "title",
                ],
            )

            if not conn.entries:
                conn.unbind()
                return LoginResponse(exito=False, mensaje="Usuario no encontrado en Active Directory.")

            entry = conn.entries[0]
            user_dn = entry.entry_dn
            conn.unbind()

            # Paso 3: Bind con credenciales del usuario
            user_conn = Connection(server, user=user_dn, password=password)
            if not user_conn.bind():
                return LoginResponse(exito=False, mensaje="Contraseña incorrecta.")
            user_conn.unbind()

            # Paso 4: Verificar grupo autorizado (si está configurado)
            if LDAP_GRUPO_AUTORIZADO:
                member_of = [str(g) for g in entry.memberOf.values] if hasattr(entry, 'memberOf') else []
                if LDAP_GRUPO_AUTORIZADO not in member_of:
                    return LoginResponse(
                        exito=False,
                        mensaje="No tienes permisos para acceder al sistema. Contacta al administrador.",
                    )

            # Paso 5: Extraer datos del usuario
            nombre = str(entry.displayName) if hasattr(entry, 'displayName') else str(entry.cn)
            email = str(entry.mail) if hasattr(entry, 'mail') and entry.mail else None
            departamento = str(entry.department) if hasattr(entry, 'department') and entry.department else None

            # Determinar rol basado en grupo o departamento
            rol = "Consultor"  # Default
            if LDAP_GRUPO_AUTORIZADO:
                member_of = [str(g).lower() for g in entry.memberOf.values] if hasattr(entry, 'memberOf') else []
                if any("admin" in g for g in member_of):
                    rol = "Administrador"
                elif any("qa" in g or "calidad" in g for g in member_of):
                    rol = "QA"

            partes = nombre.split()
            iniciales = "".join([p[0].upper() for p in partes[:2]]) if partes else "U"

            logger.info(f"LDAP login exitoso: {usuario} ({nombre}) - {rol}")

            return LoginResponse(
                exito=True,
                usuario=usuario,
                nombre=nombre,
                rol=rol,
                email=email,
                iniciales=iniciales,
                metodo="ldap",
                mensaje="Autenticación Active Directory exitosa.",
            )

        except Exception as e:
            logger.error(f"Error LDAP: {e}")
            return LoginResponse(
                exito=False,
                mensaje=f"Error de conexión con Active Directory: {str(e)}",
            )