# app/ml_models/ — Modelos de detección de anomalías

Los archivos `.pkl` de esta carpeta son generados en runtime por `MLAnomaliaService.entrenar_modelos()` y no se versionan en git.

## Nomenclatura

```
isolation_forest_global.pkl          # modelo entrenado con todas las fichas
isolation_forest_{categoria}.pkl     # modelo por categoría (ej: isolation_forest_Separador.pkl)
```

## Ciclo de vida

1. **Entrenar**: `POST /anomalias/entrenar` — lee todas las fichas de la BD, entrena y guarda los `.pkl`.
2. **Predecir**: Se llama automáticamente al crear o actualizar una ficha. Si no existe ningún modelo, el detector ML se omite silenciosamente.
3. **Reentrenar**: Ejecutar `/anomalias/entrenar` cada vez que se acumulen fichas nuevas.

## Cuándo reentrenar

- Al agregar un lote de fichas nuevas.
- Cuando una categoría alcanza 5 fichas por primera vez (habilita modelo específico).
- Si cambia el conjunto de campos numéricos en `anomalia_constant.py::CAMPOS_CARACTERISTICAS`.

## Parámetros del modelo

| Parámetro | Valor | Justificación |
|---|---|---|
| `n_estimators` | 100 | Estable para corpus pequeño |
| `contamination` | `clip(1/n, 0.05, 0.10)` | Dinámico: entre 5% y 10% según tamaño del dataset |
| `random_state` | 42 | Reproducibilidad |
| Imputer | `SimpleImputer(strategy="mean")` | Rellena campos faltantes con la media de la columna |
| Columnas activas | ≥ 30% datos válidos | Excluye campos casi siempre vacíos |
