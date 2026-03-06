import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileText, AlertTriangle, Package, Plus } from 'lucide-react';
import api from '../../../lib/api';

const coloresEstado = {
  Borrador: 'bg-gray-100 text-gray-600',
  Preliminar: 'bg-yellow-100 text-yellow-700',
  Vigente: 'bg-green-100 text-green-700',
  Obsoleto: 'bg-red-100 text-red-700',
  Activo: 'bg-green-100 text-green-700',
  Inactivo: 'bg-red-100 text-red-700',
};

export default function MaterialDetallePage() {
  const { id } = useParams();
  const [material, setMaterial] = useState(null);
  const [fichas, setFichas] = useState([]);
  const [anomalias, setAnomalias] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [tab, setTab] = useState('info');

  useEffect(() => {
    async function cargar() {
      try {
        const [matRes, fichaRes, anomRes] = await Promise.allSettled([
          api.get(`/material/${id}`),
          api.get('/ficha'),
          api.get(`/anomalias/kitem/${id}`),
        ]);

        if (matRes.status === 'fulfilled') setMaterial(matRes.value.data);
        if (fichaRes.status === 'fulfilled') {
          const fichasMaterial = fichaRes.value.data.filter(
            (f) => f.id_material_corporativo === id
          );
          setFichas(fichasMaterial);
        }
        if (anomRes.status === 'fulfilled') setAnomalias(anomRes.value.data.anomalias || []);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setCargando(false);
      }
    }
    cargar();
  }, [id]);

  async function toggleEstado(nuevoEstado) {
    try {
      await api.patch(`/material/${id}/estado`, {
        estado_material: nuevoEstado,
        usuario: 'marco.agrusa',
      });
      // Recargar datos
      const res = await api.get(`/material/${id}`);
      setMaterial(res.data);
    } catch (error) {
      const msg = error.response?.data?.detail || 'Error al cambiar estado';
      alert(msg);
    }
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm text-gray-500">Cargando material...</p>
      </div>
    );
  }

  if (!material) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Material no encontrado</p>
        <Link to="/materiales" className="text-blue-600 text-sm mt-2 inline-block">
          Volver a materiales
        </Link>
      </div>
    );
  }

  const tabs = [
    { id: 'info', label: 'Información', icono: Package },
    { id: 'fichas', label: `Fichas (${fichas.length})`, icono: FileText },
    { id: 'anomalias', label: `Anomalías (${anomalias.length})`, icono: AlertTriangle },
  ];

  return (
    <div>
      {/* Navegación */}
      <Link
        to="/materiales"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={16} />
        Volver a materiales
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {material.nombre_corporativo}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            ID: {material.id_material_corporativo}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to={`/materiales/${id}/editar`}
            className="px-4 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Editar
          </Link>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            coloresEstado[material.estado_material] || 'bg-gray-100 text-gray-600'
          }`}>
            {material.estado_material}
          </span>
        </div>
      </div>

      {/* Toggle estado Activo/Inactivo */}
      <div className="flex items-center gap-3 mb-6">
        {material.estado_material === 'Activo' ? (
          <button
            onClick={() => toggleEstado('Inactivo')}
            className="inline-flex items-center gap-1 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
          >
            Desactivar Material
          </button>
        ) : (
          <button
            onClick={() => toggleEstado('Activo')}
            className="inline-flex items-center gap-1 px-4 py-2 border border-green-200 text-green-600 rounded-lg text-sm font-medium hover:bg-green-50 transition-colors"
          >
            Reactivar Material
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-6">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <t.icono size={16} />
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Contenido del tab */}
      {tab === 'info' && <TabInfo material={material} />}
      {tab === 'fichas' && <TabFichas fichas={fichas} materialId={id} />}
      {tab === 'anomalias' && <TabAnomalias anomalias={anomalias} />}
    </div>
  );
}

/* ========== TAB: Información ========== */
function TabInfo({ material }) {
  const campos = [
    { label: 'Nombre Corporativo', valor: material.nombre_corporativo },
    { label: 'Categoría', valor: material.categoria },
    { label: 'Contenido', valor: material.contenido },
    { label: 'Material Base', valor: material.material_base },
    { label: 'Capacidad Nominal', valor: material.capacidad_nominal },
    { label: 'Tipo de Producto', valor: material.tipo_producto },
    { label: 'Estado', valor: material.estado_material },
    { label: 'Fecha Creación', valor: material.fecha_creacion ? new Date(material.fecha_creacion).toLocaleString('es') : null },
    { label: 'Última Actualización', valor: material.fecha_actualizacion ? new Date(material.fecha_actualizacion).toLocaleString('es') : null },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className="divide-y divide-gray-100">
        {campos.map((campo) => (
          <div key={campo.label} className="flex items-center px-6 py-4">
            <span className="w-48 text-sm font-medium text-gray-500">{campo.label}</span>
            <span className="text-sm text-gray-900">{campo.valor || '—'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ========== TAB: Fichas Técnicas ========== */
function TabFichas({ fichas, materialId }) {
  if (fichas.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
        <FileText size={40} className="mx-auto text-gray-300 mb-3" />
        <p className="text-sm text-gray-500 mb-4">
          Este material no tiene fichas técnicas
        </p>
        <Link
          to="/fichas/nueva"
          className="inline-flex items-center gap-2 bg-[#29b34b] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#044926]"
        >
          <Plus size={16} />
          Crear Ficha Técnica
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Código</th>
            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Versión</th>
            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">País</th>
            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Estado</th>
            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Fecha</th>
            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {fichas.map((ficha) => (
            <tr key={ficha.id_ficha} className="hover:bg-gray-50">
              <td className="px-6 py-4 text-sm font-medium text-gray-900">
                {ficha.codigo_ficha_local}
              </td>
              <td className="px-6 py-4 text-sm text-gray-600">v{ficha.codigo_version}</td>
              <td className="px-6 py-4 text-sm text-gray-600">{ficha.pais}</td>
              <td className="px-6 py-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  coloresEstado[ficha.estado_ficha] || 'bg-gray-100 text-gray-600'
                }`}>
                  {ficha.estado_ficha}
                </span>
              </td>
              <td className="px-6 py-4 text-sm text-gray-500">
                {new Date(ficha.fecha_registro).toLocaleDateString('es')}
              </td>
              <td className="px-6 py-4">
                <Link
                  to={`/fichas/${ficha.id_ficha}`}
                  className="text-sm text-[#044926] hover:text-[#29b34b] font-medium"
                >
                  Ver ficha
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ========== TAB: Anomalías ========== */
function TabAnomalias({ anomalias }) {
  const iconosSeveridad = {
    critica: '🔴',
    advertencia: '🟡',
    informativa: '🔵',
  };

  if (anomalias.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
        <AlertTriangle size={40} className="mx-auto text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">No se han detectado anomalías para este material</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {anomalias.map((a) => (
        <div key={a.id} className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <span>{iconosSeveridad[a.severidad]}</span>
            <span className="text-xs font-medium text-gray-500 bg-gray-50 px-2 py-0.5 rounded">
              {a.tipo_anomalia}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              a.estado === 'pendiente' ? 'bg-orange-50 text-orange-600' : 'bg-gray-50 text-gray-500'
            }`}>
              {a.estado}
            </span>
          </div>
          <p className="text-sm text-gray-900">{a.mensaje}</p>
          <p className="text-xs text-gray-400 mt-2">
            {new Date(a.fecha_deteccion).toLocaleString('es')}
          </p>
        </div>
      ))}
    </div>
  );
}