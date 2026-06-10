import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, FileSpreadsheet, FileText, X } from 'lucide-react';
import api from '../../../lib/api';

const coloresEstado = {
  Borrador:   'bg-gray-100 text-gray-600',
  Preliminar: 'bg-yellow-100 text-yellow-700',
  Vigente:    'bg-green-100 text-green-700',
  Obsoleto:   'bg-red-100 text-red-700',
  'Revisión': 'bg-orange-100 text-orange-700',
};

function useDebouncedValue(value, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function FichasPage() {
  const [fichas,       setFichas]       = useState([]);
  const [cargando,     setCargando]     = useState(true);
  const [busqueda,     setBusqueda]     = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');

  const textoBuscado = useDebouncedValue(busqueda);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const params = {};
      if (textoBuscado.trim()) params.texto = textoBuscado.trim();
      if (filtroEstado)        params.estado_ficha = filtroEstado;

      const res = await api.get('/ficha/buscar', { params });
      setFichas(res.data);
    } catch (error) {
      console.error('Error cargando fichas:', error);
    } finally {
      setCargando(false);
    }
  }, [textoBuscado, filtroEstado]);

  useEffect(() => { cargar(); }, [cargar]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fichas Técnicas</h1>
          <p className="text-sm text-gray-500 mt-1">Gestión de fichas técnicas estandarizadas</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              try {
                const res = await api.get('/dsms/export/fichas/excel', { responseType: 'blob' });
                const url = globalThis.URL.createObjectURL(new Blob([res.data]));
                const link = document.createElement('a');
                link.href = url;
                link.download = 'fichas_tecnicas.xlsx';
                link.click();
                globalThis.URL.revokeObjectURL(url);
              } catch {
                alert('Error al exportar Excel');
              }
            }}
            className="flex items-center gap-2 border border-[#044926] text-[#044926] px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926]/5 transition-colors"
          >
            <FileSpreadsheet size={16} /> Exportar Excel
          </button>
          <Link
            to="/fichas/nueva"
            className="flex items-center gap-2 bg-[#29b34b] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926] transition-colors"
          >
            <Plus size={16} /> Nueva Ficha
          </Link>
        </div>
      </div>

      {/* Búsqueda y filtros */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <div className="relative flex-1 min-w-60">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por código, material, nombre local, país, categoría…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-9 pr-9 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
          />
          {busqueda && (
            <button
              onClick={() => setBusqueda('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        >
          <option value="">Todos los estados</option>
          <option value="Borrador">Borrador</option>
          <option value="Preliminar">Preliminar</option>
          <option value="Vigente">Vigente</option>
          <option value="Obsoleto">Obsoleto</option>
          <option value="Revisión">Revisión</option>
        </select>
        {(busqueda || filtroEstado) && (
          <span className="text-xs text-gray-500">
            {fichas.length} {fichas.length === 1 ? 'resultado' : 'resultados'}
          </span>
        )}
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {cargando && (
          <div className="px-6 py-12 text-center text-sm text-gray-500">Cargando fichas…</div>
        )}
        {!cargando && fichas.length === 0 && (
          <div className="px-6 py-12 text-center">
            <FileText size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">
              {busqueda ? `Sin resultados para "${busqueda}"` : 'No hay fichas registradas'}
            </p>
          </div>
        )}
        {!cargando && fichas.length > 0 && (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Código</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Material</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">País</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Ver.</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Fecha</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {fichas.map((ficha) => (
                <tr key={ficha.id_ficha} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900">{ficha.codigo_ficha_local}</p>
                    <p className="text-xs text-gray-400">{ficha.codigo_material_local}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm text-gray-900">{ficha.material?.nombre_corporativo ?? '—'}</p>
                    <p className="text-xs text-gray-400">{ficha.material?.categoria ?? ''}</p>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{ficha.pais}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">v{ficha.codigo_version}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      coloresEstado[ficha.estado_ficha] || 'bg-gray-100 text-gray-600'
                    }`}>
                      {ficha.estado_ficha}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {ficha.fecha_registro
                      ? new Date(ficha.fecha_registro).toLocaleDateString('es')
                      : '—'}
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/fichas/${ficha.id_ficha}`}
                      className="text-sm text-[#044926] hover:text-[#29b34b] font-medium"
                    >
                      Ver detalle
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
