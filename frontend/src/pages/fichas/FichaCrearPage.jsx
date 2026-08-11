import { useState, useEffect, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Save, Check, Sparkles, Info } from 'lucide-react';
import api from '../../../lib/api';
import { AsistenteIA, IndicadorProgreso } from './AsistenteIA';
import { PAISES } from './paises';
import { tieneValores } from './fichaCampos';
import { PasoMedidas, PasoContenidoDinamico, PasoEmpaque, PasoMicrobiologia, PasoManejo } from './PasosFicha';

const PASOS = [
  { id: 0, titulo: 'Material y País', descripcion: 'Selecciona el material asociado' },
  { id: 1, titulo: 'Características', descripcion: 'Dimensiones, peso y propiedades físicas' },
  { id: 2, titulo: 'Contenido', descripcion: 'Propiedades según tipo de contenido' },
  { id: 3, titulo: 'Empaque y Estiba', descripcion: 'Configuración de empaque' },
  { id: 4, titulo: 'Inocuidad', descripcion: 'Parámetros microbiológicos y metales pesados' },
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

export default function FichaCrearPage() {
  const navigate = useNavigate();
  const [paso, setPaso] = useState(0);
  const [materiales, setMateriales] = useState([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [mostrarAsistente, setMostrarAsistente] = useState(true);

  // Paso 0
  const [materialId, setMaterialId] = useState('');
  const [codigoLocal, setCodigoLocal] = useState('');
  const [nombreLocal, setNombreLocal] = useState('');
  const [pais, setPais] = useState('');

  // Paso 1: Características
  const [caracteristicas, setCaracteristicas] = useState({
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
  });

  // Paso 2: Contenido
  const [contenido, setContenido] = useState({
    // Especificaciones del contenido
    peso_contenido_valor: '', peso_contenido_unidad: 'g',
    volumen_contenido_valor: '', volumen_contenido_unidad: 'oz',
    calibre_contenido: '',
    // Geometría
    profundidad_pilar_valor: '', profundidad_pilar_tolerancia: '', profundidad_pilar_unidad: 'mm', profundidad_pilar_nc: false,
    diametro_alveolo_valor: '', diametro_alveolo_tolerancia: '', diametro_alveolo_unidad: 'mm', diametro_alveolo_nc: false,
    profundidad_cavidad_valor: '', profundidad_cavidad_tolerancia: '', profundidad_cavidad_unidad: 'mm', profundidad_cavidad_nc: false,
    diametro_cavidad_valor: '', diametro_cavidad_tolerancia: '', diametro_cavidad_unidad: 'mm', diametro_cavidad_nc: false,
    ancho_cavidad_valor: '', ancho_cavidad_tolerancia: '', ancho_cavidad_unidad: 'mm', ancho_cavidad_nc: false,
    largo_cavidad_valor: '', largo_cavidad_tolerancia: '', largo_cavidad_unidad: 'mm', largo_cavidad_nc: false,
  });

  // Paso 3: Empaque
  const [empaque, setEmpaque] = useState({
    tipo_empaque: '', color_empaque: '',
    alto_empaque_valor: '', alto_empaque_tolerancia: '', alto_empaque_unidad: 'cm',
    peso_empaque_valor: '', peso_empaque_tolerancia: '', peso_empaque_unidad: 'Kg',
    undidades_empaque: '', empaques_estiba: '', camas_estiba: '', empaques_camas_estiba: '',
  });

  // Paso 4: Microbiología
  const [microbiologia, setMicrobiologia] = useState({
    recuento_aerobico_valor: '', recuento_aerobico_limite: '', recuento_aerobico_nc: false,
    recuento_moho_valor: '', recuento_moho_limite: '', recuento_moho_nc: false,
    coliforme_valor: '', coliforme_limite: '', coliforme_nc: false,
    escherichia_coli_valor: '', escherichia_coli_limite: '', escherichia_coli_nc: false,
    salmonella_spp_valor: '', salmonella_spp_limite: '', salmonella_spp_nc: false,
    cadmio_valor: '', cadmio_unidad: 'mg/Kg', cadmio_nc: false,
    plomo_valor: '', plomo_unidad: 'mg/Kg', plomo_nc: false,
    mercurio_valor: '', mercurio_unidad: 'mg/Kg', mercurio_nc: false,
    cromo_valor: '', cromo_unidad: 'mg/Kg', cromo_nc: false,
  });

  // Paso 5: Manejo
  const [manejo, setManejo] = useState({
    manejo: '', almacenamiento: '', transporte: '',
    inocuidad: '', disposicion_pt: '', garantias: '',
    manipulacion: '', vida_util: '', uso: '',
  });

  useEffect(() => {
    api.get('/material').then((res) => {
      const activos = res.data.filter((m) => m.estado_material !== 'Inactivo');
      setMateriales(activos);
    }).catch(console.error);
  }, []);

  // Determinar tipo de contenido del material seleccionado
  const materialSeleccionado = useMemo(
    () => materiales.find((m) => m.id_material_corporativo === materialId),
    [materiales, materialId]
  );

  const tipoContenido = useMemo(() => {
    if (!materialSeleccionado) return null;
    return materialSeleccionado.contenido || 'Otro';
  }, [materialSeleccionado]);

  const tipoCategoria = useMemo(() => {
    if (!materialSeleccionado) return null;
    return materialSeleccionado.categoria || '';
  }, [materialSeleccionado]);

  // Campos de características — deflexion para Separadores, resistencia para Portavasos/Bandejas,
  // ninguno para Estuches y otros
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

  // Campos de contenido — según tipo de contenido del material
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
    // Demás contenidos: profundidad + ancho + largo de cavidad
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
        if (v === true) limpio[k] = true;  // solo enviar cuando está activo
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

  // Callback para aplicar sugerencias del asistente IA
  function aplicarSugerencia(campo, valor) {
    if (paso === 1) {
      setCaracteristicas((prev) => ({ ...prev, [campo]: valor }));
    } else if (paso === 2) {
      setContenido((prev) => ({ ...prev, [campo]: valor }));
    } else if (paso === 5) {
      setManejo((prev) => ({ ...prev, [campo]: valor }));
    }
  }

  // Datos actuales para el asistente según el paso
  function getDatosActuales() {
    if (paso === 1) return caracteristicas;
    if (paso === 2) return contenido;
    if (paso === 5) return manejo;
    return {};
  }

  function construirPayload() {
    return {
      id_material_corporativo: materialId,
      codigo_material_local: codigoLocal || null,
      nombre_local_material: nombreLocal || null,
      // usuario_creador lo resuelve el backend desde el token JWT.
      pais: pais || null,
      caracteristicas: tieneValores(caracteristicas) ? limpiarSeccion(caracteristicas) : null,
      caracteristicas_contenido: tieneValores(contenido) ? limpiarSeccion(contenido) : null,
      empaque_estiba: tieneValores(empaque) ? limpiarSeccion(empaque) : null,
      microbiologia: tieneValores(microbiologia) ? limpiarSeccion(microbiologia) : null,
      manejo_disposicion: tieneValores(manejo) ? limpiarSeccion(manejo) : null,
    };
  }

  async function guardarBorrador() {
    setError(null);
    if (!materialId) { setError('Selecciona un material para guardar el borrador'); return; }
    setGuardando(true);
    try {
      const res = await api.post('/ficha', construirPayload());
      navigate(`/fichas/${res.data.id_ficha}`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar el borrador';
      setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
    } finally {
      setGuardando(false);
    }
  }

  async function handleSubmit() {
    setError(null);
    if (!materialId) { setError('Selecciona un material'); return; }
    if (!codigoLocal.trim()) { setError('El código de material local es obligatorio'); return; }
    if (!pais) { setError('Selecciona un país'); return; }
    if (!nombreLocal.trim()) { setError('El nombre local del material es obligatorio'); return; }
    if (!tieneValores(caracteristicas)) { setError('Completa al menos una característica física'); return; }
    if (!manejo.manejo || !manejo.almacenamiento || !manejo.transporte || !manejo.vida_util || !manejo.uso) {
      setError('Manejo y Disposición requiere: uso, manejo, almacenamiento, transporte y vida útil');
      return;
    }

    setGuardando(true);
    try {
      const res = await api.post('/ficha', construirPayload());
      const nuevaFichaId = res.data.id_ficha;
      const irAImagenes = window.confirm('Ficha creada exitosamente. ¿Deseas subir imágenes del producto ahora?');
      if (irAImagenes) {
        navigate(`/fichas/${nuevaFichaId}?tab=imagenes`);
      } else {
        navigate(`/fichas/${nuevaFichaId}`);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al crear la ficha';
      setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <Link to="/fichas" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={16} /> Volver a fichas
      </Link>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Nueva Ficha Técnica</h1>
        <button
          onClick={() => setMostrarAsistente(!mostrarAsistente)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            mostrarAsistente ? 'bg-[#29b34b]/10 text-[#044926]' : 'bg-gray-100 text-gray-500'
          }`}
        >
          <Sparkles size={14} />
          Asistente IA {mostrarAsistente ? 'ON' : 'OFF'}
        </button>
      </div>

      {/* Indicador de progreso general */}
      <IndicadorProgreso
        datos={{
          materialId, codigoLocal, pais,
          caracteristicas, contenido, empaque, microbiologia, manejo,
        }}
      />

      {/* Indicador de pasos */}
      <div className="flex items-center gap-2 my-6 overflow-x-auto pb-2">
        {PASOS.map((p, i) => (
          <button
            key={p.id}
            onClick={() => setPaso(i)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              paso === i
                ? 'bg-[#29b34b] text-white'
                : paso > i
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {paso > i ? <Check size={12} /> : <span>{i + 1}</span>}
            {p.titulo}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Formulario principal */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-1">{PASOS[paso].titulo}</h2>
            <p className="text-sm text-gray-500 mb-6">{PASOS[paso].descripcion}</p>

            {/* Info banner tipo contenido en pasos relevantes */}
            {paso >= 1 && paso <= 2 && tipoContenido && (
              <div className="flex items-center gap-2 p-3 bg-[#044926]/5 border border-[#29b34b]/20 rounded-lg mb-6 text-sm">
                <Info size={16} className="text-[#29b34b] shrink-0" />
                <p className="text-[#044926]">
                  Material tipo <strong>{tipoContenido}</strong>
                  {paso === 2 && ' — todos los campos de contenido son opcionales, llena solo los que apliquen'}
                </p>
              </div>
            )}

            {paso === 0 && (
              <PasoMaterial
                materiales={materiales}
                materialId={materialId} setMaterialId={setMaterialId}
                codigoLocal={codigoLocal} setCodigoLocal={setCodigoLocal}
                nombreLocal={nombreLocal} setNombreLocal={setNombreLocal}
                pais={pais} setPais={setPais}
                materialSeleccionado={materialSeleccionado}
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
                    className="w-full max-w-xs px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
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

          {/* Navegación pasos */}
          <div className="flex items-center justify-between gap-3">
            <button
              onClick={() => setPaso((p) => Math.max(0, p - 1))}
              disabled={paso === 0}
              className="flex items-center gap-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-30 transition-colors"
            >
              <ArrowLeft size={16} /> Anterior
            </button>

            <div className="flex items-center gap-2">
              {/* Guardar borrador — siempre visible, solo requiere material */}
              <button
                onClick={guardarBorrador}
                disabled={guardando || !materialId}
                className="flex items-center gap-1.5 px-4 py-2.5 border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-40 transition-colors"
                title="Guarda lo que llevas sin validar campos obligatorios"
              >
                <Save size={15} />
                {guardando ? 'Guardando...' : 'Guardar borrador'}
              </button>

              {paso < PASOS.length - 1 ? (
                <button
                  onClick={() => setPaso((p) => Math.min(PASOS.length - 1, p + 1))}
                  className="flex items-center gap-1 px-4 py-2.5 bg-[#29b34b] text-white rounded-lg text-sm font-medium hover:bg-[#044926] transition-colors"
                >
                  Siguiente <ArrowRight size={16} />
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={guardando}
                  className="flex items-center gap-2 px-6 py-2.5 bg-[#044926] text-white rounded-lg text-sm font-medium hover:bg-[#29b34b] disabled:opacity-50 transition-colors"
                >
                  <Save size={16} />
                  {guardando ? 'Creando...' : 'Crear Ficha Técnica'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Panel lateral: Asistente IA */}
        {mostrarAsistente && (
          <div className="space-y-4">
            <AsistenteIA
              contenidoMaterial={tipoContenido}
              paso={paso}
              datos={getDatosActuales()}
              onSugerencia={aplicarSugerencia}
              materialId={materialId}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/* ========== PASO 0: Material y País ========== */
function PasoMaterial({ materiales, materialId, setMaterialId, codigoLocal, setCodigoLocal, nombreLocal, setNombreLocal, pais, setPais, materialSeleccionado }) {
  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Material Comercial <span className="text-red-500">*</span>
        </label>
        <select
          value={materialId}
          onChange={(e) => setMaterialId(e.target.value)}
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        >
          <option value="">Seleccionar material...</option>
          {materiales.map((m) => (
            <option key={m.id_material_corporativo} value={m.id_material_corporativo}>
              {m.nombre_corporativo} ({m.categoria || 'Sin categoría'}) — {m.contenido || 'Sin contenido'}
            </option>
          ))}
        </select>
      </div>

      {/* Info del material seleccionado */}
      {materialSeleccionado && (
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase">Material seleccionado</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <span className="text-gray-500">Categoría:</span>
            <span className="text-gray-900 font-medium">{materialSeleccionado.categoria || '—'}</span>
            <span className="text-gray-500">Contenido:</span>
            <span className="text-gray-900 font-medium">{materialSeleccionado.contenido || '—'}</span>
            <span className="text-gray-500">Material Base:</span>
            <span className="text-gray-900 font-medium">{materialSeleccionado.material_base || '—'}</span>
            <span className="text-gray-500">Estado:</span>
            <span className="text-gray-900 font-medium">{materialSeleccionado.estado_material}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Código Material Local <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={codigoLocal}
            onChange={(e) => setCodigoLocal(e.target.value)}
            placeholder="Ej: EST-12SV-CO"
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            País <span className="text-red-500">*</span>
          </label>
          <select
            value={pais}
            onChange={(e) => setPais(e.target.value)}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
          >
            <option value="">Seleccionar país...</option>
            {PAISES.map((p) => (
              <option key={p.code} value={p.code}>{p.nombre}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nombre Local del Material</label>
        <input
          type="text"
          value={nombreLocal}
          onChange={(e) => setNombreLocal(e.target.value)}
          placeholder="Ej: Estuche 12 sin ventana (nombre usado localmente)"
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        />
      </div>
    </div>
  );
}
