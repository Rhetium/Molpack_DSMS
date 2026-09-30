import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle, XCircle, Filter, Search, FileText, Package } from 'lucide-react';
import api from '../../../lib/api';

const coloresSeveridad = {
  critica: 'bg-red-100 text-red-700 border-red-200',
  advertencia: 'bg-amber-100 text-amber-700 border-amber-200',
  informativa: 'bg-blue-100 text-blue-700 border-blue-200',
};

const iconosSeveridad = {
  critica: '🔴',
  advertencia: '🟡',
  informativa: '🔵',
};

export default function AnomaliasPage() {
  const [anomalias, setAnomalias] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('pendiente');
  const [filtroSeveridad, setFiltroSeveridad] = useState('');
  const [busqueda, setBusqueda] = useState('');
  // Las anomalías solo guardan kitem_id; el código legible se resuelve
  // en el cliente, igual que en AuditoriaPage.
  const [nombresMap, setNombresMap] = useState({});

  useEffect(() => {
    async function cargarNombres() {
      try {
        const [matRes, fichaRes] = await Promise.allSettled([
          api.get('/material'),
          api.get('/ficha'),
        ]);
        const map = {};
        if (matRes.status === 'fulfilled') {
          matRes.value.data.forEach((m) => {
            map[m.id_material_corporativo] = m.nombre_corporativo;
          });
        }
        if (fichaRes.status === 'fulfilled') {
          fichaRes.value.data.forEach((f) => {
            map[f.id_ficha] = f.codigo_ficha_local || f.codigo_material_local || f.id_ficha;
          });
        }
        setNombresMap(map);
      } catch (e) {
        console.error('Error cargando nombres:', e);
      }
    }
    cargarNombres();
  }, []);

  function getNombre(kitemId) {
    return nombresMap[kitemId] || kitemId;
  }

  function rutaKitem(anomalia) {
    return anomalia.ktype === 'MaterialComercial'
      ? `/materiales/${anomalia.kitem_id}`
      : `/fichas/${anomalia.kitem_id}?tab=anomalias`;
  }

  async function cargar() {
    setCargando(true);
    try {
      const params = { limite: 50 };
      if (filtroEstado) params.estado = filtroEstado;
      if (filtroSeveridad) params.severidad = filtroSeveridad;

      const res = await api.get('/anomalias/', { params });
      setAnomalias(res.data.anomalias);
    } catch (error) {
      console.error('Error cargando anomalías:', error);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
  }, [filtroEstado, filtroSeveridad]);

  // Búsqueda libre sobre lo ya cargado: código de la ficha/material, mensaje,
  // tipo de anomalía y campo afectado.
  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return anomalias;
    return anomalias.filter((a) =>
      [
        getNombre(a.kitem_id),
        a.mensaje,
        a.tipo_anomalia,
        a.campo_afectado,
        a.valor_detectado,
      ]
        .filter(Boolean)
        .some((campo) => String(campo).toLowerCase().includes(q))
    );
  }, [anomalias, busqueda, nombresMap]);

  async function resolverAnomalia(id, estado) {
    try {
      // La identidad la resuelve el backend desde el token JWT.
      await api.patch(`/anomalias/${id}/resolver`, {
        estado,
        nota: null,
      });
      cargar();
    } catch (error) {
      console.error('Error resolviendo anomalía:', error);
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Panel de Anomalías</h1>
        <p className="text-sm text-gray-500 mt-1">
          Revisión y resolución de anomalías detectadas por el sistema
        </p>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-400" />
          <span className="text-sm text-gray-500">Filtros:</span>
        </div>
        <select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        >
          <option value="">Todos los estados</option>
          <option value="pendiente">Pendientes</option>
          <option value="aceptada">Aceptadas</option>
          <option value="descartada">Descartadas</option>
          <option value="corregida">Corregidas</option>
        </select>
        <select
          value={filtroSeveridad}
          onChange={(e) => setFiltroSeveridad(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        >
          <option value="">Todas las severidades</option>
          <option value="critica">Críticas</option>
          <option value="advertencia">Advertencias</option>
          <option value="informativa">Informativas</option>
        </select>

        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por código, mensaje o campo..."
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
          />
        </div>
      </div>

      {!cargando && (
        <p className="text-xs text-gray-400 mb-3">
          {visibles.length} de {anomalias.length} anomalía(s) cargada(s)
          {busqueda.trim() && ' · filtrado en pantalla'}
        </p>
      )}

      {/* Lista de anomalías */}
      <div className="space-y-3">
        {cargando ? (
          <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center text-sm text-gray-500">
            Cargando anomalías...
          </div>
        ) : visibles.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
            <AlertTriangle size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">No hay anomalías con los filtros seleccionados</p>
          </div>
        ) : (
          visibles.map((anomalia) => (
            <div
              key={anomalia.id}
              className={`bg-white rounded-xl border p-5 ${
                anomalia.estado === 'pendiente' ? 'border-gray-200' : 'border-gray-100 opacity-75'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  {/* A qué ficha o material pertenece */}
                  <Link
                    to={rutaKitem(anomalia)}
                    className="inline-flex items-center gap-1.5 mb-2 text-sm font-semibold text-[#044926] hover:text-[#29b34b] hover:underline"
                  >
                    {anomalia.ktype === 'MaterialComercial' ? <Package size={14} /> : <FileText size={14} />}
                    {getNombre(anomalia.kitem_id)}
                  </Link>

                  {/* Severidad + Tipo */}
                  <div className="flex items-center gap-2 mb-2">
                    <span>{iconosSeveridad[anomalia.severidad]}</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      coloresSeveridad[anomalia.severidad]
                    }`}>
                      {anomalia.severidad}
                    </span>
                    <span className="text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded">
                      {anomalia.tipo_anomalia}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      anomalia.estado === 'pendiente'
                        ? 'bg-orange-50 text-orange-600'
                        : 'bg-gray-50 text-gray-500'
                    }`}>
                      {anomalia.estado}
                    </span>
                  </div>

                  {/* Mensaje */}
                  <p className="text-sm text-gray-900 mb-2">{anomalia.mensaje}</p>

                  {/* Detalles */}
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    {anomalia.campo_afectado && (
                      <span>Campo: <span className="text-gray-600">{anomalia.campo_afectado}</span></span>
                    )}
                    {anomalia.valor_detectado && (
                      <span>Detectado: <span className="text-gray-600">{anomalia.valor_detectado}</span></span>
                    )}
                    {anomalia.valor_esperado && (
                      <span>Esperado: <span className="text-gray-600">{anomalia.valor_esperado}</span></span>
                    )}
                    <span>
                      {new Date(anomalia.fecha_deteccion).toLocaleString('es')}
                    </span>
                  </div>
                </div>

                {/* Acciones (solo para pendientes) */}
                {anomalia.estado === 'pendiente' && (
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => resolverAnomalia(anomalia.id, 'aceptada')}
                      title="Aceptar (valor es correcto)"
                      className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                    >
                      <CheckCircle size={18} />
                    </button>
                    <button
                      onClick={() => resolverAnomalia(anomalia.id, 'descartada')}
                      title="Descartar (falso positivo)"
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <XCircle size={18} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}