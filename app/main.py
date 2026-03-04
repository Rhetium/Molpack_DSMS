from fastapi import FastAPI
from app.routers import dsms, material, ficha
from app.routers.auditoria import router as auditoria_router
from app.routers.semantic_search import router as busqueda_semantica_router
from app.routers.anomalia import router as anomalia_router

app = FastAPI(title="DSMS Backend")

# Incluir routers (de momento solo health)
app.include_router(dsms.router)
app.include_router(material.router)
app.include_router(ficha.router)
app.include_router(auditoria_router)
app.include_router(busqueda_semantica_router)
app.include_router(anomalia_router)
