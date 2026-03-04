import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Save, AlertTriangle, Check } from 'lucide-react';
import api from '../../../lib/api';

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
  { id: 2, titulo: 'Contenido', descripcion: 'Propiedades del contenido (pilar, alvéolo, cavidad)' },
  { id: 3, titulo: 'Empaque y Estiba', descripcion: 'Configuración de empaque' },
  { id: 4, titulo: 'Microbiología', descripcion: 'Parámetros microbiológicos y metales pesados' },
  { id: 5, titulo: 'Manejo y Disposición', descripcion: 'Almacenamiento, transporte y uso' },
];

export default function FichaCrearPage() {
  const navigate = useNavigate();
  const [paso, setPaso] = useState(0);
  const [materiales, setMateriales] = useState([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  // Paso 0: Material y país
  const [materialId, setMaterialId] = useState('');
  const [codigoLocal, setCodigoLocal] = useState('');
  const [pais, setPais] = useState('');

  // Paso 1: Características
  const [caracteristicas, setCaracteristicas] = useState({
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
    api.get('/material').then((res) => setMateriales(res.data)).catch(console.error);
  }, []);

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
        usuario_creador: 'marco.agrusa',
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
    <div className="max-w-3xl mx-auto">
      <Link to="/fichas" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={16} /> Volver a fichas
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Nueva Ficha Técnica</h1>

      {/* Indicador de pasos */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
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

      {/* Contenido del paso */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">{PASOS[paso].titulo}</h2>
        <p className="text-sm text-gray-500 mb-6">{PASOS[paso].descripcion}</p>

        {paso === 0 && (
          <PasoMaterial
            materiales={materiales}
            materialId={materialId} setMaterialId={setMaterialId}
            codigoLocal={codigoLocal} setCodigoLocal={setCodigoLocal}
            pais={pais} setPais={setPais}
          />
        )}
        {paso === 1 && <PasoMedidas datos={caracteristicas} setDatos={setCaracteristicas} campos={CAMPOS_CARACTERISTICAS} />}
        {paso === 2 && <PasoMedidas datos={contenido} setDatos={setContenido} campos={CAMPOS_CONTENIDO} />}
        {paso === 3 && <PasoEmpaque datos={empaque} setDatos={setEmpaque} />}
        {paso === 4 && <PasoMicrobiologia datos={microbiologia} setDatos={setMicrobiologia} />}
        {paso === 5 && <PasoManejo datos={manejo} setDatos={setManejo} />}
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
  );
}

/* ========== PASO 0: Material y País ========== */
function PasoMaterial({ materiales, materialId, setMaterialId, codigoLocal, setCodigoLocal, pais, setPais }) {
  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Material Comercial <span className="text-red-500">*</span>
        </label>
        <select
          value={materialId}
          onChange={(e) => setMaterialId(e.target.value)}
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccionar material...</option>
          {materiales.map((m) => (
            <option key={m.id_material_corporativo} value={m.id_material_corporativo}>
              {m.nombre_corporativo} ({m.categoria || 'Sin categoría'})
            </option>
          ))}
        </select>
      </div>
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
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            País <span className="text-red-500">*</span>
          </label>
          <select
            value={pais}
            onChange={(e) => setPais(e.target.value)}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            <p className="text-sm font-medium text-gray-700">{grupo.label}</p>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Valor</label>
            <input
              type="number"
              step="any"
              value={datos[`${grupo.prefijo}_valor`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
            <input
              type="number"
              step="any"
              value={datos[`${grupo.prefijo}_tolerancia`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Unidad</label>
            <input
              type="text"
              value={datos[`${grupo.prefijo}_unidad`]}
              onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Empaque <span className="text-red-500">*</span></label>
          <input type="text" value={datos.tipo_empaque} onChange={(e) => h('tipo_empaque', e.target.value)}
            placeholder="Ej: Caja corrugada" className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Color Empaque</label>
          <input type="text" value={datos.color_empaque} onChange={(e) => h('color_empaque', e.target.value)}
            placeholder="Ej: Kraft" className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700 mt-4">Dimensiones del empaque</p>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Alto Valor</label>
          <input type="number" step="any" value={datos.alto_empaque_valor} onChange={(e) => h('alto_empaque_valor', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
          <input type="number" step="any" value={datos.alto_empaque_tolerancia} onChange={(e) => h('alto_empaque_tolerancia', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidad</label>
          <input type="text" value={datos.alto_empaque_unidad} onChange={(e) => h('alto_empaque_unidad', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Peso Valor</label>
          <input type="number" step="any" value={datos.peso_empaque_valor} onChange={(e) => h('peso_empaque_valor', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
          <input type="number" step="any" value={datos.peso_empaque_tolerancia} onChange={(e) => h('peso_empaque_tolerancia', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidad</label>
          <input type="text" value={datos.peso_empaque_unidad} onChange={(e) => h('peso_empaque_unidad', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700 mt-4">Configuración de estiba</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidades por empaque</label>
          <input type="number" value={datos.undidades_empaque} onChange={(e) => h('undidades_empaque', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Empaques por estiba</label>
          <input type="number" value={datos.empaques_estiba} onChange={(e) => h('empaques_estiba', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Camas por estiba</label>
          <input type="number" value={datos.camas_estiba} onChange={(e) => h('camas_estiba', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Empaques por cama</label>
          <input type="number" value={datos.empaques_camas_estiba} onChange={(e) => h('empaques_camas_estiba', e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
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
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Límite</label>
                <input type="number" step="any" value={datos[`${p.prefijo}_limite`]} onChange={(e) => h(`${p.prefijo}_limite`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
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
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                <input type="text" value={datos[`${m.prefijo}_unidad`]} onChange={(e) => h(`${m.prefijo}_unidad`, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
          ))}
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

  return (
    <div className="space-y-4">
      {campos.map((campo) => (
        <div key={campo.id}>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {campo.label} {campo.obligatorio && <span className="text-red-500">*</span>}
          </label>
          <textarea
            value={datos[campo.id]}
            onChange={(e) => h(campo.id, e.target.value)}
            placeholder={campo.placeholder}
            rows={2}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
      ))}
    </div>
  );
}

/* ========== CONSTANTES DE CAMPOS ========== */
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

const CAMPOS_CONTENIDO = [
  { prefijo: 'profundidad_pilar', label: 'Profundidad Pilar (Huevos/Otros)' },
  { prefijo: 'diametro_alveolo', label: 'Diámetro Alvéolo (Huevos/Otros)' },
  { prefijo: 'profundidad_cavidad', label: 'Profundidad Cavidad (Frutas)' },
  { prefijo: 'diametro_cavidad', label: 'Diámetro Cavidad (Frutas)' },
];