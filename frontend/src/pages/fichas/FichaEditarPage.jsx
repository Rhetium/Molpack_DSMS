import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Save, AlertTriangle, Check } from 'lucide-react';
import api from '../../../lib/api';

const PASOS = [
  { id: 0, titulo: 'Características' },
  { id: 1, titulo: 'Contenido' },
  { id: 2, titulo: 'Empaque y Estiba' },
  { id: 3, titulo: 'Microbiología' },
  { id: 4, titulo: 'Manejo y Disposición' },
];

export default function FichaEditarPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ficha, setFicha] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [anomalias, setAnomalias] = useState([]);
  const [paso, setPaso] = useState(0);

  // Secciones editables
  const [caracteristicas, setCaracteristicas] = useState({});
  const [contenido, setContenido] = useState({});
  const [empaque, setEmpaque] = useState({});
  const [microbiologia, setMicrobiologia] = useState({});
  const [manejo, setManejo] = useState({});

  useEffect(() => {
    async function cargar() {
      try {
        const res = await api.get(`/ficha/${id}`);
        const f = res.data;
        setFicha(f);
        setCaracteristicas(f.caracteristicas || {});
        setContenido(f.caracteristicas_contenido || {});
        setEmpaque(f.empaque_estiba || {});
        setMicrobiologia(f.microbiologia || {});
        setManejo(f.manejo_disposicion || {});
      } catch (err) {
        setError('Error cargando ficha');
      } finally {
        setCargando(false);
      }
    }
    cargar();
  }, [id]);

  async function handleSubmit() {
    setError(null);
    setAnomalias([]);
    setGuardando(true);

    try {
      const payload = {
        usuario_actualizacion: 'marco.agrusa',
      };

      // Solo enviar secciones que tengan datos
      if (Object.keys(caracteristicas).length > 0) payload.caracteristicas = limpiar(caracteristicas);
      if (Object.keys(contenido).length > 0) payload.caracteristicas_contenido = limpiar(contenido);
      if (Object.keys(empaque).length > 0) payload.empaque_estiba = limpiar(empaque);
      if (Object.keys(microbiologia).length > 0) payload.microbiologia = limpiar(microbiologia);
      if (Object.keys(manejo).length > 0) payload.manejo_disposicion = manejo;

      const res = await api.patch(`/ficha/${id}`, payload);

      if (res.data.anomalias && res.data.anomalias.length > 0) {
        setAnomalias(res.data.anomalias);
        // No navegar, mostrar anomalías
        return;
      }

      navigate(`/fichas/${id}`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al actualizar ficha';
      setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
    } finally {
      setGuardando(false);
    }
  }

  function limpiar(datos) {
    const resultado = {};
    for (const [k, v] of Object.entries(datos)) {
      if (v === '' || v === undefined) {
        resultado[k] = null;
      } else if (typeof v === 'string' && !isNaN(v) && v.trim() !== '') {
        resultado[k] = parseFloat(v);
      } else {
        resultado[k] = v;
      }
    }
    return resultado;
  }

  if (cargando) {
    return <div className="text-center py-12 text-sm text-gray-500">Cargando ficha...</div>;
  }

  if (!ficha) {
    return <div className="text-center py-12 text-sm text-gray-500">Ficha no encontrada</div>;
  }

  // Si es Vigente u Obsoleto, advertir
  const esEditable = ficha.estado_ficha === 'Borrador' || ficha.estado_ficha === 'Preliminar' || ficha.estado_ficha === 'Revisión';

  return (
    <div className="max-w-3xl mx-auto">
      <Link to={`/fichas/${id}`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={16} /> Volver a la ficha
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">Editar Ficha Técnica</h1>
      <p className="text-sm text-gray-500 mb-6">
        {ficha.codigo_ficha_local} — v{ficha.codigo_version} — Estado: {ficha.estado_ficha}
      </p>

      {!esEditable && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg mb-6 text-sm">
          Esta ficha está en estado <strong>{ficha.estado_ficha}</strong>.
          {ficha.estado_ficha === 'Vigente'
            ? ' Al guardar se creará una nueva versión en Preliminar y esta pasará a Obsoleto.'
            : ' Las fichas obsoletas no se pueden modificar. Cámbiala a Revisión primero.'}
        </div>
      )}

      {ficha.estado_ficha === 'Obsoleto' && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          Las fichas obsoletas no se pueden modificar.
          <Link to={`/fichas/${id}`} className="ml-2 underline">Volver</Link>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">{error}</div>
      )}

      {anomalias.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-amber-600" />
            <p className="text-sm font-medium text-amber-800">{anomalias.length} anomalía(s) detectada(s)</p>
          </div>
          {anomalias.map((a, i) => (
            <p key={i} className="text-sm text-amber-700 ml-6">• {a.mensaje}</p>
          ))}
          <button
            onClick={() => navigate(`/fichas/${id}`)}
            className="mt-3 ml-6 text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Ver ficha actualizada →
          </button>
        </div>
      )}

      {ficha.estado_ficha !== 'Obsoleto' && (
        <>
          {/* Indicador de pasos */}
          <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
            {PASOS.map((p, i) => (
              <button
                key={p.id}
                onClick={() => setPaso(i)}
                className={`px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  paso === i ? 'bg-[#29b34b] text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {p.titulo}
              </button>
            ))}
          </div>

          {/* Editor de sección */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            {paso === 0 && <EditorSeccion datos={caracteristicas} setDatos={setCaracteristicas} />}
            {paso === 1 && <EditorSeccion datos={contenido} setDatos={setContenido} />}
            {paso === 2 && <EditorSeccion datos={empaque} setDatos={setEmpaque} />}
            {paso === 3 && <EditorSeccion datos={microbiologia} setDatos={setMicrobiologia} />}
            {paso === 4 && <EditorTextos datos={manejo} setDatos={setManejo} />}
          </div>

          {/* Guardar */}
          <div className="flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={guardando}
              className="flex items-center gap-2 bg-[#29b34b] text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926] disabled:opacity-50 transition-colors"
            >
              <Save size={16} />
              {guardando ? 'Guardando...' : (ficha.estado_ficha === 'Vigente' || ficha.estado_ficha === 'Revisión') ? 'Crear Nueva Versión' : 'Guardar Cambios'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ========== Editor genérico de sección JSONB con valor/tolerancia/unidad ========== */
function EditorSeccion({ datos, setDatos }) {
  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  // Agrupar en tríos y campos sueltos
  const claves = Object.keys(datos);
  const grupos = [];
  const sueltos = [];
  const procesados = new Set();

  for (const clave of claves) {
    if (procesados.has(clave)) continue;

    if (clave.endsWith('_valor')) {
      const prefijo = clave.replace('_valor', '');
      const tieneTolerancia = datos.hasOwnProperty(`${prefijo}_tolerancia`);
      const tieneUnidad = datos.hasOwnProperty(`${prefijo}_unidad`);
      const tieneLimite = datos.hasOwnProperty(`${prefijo}_limite`);

      if (tieneTolerancia || tieneUnidad) {
        grupos.push({ prefijo, tipo: 'trio' });
        procesados.add(`${prefijo}_valor`);
        procesados.add(`${prefijo}_tolerancia`);
        procesados.add(`${prefijo}_unidad`);
      } else if (tieneLimite) {
        grupos.push({ prefijo, tipo: 'par' });
        procesados.add(`${prefijo}_valor`);
        procesados.add(`${prefijo}_limite`);
      } else {
        sueltos.push(clave);
        procesados.add(clave);
      }
    }
  }

  for (const clave of claves) {
    if (!procesados.has(clave)) {
      sueltos.push(clave);
      procesados.add(clave);
    }
  }

  return (
    <div className="space-y-4">
      {grupos.map((grupo) => (
        <div key={grupo.prefijo}>
          <p className="text-sm font-medium text-gray-700 mb-2">
            {formatearNombre(grupo.prefijo)}
          </p>
          {grupo.tipo === 'trio' ? (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valor</label>
                <input
                  type="number" step="any"
                  value={datos[`${grupo.prefijo}_valor`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
                <input
                  type="number" step="any"
                  value={datos[`${grupo.prefijo}_tolerancia`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                <input
                  type="text"
                  value={datos[`${grupo.prefijo}_unidad`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valor</label>
                <input
                  type="number" step="any"
                  value={datos[`${grupo.prefijo}_valor`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Límite</label>
                <input
                  type="number" step="any"
                  value={datos[`${grupo.prefijo}_limite`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_limite`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}
        </div>
      ))}

      {sueltos.map((clave) => (
        <div key={clave}>
          <label className="block text-sm font-medium text-gray-700 mb-1">{formatearNombre(clave)}</label>
          <input
            type={typeof datos[clave] === 'number' ? 'number' : 'text'}
            step="any"
            value={datos[clave] ?? ''}
            onChange={(e) => handleChange(clave, e.target.value)}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      ))}

      {claves.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-4">Esta sección no tiene datos aún.</p>
      )}
    </div>
  );
}

/* ========== Editor de textos (Manejo y Disposición) ========== */
function EditorTextos({ datos, setDatos }) {
  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const campos = Object.keys(datos);
  const obligatorios = ['manejo', 'almacenamiento', 'transporte', 'vida_util', 'uso'];

  return (
    <div className="space-y-4">
      {campos.map((campo) => (
        <div key={campo}>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {formatearNombre(campo)}
            {obligatorios.includes(campo) && <span className="text-red-500 ml-1">*</span>}
          </label>
          <textarea
            value={datos[campo] ?? ''}
            onChange={(e) => handleChange(campo, e.target.value)}
            rows={2}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
      ))}
    </div>
  );
}

function formatearNombre(campo) {
  return campo.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}