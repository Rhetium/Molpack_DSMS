import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, FileText, FileSpreadsheet } from 'lucide-react';
import api from '../../../lib/api';

const coloresEstado = {
  Borrador: 'bg-gray-100 text-gray-600',
  Preliminar: 'bg-yellow-100 text-yellow-700',
  Vigente: 'bg-green-100 text-green-700',
  Obsoleto: 'bg-red-100 text-red-700',
  'Revisión': 'bg-orange-100 text-orange-700',
};

export default function FichasPage() {
  const [fichas, setFichas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');

  useEffect(() => {
    async function cargar() {
      try {
        const res = await api.get('/ficha');
        setFichas(res.data);
      } catch (error) {
        console.error('Error cargando fichas:', error);
      } finally {
        setCargando(false);
      }
    }
    cargar();
  }, []);

  const fichasFiltradas = fichas.filter((f) => {
    const coincideBusqueda =
      (f.codigo_ficha_local || '').toLowerCase().includes(busqueda.toLowerCase()) ||
      (f.pais || '').toLowerCase().includes(busqueda.toLowerCase());
    const coincideEstado = !filtroEstado || f.estado_ficha === filtroEstado;
    return coincideBusqueda && coincideEstado;
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fichas Técnicas</h1>
          <p className="text-sm text-gray-500 mt-1">
            Gestión de fichas técnicas estandarizadas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              try {
                const res = await api.get('/dsms/export/fichas/excel', { responseType: 'blob' });
                const url = window.URL.createObjectURL(new Blob([res.data]));
                const link = document.createElement('a');
                link.href = url;
                link.download = 'fichas_tecnicas.xlsx';
                link.click();
                window.URL.revokeObjectURL(url);
              } catch (err) {
                alert('Error al exportar Excel');
              }
            }}
            className="flex items-center gap-2 border border-[#044926] text-[#044926] px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926]/5 transition-colors"
          >
            <FileSpreadsheet size={16} />
            Exportar Excel
          </button>
          <Link
            to="/fichas/nueva"
            className="flex items-center gap-2 bg-[#29b34b] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926] transition-colors"
          >
            <Plus size={16} />
            Nueva Ficha
          </Link>
        </div>
      </div>

      {/* Búsqueda y filtros */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por código o país..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b] focus:border-transparent"
          />
        </div>
        <select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos los estados</option>
          <option value="Borrador">Borrador</option>
          <option value="Preliminar">Preliminar</option>
          <option value="Vigente">Vigente</option>
          <option value="Obsoleto">Obsoleto</option>
          <option value="Revisión">Revisión</option>
        </select>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {cargando ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Cargando fichas...
          </div>
        ) : fichasFiltradas.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <FileText size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">
              {busqueda ? 'No se encontraron fichas' : 'No hay fichas registradas'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Código
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Versión
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  País
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Estado
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Creador
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Fecha
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {fichasFiltradas.map((ficha) => (
                <tr key={ficha.id_ficha} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900">
                      {ficha.codigo_ficha_local}
                    </p>
                    <p className="text-xs text-gray-400">{ficha.codigo_material_local}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      v{ficha.codigo_version}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">{ficha.pais}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      coloresEstado[ficha.estado_ficha] || 'bg-gray-100 text-gray-600'
                    }`}>
                      {ficha.estado_ficha}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">{ficha.usuario_creador}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-500">
                      {new Date(ficha.fecha_registro).toLocaleDateString('es')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/fichas/${ficha.id_ficha}`}
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium"
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