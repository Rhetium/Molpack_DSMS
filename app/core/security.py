import os
import time
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


JWT_SECRET = os.getenv("JWT_SECRET", "molpack-dsms-dev-secret-key-cambiar-en-produccion-2025")


JWT_ALGORITHM = "HS256"


JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))



def crear_token(datos: dict) -> str:
    payload = {
        **datos,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verificar_token(token: str) -> dict:
  
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


async def get_usuario_nombre(
    payload: dict = Depends(get_usuario_actual),
) -> str:
    """
    Devuelve el identificador del usuario autenticado, tomado del token JWT.

    Esta es la ÚNICA fuente de identidad válida para auditoría. Los routers
    deben usar esta dependencia en lugar de leer el usuario del cuerpo de la
    petición: un campo `usuario` enviado por el cliente es autodeclarado y
    puede falsificarse, lo que permitiría registrar acciones a nombre de un
    tercero y corromper la trazabilidad.

    Uso en routers:
        @router.post("/algo")
        async def endpoint(usuario: str = Depends(get_usuario_nombre)):
            await service.hacer_algo(usuario=usuario)
    """
    nombre = payload.get("usuario") or payload.get("nombre")
    if not nombre:
        raise HTTPException(
            status_code=401,
            detail="El token no contiene la identidad del usuario.",
        )
    return nombre


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
        self.intentos: dict[str, list[tuple[float, bool]]] = defaultdict(list)
        self.bloqueados: dict[str, float] = {}

    def verificar(self, ip: str) -> None:
        """
        Verifica si la IP puede intentar login.
        Lanza HTTPException 429 si está bloqueada.
        """
        ahora = time.time()

        if ip in self.bloqueados:
            desbloqueo = self.bloqueados[ip]
            if ahora < desbloqueo:
                restante = int(desbloqueo - ahora)
                raise HTTPException(
                    status_code=429,
                    detail=f"Demasiados intentos fallidos. Intenta de nuevo en {restante} segundos.",
                )
            else:
                del self.bloqueados[ip]
                self.intentos[ip] = []

    def registrar_intento(self, ip: str, exitoso: bool) -> None:
        """Registra un intento de login."""
        ahora = time.time()

        if exitoso:
            self.intentos[ip] = []
            if ip in self.bloqueados:
                del self.bloqueados[ip]
            return

  
        self.intentos[ip].append((ahora, False))


        self.intentos[ip] = [
            (t, e) for t, e in self.intentos[ip]
            if ahora - t < self.ventana_segundos
        ]

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