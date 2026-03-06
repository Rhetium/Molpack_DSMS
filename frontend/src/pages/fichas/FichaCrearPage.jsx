import { useState, useEffect, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Save, Check, Sparkles, Info } from 'lucide-react';
import api from '../../../lib/api';
import { useAuth } from '../../../lib/auth';
import { AsistenteIA, IndicadorProgreso, TipCampo } from './AsistenteIA';

const PAISES = [
  { code: 'CO', nombre: 'Colombia' },
  { code: 'VE', nombre: 'Venezuela' },
  { code: 'EC', nombre: 'Ecuador' },
  { code: 'PE', nombre: 'Perú' },
  { code: 'CR', nombre: 'Costa Rica' },
  { code: 'GT', nombre: 'Guatemala' },
  { code: 'HN', nombre: 'Honduras' },
  { code: 'SV', nombre: 'El Salvador' },
];

const PASOS = [
  { id: 0, titulo: 'Material y País', descripcion: 'Selecciona el material asociado' },
  { id: 1, titulo: 'Características', descripcion: 'Dimensiones, peso y propiedades físicas' },
  { id: 2, titulo: 'Contenido', descripcion: 'Propiedades según tipo de contenido' },
  { id: 3, titulo: 'Empaque y Estiba', descripcion: 'Configuración de empaque' },
  { id: 4, titulo: 'Microbiología', descripcion: 'Parámetros microbiológicos y metales pesados' },
  { id: 5, titulo: 'Manejo y Disposición', descripcion: 'Almacenamiento, transporte y uso' },
];

const CAMPOS_CARACTERISTICAS = [
  { prefijo: 'dimensiones_largo', label: 'Largo' },
  { prefijo: 'dimensiones_ancho', label: 'Ancho' },
  { prefijo: 'dimensiones_alto', label: 'Alto' },
  { prefijo: 'peso', label: 'Peso' },
  { prefijo: 'ruptura', label: 'Ruptura' },
  { prefijo: 'tiempo_encolado', label: 'Tiempo de Encolado' },
  { prefijo: 'porcentaje_absorcion', label: 'Porcentaje de Absorción' },
  { prefijo: 'deflexion_interna', label: 'Deflexión Interna' },
  { prefijo: 'deflexion_externa', label: 'Deflexión Externa' },
];

export default function FichaCrearPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [paso, setPaso] = useState(0);
  const [materiales, setMateriales] = useState([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [mostrarAsistente, setMostrarAsistente] = useState(true);

  // Paso 0
  const [materialId, setMaterialId] = useState('');
  const [codigoLocal, setCodigoLocal] = useState('');
  const [pais, setPais] = useState('');

  // Paso 1: Características
  const [caracteristicas, setCaracteristicas] = useState({
    color: '',
    dimensiones_largo_valor: '', dimensiones_largo_tolerancia: '', dimensiones_largo_unidad: 'cm',
    dimensiones_ancho_valor: '', dimensiones_ancho_tolerancia: '', dimensiones_ancho_unidad: 'cm',
    dimensiones_alto_valor: '', dimensiones_alto_tolerancia: '', dimensiones_alto_unidad: 'cm',
    peso_valor: '', peso_tolerancia: '', peso_unidad: 'g',
    ruptura_valor: '', ruptura_tolerancia: '', ruptura_unidad: 'kgf',
    tiempo_encolado_valor: '', tiempo_encolado_tolerancia: '', tiempo_encolado_unidad: 's',
    porcentaje_absorcion_valor: '', porcentaje_absorcion_tolerancia: '', porcentaje_absorcion_unidad: '%',
    deflexion_interna_valor: '', deflexion_interna_tolerancia: '', deflexion_interna_unidad: 'mm',
    deflexion_externa_valor: '', deflexion_externa_tolerancia: '', deflexion_externa_unidad: 'mm',
  });

  // Paso 2: Contenido
  const [contenido, setContenido] = useState({
    profundidad_pilar_valor: '', profundidad_pilar_tolerancia: '', profundidad_pilar_unidad: 'mm',
    diametro_alveolo_valor: '', diametro_alveolo_tolerancia: '', diametro_alveolo_unidad: 'mm',
    profundidad_cavidad_valor: '', profundidad_cavidad_tolerancia: '', profundidad_cavidad_unidad: 'mm',
    diametro_cavidad_valor: '', diametro_cavidad_tolerancia: '', diametro_cavidad_unidad: 'mm',
  });

  // Paso 3: Empaque
  const [empaque, setEmpaque] = useState({
    tipo_empaque: '', color_empaque: '',
    alto_empaque_valor: '', alto_empaque_tolerancia: '', alto_empaque_unidad: 'cm',
    peso_empaque_valor: '', peso_empaque_tolerancia: '', peso_empaque_unidad: 'kg',
    undidades_empaque: '', empaques_estiba: '', camas_estiba: '', empaques_camas_estiba: '',
  });

  // Paso 4: Microbiología
  const [microbiologia, setMicrobiologia] = useState({
    recuento_aerobico_valor: '', recuento_aerobico_limite: '',
    recuento_moho_valor: '', recuento_moho_limite: '',
    coliforme_valor: '', coliforme_limite: '',
    escherichia_coli_valor: '', escherichia_coli_limite: '',
    salmonella_spp_valor: '', salmonella_spp_limite: '',
    cadmio_valor: '', cadmio_unidad: 'mg/kg',
    plomo_valor: '', plomo_unidad: 'mg/kg',
    mercurio_valor: '', mercurio_unidad: 'mg/kg',
    cromo_valor: '', cromo_unidad: 'mg/kg',
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

  // Campos de contenido — TODOS opcionales, orden según tipo de contenido
  const camposContenidoDinamicos = useMemo(() => {
    const c = (tipoContenido || '').toLowerCase();
    if (c.includes('fruta')) {
      return [
        { prefijo: 'profundidad_cavidad', label: 'Profundidad Cavidad' },
        { prefijo: 'diametro_cavidad', label: 'Diámetro Cavidad' },
        { prefijo: 'profundidad_pilar', label: 'Profundidad Pilar' },
        { prefijo: 'diametro_alveolo', label: 'Diámetro Alvéolo' },
      ];
    }
    if (c.includes('huevo')) {
      return [
        { prefijo: 'profundidad_pilar', label: 'Profundidad Pilar' },
        { prefijo: 'diametro_alveolo', label: 'Diámetro Alvéolo' },
        { prefijo: 'profundidad_cavidad', label: 'Profundidad Cavidad' },
        { prefijo: 'diametro_cavidad', label: 'Diámetro Cavidad' },
      ];
    }
    // Potes de pintura, Vasos, Industrial, Otro
    return [
      { prefijo: 'profundidad_pilar', label: 'Profundidad Pilar' },
      { prefijo: 'diametro_alveolo', label: 'Diámetro Alvéolo' },
      { prefijo: 'profundidad_cavidad', label: 'Profundidad Cavidad' },
      { prefijo: 'diametro_cavidad', label: 'Diámetro Cavidad' },
    ];
  }, [tipoContenido]);

  function limpiarSeccion(datos) {
    const limpio = {};
    for (const [k, v] of Object.entries(datos)) {
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

  function tieneValores(datos) {
    return Object.values(datos).some((v) => v !== '' && v !== null && v !== undefined);
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

  async function handleSubmit() {
    setError(null);
    if (!materialId) { setError('Selecciona un material'); return; }
    if (!codigoLocal.trim()) { setError('El código de material local es obligatorio'); return; }
    if (!pais) { setError('Selecciona un país'); return; }
    if (!manejo.manejo || !manejo.almacenamiento || !manejo.transporte || !manejo.vida_util || !manejo.uso) {
      setError('Los campos obligatorios de Manejo y Disposición son: manejo, almacenamiento, transporte, vida útil y uso');
      return;
    }

    setGuardando(true);
    try {
      const payload = {
        id_material_corporativo: materialId,
        codigo_material_local: codigoLocal,
        usuario_creador: user?.usuario || 'sistema',
        pais,
        caracteristicas: tieneValores(caracteristicas) ? limpiarSeccion(caracteristicas) : null,
        caracteristicas_contenido: tieneValores(contenido) ? limpiarSeccion(contenido) : null,
        empaque_estiba: tieneValores(empaque) ? limpiarSeccion(empaque) : null,
        microbiologia: tieneValores(microbiologia) ? limpiarSeccion(microbiologia) : null,
        manejo_disposicion: limpiarSeccion(manejo),
      };

      const res = await api.post('/ficha', payload);
      navigate(`/fichas/${res.data.id_ficha}`);
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
                <PasoMedidas datos={caracteristicas} setDatos={setCaracteristicas} campos={CAMPOS_CARACTERISTICAS} />
              </div>
            )}
            {paso === 2 && <PasoContenidoDinamico datos={contenido} setDatos={setContenido} campos={camposContenidoDinamicos} tipoContenido={tipoContenido} />}
            {paso === 3 && <PasoEmpaque datos={empaque} setDatos={setEmpaque} />}
            {paso === 4 && <PasoMicrobiologia datos={microbiologia} setDatos={setMicrobiologia} />}
            {paso === 5 && <PasoManejo datos={manejo} setDatos={setManejo} tipoContenido={tipoContenido} onSugerencia={aplicarSugerencia} />}
          </div>

          {/* Navegación pasos */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setPaso((p) => Math.max(0, p - 1))}
              disabled={paso === 0}
              className="flex items-center gap-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-30 transition-colors"
            >
              <ArrowLeft size={16} /> Anterior
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
function PasoMaterial({ materiales, materialId, setMaterialId, codigoLocal, setCodigoLocal, pais, setPais, materialSeleccionado }) {
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
              <option key={p.code} value={p.nombre}>{p.nombre}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

/* ========== PASO GENÉRICO: Medidas (valor/tolerancia/unidad) ========== */
function PasoMedidas({ datos, setDatos, campos }) {
  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  return (
    <div className="space-y-4">
      {campos.map((grupo) => (
        <div key={grupo.prefijo} className="grid grid-cols-4 gap-3 items-end">
          <div className="col-span-4">
            <p className="text-sm font-medium text-gray-700">
              {grupo.label}
              <TipCampo campo={grupo.prefijo} />
            </p>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Valor</label>
            <input
              type="number" step="any"
              value={datos[`${grupo.prefijo}_valor`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
            <input
              type="number" step="any"
              value={datos[`${grupo.prefijo}_tolerancia`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Unidad</label>
            <input
              type="text"
              value={datos[`${grupo.prefijo}_unidad`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div />
        </div>
      ))}
    </div>
  );
}

/* ========== PASO 2: Contenido Dinámico según tipo ========== */
function PasoContenidoDinamico({ datos, setDatos, campos, tipoContenido }) {
  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
        Todos los campos de esta sección son opcionales. Llena solo los que apliquen a este producto.
      </p>
      {campos.map((grupo) => (
        <div
          key={grupo.prefijo}
          className="grid grid-cols-4 gap-3 items-end p-3 rounded-lg bg-gray-50"
        >
          <div className="col-span-4 flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">
              {grupo.label}
              <TipCampo campo={grupo.prefijo} />
            </span>
            <span className="text-xs text-gray-400">Opcional</span>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Valor</label>
            <input
              type="number" step="any"
              value={datos[`${grupo.prefijo}_valor`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
            <input
              type="number" step="any"
              value={datos[`${grupo.prefijo}_tolerancia`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Unidad</label>
            <input
              type="text"
              value={datos[`${grupo.prefijo}_unidad`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
            />
          </div>
          <div />
        </div>
      ))}
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
            placeholder="Ej: Caja corrugada" className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Color Empaque</label>
          <input type="text" value={datos.color_empaque} onChange={(e) => h('color_empaque', e.target.value)}
            placeholder="Ej: Kraft" className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700 mt-4">Dimensiones del empaque</p>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Alto Valor</label>
          <input type="number" step="any" value={datos.alto_empaque_valor} onChange={(e) => h('alto_empaque_valor', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
          <input type="number" step="any" value={datos.alto_empaque_tolerancia} onChange={(e) => h('alto_empaque_tolerancia', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidad</label>
          <input type="text" value={datos.alto_empaque_unidad} onChange={(e) => h('alto_empaque_unidad', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Peso Valor</label>
          <input type="number" step="any" value={datos.peso_empaque_valor} onChange={(e) => h('peso_empaque_valor', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
          <input type="number" step="any" value={datos.peso_empaque_tolerancia} onChange={(e) => h('peso_empaque_tolerancia', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidad</label>
          <input type="text" value={datos.peso_empaque_unidad} onChange={(e) => h('peso_empaque_unidad', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700 mt-4">Configuración de estiba</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidades por empaque</label>
          <input type="number" value={datos.undidades_empaque} onChange={(e) => h('undidades_empaque', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Empaques por estiba</label>
          <input type="number" value={datos.empaques_estiba} onChange={(e) => h('empaques_estiba', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Camas por estiba</label>
          <input type="number" value={datos.camas_estiba} onChange={(e) => h('camas_estiba', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Empaques por cama</label>
          <input type="number" value={datos.empaques_camas_estiba} onChange={(e) => h('empaques_camas_estiba', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
        </div>
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

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Parámetros Microbiológicos (valor / límite)</p>
        <div className="space-y-3">
          {pares.map((p) => (
            <div key={p.prefijo} className="grid grid-cols-3 gap-3 items-end">
              <p className="text-sm text-gray-600">{p.label}</p>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valor</label>
                <input type="number" step="any" value={datos[`${p.prefijo}_valor`]} onChange={(e) => h(`${p.prefijo}_valor`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Límite</label>
                <input type="number" step="any" value={datos[`${p.prefijo}_limite`]} onChange={(e) => h(`${p.prefijo}_limite`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Metales Pesados (valor / unidad)</p>
        <div className="space-y-3">
          {metales.map((m) => (
            <div key={m.prefijo} className="grid grid-cols-3 gap-3 items-end">
              <p className="text-sm text-gray-600">{m.label}</p>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valor</label>
                <input type="number" step="any" value={datos[`${m.prefijo}_valor`]} onChange={(e) => h(`${m.prefijo}_valor`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                <input type="text" value={datos[`${m.prefijo}_unidad`]} onChange={(e) => h(`${m.prefijo}_unidad`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ========== PASO 5: Manejo y Disposición con sugerencias ========== */
function PasoManejo({ datos, setDatos, tipoContenido, onSugerencia }) {
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

  const tieneDatos = (campo) => datos[campo] && datos[campo].trim().length > 0;

  return (
    <div className="space-y-4">
      {campos.map((campo) => (
        <div key={campo.id} className={`rounded-lg transition-colors ${
          campo.obligatorio && !tieneDatos(campo.id) ? 'bg-red-50/50 p-3 border border-red-100' : ''
        }`}>
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
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b] resize-none"
          />
        </div>
      ))}
    </div>
  );
}