"""
Servicio de Machine Learning para detección de anomalías multivariadas.

Implementa Isolation Forest sobre el vector numérico combinado de cada ficha.
A diferencia de los detectores estadísticos (que analizan campo por campo),
este detector considera la combinación de todos los campos en conjunto,
capturando patrones anómalos que no se detectan de forma univariada.

Ejemplo: largo=30cm, ancho=40cm, alto=3cm pueden ser normales
individualmente, pero su combinación puede ser inusual para separadores.

Ciclo de vida:
  1. POST /anomalias/entrenar  → llama entrenar_modelos()
  2. analizar_ficha()          → llama predecir()

Modelos persistidos en app/ml_models/ como archivos .pkl (joblib).
Se entrena un modelo global con todas las fichas y modelos por categoría
cuando esa categoría alcanza MIN_MUESTRAS_ML fichas.
"""

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
from app.core.anomalia_constant import (
    CAMPOS_CARACTERISTICAS,
    CAMPOS_CONTENIDO,
    CAMPOS_EMPAQUE,
    MIN_MUESTRAS_ML,
    MODELO_GLOBAL,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "ml_models"
MODELS_DIR.mkdir(exist_ok=True)

# Vector de longitud fija: todos los campos numéricos posibles en fichas
ALL_NUMERIC_FIELDS: list[str] = [
    campo_valor
    for campo_valor, _, _ in CAMPOS_CARACTERISTICAS + CAMPOS_CONTENIDO + CAMPOS_EMPAQUE
]


# ─────────────────────────────────────────────────────────────
# Helpers de extracción de features
# ─────────────────────────────────────────────────────────────

def _extraer_vector(ficha: FichaTecnica) -> list[float | None]:
    """
    Extrae un vector de longitud fija desde los JSONB de la ficha.
    Devuelve None en posiciones sin dato o marcadas N/C.
    """
    mapa: dict[str, float | None] = {}

    secciones = [
        (ficha.caracteristicas, CAMPOS_CARACTERISTICAS),
        (ficha.caracteristicas_contenido, CAMPOS_CONTENIDO),
        (ficha.empaque_estiba, CAMPOS_EMPAQUE),
    ]
    for datos, campos in secciones:
        if not datos:
            continue
        for campo_valor, _, _ in campos:
            nc_key = campo_valor.removesuffix("_valor") + "_nc"
            if datos.get(nc_key):
                mapa[campo_valor] = None
                continue
            valor = datos.get(campo_valor)
            if valor is not None and isinstance(valor, (int, float)):
                mapa[campo_valor] = float(valor)

    return [mapa.get(campo) for campo in ALL_NUMERIC_FIELDS]


def _construir_matriz(fichas: list[FichaTecnica]) -> np.ndarray:
    """Shape: (n_fichas, n_campos_totales). NaN donde no hay dato."""
    filas = [
        [np.nan if v is None else v for v in _extraer_vector(f)]
        for f in fichas
    ]
    return np.array(filas, dtype=float)


def _ruta_modelo(nombre: str) -> Path:
    safe = nombre.lower().replace(" ", "_").replace("/", "_")
    return MODELS_DIR / f"isolation_forest_{safe}.pkl"


def _contamination(n: int) -> float:
    """Entre 5% y 10%, ajustado inversamente al tamaño del set."""
    return float(np.clip(1.0 / n, 0.05, 0.10))


def _construir_pipeline(contamination: float) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler()),
        ("modelo", IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        )),
    ])


# ─────────────────────────────────────────────────────────────
# Servicio principal
# ─────────────────────────────────────────────────────────────

class MLAnomaliaService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        # Caché en memoria para evitar I/O repetido por request
        self._cache: dict[str, dict] = {}

    # ══════════════════════════════════════════════════
    # ENTRENAMIENTO
    # ══════════════════════════════════════════════════

    async def entrenar_modelos(self) -> dict:
        """
        Entrena modelos Isolation Forest con todas las fichas en BD.

        - Siempre entrena un modelo global.
        - Entrena modelo por categoría si esa categoría tiene >= MIN_MUESTRAS_ML.

        Returns:
            dict con estadísticas: modelos entrenados, categorías sin datos, errores.
        """
        result = await self.db.execute(
            select(FichaTecnica, MaterialComercial).join(
                MaterialComercial,
                FichaTecnica.id_material_corporativo
                == MaterialComercial.id_material_corporativo,
            )
        )
        filas = result.all()

        if not filas:
            return {"error": "No hay fichas en la base de datos para entrenar"}

        # Separar por categoría
        por_categoria: dict[str, list[FichaTecnica]] = {}
        todas: list[FichaTecnica] = []

        for ficha, material in filas:
            cat = (material.categoria or "sin_categoria").strip()
            por_categoria.setdefault(cat, []).append(ficha)
            todas.append(ficha)

        entrenados: list[dict] = []
        sin_datos: list[dict] = []

        # Modelo global
        stats = self._entrenar_y_guardar(todas, MODELO_GLOBAL)
        if stats:
            entrenados.append(stats)
        else:
            return {"error": "No se pudo extraer features de ninguna ficha"}

        # Modelos por categoría
        for categoria, fichas_cat in sorted(por_categoria.items()):
            if len(fichas_cat) < MIN_MUESTRAS_ML:
                sin_datos.append({
                    "categoria": categoria,
                    "n_fichas": len(fichas_cat),
                    "minimo_requerido": MIN_MUESTRAS_ML,
                })
                continue
            stats_cat = self._entrenar_y_guardar(fichas_cat, categoria)
            if stats_cat:
                entrenados.append(stats_cat)

        # Invalidar caché tras reentrenamiento
        self._cache.clear()

        return {
            "total_fichas_procesadas": len(todas),
            "modelos_entrenados": entrenados,
            "categorias_sin_datos_suficientes": sin_datos,
        }

    def _entrenar_y_guardar(
        self, fichas: list[FichaTecnica], nombre: str
    ) -> dict | None:
        """
        Entrena un pipeline para el conjunto dado y lo persiste en disco.

        Solo usa columnas donde al menos el 30% de fichas tienen dato,
        para evitar que el imputer trabaje sobre columnas vacías.
        """
        if not fichas:
            return None

        X = _construir_matriz(fichas)

        # Máscara: columnas con al menos 30% de valores no-NaN
        fraccion_valida = np.mean(~np.isnan(X), axis=0)
        mascara_cols = fraccion_valida >= 0.30

        if not mascara_cols.any():
            logger.warning(f"Modelo '{nombre}': ninguna columna tiene suficientes datos")
            return None

        X_filtrado = X[:, mascara_cols]
        campos_usados = [ALL_NUMERIC_FIELDS[i] for i, ok in enumerate(mascara_cols) if ok]
        n = len(fichas)
        cont = _contamination(n)

        pipeline = _construir_pipeline(cont)
        pipeline.fit(X_filtrado)

        datos_modelo = {
            "pipeline": pipeline,
            "mascara_cols": mascara_cols,
            "campos_usados": campos_usados,
            "n_entrenamiento": n,
            "contamination": cont,
        }
        joblib.dump(datos_modelo, _ruta_modelo(nombre))

        logger.info(
            f"[ML] Modelo '{nombre}': {n} fichas, "
            f"{len(campos_usados)} campos, contamination={cont:.3f}"
        )
        return {
            "nombre": nombre,
            "n_fichas": n,
            "campos_usados": campos_usados,
            "contamination": round(cont, 4),
        }

    # ══════════════════════════════════════════════════
    # PREDICCIÓN
    # ══════════════════════════════════════════════════

    def predecir(
        self,
        ficha: FichaTecnica,
        categoria: str | None = None,
    ) -> dict | None:
        """
        Evalúa si una ficha es anómala según los modelos ML.

        Prioridad: modelo de categoría → modelo global → None (sin modelo).

        Returns:
            dict con:
              - es_anomalo (bool)
              - score (float, más negativo = más anómalo)
              - modelo_usado (str)
              - campos_analizados (list[str])
              - n_entrenamiento (int)
            O None si no hay modelos disponibles.
        """
        datos_modelo = None
        modelo_usado = None

        if categoria:
            datos_modelo = self._cargar_modelo(categoria)
            if datos_modelo:
                modelo_usado = categoria

        if datos_modelo is None:
            datos_modelo = self._cargar_modelo(MODELO_GLOBAL)
            if datos_modelo:
                modelo_usado = MODELO_GLOBAL

        if datos_modelo is None:
            return None  # Sin modelo entrenado: no se puede predecir

        # Construir vector y aplicar la misma máscara de columnas
        vector = _extraer_vector(ficha)
        x = np.array(
            [[np.nan if v is None else v for v in vector]], dtype=float
        )
        x_filtrado = x[:, datos_modelo["mascara_cols"]]

        pipeline: Pipeline = datos_modelo["pipeline"]
        prediccion = pipeline.predict(x_filtrado)[0]       # 1=normal, -1=anómalo
        score = float(pipeline.decision_function(x_filtrado)[0])

        return {
            # bool nativo: np.bool_ no es subclase de bool y revienta la
            # serialización JSON de FastAPI (endpoint /anomalias/debug)
            "es_anomalo": bool(prediccion == -1),
            "score": score,
            "modelo_usado": modelo_usado,
            "campos_analizados": datos_modelo["campos_usados"],
            "n_entrenamiento": datos_modelo["n_entrenamiento"],
        }

    def modelo_disponible(self, categoria: str | None = None) -> bool:
        """True si existe algún modelo (categoría o global) para predecir."""
        if categoria and _ruta_modelo(categoria).exists():
            return True
        return _ruta_modelo(MODELO_GLOBAL).exists()

    def _cargar_modelo(self, nombre: str) -> dict | None:
        if nombre in self._cache:
            return self._cache[nombre]
        path = _ruta_modelo(nombre)
        if not path.exists():
            return None
        try:
            datos = joblib.load(path)
            self._cache[nombre] = datos
            return datos
        except Exception as e:
            logger.warning(f"[ML] Error cargando modelo '{nombre}': {e}")
            return None
