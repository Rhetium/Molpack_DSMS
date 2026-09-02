# =============================================================
# Molpack DSMS — imagen unica: API FastAPI + SPA React compilada.
# El backend sirve ambas cosas, por eso no hace falta nginx.
# =============================================================

# ---------- Etapa 1: compilar el frontend ----------
FROM node:20-slim AS frontend

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- Etapa 2: runtime ----------
FROM python:3.12-slim

# Node no llega hasta aca: solo se copia el resultado del build.
# Estas librerias son para compilar las dependencias que no publican
# rueda binaria (reportlab y su manejo de fuentes/imagenes).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libfreetype6-dev \
      libjpeg62-turbo-dev \
      zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/huggingface

# torch en su version CPU antes que el resto: la rueda por defecto arrastra
# ~2 GB de CUDA que este despliegue no usa.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# El modelo de embeddings queda dentro de la imagen: el contenedor no
# necesita salida a internet en el primer arranque.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app/ ./app/
COPY --from=frontend /build/dist ./frontend/dist

EXPOSE 8000

# --workers 1 es obligatorio: el rate limiter de login vive en memoria del
# proceso (docs/DESPLIEGUE_Y_SEGURIDAD.md, seccion 6.2). Con varios workers
# cada uno lleva su propio conteo y la proteccion anti-fuerza-bruta se debilita.
#
# --proxy-headers hace que request.client.host sea la IP real del usuario y no
# la de nginx, que es lo que cuenta el rate limiter. Solo se confia en la
# cabecera si el emisor esta en FORWARDED_ALLOW_IPS (por defecto 127.0.0.1):
# sin ese cerco, cualquiera enviaria un X-Forwarded-For inventado por intento
# fallido y no se bloquearia nunca. El valor lo fija docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
