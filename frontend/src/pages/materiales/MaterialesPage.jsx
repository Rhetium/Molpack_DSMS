import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Package } from 'lucide-react';
import api from '../../../lib/api';

export default function MaterialesPage() {
  const [materiales, setMateriales] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [busqueda, setBusqueda] = useState('');

  useEffect(() => {
    async function cargar() {
      try {
        const res = await api.get('/material');
        setMateriales(res.data);
      } catch (error) {
        console.error('Error cargando materiales:', error);
      } finally {
        setCargando(false);
      }
    }
    cargar();
  }, []);

  const materialesFiltrados = materiales.filter((m) =>
    m.nombre_corporativo.toLowerCase().includes(busqueda.toLowerCase()) ||
    (m.categoria || '').toLowerCase().includes(busqueda.toLowerCase())
  );

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Materiales Comerciales</h1>
          <p className="text-sm text-gray-500 mt-1">
            Gestión de materiales del catálogo corporativo
          </p>
        </div>
        <Link
          to="/materiales/nuevo"
          className="flex items-center gap-2 bg-[#29b34b] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926] transition-colors"
        >
          <Plus size={16} />
          Nuevo Material
        </Link>
      </div>

      {/* Barra de búsqueda */}
      <div className="relative mb-6">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por nombre o categoría..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b] focus:border-transparent"
        />
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {cargando ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Cargando materiales...
          </div>
        ) : materialesFiltrados.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <Package size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">
              {busqueda ? 'No se encontraron materiales' : 'No hay materiales registrados'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Nombre
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Categoría
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Contenido
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Material Base
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Estado
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {materialesFiltrados.map((material) => (
                <tr key={material.id_material_corporativo} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900">
                      {material.nombre_corporativo}
                    </p>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      {material.categoria || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      {material.contenido || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      {material.material_base || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      material.estado_material === 'Activo'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {material.estado_material}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/materiales/${material.id_material_corporativo}`}
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