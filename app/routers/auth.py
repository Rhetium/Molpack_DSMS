"""
Router de Autenticación — Login con JWT + Rate Limiting.

Endpoints:
    POST /auth/login     — Login (devuelve JWT token)
    GET  /auth/me        — Info del usuario actual (requiere token)
    POST /auth/refresh   — Renovar token antes de que expire
"""

from fastapi import APIRouter, Depends, Request
from app.services.auth_service import AuthService, LoginRequest, LoginResponse
from app.core.security import (
    crear_token,
    get_usuario_actual,
    login_rate_limiter,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
async def login(request: LoginRequest, req: Request):
    """
    Autenticación de usuario con JWT y rate limiting.
    
    Retorna un token JWT que debe enviarse en el header:
        Authorization: Bearer <token>
    
    Rate limiting: máximo 5 intentos fallidos por minuto.
    Después de 5 fallos, bloqueo por 5 minutos.
    """
    # Obtener IP del cliente
    ip = req.client.host if req.client else "unknown"

    # Verificar rate limit
    login_rate_limiter.verificar(ip)

    # Intentar login
    service = AuthService()
    resultado = await service.login(request)

    # Registrar intento
    login_rate_limiter.registrar_intento(ip, resultado.exito)

    if not resultado.exito:
        intentos_restantes = login_rate_limiter.get_intentos_restantes(ip)
        return {
            "exito": False,
            "mensaje": resultado.mensaje,
            "intentos_restantes": intentos_restantes,
        }

    # Generar JWT token
    token = crear_token({
        "usuario": resultado.usuario,
        "nombre": resultado.nombre,
        "rol": resultado.rol,
        "iniciales": resultado.iniciales,
        "email": resultado.email,
        "metodo": resultado.metodo,
    })

    return {
        "exito": True,
        "token": token,
        "usuario": resultado.usuario,
        "nombre": resultado.nombre,
        "rol": resultado.rol,
        "iniciales": resultado.iniciales,
        "email": resultado.email,
        "metodo": resultado.metodo,
        "mensaje": resultado.mensaje,
    }


@router.get("/me")
async def me(usuario: dict = Depends(get_usuario_actual)):
    """
    Retorna la información del usuario autenticado.
    Requiere token JWT en el header Authorization.
    Útil para verificar si el token sigue vigente.
    """
    return {
        "usuario": usuario.get("usuario"),
        "nombre": usuario.get("nombre"),
        "rol": usuario.get("rol"),
        "iniciales": usuario.get("iniciales"),
        "email": usuario.get("email"),
    }


@router.post("/refresh")
async def refresh(usuario: dict = Depends(get_usuario_actual)):
    """
    Renueva el token JWT antes de que expire.
    Requiere un token válido (no expirado).
    Retorna un nuevo token con tiempo de expiración extendido.
    """
    token = crear_token({
        "usuario": usuario.get("usuario"),
        "nombre": usuario.get("nombre"),
        "rol": usuario.get("rol"),
        "iniciales": usuario.get("iniciales"),
        "email": usuario.get("email"),
        "metodo": usuario.get("metodo"),
    })

    return {
        "token": token,
        "mensaje": "Token renovado exitosamente.",
    }