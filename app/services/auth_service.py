import os
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

LDAP_SERVER = os.getenv("LDAP_SERVER", "")


LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "")

LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")


LDAP_GRUPO_AUTORIZADO = os.getenv("LDAP_GRUPO_AUTORIZADO", "")

LDAP_USER_FILTER = os.getenv("LDAP_USER_FILTER", "(sAMAccountName={username})")

LDAP_USE_SSL = os.getenv("LDAP_USE_SSL", "false").lower() == "true"


LDAP_HABILITADO = bool(LDAP_SERVER and LDAP_BASE_DN)

# Los usuarios locales de abajo son credenciales de desarrollo embebidas en el
# codigo: sirven para trabajar sin un Domain Controller a mano, no para
# produccion. Por eso se apagan solos en cuanto LDAP queda configurado.
#
#   AUTH_LOCAL_HABILITADO sin definir  -> habilitados solo si LDAP no lo esta
#   AUTH_LOCAL_HABILITADO=true         -> habilitados igual (soporte, con LDAP caido)
#   AUTH_LOCAL_HABILITADO=false        -> apagados siempre
#
# Dejarlo en "true" con LDAP activo reabre el acceso con admin/admin: es una
# palanca de emergencia, no un valor de configuracion permanente.
_local_env = os.getenv("AUTH_LOCAL_HABILITADO", "").strip().lower()
if _local_env in ("true", "1", "si", "yes"):
    AUTH_LOCAL_HABILITADO = True
elif _local_env in ("false", "0", "no"):
    AUTH_LOCAL_HABILITADO = False
else:
    AUTH_LOCAL_HABILITADO = not LDAP_HABILITADO

if AUTH_LOCAL_HABILITADO and LDAP_HABILITADO:
    logger.warning(
        "AUTH_LOCAL_HABILITADO=true con LDAP activo: las credenciales locales "
        "embebidas siguen aceptandose. Desactivar en cuanto se valide el AD."
    )

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

    async def login(self, request: LoginRequest) -> LoginResponse:
        usuario = request.usuario.strip().lower()
        password = request.password

        if not usuario or not password:
            return LoginResponse(exito=False, mensaje="Usuario y contraseña son obligatorios.")

        if LDAP_HABILITADO:
            resultado = await self._autenticar_ldap(usuario, password)
            if resultado.exito:
                return resultado

            # Sin usuarios locales habilitados, lo que diga LDAP es la palabra
            # final: no hay segunda via de entrada que lo contradiga.
            if not AUTH_LOCAL_HABILITADO:
                return resultado

            logger.info("LDAP falló para %s, intentando autenticación local.", usuario)

        return self._autenticar_local(usuario, password)

    def _autenticar_local(self, usuario: str, password: str) -> LoginResponse:
        if not AUTH_LOCAL_HABILITADO:
            logger.warning("Intento de login local para %s con la vía local desactivada.", usuario)
            return LoginResponse(exito=False, mensaje="Credenciales inválidas.")

        user_data = USUARIOS_LOCALES.get(usuario)
        # compare_digest y no "!=" para no filtrar por tiempo de respuesta
        # cuantos caracteres iniciales de la contraseña son correctos.
        if not user_data or not secrets.compare_digest(user_data["password"], password):
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
            rol = "Consultor" 
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
            # El detalle va al log, no a la respuesta: los errores de ldap3
            # incluyen el DN de la cuenta de servicio y la URL del DC.
            logger.error("Error LDAP: %s", e)
            return LoginResponse(
                exito=False,
                mensaje="No se pudo contactar con Active Directory. Contacta al administrador.",
            )