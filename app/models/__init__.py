"""
Registro central de modelos del Dataspace.
Importar todos los modelos aquí asegura que SQLAlchemy/Alembic
los detecte para migraciones y creación de tablas.
"""

from app.models.kitem import KItem
from app.models.kitem_relacion import KItemRelacion
from app.models.kitem_auditoria import KItemAuditoria
from app.models.material import MaterialComercial
from app.models.ficha import FichaTecnica

__all__ = [
    "KItem",
    "KItemRelacion",
    "KItemAuditoria",
    "MaterialComercial",
    "FichaTecnica",
]