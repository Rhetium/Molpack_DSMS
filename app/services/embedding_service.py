import os
import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL_NAME)


_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(
            f"Modelo cargado. Dimensión: {_model.get_sentence_embedding_dimension()}"
        )
    return _model


def construir_texto_embedding(
    ktype: str,
    nombre: str,
    descripcion: str | None = None,
    metadata_extra: dict | None = None,
    campos_adicionales: dict | None = None,
) -> str:
    partes: list[str] = []


    partes.append(f"[{ktype}] {nombre}")


    if descripcion:
        partes.append(descripcion)

    if campos_adicionales:
        pares = []
        for clave, valor in campos_adicionales.items():
            if valor is not None and str(valor).strip():

                clave_limpia = clave.replace("_", " ")
                pares.append(f"{clave_limpia}: {valor}")
        if pares:
            partes.append(" | ".join(pares))

    if metadata_extra:

        claves_utiles = {"tags", "keywords", "sector", "aplicacion", "notas"}
        pares_meta = []
        for clave, valor in metadata_extra.items():
            if clave.lower() in claves_utiles and valor:
                if isinstance(valor, list):
                    pares_meta.append(f"{clave}: {', '.join(str(v) for v in valor)}")
                else:
                    pares_meta.append(f"{clave}: {valor}")
        if pares_meta:
            partes.append(" | ".join(pares_meta))

    texto = "\n".join(partes)
    logger.debug(f"Texto para embedding ({len(texto)} chars): {texto[:200]}...")
    return texto


def generar_embedding(texto: str) -> list[float]:
    modelo = get_embedding_model()
    embedding = modelo.encode(texto, normalize_embeddings=True)
    return embedding.tolist()


def generar_embeddings_batch(textos: list[str], batch_size: int = 64) -> list[list[float]]:
    modelo = get_embedding_model()
    embeddings = modelo.encode(
        textos,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=len(textos) > 100,
    )
    return [emb.tolist() for emb in embeddings]


def calcular_similitud_coseno(vec_a: list[float], vec_b: list[float]) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))