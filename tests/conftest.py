"""
Configuración compartida de las pruebas unitarias.

Estos tests cubren **lógica pura** de dominio (máquina de estados,
validaciones, detectores de anomalías, helpers de exportación) sin tocar
la base de datos ni el modelo de embeddings.

Estrategia: los servicios se instancian con ``__new__`` para saltarse
``__init__`` (que requiere sesión de BD y carga sub-servicios pesados como
sentence-transformers). Los métodos bajo prueba solo dependen de sus
argumentos, no del estado del servicio.

Los objetos de dominio (FichaTecnica, MaterialComercial) se sustituyen por
stubs ``SimpleNamespace`` con solo los atributos que los métodos leen.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

# Raíz del repo en sys.path (redundante con pytest.ini pero robusto si se
# ejecuta pytest desde otro directorio de trabajo).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ──────────────────────────────────────────────────────────────────────────
# Factories de stubs de dominio
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture
def make_ficha():
    """Devuelve una factory de stubs de FichaTecnica.

    Solo expone atributos de datos (secciones JSONB + escalares). Los
    servicios acceden a ``ficha.caracteristicas``, ``ficha.empaque_estiba``,
    etc.; nada de ORM, relaciones ni sesión.
    """
    def _make(**kw):
        base = dict(
            id_ficha=None,
            id_material_corporativo=None,
            codigo_material_local=None,
            codigo_ficha_local=None,
            nombre_local_material=None,
            codigo_version="1.0",
            pais=None,
            caracteristicas=None,
            caracteristicas_contenido=None,
            empaque_estiba=None,
            microbiologia=None,
            manejo_disposicion=None,
        )
        base.update(kw)
        return SimpleNamespace(**base)
    return _make


@pytest.fixture
def make_material():
    """Devuelve una factory de stubs de MaterialComercial."""
    def _make(**kw):
        base = dict(
            id_material_corporativo=None,
            nombre_corporativo="Material de prueba",
            categoria=None,
            contenido=None,
            material_base=None,
            tipo_producto=None,
            estado_material="Activo",
        )
        base.update(kw)
        return SimpleNamespace(**base)
    return _make


# ──────────────────────────────────────────────────────────────────────────
# Instancias de servicios sin __init__ (sin BD ni embeddings)
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def ficha_service():
    from app.services.fichas_services import FichaService
    return FichaService.__new__(FichaService)


@pytest.fixture(scope="session")
def anomalia_service():
    from app.services.anomalia_service import AnomaliaService
    return AnomaliaService.__new__(AnomaliaService)


@pytest.fixture(scope="session")
def export_service():
    from app.services.export_service import ExportService
    return ExportService.__new__(ExportService)


# ──────────────────────────────────────────────────────────────────────────
# Sesión de BD simulada para tests de orquestación de servicio
# ──────────────────────────────────────────────────────────────────────────

class FakeResult:
    """Imita el objeto Result de SQLAlchemy para ``execute``.

    Solo implementa lo que usan los servicios: ``.scalars().first()`` y
    ``.scalars().all()``.
    """

    def __init__(self, rows=None):
        self._rows = list(rows) if rows is not None else []

    def scalars(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class FakeSession:
    """AsyncSession simulada. ``execute`` devuelve, en orden, los resultados
    provistos (lista de FakeResult). commit/refresh/flush son no-ops
    registrables; add acumula los objetos añadidos.
    """

    def __init__(self, results):
        self.execute = AsyncMock(side_effect=list(results))
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.flush = AsyncMock()
        self.added = []

    def add(self, obj):
        self.added.append(obj)


@pytest.fixture
def fake_result():
    """Expone la clase FakeResult para construir resultados de execute."""
    return FakeResult


@pytest.fixture
def make_ficha_service():
    """Factory de FichaService cableado con una FakeSession y colaboradores
    (kitem_service, auditoria, busqueda, anomalias) mockeados como AsyncMock.

    ``results`` es la lista ordenada de FakeResult que devolverá cada llamada
    a ``db_session.execute`` durante el flujo bajo prueba.
    """
    from app.services.fichas_services import FichaService

    def _make(results):
        svc = FichaService.__new__(FichaService)
        svc.db_session = FakeSession(results)
        svc.kitem_service = AsyncMock()
        svc.auditoria = AsyncMock()
        svc.busqueda = AsyncMock()
        svc.anomalias = AsyncMock()
        return svc

    return _make
