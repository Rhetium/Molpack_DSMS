# app/services/ — Lógica de negocio

| Servicio | Responsabilidad |
|---|---|
| `KItemService` | CRUD de k-items, relaciones semánticas, grafo. Punto de entrada para toda mutación — invoca embedding y auditoría. |
| `FichaService` | Ciclo de vida de fichas técnicas: crear, actualizar, cambiar estado, nueva versión. Valida máquina de estados. |
| `MaterialService` | CRUD de materiales comerciales. |
| `EmbeddingService` | Genera embeddings 384D con `all-MiniLM-L6-v2` y los persiste en `kitem.embedding`. |
| `AnomaliaService` | Orquesta los 6 detectores de anomalías. Persiste resultados en `anomalia_registro`. |
| `MLAnomaliaService` | Isolation Forest: entrenamiento (`entrenar_modelos`) y predicción (`predecir`). Modelos en `app/ml_models/`. |
| `BusquedaSemanticaService` | Búsqueda coseno via pgvector, detección de duplicados, reindexación masiva. |
| `AuditoriaService` | Registra acciones en `kitem_auditoria`. Llamado desde `KItemService` y `FichaService`. |
| `AuthService` | Autenticación LDAP contra Active Directory; genera y valida JWT. |
| `ExportService` | Genera PDF (ReportLab) y Excel (openpyxl) de fichas técnicas. |

## Flujo de creación de ficha

```
FichaService.crear(datos)
  └─ KItemService.crear_kitem()          # persiste kitem + material_comercial (si nuevo)
       ├─ EmbeddingService.generar()     # embedding async, actualiza kitem.embedding
       ├─ AnomaliaService.analizar_ficha()
       │    ├─ Detector 1: z-score por campo
       │    ├─ Detector 2: unidades inconsistentes
       │    ├─ Detector 3: clasificación cruzada (coseno)
       │    ├─ Detector 4: duplicado semántico (coseno)
       │    ├─ Detector 5: perfil numérico cruzado
       │    └─ Detector 6: Isolation Forest multivariado
       └─ AuditoriaService.registrar()
```

## MLAnomaliaService

El modelo se entrena con `POST /anomalias/entrenar`. Genera:
- Un modelo **global** con todas las fichas disponibles.
- Un modelo **por categoría** para cada categoría con ≥ 5 fichas.

En predicción, usa el modelo de categoría si existe; si no, cae al global. Devuelve `None` si ningún modelo está disponible.

El pipeline interno es: `SimpleImputer(mean) → StandardScaler → IsolationForest(n_estimators=100)`. Columnas con menos del 30% de datos válidos se excluyen del modelo.
