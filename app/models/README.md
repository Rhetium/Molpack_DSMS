# app/models/ — Modelos ORM

Todos los modelos usan SQLAlchemy 2.0 con `mapped_column` y `Mapped[T]`.

| Modelo | Tabla | Descripción |
|---|---|---|
| `KItem` | `kitem` | Supertipo universal. UUID PK, ktype, nombre, embedding VECTOR(384), estado |
| `MaterialComercial` | `material_comercial` | Extiende KItem (FK cascade). Datos corporativos del material |
| `FichaTecnica` | `ficha_tecnica` | Extiende KItem (FK cascade). JSONB para secciones técnicas |
| `KItemRelacion` | `kitem_relacion` | Arista dirigida del grafo: source_id → target_id, tipo_relacion |
| `KItemAuditoria` | `kitem_auditoria` | Log inmutable de acciones sobre k-items |
| `AnomaliaRegistro` | `anomalia_registro` | Repositorio histórico de anomalías detectadas |

## Patrón KItem

`MaterialComercial` y `FichaTecnica` no tienen UUID propio: su PK es el mismo UUID del `KItem` padre (FK + PK a la vez). Al borrar el `KItem`, el registro hijo se elimina en cascada.

```python
class MaterialComercial(Base):
    id_material_corporativo: Mapped[UUID] = mapped_column(
        ForeignKey("kitem.id", ondelete="CASCADE"), primary_key=True
    )
```

## JSONB en FichaTecnica

Las secciones técnicas se almacenan como JSONB con un esquema flexible:

| Columna | Contenido |
|---|---|
| `caracteristicas` | Dimensiones, peso, ruptura, deflexión, absorción |
| `caracteristicas_contenido` | Geometría del contenido (pilar/alvéolo, cavidad) |
| `empaque_estiba` | Empaque, dimensiones, estiba |
| `microbiologia` | Parámetros microbiológicos y metales pesados |
| `manejo_disposicion` | Almacenamiento, transporte, vida útil |

Los campos NC (No Calculado) se persisten como `{campo_nc: true}` sin el `_valor` correspondiente.
