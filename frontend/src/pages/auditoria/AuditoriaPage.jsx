import { useEffect, useState } from 'react';
import { History, Filter, ChevronLeft, ChevronRight, X, Eye } from 'lucide-react';
import api from '../../../lib/api';

const POR_PAGINA = 25;

// Acciones tal como las guarda el backend (dsms_constants.py)
const ACCIONES = [
  { valor: 'CREACION', label: 'Creación' },
  { valor: 'MODIFICACION', label: 'Modificación' },
  { valor: 'CAMBIO_ESTADO', label: 'Cambio de Estado' },
  { valor: 'NUEVA_VERSION', label: 'Nueva Versión' },
  { valor: 'RELACION_CREADA', label: 'Relación Creada' },
  { valor: 'RELACION_ELIMINADA', label: 'Relación Eliminada' },
];

const coloresAccion = {
  CREACION: 'bg-green-100 text-green-700',
  MODIFICACION: 'bg-blue-100 text-blue-700',
  CAMBIO_ESTADO: 'bg-purple-100 text-purple-700',
  NUEVA_VERSION: 'bg-indigo-100 text-indigo-700',
  RELACION_CREADA: 'bg-teal-100 text-teal-700',
  RELACION_ELIMINADA: 'bg-red-100 text-red-700',
};

export default function AuditoriaPage() {
  const [actividad, setActividad] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtroKtype, setFiltroKtype] = useState('');
  const [filtroAccion, setFiltroAccion] = useState('');
  const [pagina, setPagina] = useState(0);
  const [hayMas, setHayMas] = useState(false);
  const [detalleEvento, setDetalleEvento] = useState(null);

  async function cargar() {
    setCargando(true);
    try {
      const params = {
        limite: POR_PAGINA + 1, // Pedir 1 extra para saber si hay más
        offset: pagina * POR_PAGINA,
      };
      if (filtroKtype) params.ktype = filtroKtype;
      if (filtroAccion) params.accion = filtroAccion;

      const res = await api.get('/dsms/auditoria/actividad', { params });
      const datos = res.data;

      if (datos.length > POR_PAGINA) {
        setHayMas(true);
        setActividad(datos.slice(0, POR_PAGINA));
      } else {
        setHayMas(false);
        setActividad(datos);
      }
    } catch (error) {
      console.error('Error cargando auditoría:', error);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
  }, [filtroKtype, filtroAccion, pagina]);

  // Reset página al cambiar filtros
  function handleFiltroKtype(valor) {
    setFiltroKtype(valor);
    setPagina(0);
  }

  function handleFiltroAccion(valor) {
    setFiltroAccion(valor);
    setPagina(0);
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Auditoría</h1>
        <p className="text-sm text-gray-500 mt-1">
          Trazabilidad completa de acciones en el Dataspace
        </p>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-400" />
          <span className="text-sm text-gray-500">Filtros:</span>
        </div>
        <select
          value={filtroKtype}
          onChange={(e) => handleFiltroKtype(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        >
          <option value="">Todos los tipos</option>
          <option value="MaterialComercial">Materiales</option>
          <option value="FichaTecnica">Fichas Técnicas</option>
        </select>
        <select
          value={filtroAccion}
          onChange={(e) => handleFiltroAccion(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        >
          <option value="">Todas las acciones</option>
          {ACCIONES.map((a) => (
            <option key={a.valor} value={a.valor}>{a.label}</option>
          ))}
        </select>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl border border-gray-200">
        {cargando ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Cargando auditoría...
          </div>
        ) : actividad.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <History size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">No hay registros de auditoría</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {actividad.map((evento) => (
              <div key={evento.id} className="px-6 py-4 flex items-start gap-4 hover:bg-gray-50">
                <div className="mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-sm font-medium text-gray-900">
                      {evento.usuario}
                    </span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      coloresAccion[evento.accion] || 'bg-gray-100 text-gray-600'
                    }`}>
                      {formatearAccion(evento.accion)}
                    </span>
                    <span className="text-xs bg-gray-50 text-gray-500 px-2 py-0.5 rounded">
                      {evento.ktype}
                    </span>
                    {evento.estado_anterior && evento.estado_nuevo && (
                      <span className="text-xs text-gray-400">
                        {evento.estado_anterior} → {evento.estado_nuevo}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 truncate">
                    ID: {evento.kitem_id}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(evento.fecha).toLocaleString('es')}
                  </span>
                  <button
                    onClick={() => setDetalleEvento(evento)}
                    className="p-1.5 text-gray-400 hover:text-[#044926] hover:bg-green-50 rounded-lg transition-colors"
                    title="Ver detalle"
                  >
                    <Eye size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Paginación */}
        {!cargando && actividad.length > 0 && (
          <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
            <p className="text-xs text-gray-500">
              Mostrando {pagina * POR_PAGINA + 1}–{pagina * POR_PAGINA + actividad.length} registros
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(0, p - 1))}
                disabled={pagina === 0}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft size={14} />
                Anterior
              </button>
              <span className="text-xs text-gray-500 px-2">
                Página {pagina + 1}
              </span>
              <button
                onClick={() => setPagina((p) => p + 1)}
                disabled={!hayMas}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-30 transition-colors"
              >
                Siguiente
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal de detalle */}
      {detalleEvento && (
        <ModalDetalle evento={detalleEvento} onCerrar={() => setDetalleEvento(null)} />
      )}
    </div>
  );
}

/* ========== Modal de Detalle ========== */
function ModalDetalle({ evento, onCerrar }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50" onClick={onCerrar} />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Detalle de Auditoría</h3>
          <button
            onClick={onCerrar}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <X size={20} />
          </button>
        </div>

        {/* Contenido */}
        <div className="px-6 py-4 overflow-y-auto max-h-[60vh] space-y-4">
          <FilaDetalle label="ID Evento" valor={evento.id} />
          <FilaDetalle label="Usuario" valor={evento.usuario} />
          <FilaDetalle label="Acción" valor={formatearAccion(evento.accion)} />
          <FilaDetalle label="Tipo" valor={evento.ktype} />
          <FilaDetalle label="K-Item ID" valor={evento.kitem_id} />
          <FilaDetalle label="Fecha" valor={new Date(evento.fecha).toLocaleString('es')} />

          {evento.estado_anterior && (
            <FilaDetalle label="Estado Anterior" valor={evento.estado_anterior} />
          )}
          {evento.estado_nuevo && (
            <FilaDetalle label="Estado Nuevo" valor={evento.estado_nuevo} />
          )}

          {/* Detalles JSONB */}
          {evento.detalles && Object.keys(evento.detalles).length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-500 mb-2">Detalles</p>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                {Object.entries(evento.detalles).map(([clave, valor]) => (
                  <div key={clave}>
                    <span className="text-xs font-medium text-gray-500">
                      {formatearNombre(clave)}:
                    </span>
                    <div className="text-sm text-gray-900 mt-0.5">
                      {renderValorDetalle(clave, valor)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 flex justify-end">
          <button
            onClick={onCerrar}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

function FilaDetalle({ label, valor }) {
  return (
    <div className="flex items-start">
      <span className="w-32 text-sm font-medium text-gray-500 shrink-0">{label}</span>
      <span className="text-sm text-gray-900 break-all">{String(valor ?? '—')}</span>
    </div>
  );
}

function renderValorDetalle(clave, valor) {
  if (valor === null || valor === undefined) return '—';

  // Campos que son objetos de cambios (anterior/nuevo)
  if (typeof valor === 'object' && !Array.isArray(valor) && valor.anterior !== undefined) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="bg-red-50 text-red-600 px-2 py-0.5 rounded">{String(valor.anterior ?? 'vacío')}</span>
        <span className="text-gray-400">→</span>
        <span className="bg-green-50 text-green-600 px-2 py-0.5 rounded">{String(valor.nuevo ?? 'vacío')}</span>
      </div>
    );
  }

  // Objeto de cambios con múltiples campos
  if (clave === 'cambios' && typeof valor === 'object') {
    return (
      <div className="space-y-1.5 mt-1">
        {Object.entries(valor).map(([campo, cambio]) => (
          <div key={campo} className="flex items-center gap-2 text-xs">
            <span className="font-medium text-gray-600 w-28">{formatearNombre(campo)}</span>
            {typeof cambio === 'object' && cambio.anterior !== undefined ? (
              <>
                <span className="bg-red-50 text-red-600 px-2 py-0.5 rounded">{String(cambio.anterior ?? 'vacío')}</span>
                <span className="text-gray-400">→</span>
                <span className="bg-green-50 text-green-600 px-2 py-0.5 rounded">{String(cambio.nuevo ?? 'vacío')}</span>
              </>
            ) : (
              <span>{JSON.stringify(cambio)}</span>
            )}
          </div>
        ))}
      </div>
    );
  }

  // Arrays (campos_modificados, etc.)
  if (Array.isArray(valor)) {
    return valor.map((v) => formatearNombre(String(v))).join(', ');
  }

  // Objetos genéricos
  if (typeof valor === 'object') {
    return JSON.stringify(valor, null, 2);
  }

  return String(valor);
}

/* ========== Helpers ========== */
function formatearAccion(accion) {
  const mapa = {
    CREACION: 'Creación',
    MODIFICACION: 'Modificación',
    CAMBIO_ESTADO: 'Cambio de Estado',
    NUEVA_VERSION: 'Nueva Versión',
    RELACION_CREADA: 'Relación Creada',
    RELACION_ELIMINADA: 'Relación Eliminada',
  };
  return mapa[accion] || accion;
}

function formatearNombre(campo) {
  return campo.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}