import { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Save, Check, Info, AlertTriangle, Pencil } from 'lucide-react';
import api from '../../../lib/api';
import { useAuth } from '../../../lib/auth';
import { TipCampo } from './AsistenteIA';
import { PAISES } from './paises';
import { toggleNc, tieneValores } from './fichaCampos';

const PASOS = [
  { id: 0, titulo: 'Información Base', descripcion: 'Datos de identificación de la ficha' },
  { id: 1, titulo: 'Características', descripcion: 'Dimensiones, peso y propiedades físicas' },
  { id: 2, titulo: 'Contenido', descripcion: 'Propiedades según tipo de contenido' },
  { id: 3, titulo: 'Empaque y Estiba', descripcion: 'Configuración de empaque' },
  { id: 4, titulo: 'Microbiología', descripcion: 'Parámetros microbiológicos y metales pesados' },
  { id: 5, titulo: 'Manejo y Disposición', descripcion: 'Almacenamiento, transporte y uso' },
];

const CAMPOS_CARACTERISTICAS_BASE = [
  { prefijo: 'dimensiones_largo', label: 'Largo' },
  { prefijo: 'dimensiones_ancho', label: 'Ancho' },
  { prefijo: 'dimensiones_alto', label: 'Alto' },
  { prefijo: 'peso', label: 'Peso' },
  { prefijo: 'ruptura', label: 'Ruptura', sinTolerancia: true },
  { prefijo: 'tiempo_encolado', label: 'Tiempo de Encolado', sinTolerancia: true },
  { prefijo: 'porcentaje_absorcion', label: 'Porcentaje de Absorción' },
];

const DEFAULTS_CARACTERISTICAS = {
  color: '',
  dimensiones_largo_valor: '', dimensiones_largo_tolerancia: '', dimensiones_largo_unidad: 'mm', dimensiones_largo_nc: false,
  dimensiones_ancho_valor: '', dimensiones_ancho_tolerancia: '', dimensiones_ancho_unidad: 'mm', dimensiones_ancho_nc: false,
  dimensiones_alto_valor: '', dimensiones_alto_tolerancia: '', dimensiones_alto_unidad: 'mm', dimensiones_alto_nc: false,
  peso_valor: '', peso_tolerancia: '', peso_unidad: 'g', peso_nc: false,
  ruptura_valor: '', ruptura_unidad: 'Kgf', ruptura_nc: false,
  tiempo_encolado_valor: '', tiempo_encolado_unidad: 'min', tiempo_encolado_nc: false,
  porcentaje_absorcion_valor: '', porcentaje_absorcion_tolerancia: '', porcentaje_absorcion_unidad: '%', porcentaje_absorcion_nc: false,
  deflexion_interna_valor: '', deflexion_interna_unidad: 'mm', deflexion_interna_nc: false,
  deflexion_externa_valor: '', deflexion_externa_unidad: 'mm', deflexion_externa_nc: false,
  resistencia_valor: '', resistencia_unidad: 'Kgf', resistencia_nc: false,
};

const DEFAULTS_CONTENIDO = {
  peso_contenido_valor: '', peso_contenido_unidad: 'g',
  volumen_contenido_valor: '', volumen_contenido_unidad: 'oz',
  calibre_contenido: '',
  profundidad_pilar_valor: '', profundidad_pilar_tolerancia: '', profundidad_pilar_unidad: 'mm', profundidad_pilar_nc: false,
  diametro_alveolo_valor: '', diametro_alveolo_tolerancia: '', diametro_alveolo_unidad: 'mm', diametro_alveolo_nc: false,
  profundidad_cavidad_valor: '', profundidad_cavidad_tolerancia: '', profundidad_cavidad_unidad: 'mm', profundidad_cavidad_nc: false,
  diametro_cavidad_valor: '', diametro_cavidad_tolerancia: '', diametro_cavidad_unidad: 'mm', diametro_cavidad_nc: false,
  ancho_cavidad_valor: '', ancho_cavidad_tolerancia: '', ancho_cavidad_unidad: 'mm', ancho_cavidad_nc: false,
  largo_cavidad_valor: '', largo_cavidad_tolerancia: '', largo_cavidad_unidad: 'mm', largo_cavidad_nc: false,
};

const DEFAULTS_EMPAQUE = {
  tipo_empaque: '', color_empaque: '',
  alto_empaque_valor: '', alto_empaque_tolerancia: '', alto_empaque_unidad: 'cm',
  peso_empaque_valor: '', peso_empaque_tolerancia: '', peso_empaque_unidad: 'Kg',
  undidades_empaque: '', empaques_estiba: '', camas_estiba: '', empaques_camas_estiba: '',
};

const DEFAULTS_MICROBIOLOGIA = {
  recuento_aerobico_valor: '', recuento_aerobico_limite: '', recuento_aerobico_nc: false,
  recuento_moho_valor: '', recuento_moho_limite: '', recuento_moho_nc: false,
  coliforme_valor: '', coliforme_limite: '', coliforme_nc: false,
  escherichia_coli_valor: '', escherichia_coli_limite: '', escherichia_coli_nc: false,
  salmonella_spp_valor: '', salmonella_spp_limite: '', salmonella_spp_nc: false,
  cadmio_valor: '', cadmio_unidad: 'mg/Kg', cadmio_nc: false,
  plomo_valor: '', plomo_unidad: 'mg/Kg', plomo_nc: false,
  mercurio_valor: '', mercurio_unidad: 'mg/Kg', mercurio_nc: false,
  cromo_valor: '', cromo_unidad: 'mg/Kg', cromo_nc: false,
};

const DEFAULTS_MANEJO = {
  manejo: '', almacenamiento: '', transporte: '',
  inocuidad: '', disposicion_pt: '', garantias: '',
  manipulacion: '', vida_util: '', uso: '',
};

const ESTADO_COLORES = {
  Borrador:    'bg-yellow-100 text-yellow-800 border-yellow-200',
  Preliminar:  'bg-blue-100 text-blue-800 border-blue-200',
  Vigente:     'bg-green-100 text-green-800 border-green-200',
  Obsoleto:    'bg-red-100 text-red-800 border-red-200',
  'Revisión':  'bg-purple-100 text-purple-800 border-purple-200',
};

function hidratarSeccion(datos, defaults) {
  if (!datos) return defaults;
  const result = { ...defaults };
  for (const [k, v] of Object.entries(datos)) {
    if (k.endsWith('_nc')) {
      result[k] = !!v;
    } else {
      result[k] = v === null || v === undefined ? '' : v;
    }
  }
  return result;
}

export default function FichaEditarPage() {
  const { id } = useParams();
  const { user } = useAuth();

  const [paso, setPaso] = useState(0);
  const [ficha, setFicha] = useState(null);
  const [materiales, setMateriales] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [exitoMsg, setExitoMsg] = useState(null);

  const [nombreLocal, setNombreLocal] = useState('');
  const [codigoLocal, setCodigoLocal] = useState('');
  const [pais, setPais] = useState('');
  const [caracteristicas, setCaracteristicas] = useState(DEFAULTS_CARACTERISTICAS);
  const [contenido, setContenido] = useState(DEFAULTS_CONTENIDO);
  const [empaque, setEmpaque] = useState(DEFAULTS_EMPAQUE);
  const [microbiologia, setMicrobiologia] = useState(DEFAULTS_MICROBIOLOGIA);
  const [manejo, setManejo] = useState(DEFAULTS_MANEJO);

  useEffect(() => {
    Promise.all([
      api.get(`/ficha/${id}`),
      api.get('/material'),
    ]).then(([fichaRes, matRes]) => {
      const f = fichaRes.data;
      setFicha(f);
      setMateriales(matRes.data);
      setNombreLocal(f.nombre_local_material || '');
      setCodigoLocal(f.codigo_material_local || '');
      setPais(f.pais || '');
      setCaracteristicas(hidratarSeccion(f.caracteristicas, DEFAULTS_CARACTERISTICAS));
      setContenido(hidratarSeccion(f.caracteristicas_contenido, DEFAULTS_CONTENIDO));
      setEmpaque(hidratarSeccion(f.empaque_estiba, DEFAULTS_EMPAQUE));
      setMicrobiologia(hidratarSeccion(f.microbiologia, DEFAULTS_MICROBIOLOGIA));
      setManejo(hidratarSeccion(f.manejo_disposicion, DEFAULTS_MANEJO));
    }).catch(() => {
      setError('No se pudo cargar la ficha. Verifica que el ID sea válido.');
    }).finally(() => {
      setCargando(false);
    });
  }, [id]);

  const materialSeleccionado = useMemo(
    () => materiales.find((m) => m.id_material_corporativo === ficha?.id_material_corporativo),
    [materiales, ficha],
  );

  const tipoContenido = useMemo(() => materialSeleccionado?.contenido || null, [materialSeleccionado]);
  const tipoCategoria = useMemo(() => materialSeleccionado?.categoria || '', [materialSeleccionado]);

  const camposCaracteristicasDinamicos = useMemo(() => {
    // Sin espacios: 'Porta vasos' y 'Portavasos' son la misma categoría
    const cat = (tipoCategoria || '').toLowerCase().replace(/\s+/g, '');
    const campos = [...CAMPOS_CARACTERISTICAS_BASE];
    if (cat.includes('separador')) {
      campos.push(
        { prefijo: 'deflexion_interna', label: 'Deflexión Interna', sinTolerancia: true },
        { prefijo: 'deflexion_externa', label: 'Deflexión Externa', sinTolerancia: true },
      );
    } else if (cat.includes('portavaso') || cat.includes('bandeja')) {
      campos.push({ prefijo: 'resistencia', label: 'Resistencia', sinTolerancia: true });
    }
    return campos;
  }, [tipoCategoria]);

  const camposContenidoDinamicos = useMemo(() => {
    const c = (tipoContenido || '').toLowerCase();
    if (c.includes('huevo')) {
      return [
        { prefijo: 'profundidad_pilar', label: 'Profundidad Pilar' },
        { prefijo: 'diametro_alveolo', label: 'Diámetro Alvéolo' },
      ];
    }
    if (c.includes('fruta') || c.includes('pintura') || c.includes('vaso')) {
      return [
        { prefijo: 'profundidad_cavidad', label: 'Profundidad Cavidad' },
        { prefijo: 'diametro_cavidad', label: 'Diámetro Cavidad' },
      ];
    }
    return [
      { prefijo: 'profundidad_cavidad', label: 'Profundidad Cavidad' },
      { prefijo: 'ancho_cavidad', label: 'Ancho Cavidad' },
      { prefijo: 'largo_cavidad', label: 'Largo Cavidad' },
    ];
  }, [tipoContenido]);

  function limpiarSeccion(datos) {
    const limpio = {};
    for (const [k, v] of Object.entries(datos)) {
      if (k.endsWith('_nc')) {
        if (v === true) limpio[k] = true;
        continue;
      }
      if (v === '' || v === null || v === undefined) {
        limpio[k] = null;
      } else if (typeof v === 'string' && !isNaN(v) && v.trim() !== '') {
        limpio[k] = parseFloat(v);
      } else {
        limpio[k] = v;
      }
    }
    return limpio;
  }

  async function handleSubmit() {
    setError(null);
    setExitoMsg(null);
    setGuardando(true);
    try {
      const esBorrador = ficha?.estado_ficha === 'Borrador';
      const payload = {
        nombre_local_material: nombreLocal || null,
        // Identidad de la ficha: el backend solo la acepta en Borrador
        ...(esBorrador && {
          codigo_material_local: codigoLocal.trim() || null,
          pais: pais || null,
        }),
        caracteristicas: tieneValores(caracteristicas) ? limpiarSeccion(caracteristicas) : null,
        caracteristicas_contenido: tieneValores(contenido) ? limpiarSeccion(contenido) : null,
        empaque_estiba: tieneValores(empaque) ? limpiarSeccion(empaque) : null,
        microbiologia: tieneValores(microbiologia) ? limpiarSeccion(microbiologia) : null,
        manejo_disposicion: tieneValores(manejo) ? limpiarSeccion(manejo) : null,
        usuario_actualizacion: user?.usuario || 'sistema',
      };
      const res = await api.patch(`/ficha/${id}`, payload);
      setFicha(res.data);
      setExitoMsg('Cambios guardados correctamente.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar los cambios';
      setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="animate-pulse space-y-4 mt-8">
          <div className="h-6 bg-gray-200 rounded w-48" />
          <div className="h-10 bg-gray-200 rounded w-full" />
          <div className="h-64 bg-gray-200 rounded w-full" />
        </div>
      </div>
    );
  }

  if (error && !ficha) {
    return (
      <div className="max-w-4xl mx-auto mt-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl text-sm">
          {error}
        </div>
        <Link to="/fichas" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mt-4">
          <ArrowLeft size={16} /> Volver a fichas
        </Link>
      </div>
    );
  }

  const estadoColor = ESTADO_COLORES[ficha?.estado_ficha] || 'bg-gray-100 text-gray-700 border-gray-200';

  return (
    <div className="max-w-4xl mx-auto">
      <Link to={`/fichas/${id}`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={16} /> Volver a la ficha
      </Link>

      {/* Header de edición */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Pencil size={16} className="text-amber-600" />
              <h1 className="text-xl font-bold text-gray-900">Editar Ficha Técnica</h1>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${estadoColor}`}>
                {ficha?.estado_ficha}
              </span>
            </div>
            <p className="text-sm text-gray-600">
              <span className="font-medium">{materialSeleccionado?.nombre_corporativo || '—'}</span>
              {ficha?.codigo_material_local && <span className="text-gray-400 mx-2">·</span>}
              {ficha?.codigo_material_local && <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{ficha.codigo_material_local}</span>}
              {ficha?.pais && <span className="text-gray-400 mx-2">·</span>}
              {ficha?.pais && <span className="text-gray-500">{ficha.pais}</span>}
            </p>
          </div>
          {ficha?.codigo_ficha_local && (
            <span className="text-xs font-mono text-gray-500 bg-white border border-gray-200 px-2 py-1 rounded shrink-0">
              {ficha.codigo_ficha_local}
            </span>
          )}
        </div>

        {(ficha?.estado_ficha === 'Vigente' || ficha?.estado_ficha === 'Obsoleto') && (
          <div className="flex items-center gap-2 mt-3 text-xs text-amber-700">
            <AlertTriangle size={13} />
            <span>Estás editando una ficha en estado <strong>{ficha.estado_ficha}</strong>. Los cambios se guardan directamente.</span>
          </div>
        )}
      </div>

      {/* Éxito */}
      {exitoMsg && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4 text-sm flex items-center gap-2">
          <Check size={15} /> {exitoMsg}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Indicador de pasos */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {PASOS.map((p, i) => (
          <button
            key={p.id}
            onClick={() => setPaso(i)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              paso === i
                ? 'bg-amber-500 text-white'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            <span>{i + 1}</span>
            {p.titulo}
          </button>
        ))}
      </div>

      {/* Formulario */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">{PASOS[paso].titulo}</h2>
        <p className="text-sm text-gray-500 mb-6">{PASOS[paso].descripcion}</p>

        {paso >= 1 && paso <= 2 && tipoContenido && (
          <div className="flex items-center gap-2 p-3 bg-[#044926]/5 border border-[#29b34b]/20 rounded-lg mb-6 text-sm">
            <Info size={16} className="text-[#29b34b] shrink-0" />
            <p className="text-[#044926]">
              Material tipo <strong>{tipoContenido}</strong>
              {paso === 2 && ' — todos los campos de contenido son opcionales'}
            </p>
          </div>
        )}

        {paso === 0 && (
          <PasoInfoBase
            ficha={ficha}
            materialSeleccionado={materialSeleccionado}
            nombreLocal={nombreLocal}
            setNombreLocal={setNombreLocal}
            codigoLocal={codigoLocal}
            setCodigoLocal={setCodigoLocal}
            pais={pais}
            setPais={setPais}
          />
        )}
        {paso === 1 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Color del Producto</label>
              <input
                type="text"
                value={caracteristicas.color}
                onChange={(e) => setCaracteristicas((prev) => ({ ...prev, color: e.target.value }))}
                placeholder="Ej: Natural, Blanco, Verde, Kraft"
                className="w-full max-w-xs px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            <PasoMedidas datos={caracteristicas} setDatos={setCaracteristicas} campos={camposCaracteristicasDinamicos} />
          </div>
        )}
        {paso === 2 && <PasoContenidoDinamico datos={contenido} setDatos={setContenido} campos={camposContenidoDinamicos} tipoContenido={tipoContenido} />}
        {paso === 3 && <PasoEmpaque datos={empaque} setDatos={setEmpaque} />}
        {paso === 4 && <PasoMicrobiologia datos={microbiologia} setDatos={setMicrobiologia} />}
        {paso === 5 && <PasoManejo datos={manejo} setDatos={setManejo} />}
      </div>

      {/* Navegación */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setPaso((p) => Math.max(0, p - 1))}
          disabled={paso === 0}
          className="flex items-center gap-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-30 transition-colors"
        >
          <ArrowLeft size={16} /> Anterior
        </button>

        <div className="flex items-center gap-2">
          {paso < PASOS.length - 1 ? (
            <button
              onClick={() => setPaso((p) => Math.min(PASOS.length - 1, p + 1))}
              className="flex items-center gap-1 px-4 py-2.5 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors"
            >
              Siguiente <ArrowRight size={16} />
            </button>
          ) : null}

          <button
            onClick={handleSubmit}
            disabled={guardando}
            className="flex items-center gap-2 px-6 py-2.5 bg-[#044926] text-white rounded-lg text-sm font-medium hover:bg-[#29b34b] disabled:opacity-50 transition-colors"
          >
            <Save size={16} />
            {guardando ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ========== PASO 0: Info Base (solo lectura + campos editables según estado) ========== */
function PasoInfoBase({ ficha, materialSeleccionado, nombreLocal, setNombreLocal, codigoLocal, setCodigoLocal, pais, setPais }) {
  const esBorrador = ficha?.estado_ficha === 'Borrador';
  return (
    <div className="space-y-5">
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 space-y-3">
        <p className="text-xs font-semibold text-gray-500 uppercase">Datos de identificación (no editables)</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <span className="text-gray-500">Material Corporativo</span>
          <span className="text-gray-900 font-medium">{materialSeleccionado?.nombre_corporativo || '—'}</span>
          <span className="text-gray-500">Categoría</span>
          <span className="text-gray-900 font-medium">{materialSeleccionado?.categoria || '—'}</span>
          <span className="text-gray-500">Contenido</span>
          <span className="text-gray-900 font-medium">{materialSeleccionado?.contenido || '—'}</span>
          {!esBorrador && (
            <>
              <span className="text-gray-500">Código Local</span>
              <span className="font-mono text-gray-900">{ficha?.codigo_material_local || '—'}</span>
              <span className="text-gray-500">País</span>
              <span className="text-gray-900 font-medium">{ficha?.pais || '—'}</span>
            </>
          )}
          <span className="text-gray-500">Estado</span>
          <span className="text-gray-900 font-medium">{ficha?.estado_ficha || '—'}</span>
          <span className="text-gray-500">Versión</span>
          <span className="font-mono text-gray-900">{ficha?.codigo_version || '—'}</span>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {esBorrador
            ? 'Para cambiar el material crea una nueva ficha.'
            : 'Para cambiar el material o el país crea una nueva versión desde la página de detalle.'}
        </p>
      </div>

      {esBorrador && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Código de Material Local</label>
            <input
              type="text"
              value={codigoLocal}
              onChange={(e) => setCodigoLocal(e.target.value)}
              placeholder="Ej: EST-12"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
            <p className="text-xs text-gray-400 mt-1">Obligatorio para pasar a Preliminar.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">País</label>
            <select
              value={pais}
              onChange={(e) => setPais(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
            >
              <option value="">Seleccionar país...</option>
              {PAISES.map((p) => (
                <option key={p.code} value={p.code}>{p.nombre}</option>
              ))}
            </select>
            <p className="text-xs text-gray-400 mt-1">Obligatorio para pasar a Preliminar.</p>
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nombre Local del Material</label>
        <input
          type="text"
          value={nombreLocal}
          onChange={(e) => setNombreLocal(e.target.value)}
          placeholder="Ej: Estuche 12 sin ventana (nombre usado localmente)"
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <p className="text-xs text-gray-400 mt-1">Nombre con que se identifica este material en la planta local.</p>
      </div>
    </div>
  );
}

/* ========== PASO GENÉRICO: Medidas ========== */
function PasoMedidas({ datos, setDatos, campos }) {
  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  return (
    <div className="space-y-4">
      {campos.map((grupo) => {
        const isNc = !!datos[`${grupo.prefijo}_nc`];
        const inputClass = `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 ${
          isNc ? 'bg-gray-50 border-gray-100 text-gray-300 cursor-not-allowed' : 'border-gray-200'
        }`;
        return (
          <div key={grupo.prefijo} className={`grid gap-3 items-end ${grupo.sinTolerancia ? 'grid-cols-3' : 'grid-cols-4'}`}>
            <div className={`flex items-center justify-between ${grupo.sinTolerancia ? 'col-span-3' : 'col-span-4'}`}>
              <p className="text-sm font-medium text-gray-700">
                {grupo.label}
                <TipCampo campo={grupo.prefijo} />
              </p>
              <label className="flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isNc}
                  onChange={() => setDatos((prev) => toggleNc(prev, grupo.prefijo))}
                  className="w-3.5 h-3.5 accent-amber-500"
                />
                <span className={`text-xs font-semibold ${isNc ? 'text-amber-600' : 'text-gray-400'}`}>N/C</span>
              </label>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Valor</label>
              <input
                type="number" step="any" disabled={isNc}
                value={isNc ? '' : datos[`${grupo.prefijo}_valor`] ?? ''}
                onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
                placeholder={isNc ? 'N/C' : ''}
                className={inputClass}
              />
            </div>
            {!grupo.sinTolerancia && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
                <input
                  type="number" step="any" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_tolerancia`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
                  placeholder={isNc ? 'N/C' : ''}
                  className={inputClass}
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Unidad</label>
              <input
                type="text" disabled={isNc}
                value={isNc ? '' : datos[`${grupo.prefijo}_unidad`] ?? ''}
                onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
                placeholder={isNc ? 'N/C' : ''}
                className={inputClass}
              />
            </div>
            {!grupo.sinTolerancia && <div />}
          </div>
        );
      })}
    </div>
  );
}

/* ========== PASO 2: Contenido Dinámico ========== */
function PasoContenidoDinamico({ datos, setDatos, campos, tipoContenido }) {
  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const tc = (tipoContenido || '').toLowerCase();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-gray-700 mb-3">Especificaciones del Contenido</p>
        <div className="grid grid-cols-2 gap-4">
          {(tc.includes('huevo') || tc.includes('fruta') || !tc.includes('vaso')) && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Peso del contenido {tc.includes('huevo') ? '(peso del huevo)' : tc.includes('fruta') ? '(peso de la fruta)' : ''}
              </label>
              <div className="flex gap-2">
                <input
                  type="number" step="any"
                  value={datos.peso_contenido_valor}
                  onChange={(e) => handleChange('peso_contenido_valor', e.target.value)}
                  placeholder="Ej: 60"
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
                <select
                  value={datos.peso_contenido_unidad}
                  onChange={(e) => handleChange('peso_contenido_unidad', e.target.value)}
                  className="w-20 px-2 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                  <option value="oz">oz</option>
                  <option value="lb">lb</option>
                </select>
              </div>
            </div>
          )}
          {(tc.includes('vaso') || tc.includes('pote')) && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Volumen del contenido {tc.includes('vaso') ? '(volumen del vaso)' : '(volumen del pote)'}
              </label>
              <div className="flex gap-2">
                <input
                  type="number" step="any"
                  value={datos.volumen_contenido_valor}
                  onChange={(e) => handleChange('volumen_contenido_valor', e.target.value)}
                  placeholder="Ej: 12"
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
                <select
                  value={datos.volumen_contenido_unidad}
                  onChange={(e) => handleChange('volumen_contenido_unidad', e.target.value)}
                  className="w-20 px-2 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  <option value="oz">oz</option>
                  <option value="ml">ml</option>
                  <option value="L">L</option>
                  <option value="gal">gal</option>
                </select>
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Calibre / Tamaño {tc.includes('huevo') ? '(AA, A, B, C)' : tc.includes('fruta') ? '(calibre de fruta)' : ''}
            </label>
            <input
              type="text"
              value={datos.calibre_contenido}
              onChange={(e) => handleChange('calibre_contenido', e.target.value)}
              placeholder={tc.includes('huevo') ? 'Ej: AA, A, B' : tc.includes('fruta') ? 'Ej: Cal. 18, Cal. 24' : 'Ej: Estándar'}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>
        </div>
      </div>

      <div className="border-t border-gray-100" />

      <div>
        <p className="text-sm font-semibold text-gray-700 mb-1">Geometría del Empaque</p>
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-3">
          Todos los campos de geometría son opcionales.
        </p>
        {campos.map((grupo) => {
          const isNc = !!datos[`${grupo.prefijo}_nc`];
          const inputClass = `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 ${
            isNc ? 'bg-gray-50 border-gray-100 text-gray-300 cursor-not-allowed' : 'border-gray-200'
          }`;
          return (
            <div key={grupo.prefijo} className="grid grid-cols-4 gap-3 items-end p-3 rounded-lg bg-gray-50 mb-2">
              <div className="col-span-4 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">{grupo.label}</span>
                <label className="flex items-center gap-1.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isNc}
                    onChange={() => setDatos((prev) => toggleNc(prev, grupo.prefijo))}
                    className="w-3.5 h-3.5 accent-amber-500"
                  />
                  <span className={`text-xs font-semibold ${isNc ? 'text-amber-600' : 'text-gray-400'}`}>N/C</span>
                </label>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valor</label>
                <input type="number" step="any" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_valor`] ?? ''}
                  onChange={(e) => setDatos((prev) => ({ ...prev, [`${grupo.prefijo}_valor`]: e.target.value }))}
                  className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
                <input type="number" step="any" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_tolerancia`] ?? ''}
                  onChange={(e) => setDatos((prev) => ({ ...prev, [`${grupo.prefijo}_tolerancia`]: e.target.value }))}
                  className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                <input type="text" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_unidad`] ?? ''}
                  onChange={(e) => setDatos((prev) => ({ ...prev, [`${grupo.prefijo}_unidad`]: e.target.value }))}
                  className={inputClass} />
              </div>
              <div />
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ========== PASO 3: Empaque ========== */
function PasoEmpaque({ datos, setDatos }) {
  function h(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Empaque</label>
          <input type="text" value={datos.tipo_empaque} onChange={(e) => h('tipo_empaque', e.target.value)}
            placeholder="Ej: Caja corrugada"
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Color Empaque</label>
          <input type="text" value={datos.color_empaque} onChange={(e) => h('color_empaque', e.target.value)}
            placeholder="Ej: Kraft"
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700">Dimensiones del empaque</p>
      <div className="grid grid-cols-3 gap-3">
        {[['alto_empaque_valor', 'Alto Valor', 'number'], ['alto_empaque_tolerancia', 'Tolerancia (±)', 'number'], ['alto_empaque_unidad', 'Unidad', 'text']].map(([campo, label, tipo]) => (
          <div key={campo}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input type={tipo} step={tipo === 'number' ? 'any' : undefined} value={datos[campo]}
              onChange={(e) => h(campo, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[['peso_empaque_valor', 'Peso Valor', 'number'], ['peso_empaque_tolerancia', 'Tolerancia (±)', 'number'], ['peso_empaque_unidad', 'Unidad', 'text']].map(([campo, label, tipo]) => (
          <div key={campo}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input type={tipo} step={tipo === 'number' ? 'any' : undefined} value={datos[campo]}
              onChange={(e) => h(campo, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
          </div>
        ))}
      </div>

      <p className="text-sm font-medium text-gray-700">Configuración de estiba</p>
      <div className="grid grid-cols-2 gap-4">
        {[['undidades_empaque', 'Unidades por empaque'], ['empaques_estiba', 'Empaques por estiba'], ['camas_estiba', 'Camas por estiba'], ['empaques_camas_estiba', 'Empaques por cama']].map(([campo, label]) => (
          <div key={campo}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input type="number" value={datos[campo]} onChange={(e) => h(campo, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ========== PASO 4: Microbiología ========== */
function PasoMicrobiologia({ datos, setDatos }) {
  function h(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const pares = [
    { prefijo: 'recuento_aerobico', label: 'Recuento aeróbico' },
    { prefijo: 'recuento_moho', label: 'Recuento de moho' },
    { prefijo: 'coliforme', label: 'Coliformes' },
    { prefijo: 'escherichia_coli', label: 'Escherichia coli' },
    { prefijo: 'salmonella_spp', label: 'Salmonella spp' },
  ];

  const metales = [
    { prefijo: 'cadmio', label: 'Cadmio' },
    { prefijo: 'plomo', label: 'Plomo' },
    { prefijo: 'mercurio', label: 'Mercurio' },
    { prefijo: 'cromo', label: 'Cromo' },
  ];

  const inputClass = (nc) =>
    `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 ${
      nc ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed' : 'border-gray-200'
    }`;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Parámetros Microbiológicos (valor / límite)</p>
        <div className="space-y-3">
          {pares.map((p) => {
            const nc = datos[`${p.prefijo}_nc`];
            return (
              <div key={p.prefijo} className="grid grid-cols-4 gap-3 items-end">
                <p className="text-sm text-gray-600">{p.label}</p>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Valor</label>
                  <input type="number" step="any" value={datos[`${p.prefijo}_valor`]}
                    onChange={(e) => h(`${p.prefijo}_valor`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Límite</label>
                  <input type="number" step="any" value={datos[`${p.prefijo}_limite`]}
                    onChange={(e) => h(`${p.prefijo}_limite`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div className="flex items-center gap-1.5 pb-1">
                  <input type="checkbox" checked={nc}
                    onChange={() => setDatos((prev) => toggleNc(prev, p.prefijo))}
                    className="w-4 h-4 rounded accent-amber-500" />
                  <span className="text-xs text-gray-500 select-none">N/C</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Metales Pesados (valor / unidad)</p>
        <div className="space-y-3">
          {metales.map((m) => {
            const nc = datos[`${m.prefijo}_nc`];
            return (
              <div key={m.prefijo} className="grid grid-cols-4 gap-3 items-end">
                <p className="text-sm text-gray-600">{m.label}</p>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Valor</label>
                  <input type="number" step="any" value={datos[`${m.prefijo}_valor`]}
                    onChange={(e) => h(`${m.prefijo}_valor`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                  <input type="text" value={datos[`${m.prefijo}_unidad`]}
                    onChange={(e) => h(`${m.prefijo}_unidad`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div className="flex items-center gap-1.5 pb-1">
                  <input type="checkbox" checked={nc}
                    onChange={() => setDatos((prev) => toggleNc(prev, m.prefijo))}
                    className="w-4 h-4 rounded accent-amber-500" />
                  <span className="text-xs text-gray-500 select-none">N/C</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ========== PASO 5: Manejo y Disposición ========== */
function PasoManejo({ datos, setDatos }) {
  function h(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const campos = [
    { id: 'uso', label: 'Uso', obligatorio: true, placeholder: 'Ej: Estuche para empaque de 12 huevos frescos de gallina.' },
    { id: 'manejo', label: 'Manejo', obligatorio: true, placeholder: 'Instrucciones de manipulación del producto.' },
    { id: 'almacenamiento', label: 'Almacenamiento', obligatorio: true, placeholder: 'Condiciones de almacenamiento.' },
    { id: 'transporte', label: 'Transporte', obligatorio: true, placeholder: 'Condiciones de transporte.' },
    { id: 'vida_util', label: 'Vida Útil', obligatorio: true, placeholder: 'Ej: 24 meses desde la fecha de fabricación.' },
    { id: 'inocuidad', label: 'Inocuidad', obligatorio: false, placeholder: 'Información de inocuidad.' },
    { id: 'disposicion_pt', label: 'Disposición', obligatorio: false, placeholder: 'Disposición del producto terminado.' },
    { id: 'garantias', label: 'Garantías', obligatorio: false, placeholder: 'Información de garantía.' },
    { id: 'manipulacion', label: 'Manipulación', obligatorio: false, placeholder: 'Instrucciones adicionales de manipulación.' },
  ];

  const tieneDatos = (campo) => datos[campo] && datos[campo].toString().trim().length > 0;

  return (
    <div className="space-y-4">
      {campos.map((campo) => (
        <div key={campo.id}>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">
              {campo.label} {campo.obligatorio && <span className="text-red-500">*</span>}
              <TipCampo campo={campo.id} />
            </label>
            {tieneDatos(campo.id) && (
              <span className="text-xs text-green-600 flex items-center gap-1">
                <Check size={10} /> Completado
              </span>
            )}
          </div>
          <textarea
            value={datos[campo.id]}
            onChange={(e) => h(campo.id, e.target.value)}
            placeholder={campo.placeholder}
            rows={2}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
        </div>
      ))}
    </div>
  );
}
