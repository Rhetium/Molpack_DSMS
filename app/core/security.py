"""
Módulo de Seguridad — JWT + Rate Limiting.

JWT:
    - Tokens firmados con HS256, expiración configurable (default 8h)
    - Se genera al login exitoso, se valida en cada request protegido
    - Contiene: usuario, nombre, rol, iniciales, email, exp

Rate Limiting:
    - Máximo 5 intentos de login fallidos por IP en 1 minuto
    - Después de 5 fallos, bloqueo por 5 minutos
    - Se resetea al hacer login exitoso

Integración:
    1. Copiar a app/core/security.py
    2. En auth_service.py: importar crear_token y agregar al LoginResponse
    3. En cada router protegido: agregar Depends(get_usuario_actual)
    4. En main.py: agregar middleware de rate limiting

Dependencias:
    pip install PyJWT
"""

import os
import time
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# ============================================================
# CONFIGURACIÓN JWT
# ============================================================

# Clave secreta para firmar tokens — CAMBIAR EN PRODUCCIÓN
# Generar con: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET = os.getenv("JWT_SECRET", "molpack-dsms-dev-secret-key-cambiar-en-produccion-2025")

# Algoritmo de firma
JWT_ALGORITHM = "HS256"

# Tiempo de expiración del token (en horas)
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))


# ============================================================
# FUNCIONES JWT
# ============================================================

def crear_token(datos: dict) -> str:
    """
    Genera un token JWT firmado.
    
    Args:
        datos: Dict con los campos del usuario (usuario, nombre, rol, etc.)
    
    Returns:
        Token JWT como string
    """
    payload = {
        **datos,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verificar_token(token: str) -> dict:
    """
    Verifica y decodifica un token JWT.
    
    Args:
        token: Token JWT string
    
    Returns:
        Dict con los datos del payload
    
    Raises:
        HTTPException 401 si el token es inválido o expirado
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Sesión expirada. Por favor inicia sesión nuevamente.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticación inválido.",
        )


# ============================================================
# DEPENDENCIA DE AUTENTICACIÓN PARA FASTAPI
# ============================================================

security_scheme = HTTPBearer(auto_error=False)


async def get_usuario_actual(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """
    Dependencia de FastAPI que extrae y valida el usuario del token JWT.
    
    Uso en routers:
        @router.get("/ruta-protegida")
        async def endpoint(usuario = Depends(get_usuario_actual)):
            print(usuario["nombre"])  # Marco Agrusa
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="No autenticado. Envía el token en el header Authorization: Bearer <token>",
        )
    return verificar_token(credentials.credentials)


async def get_usuario_opcional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[dict]:
    """
    Igual que get_usuario_actual pero no lanza error si no hay token.
    Útil para endpoints que funcionan con o sin autenticación.
    """
    if not credentials:
        return None
    try:
        return verificar_token(credentials.credentials)
    except HTTPException:
        return None


# ============================================================
# RATE LIMITING
# ============================================================

class RateLimiter:
    """
    Rate limiter en memoria para protección contra fuerza bruta.
    
    Configuración:
        max_intentos: Máximo de intentos fallidos antes de bloquear
        ventana_segundos: Ventana de tiempo para contar intentos
        bloqueo_segundos: Tiempo de bloqueo después de exceder intentos
    """

    def __init__(
        self,
        max_intentos: int = 5,
        ventana_segundos: int = 60,
        bloqueo_segundos: int = 300,
    ):
        self.max_intentos = max_intentos
        self.ventana_segundos = ventana_segundos
        self.bloqueo_segundos = bloqueo_segundos
        # {ip: [(timestamp, exitoso), ...]}
        self.intentos: dict[str, list[tuple[float, bool]]] = defaultdict(list)
        # {ip: timestamp_desbloqueo}
        self.bloqueados: dict[str, float] = {}

    def verificar(self, ip: str) -> None:
        """
        Verifica si la IP puede intentar login.
        Lanza HTTPException 429 si está bloqueada.
        """
        ahora = time.time()

        # ¿Está bloqueada?
        if ip in self.bloqueados:
            desbloqueo = self.bloqueados[ip]
            if ahora < desbloqueo:
                restante = int(desbloqueo - ahora)
                raise HTTPException(
                    status_code=429,
                    detail=f"Demasiados intentos fallidos. Intenta de nuevo en {restante} segundos.",
                )
            else:
                # Desbloquear
                del self.bloqueados[ip]
                self.intentos[ip] = []

    def registrar_intento(self, ip: str, exitoso: bool) -> None:
        """Registra un intento de login."""
        ahora = time.time()

        if exitoso:
            # Login exitoso: limpiar intentos
            self.intentos[ip] = []
            if ip in self.bloqueados:
                del self.bloqueados[ip]
            return

        # Login fallido: agregar al historial
        self.intentos[ip].append((ahora, False))

        # Limpiar intentos fuera de la ventana
        self.intentos[ip] = [
            (t, e) for t, e in self.intentos[ip]
            if ahora - t < self.ventana_segundos
        ]

        # ¿Excedió el máximo?
        if len(self.intentos[ip]) >= self.max_intentos:
            self.bloqueados[ip] = ahora + self.bloqueo_segundos
            self.intentos[ip] = []

    def get_intentos_restantes(self, ip: str) -> int:
        """Retorna cuántos intentos le quedan a la IP."""
        ahora = time.time()
        intentos_recientes = [
            t for t, e in self.intentos.get(ip, [])
            if ahora - t < self.ventana_segundos
        ]
        return max(0, self.max_intentos - len(intentos_recientes))


# Instancia global del rate limiter
login_rate_limiter = RateLimiter(
    max_intentos=5,
    ventana_segundos=60,
    bloqueo_segundos=300,
)