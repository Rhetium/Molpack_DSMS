from fastapi import FastAPI, Depends
from app.routers import dsms, material, ficha
from app.routers.auditoria import router as auditoria_router
from app.routers.semantic_search import router as busqueda_semantica_router
from app.routers.anomalia import router as anomalia_router
from app.routers.export import router as export_router
from app.routers.imagenes import router as imagenes_router
from app.routers.auth import router as auth_router
from app.core.security import get_usuario_actual

app = FastAPI(title="DSMS Backend")

# Autenticación JWT obligatoria para todos los routers de datos.
# Excepciones:
#   - auth_router: /auth/login debe ser público (allí se obtiene el token);
#     /auth/me y /auth/refresh ya se protegen a nivel de endpoint.
#   - imagenes_router: el GET de imagen se sirve vía <img src> (sin header
#     Authorization), por lo que se deja público; el POST/DELETE se protegen
#     dentro del propio router.
auth = [Depends(get_usuario_actual)]

app.include_router(dsms.router, dependencies=auth)
app.include_router(material.router, dependencies=auth)
app.include_router(ficha.router, dependencies=auth)
app.include_router(auditoria_router, dependencies=auth)
app.include_router(busqueda_semantica_router, dependencies=auth)
app.include_router(anomalia_router, dependencies=auth)
app.include_router(export_router, prefix="/dsms", dependencies=auth)
app.include_router(imagenes_router)
app.include_router(auth_router)
