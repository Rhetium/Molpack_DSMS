import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, FileText, AlertTriangle, Package,
  Ruler, Egg, BoxSelect, Bug, ShieldCheck, ChevronRight,
  Download, FileSpreadsheet, Image,
} from 'lucide-react';
import api from '../../../lib/api';
import ImagenesFicha from './ImagenesFicha';

const coloresEstado = {
  Borrador: 'bg-gray-100 text-gray-600',
  Preliminar: 'bg-yellow-100 text-yellow-700',
  Vigente: 'bg-green-100 text-green-700',
  Obsoleto: 'bg-red-100 text-red-700',
  'Revisión': 'bg-orange-100 text-orange-700',
};

const transicionesPermitidas = {
  Borrador: ['Preliminar'],
  Preliminar: ['Vigente'],
  Vigente: [],
  Obsoleto: ['Revisión'],
  'Revisión': ['Preliminar'],
};

export default function FichaDetallePage() {
  const { id } = useParams();
  const [ficha, setFicha] = useState(null);
  const [material, setMaterial] = useState(null);
  const [anomalias, setAnomalias] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [tab, setTab] = useState('caracteristicas');
  const [cambiandoEstado, setCambiandoEstado] = useState(false);

  async function cargar() {
    try {
      const [fichaRes, anomRes] = await Promise.allSettled([
        api.get(`/ficha/${id}`),
        api.get(`/anomalias/kitem/${id}`),
      ]);

      if (fichaRes.status === 'fulfilled') {
        setFicha(fichaRes.value.data);
        // Cargar material asociado
        try {
          const matRes = await api.get(`/material/${fichaRes.value.data.id_material_corporativo}`);
          setMaterial(matRes.data);
        } catch (e) {
          console.error('Error cargando material:', e);
        }
      }
      if (anomRes.status === 'fulfilled') {
        setAnomalias(anomRes.value.data.anomalias || []);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
  }, [id]);

  async function cambiarEstado(nuevoEstado) {
    // Verificar anomalías pendientes antes de cambiar
    if (anomalias.filter((a) => a.estado === 'pendiente').length > 0) {
      alert(
        'No se puede cambiar el estado: hay anomalías pendientes por resolver. ' +
        'Ve a la pestaña de Anomalías para revisarlas.'
      );
      return;
    }

    setCambiandoEstado(true);
    try {
      await api.patch(`/ficha/${id}/estado`, {
        nuevo_estado: nuevoEstado,
        usuario_actualizacion: 'marco.agrusa',
      });
      await cargar();
    } catch (error) {
      const msg = error.response?.data?.detail || 'Error al cambiar estado';
      alert(msg);
    } finally {
      setCambiandoEstado(false);
    }
  }

  async function analizarAnomalias() {
    try {
      const res = await api.post('/anomalias/analizar/ficha', {
        id_ficha: id,
        usuario: 'marco.agrusa',
      });
      alert(`Análisis completado: ${res.data.total_anomalias} anomalías detectadas`);
      await cargar();
    } catch (error) {
      console.error('Error analizando:', error);
    }
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm text-gray-500">Cargando ficha...</p>
      </div>
    );
  }

  if (!ficha) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Ficha no encontrada</p>
        <Link to="/fichas" className="text-blue-600 text-sm mt-2 inline-block">
          Volver a fichas
        </Link>
      </div>
    );
  }

  const estadoActual = ficha.estado_ficha;
  const transiciones = transicionesPermitidas[estadoActual] || [];
  const puedeObsoletar = estadoActual !== 'Obsoleto' && estadoActual !== 'Revisión';

  const tabs = [
    { id: 'caracteristicas', label: 'Características', icono: Ruler },
    { id: 'contenido', label: 'Contenido', icono: Egg },
    { id: 'empaque', label: 'Empaque y Estiba', icono: BoxSelect },
    { id: 'microbiologia', label: 'Microbiología', icono: Bug },
    { id: 'manejo', label: 'Manejo y Disposición', icono: ShieldCheck },
    { id: 'imagenes', label: 'Imágenes', icono: Image },
    { id: 'anomalias', label: `Anomalías (${anomalias.length})`, icono: AlertTriangle },
  ];

  return (
    <div>
      {/* Navegación */}
      <Link
        to="/fichas"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={16} />
        Volver a fichas
      </Link>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{ficha.codigo_ficha_local}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Código Local: <span className="font-medium text-gray-700">{ficha.codigo_material_local}</span>
              {' · '}Versión {ficha.codigo_version}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              coloresEstado[estadoActual] || 'bg-gray-100 text-gray-600'
            }`}>
              {estadoActual}
            </span>
          </div>
        </div>

        {/* Info rápida */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500">Material</p>
            <Link
              to={`/materiales/${ficha.id_material_corporativo}`}
              className="text-sm font-medium text-[#044926] hover:text-[#29b34b]"
            >
              {material?.nombre_corporativo || ficha.codigo_material_local}
            </Link>
          </div>
          <div>
            <p className="text-xs text-gray-500">País</p>
            <p className="text-sm font-medium text-gray-900">{ficha.pais}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Color</p>
            <p className="text-sm font-medium text-gray-900">{ficha.caracteristicas?.color || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Creador</p>
            <p className="text-sm font-medium text-gray-900">{ficha.usuario_creador}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Fecha</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(ficha.fecha_registro).toLocaleDateString('es')}
            </p>
          </div>
        </div>

        {/* Acciones de estado */}
        <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
          <Link
            to={`/fichas/${id}/editar`}
            className="inline-flex items-center gap-1 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Editar Ficha
          </Link>
          {transiciones.map((estado) => (
            <button
              key={estado}
              onClick={() => cambiarEstado(estado)}
              disabled={cambiandoEstado}
              className="inline-flex items-center gap-1 px-4 py-2 bg-[#29b34b] text-white rounded-lg text-sm font-medium hover:bg-[#044926] disabled:opacity-50 transition-colors"
            >
              Cambiar a {estado}
              <ChevronRight size={14} />
            </button>
          ))}
          <button
            onClick={analizarAnomalias}
            className="inline-flex items-center gap-1 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            <AlertTriangle size={14} />
            Analizar anomalías
          </button>
          {puedeObsoletar && (
            <button
              onClick={() => {
                if (window.confirm("\u00bfEst\u00e1s seguro de marcar esta ficha como Obsoleta? Esta acci\u00f3n no se puede revertir.")) {
                  cambiarEstado("Obsoleto");
                }
              }}
              disabled={cambiandoEstado}
              className="inline-flex items-center gap-1 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              Marcar Obsoleta
            </button>
          )}
          {estadoActual === 'Revisión' && (
            <button
              onClick={() => {
                if (window.confirm('¿Cancelar la revisión y volver a Obsoleto?')) {
                  cambiarEstado('Obsoleto');
                }
              }}
              disabled={cambiandoEstado}
              className="inline-flex items-center gap-1 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Cancelar Revisión
            </button>
          )}

          {/* Exportación — solo Preliminar y Vigente */}
          {(estadoActual === 'Preliminar' || estadoActual === 'Vigente') && (
            <>
              <button
                onClick={async () => {
                  try {
                    const res = await api.get(`/dsms/export/ficha/${id}/pdf`, { responseType: 'blob' });
                    const url = window.URL.createObjectURL(new Blob([res.data]));
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `ficha_${ficha.codigo_ficha_local || id}.pdf`;
                    link.click();
                    window.URL.revokeObjectURL(url);
                  } catch (err) {
                    alert(err.response?.data?.detail || 'Error al exportar PDF');
                  }
                }}
                className="inline-flex items-center gap-1 px-4 py-2 bg-[#044926] text-white rounded-lg text-sm font-medium hover:bg-[#29b34b] transition-colors"
              >
                <Download size={14} />
                Exportar PDF
              </button>
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
                    alert(err.response?.data?.detail || 'Error al exportar Excel');
                  }
                }}
                className="inline-flex items-center gap-1 px-4 py-2 border border-[#044926] text-[#044926] rounded-lg text-sm font-medium hover:bg-[#044926]/5 transition-colors"
              >
                <FileSpreadsheet size={14} />
                Exportar Excel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tabs de secciones */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-4 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 pb-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
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

      {/* Contenido de secciones */}
      {tab === 'caracteristicas' && <SeccionJsonb datos={ficha.caracteristicas} titulo="Características Físicas" />}
      {tab === 'contenido' && <SeccionJsonb datos={ficha.caracteristicas_contenido} titulo="Características del Contenido" />}
      {tab === 'empaque' && <SeccionJsonb datos={ficha.empaque_estiba} titulo="Empaque y Estiba" />}
      {tab === 'microbiologia' && <SeccionJsonb datos={ficha.microbiologia} titulo="Microbiología y Metales Pesados" />}
      {tab === 'manejo' && <SeccionJsonb datos={ficha.manejo_disposicion} titulo="Manejo y Disposición" />}
      {tab === 'imagenes' && (
        <ImagenesFicha
          idFicha={id}
          imagenes={ficha.caracteristicas?.imagenes}
          onActualizar={cargar}
          soloLectura={true}
        />
      )}
      {tab === 'anomalias' && <TabAnomalias anomalias={anomalias} />}
    </div>
  );
}

/* ========== Sección JSONB genérica ========== */
function SeccionJsonb({ datos, titulo }) {
  if (!datos || Object.keys(datos).length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
        <p className="text-sm text-gray-500">No hay datos en esta sección</p>
      </div>
    );
  }

  // Agrupar campos en tríos (valor/tolerancia/unidad) y campos sueltos
  const grupos = agruparCampos(datos);

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">{titulo}</h3>
      </div>

      {grupos.medidas.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-6 py-2.5 text-xs font-medium text-gray-500 uppercase">Propiedad</th>
                <th className="text-left px-6 py-2.5 text-xs font-medium text-gray-500 uppercase">Valor</th>
                <th className="text-left px-6 py-2.5 text-xs font-medium text-gray-500 uppercase">Tolerancia</th>
                <th className="text-left px-6 py-2.5 text-xs font-medium text-gray-500 uppercase">Unidad</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {grupos.medidas.map((medida) => (
                <tr key={medida.nombre} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-sm font-medium text-gray-700">
                    {formatearNombreCampo(medida.nombre)}
                  </td>
                  <td className="px-6 py-3 text-sm text-gray-900 font-mono">
                    {medida.valor ?? '—'}
                  </td>
                  <td className="px-6 py-3 text-sm text-gray-600 font-mono">
                    {medida.tolerancia != null ? `± ${medida.tolerancia}` : '—'}
                  </td>
                  <td className="px-6 py-3 text-sm text-gray-600">
                    {medida.unidad || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {grupos.otros.length > 0 && (
        <div className={`divide-y divide-gray-100 ${grupos.medidas.length > 0 ? 'border-t border-gray-200' : ''}`}>
          {grupos.otros.map(({ clave, valor }) => (
            <div key={clave} className="flex items-start px-6 py-3">
              <span className="w-48 text-sm font-medium text-gray-500 shrink-0">
                {formatearNombreCampo(clave)}
              </span>
              <span className="text-sm text-gray-900">
                {typeof valor === 'object' ? JSON.stringify(valor) : String(valor ?? '—')}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ========== Tab Anomalías ========== */
function TabAnomalias({ anomalias }) {
  const iconos = { critica: '🔴', advertencia: '🟡', informativa: '🔵' };

  if (anomalias.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
        <AlertTriangle size={40} className="mx-auto text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">No se han detectado anomalías para esta ficha</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {anomalias.map((a) => (
        <div key={a.id} className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <span>{iconos[a.severidad]}</span>
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
          {a.campo_afectado && (
            <p className="text-xs text-gray-400 mt-1">
              Campo: {a.campo_afectado}
              {a.valor_detectado && ` | Detectado: ${a.valor_detectado}`}
              {a.valor_esperado && ` | Esperado: ${a.valor_esperado}`}
            </p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            {new Date(a.fecha_deteccion).toLocaleString('es')}
          </p>
        </div>
      ))}
    </div>
  );
}

/* ========== Helpers ========== */
function agruparCampos(datos) {
  const medidas = [];
  const otros = [];
  const procesados = new Set();

  const claves = Object.keys(datos);

  for (const clave of claves) {
    if (procesados.has(clave)) continue;

    // Detectar tríos: xxxx_valor, xxxx_tolerancia, xxxx_unidad
    if (clave.endsWith('_valor')) {
      const prefijo = clave.replace('_valor', '');
      medidas.push({
        nombre: prefijo,
        valor: datos[`${prefijo}_valor`],
        tolerancia: datos[`${prefijo}_tolerancia`],
        unidad: datos[`${prefijo}_unidad`],
      });
      procesados.add(`${prefijo}_valor`);
      procesados.add(`${prefijo}_tolerancia`);
      procesados.add(`${prefijo}_unidad`);
    }
    // Detectar pares microbiología: xxxx_valor, xxxx_limite
    else if (clave.endsWith('_limite')) {
      // ya procesado via _valor
    }
  }

  // Campos no procesados
  for (const clave of claves) {
    if (!procesados.has(clave) && datos[clave] !== null && datos[clave] !== undefined) {
      // Verificar si es un par valor/limite
      if (clave.endsWith('_valor') && datos[clave.replace('_valor', '_limite')] !== undefined) {
        const prefijo = clave.replace('_valor', '');
        medidas.push({
          nombre: prefijo,
          valor: datos[`${prefijo}_valor`],
          tolerancia: datos[`${prefijo}_limite`],
          unidad: 'límite',
        });
        procesados.add(`${prefijo}_valor`);
        procesados.add(`${prefijo}_limite`);
      } else if (!clave.endsWith('_tolerancia') && !clave.endsWith('_unidad') && !clave.endsWith('_limite')) {
        otros.push({ clave, valor: datos[clave] });
        procesados.add(clave);
      }
    }
  }

  return { medidas, otros };
}

function formatearNombreCampo(campo) {
  return campo
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}