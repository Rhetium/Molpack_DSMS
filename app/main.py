from fastapi import FastAPI
from app.routers import dsms, material, ficha
from app.routers.auditoria import router as auditoria_router

app = FastAPI(title="DSMS Backend")

# Incluir routers (de momento solo health)
app.include_router(dsms.router)
app.include_router(material.router)
app.include_router(ficha.router)
app.include_router(auditoria_router)