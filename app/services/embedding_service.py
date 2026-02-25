"""
Servicio de Embeddings — Generación de vectores semánticos para k-items.

Responsabilidades:
1. Construir el texto representativo de un k-item para embedding
2. Generar embeddings con sentence-transformers (local, sin costo de API)
3. Proveer interfaz abstracta para migrar a OpenAI/Cohere en el futuro

Modelo utilizado: all-MiniLM-L6-v2
- Dimensión: 384
- Velocidad: ~14,000 sentences/sec en CPU
- Calidad: Top-tier para su tamaño en MTEB benchmark
- Multilingüe: Buen soporte español/inglés (importante para Molpack)
- Licencia: Apache 2.0

Referencia DSMS (Nahshon et al., 2023):
- Los embeddings habilitan "Semantic Search" (Sección 2.3.4)
- Permiten descubrir k-items similares sin relaciones explícitas
- Base para detección de anomalías (Integration Level 4)
"""

import os
import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ============================================================
# Configuración del modelo
# ============================================================

# Modelo por defecto. Se puede sobreescribir con variable de entorno.
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL_NAME)

# Singleton del modelo (se carga una sola vez en memoria)
_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """
    Retorna el modelo de embeddings (singleton).
    Se carga en el primer llamado y se reutiliza.
    """
    global _model
    if _model is None:
        logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(
            f"Modelo cargado. Dimensión: {_model.get_sentence_embedding_dimension()}"
        )
    return _model


# ============================================================
# Construcción de texto para embedding
# ============================================================

def construir_texto_embedding(
    ktype: str,
    nombre: str,
    descripcion: str | None = None,
    metadata_extra: dict | None = None,
    campos_adicionales: dict | None = None,
) -> str:
    """
    Construye el texto representativo de un k-item para generar su embedding.

    La calidad del embedding depende directamente de la riqueza del texto
    de entrada. Esta función combina campos del k-item base con campos
    específicos del k-type para maximizar la representación semántica.

    Estructura del texto generado:
        [KTYPE] nombre_del_kitem
        descripción del k-item
        campo1: valor1 | campo2: valor2 | ...

    Args:
        ktype: Tipo de conocimiento (MaterialComercial, FichaTecnica, etc.)
        nombre: Nombre del k-item
        descripcion: Descripción/resumen del k-item
        metadata_extra: Metadata JSONB extensible del k-item base
        campos_adicionales: Campos específicos del k-type (categoría, tipo_producto, etc.)

    Returns:
        Texto concatenado optimizado para embedding.
    """
    partes: list[str] = []

    # Línea 1: Tipo + Nombre (siempre presente)
    partes.append(f"[{ktype}] {nombre}")

    # Línea 2: Descripción (si existe)
    if descripcion:
        partes.append(descripcion)

    # Línea 3: Campos adicionales del k-type (categoría, tipo_producto, etc.)
    if campos_adicionales:
        pares = []
        for clave, valor in campos_adicionales.items():
            if valor is not None and str(valor).strip():
                # Limpiar nombres de campo para legibilidad
                clave_limpia = clave.replace("_", " ")
                pares.append(f"{clave_limpia}: {valor}")
        if pares:
            partes.append(" | ".join(pares))

    # Línea 4: Metadata extra relevante (si existe)
    if metadata_extra:
        # Solo incluir claves que aporten información semántica
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


# ============================================================
# Generación de embeddings
# ============================================================

def generar_embedding(texto: str) -> list[float]:
    """
    Genera un vector embedding a partir de un texto.

    Args:
        texto: Texto representativo del k-item.

    Returns:
        Lista de floats con el embedding (dimensión 384).
    """
    modelo = get_embedding_model()
    embedding = modelo.encode(texto, normalize_embeddings=True)
    return embedding.tolist()


def generar_embeddings_batch(textos: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Genera embeddings en lote para múltiples textos.

    Útil para:
    - Migración inicial (generar embeddings para k-items existentes)
    - Reindexación masiva si se cambia el modelo

    Args:
        textos: Lista de textos a procesar.
        batch_size: Tamaño del batch (64 es óptimo para CPU).

    Returns:
        Lista de embeddings (cada uno es lista de floats).
    """
    modelo = get_embedding_model()
    embeddings = modelo.encode(
        textos,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=len(textos) > 100,
    )
    return [emb.tolist() for emb in embeddings]


def calcular_similitud_coseno(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Calcula la similitud coseno entre dos vectores.

    Útil para comparaciones directas fuera de PostgreSQL
    (ej: en la lógica de detección de anomalías).

    Returns:
        Float entre -1 y 1 (1 = idénticos, 0 = ortogonales).
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))