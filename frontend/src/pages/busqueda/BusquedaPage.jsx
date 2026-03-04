import { useState } from 'react';
import { Search, Sparkles } from 'lucide-react';
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
      setResultados(res.data.resultados);
    } catch (error) {
      console.error('Error en búsqueda:', error);
      setResultados([]);
    } finally {
      setBuscando(false);
    }
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
      <form onSubmit={buscar} className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        {/* Búsqueda semántica principal */}
        <div className="relative mb-4">
          <Sparkles size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#29b34b]" />
          <input
            type="text"
            placeholder="Describe lo que buscas... (ej: estuche para huevos, separador grande)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Filtros adicionales */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Filtro textual exacto</label>
            <input
              type="text"
              placeholder="ej: con ventana"
              value={filtroTexto}
              onChange={(e) => setFiltroTexto(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tipo</label>
            <select
              value={ktype}
              onChange={(e) => setKtype(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="MaterialComercial">Materiales</option>
              <option value="FichaTecnica">Fichas Técnicas</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Umbral similitud: {umbral}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={umbral}
              onChange={(e) => setUmbral(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={buscando || !query.trim()}
              className="w-full bg-[#29b34b] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#044926] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {buscando ? 'Buscando...' : 'Buscar'}
            </button>
          </div>
        </div>
      </form>

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
                No se encontraron resultados. Intenta con un umbral más bajo.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {resultados.map((resultado, index) => (
                <div key={index} className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {resultado.nombre}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {resultado.ktype}
                      {resultado.descripcion && ` — ${resultado.descripcion}`}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                      resultado.similitud >= 0.85
                        ? 'bg-green-100 text-green-700'
                        : resultado.similitud >= 0.5
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {(resultado.similitud * 100).toFixed(1)}% similar
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}