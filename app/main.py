from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import dsms, material, ficha
from app.routers.auditoria import router as auditoria_router
from app.routers.semantic_search import router as busqueda_semantica_router
from app.routers.anomalia import router as anomalia_router
from app.routers.export import router as export_router
from app.routers.imagenes import router as imagenes_router
from app.routers.auth import router as auth_router

app = FastAPI(title="DSMS Backend")

# Todos los endpoints cuelgan de /api, el mismo prefijo que usa el cliente
# Axios (frontend/lib/api.js). Asi desarrollo y produccion comparten las
# mismas rutas y el reverse proxy no tiene que reescribir nada.
API_PREFIX = "/api"

api = APIRouter(prefix=API_PREFIX)

api.include_router(dsms.router)
api.include_router(material.router)
api.include_router(ficha.router)
api.include_router(auditoria_router)
api.include_router(busqueda_semantica_router)
api.include_router(anomalia_router)
api.include_router(export_router, prefix="/dsms")
api.include_router(imagenes_router)
api.include_router(auth_router)

app.include_router(api)


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """Sirve la SPA compilada.

    Cualquier ruta que no corresponda a un archivo real devuelve index.html,
    para que React Router resuelva la navegacion en el cliente (si no, un
    F5 sobre /fichas/<id> daria 404).

    Dos excepciones, para que un 404 real no quede disfrazado de pagina:

    - /api: un endpoint inexistente debe dar 404, no el HTML de la SPA, que
      el cliente Axios no sabria interpretar.
    - Rutas con extension (.png, .css, .js...): son pedidos de archivos, no
      navegacion. Devolverles index.html haria que un asset faltante pareciera
      cargar (200 con HTML) en vez de fallar visiblemente.
    """

    async def _index(self, scope):
        return await super().get_response("index.html", scope)

    async def get_response(self, path: str, scope):
        # Se usa scope["path"] y no `path`: este ultimo llega normalizado con
        # el separador del sistema operativo (en Windows, "\").
        ruta = scope["path"]
        # Las rutas de React Router no llevan extension (/fichas/<uuid>).
        pide_archivo = "." in ruta.rsplit("/", 1)[-1]
        sin_fallback = ruta.startswith(API_PREFIX) or pide_archivo

        try:
            respuesta = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or sin_fallback:
                raise
            return await self._index(scope)

        if respuesta.status_code == 404 and not sin_fallback:
            return await self._index(scope)
        return respuesta


# El montaje va al final: las rutas registradas antes (incluidas /docs y
# /openapi.json) tienen prioridad sobre el comodin "/".
# En desarrollo el build no existe y la SPA la sirve `npm run dev`.
if FRONTEND_DIST.is_dir():
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="spa")
