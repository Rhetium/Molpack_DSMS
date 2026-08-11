
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


    ip = req.client.host if req.client else "unknown"


    login_rate_limiter.verificar(ip)

    service = AuthService()
    resultado = await service.login(request)

    login_rate_limiter.registrar_intento(ip, resultado.exito)

    if not resultado.exito:
        intentos_restantes = login_rate_limiter.get_intentos_restantes(ip)
        return {
            "exito": False,
            "mensaje": resultado.mensaje,
            "intentos_restantes": intentos_restantes,
        }

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

    return {
        "usuario": usuario.get("usuario"),
        "nombre": usuario.get("nombre"),
        "rol": usuario.get("rol"),
        "iniciales": usuario.get("iniciales"),
        "email": usuario.get("email"),
    }


@router.post("/refresh")
async def refresh(usuario: dict = Depends(get_usuario_actual)):

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