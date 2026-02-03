from fastapi import FastAPI
from app.routers import health, material, ficha

app = FastAPI(title="DSMS Backend")

# Incluir routers (de momento solo health)
app.include_router(health.router)
app.include_router(material.router)
app.include_router(ficha.router)