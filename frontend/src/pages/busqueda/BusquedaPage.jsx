import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Sparkles, Package, FileText, ChevronRight } from 'lucide-react';
import api from '../../../lib/api';

export default function BusquedaPage() {
  const [query, setQuery] = useState('');
  const [filtroTexto, setFiltroTexto] = useState('');
  const [ktype, setKtype] = useState('');
  const [umbral, setUmbral] = useState(0.3);
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [buscado, setBuscado] = useState(false);

  async function buscar(e) {
    e.preventDefault();
    if (!query.trim()) return;

    setBuscando(true);
    setBuscado(true);
    try {
      const body = {
        texto: query,
        umbral_similitud: umbral,
        limite: 20,
      };
      if (ktype) body.ktype = ktype;
      if (filtroTexto.trim()) body.filtro_texto = filtroTexto;

      const res = await api.post('/dsms/semantica/buscar', body);
      setResultados(res.data.resultados || []);
    } catch (error) {
      console.error('Error en búsqueda:', error);
      setResultados([]);
    } finally {
      setBuscando(false);
    }
  }

  function getLinkForResult(resultado) {
    const kitem = resultado.kitem;
    if (!kitem) return null;
    if (kitem.ktype === 'MaterialComercial') return `/materiales/${kitem.id}`;
    if (kitem.ktype === 'FichaTecnica') return `/fichas/${kitem.id}`;
    return null;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Búsqueda Semántica</h1>
        <p className="text-sm text-gray-500 mt-1">
          Busca por significado usando inteligencia artificial (pgvector + embeddings)
        </p>
      </div>

      {/* Formulario */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="relative mb-4">
          <Sparkles size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#29b34b]" />
          <input
            type="text"
            placeholder="Describe lo que buscas... (ej: estuche para huevos, bandeja de frutas grande)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && buscar(e)}
            className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b] focus:border-transparent"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Filtro textual exacto</label>
            <input
              type="text"
              placeholder="ej: con ventana"
              value={filtroTexto}
              onChange={(e) => setFiltroTexto(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tipo</label>
            <select
              value={ktype}
              onChange={(e) => setKtype(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            >
              <option value="">Todos</option>
              <option value="MaterialComercial">Materiales</option>
              <option value="FichaTecnica">Fichas Técnicas</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Umbral similitud: {(umbral * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={umbral}
              onChange={(e) => setUmbral(parseFloat(e.target.value))}
              className="w-full accent-[#29b34b]"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={buscar}
              disabled={buscando || !query.trim()}
              className="w-full bg-[#29b34b] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#044926] transition-colors disabled:opacity-50"
            >
              {buscando ? 'Buscando...' : 'Buscar'}
            </button>
          </div>
        </div>
      </div>

      {/* Resultados */}
      {buscado && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-900">
              {resultados.length} resultado{resultados.length !== 1 ? 's' : ''}
            </h2>
          </div>

          {resultados.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Search size={40} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">
                No se encontraron resultados. Intenta con un umbral más bajo o términos diferentes.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {resultados.map((resultado, index) => {
                const kitem = resultado.kitem || {};
                const link = getLinkForResult(resultado);
                const esMaterial = kitem.ktype === 'MaterialComercial';

                return (
                  <div key={index} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        {/* Icono tipo */}
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                          esMaterial ? 'bg-[#044926]' : 'bg-[#29b34b]'
                        }`}>
                          {esMaterial ? (
                            <Package size={14} className="text-white" />
                          ) : (
                            <FileText size={14} className="text-white" />
                          )}
                        </div>

                        {/* Info */}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            {link ? (
                              <Link to={link} className="text-sm font-medium text-[#044926] hover:text-[#29b34b] truncate">
                                {kitem.nombre || 'Sin nombre'}
                              </Link>
                            ) : (
                              <span className="text-sm font-medium text-gray-900 truncate">
                                {kitem.nombre || 'Sin nombre'}
                              </span>
                            )}
                            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded shrink-0">
                              {esMaterial ? 'Material' : 'Ficha'}
                            </span>
                            {kitem.estado && (
                              <span className={`text-xs px-2 py-0.5 rounded shrink-0 ${
                                kitem.estado === 'Vigente' || kitem.estado === 'Activo' ? 'bg-green-100 text-green-700' :
                                kitem.estado === 'Preliminar' ? 'bg-yellow-100 text-yellow-700' :
                                kitem.estado === 'Obsoleto' || kitem.estado === 'Inactivo' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-600'
                              }`}>
                                {kitem.estado}
                              </span>
                            )}
                          </div>
                          {kitem.descripcion && (
                            <p className="text-xs text-gray-500 mt-0.5 truncate">{kitem.descripcion}</p>
                          )}
                        </div>
                      </div>

                      {/* Similitud + Link */}
                      <div className="flex items-center gap-3 shrink-0 ml-4">
                        <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                          resultado.similitud >= 0.85
                            ? 'bg-green-100 text-green-700'
                            : resultado.similitud >= 0.5
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {(resultado.similitud * 100).toFixed(1)}%
                        </div>
                        {link && (
                          <Link to={link} className="p-1.5 text-gray-400 hover:text-[#044926] hover:bg-green-50 rounded-lg transition-colors">
                            <ChevronRight size={16} />
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}