# app/core/ — Configuración transversal

| Archivo | Contenido |
|---|---|
| `database.py` | Engine async de SQLAlchemy, `AsyncSessionLocal`, `Base` declarativa |
| `deps.py` | `get_session` — generador de sesión para inyección en routers |
| `security.py` | Generación/validación de JWT, hash de contraseñas |
| `utils.py` | `nombre_pais_a_iso` y utilidades menores |
| `dsms_constants.py` | Estados de ficha, K-Types, tipos de relación, acciones de auditoría, umbrales semánticos |
| `anomalia_constant.py` | Tipos de anomalía, severidades, estados de resolución, umbrales z-score y ML |

## Constantes clave

### Estados y máquina de estados (`dsms_constants.py`)

```python
TRANSACCIONES_PERMITIDAS = {
    "Borrador":   {"Preliminar", "Obsoleto"},
    "Preliminar": {"Vigente", "Obsoleto"},
    "Vigente":    {"Obsoleto"},
    "Obsoleto":   {"Revisión"},
    "Revisión":   {"Obsoleto", "Preliminar"},
}
```

### Umbrales de anomalía (`anomalia_constant.py`)

| Constante | Valor | Uso |
|---|---|---|
| `ZSCORE_ADVERTENCIA` | 2.0 | Campo numérico > 2σ |
| `ZSCORE_CRITICO` | 3.0 | Campo numérico > 3σ |
| `UMBRAL_DUPLICADO_SEMANTICO` | 0.90 | Similitud coseno para duplicado probable |
| `UMBRAL_DUPLICADO_CRITICO` | 0.95 | Similitud coseno para duplicado casi seguro |
| `ML_SCORE_CRITICO` | -0.15 | Score Isolation Forest para severidad crítica |
| `ML_SCORE_ADVERTENCIA` | -0.05 | Score Isolation Forest para advertencia |
