import { useEffect, useState } from 'react';
import { Package, FileText, AlertTriangle, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../../lib/api';

const coloresAccion = {
  CREACION: 'bg-green-100 text-green-700',
  MODIFICACION: 'bg-blue-100 text-blue-700',
  CAMBIO_ESTADO: 'bg-purple-100 text-purple-700',
  NUEVA_VERSION: 'bg-indigo-100 text-indigo-700',
  RELACION_CREADA: 'bg-teal-100 text-teal-700',
  RELACION_ELIMINADA: 'bg-red-100 text-red-700',
};

const nombresAccion = {
  CREACION: 'Creación',
  MODIFICACION: 'Modificación',
  CAMBIO_ESTADO: 'Cambio de Estado',
  NUEVA_VERSION: 'Nueva Versión',
  RELACION_CREADA: 'Relación Creada',
  RELACION_ELIMINADA: 'Relación Eliminada',
};

function TarjetaEstadistica({ titulo, valor, icono: Icono, color, cargando }) {
  const colores = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{titulo}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{cargando ? '...' : valor}</p>
        </div>
        <div className={`p-3 rounded-lg ${colores[color]}`}><Icono size={24} /></div>
      </div>
    </div>
  );
}

function esHoy(fechaStr) {
  const fecha = new Date(fechaStr);
  const hoy = new Date();
  return (
    fecha.getDate() === hoy.getDate() &&
    fecha.getMonth() === hoy.getMonth() &&
    fecha.getFullYear() === hoy.getFullYear()
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState({ materiales: 0, fichas: 0, anomalias: 0, actividadHoy: 0 });
  const [cargando, setCargando] = useState(true);
  const [actividad, setActividad] = useState([]);

  useEffect(() => {
    async function cargarDatos() {
      try {
        const [matRes, fichaRes, anomRes, actRes] = await Promise.allSettled([
          api.get('/material'),
          api.get('/ficha'),
          api.get('/anomalias/', { params: { estado: 'pendiente', limite: 5 } }),
          api.get('/dsms/auditoria/actividad', { params: { limite: 100 } }),
        ]);
        const actividadData = actRes.status === 'fulfilled' ? actRes.value.data : [];
        const eventosHoy = actividadData.filter((e) => esHoy(e.fecha));
        setStats({
          materiales: matRes.status === 'fulfilled' ? matRes.value.data.length : 0,
          fichas: fichaRes.status === 'fulfilled' ? fichaRes.value.data.length : 0,
          anomalias: anomRes.status === 'fulfilled' ? (anomRes.value.data.total ?? 0) : 0,
          actividadHoy: eventosHoy.length,
        });
        setActividad(actividadData.slice(0, 10));
      } catch (error) {
        console.error('Error cargando dashboard:', error);
      } finally {
        setCargando(false);
      }
    }
    cargarDatos();
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Resumen general del Dataspace Management System</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <TarjetaEstadistica titulo="Materiales" valor={stats.materiales} icono={Package} color="blue" cargando={cargando} />
        <TarjetaEstadistica titulo="Fichas Técnicas" valor={stats.fichas} icono={FileText} color="green" cargando={cargando} />
        <TarjetaEstadistica titulo="Anomalías Pendientes" valor={stats.anomalias} icono={AlertTriangle} color="amber" cargando={cargando} />
        <TarjetaEstadistica titulo="Actividad Hoy" valor={stats.actividadHoy} icono={Activity} color="purple" cargando={cargando} />
      </div>
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Actividad Reciente</h2>
          <Link to="/auditoria" className="text-sm text-[#044926] hover:text-[#29b34b] font-medium">Ver todo</Link>
        </div>
        <div className="divide-y divide-gray-100">
          {cargando ? (
            <div className="px-6 py-8 text-center text-sm text-gray-500">Cargando actividad...</div>
          ) : actividad.length === 0 ? (
            <div className="px-6 py-8 text-center text-sm text-gray-500">No hay actividad reciente. Empieza creando un material.</div>
          ) : (
            actividad.map((evento) => (
              <div key={evento.id} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{evento.usuario}</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${coloresAccion[evento.accion] || 'bg-gray-100 text-gray-600'}`}>
                    {nombresAccion[evento.accion] || evento.accion}
                  </span>
                  <span className="text-xs text-gray-500">{evento.ktype}</span>
                </div>
                <p className="text-xs text-gray-400">{new Date(evento.fecha).toLocaleString('es')}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}