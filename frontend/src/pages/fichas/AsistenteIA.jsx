import { useState, useEffect } from 'react';
import { Sparkles, ChevronDown, ChevronUp, CheckCircle, AlertTriangle, Info, Database, Calculator } from 'lucide-react';
import api from '../../../lib/api';

/**
 * Asistente IA para formularios de fichas técnicas.
 * 
 * Sistema híbrido de rangos:
 * 1. Intenta cargar rangos dinámicos desde fichas existentes del mismo material
 * 2. Si no hay datos suficientes (<2 fichas), usa rangos estáticos amplios como fallback
 * 3. Muestra al usuario de dónde vienen los rangos
 */

// ========== RANGOS ESTÁTICOS (FALLBACK) ==========
// Rangos amplios para todos los tipos de producto.
// Se usan cuando no hay datos históricos suficientes.
const RANGOS_ESTATICOS = {
  dimensiones_largo_valor: { min: 100, max: 500, unidad: 'mm', sugerido: 300 },
  dimensiones_ancho_valor: { min: 80, max: 400, unidad: 'mm', sugerido: 250 },
  dimensiones_alto_valor: { min: 10, max: 120, unidad: 'mm', sugerido: 50 },
  peso_valor: { min: 5, max: 200, unidad: 'g', sugerido: 50 },
  ruptura_valor: { min: 0.5, max: 25, unidad: 'Kgf', sugerido: 13 },
  profundidad_pilar_valor: { min: 30, max: 60, unidad: 'mm', sugerido: 48 },
  diametro_alveolo_valor: { min: 25, max: 70, unidad: 'mm', sugerido: 45 },
  profundidad_cavidad_valor: { min: 5, max: 80, unidad: 'mm', sugerido: 35 },
  diametro_cavidad_valor: { min: 20, max: 200, unidad: 'mm', sugerido: 80 },
};

function getRangosEstaticos() {
  return RANGOS_ESTATICOS;
}

// ========== TIPS CONTEXTUALES ==========
const TIPS_CAMPOS = {
  dimensiones_largo: 'Largo total del producto. Medir la dimensión mayor del estuche o bandeja.',
  dimensiones_ancho: 'Ancho total del producto. Medir la segunda dimensión mayor.',
  dimensiones_alto: 'Alto total incluyendo pilares o cavidades.',
  peso: 'Peso en seco del producto sin contenido. Usar balanza calibrada.',
  ruptura: 'Fuerza de ruptura medida con dinamómetro. Valor mínimo aceptable.',
  tiempo_encolado: 'Tiempo que tarda el adhesivo en secar. Medir en condiciones estándar (20°C, 60% HR).',
  porcentaje_absorcion: 'Capacidad de absorción de agua del material. Método de inmersión.',
  deflexion_interna: 'Deflexión medida en la cara interna. Indicador de rigidez.',
  deflexion_externa: 'Deflexión medida en la cara externa.',
  profundidad_pilar: 'Profundidad del pilar que soporta el huevo. Crítico para protección.',
  diametro_alveolo: 'Diámetro del alvéolo donde se aloja el huevo. Debe contener huevos tipo AA.',
  profundidad_cavidad: 'Profundidad de la cavidad para la fruta. Varía según calibre.',
  diametro_cavidad: 'Diámetro de la cavidad. Ajustar al calibre de fruta objetivo.',
  manejo: 'Instrucciones para manipulación segura del producto.',
  almacenamiento: 'Condiciones de almacenamiento: temperatura, humedad, apilamiento.',
  transporte: 'Requisitos de transporte: vehículo cerrado, protección contra lluvia.',
  vida_util: 'Período de garantía desde fabricación. Típico: 12-24 meses.',
  uso: 'Descripción del uso final del producto.',
};

// ========== TEXTOS SUGERIDOS ==========
const TEXTOS_SUGERIDOS = {
  Huevos: {
    uso: 'Estuche para empaque de huevos frescos de gallina, diseñado para proteger el producto durante su almacenamiento, transporte y exhibición.',
    manejo: 'Manipular con manos limpias y secas. Evitar contacto con sustancias químicas, humedad excesiva o fuentes de calor. No apilar más de las unidades indicadas por empaque.',
    almacenamiento: 'Almacenar en lugar fresco y seco, temperatura entre 15°C y 30°C, humedad relativa menor al 70%. Proteger de la luz solar directa. Sobre estibas, sin contacto directo con el piso.',
    transporte: 'Transportar en vehículo cerrado y limpio. Proteger de la lluvia y humedad. No colocar objetos pesados encima del producto.',
    vida_util: '24 meses a partir de la fecha de fabricación, bajo las condiciones de almacenamiento indicadas.',
  },
  Frutas: {
    uso: 'Bandeja para empaque de frutas frescas, diseñada para proteger el producto durante su almacenamiento, transporte y exhibición en punto de venta.',
    manejo: 'Manipular con manos limpias y secas. Evitar contacto con sustancias químicas o humedad excesiva. No exponer a temperaturas superiores a 40°C.',
    almacenamiento: 'Almacenar en lugar fresco y seco, temperatura entre 15°C y 30°C, humedad relativa menor al 70%. Proteger de la luz solar directa.',
    transporte: 'Transportar en vehículo cerrado y limpio. Proteger de la lluvia y condensación. Mantener ventilación adecuada.',
    vida_util: '18 meses a partir de la fecha de fabricación, bajo las condiciones de almacenamiento indicadas.',
  },
  'Potes de pintura': {
    uso: 'Bandeja para transporte y exhibición de potes de pintura, diseñada para brindar estabilidad y protección durante la cadena logística.',
    manejo: 'Manipular con manos limpias y secas. Evitar contacto con solventes o sustancias químicas. Verificar capacidad de carga antes de usar.',
    almacenamiento: 'Almacenar en lugar fresco y seco, temperatura entre 15°C y 30°C. Proteger de la luz solar directa y fuentes de calor.',
    transporte: 'Transportar en vehículo cerrado y limpio. Asegurar estabilidad de la carga. Proteger de la lluvia.',
    vida_util: '24 meses a partir de la fecha de fabricación, bajo las condiciones de almacenamiento indicadas.',
  },
  Vasos: {
    uso: 'Porta vasos de pulpa moldeada para transporte seguro de bebidas, diseñado para brindar estabilidad y facilitar el manejo.',
    manejo: 'Manipular con manos limpias y secas. Evitar contacto con líquidos antes de uso. No reutilizar.',
    almacenamiento: 'Almacenar en lugar fresco y seco, temperatura entre 15°C y 30°C, humedad relativa menor al 70%.',
    transporte: 'Transportar en vehículo cerrado y limpio. Proteger de la lluvia y humedad.',
    vida_util: '18 meses a partir de la fecha de fabricación, bajo las condiciones de almacenamiento indicadas.',
  },
  _default: {
    uso: 'Empaque de pulpa moldeada para protección de producto durante almacenamiento, transporte y exhibición.',
    manejo: 'Manipular con manos limpias y secas. Evitar contacto con sustancias químicas o humedad excesiva.',
    almacenamiento: 'Almacenar en lugar fresco y seco, temperatura entre 15°C y 30°C, humedad relativa menor al 70%.',
    transporte: 'Transportar en vehículo cerrado y limpio. Proteger de la lluvia y humedad.',
    vida_util: '24 meses a partir de la fecha de fabricación, bajo las condiciones de almacenamiento indicadas.',
  },
};

// ========== COMPONENTE PRINCIPAL ==========
export function AsistenteIA({ contenidoMaterial, paso, datos, onSugerencia, materialId }) {
  const [abierto, setAbierto] = useState(true);
  const [rangosDinamicos, setRangosDinamicos] = useState(null);
  const [fuenteRangos, setFuenteRangos] = useState('estatico');
  const [totalFichas, setTotalFichas] = useState(0);

  const tipoContenido = contenidoMaterial || 'Otros';

  // Cargar rangos dinámicos cuando cambia el material
  useEffect(() => {
    if (!materialId) {
      setRangosDinamicos(null);
      setFuenteRangos('estatico');
      return;
    }

    api.get(`/ficha/${materialId}/rangos-tipicos`)
      .then((res) => {
        const data = res.data;
        setTotalFichas(data.total_fichas || 0);
        if (data.fuente === 'calculado' && Object.keys(data.rangos).length > 0) {
          // Convertir rangos dinámicos al formato esperado
          const rangosConvertidos = {};
          for (const [campo, vals] of Object.entries(data.rangos)) {
            rangosConvertidos[campo] = {
              min: vals.min,
              max: vals.max,
              sugerido: vals.promedio,
              unidad: '',
              muestras: vals.muestras,
            };
          }
          setRangosDinamicos(rangosConvertidos);
          setFuenteRangos('calculado');
        } else {
          setRangosDinamicos(null);
          setFuenteRangos('estatico');
        }
      })
      .catch(() => {
        setRangosDinamicos(null);
        setFuenteRangos('estatico');
      });
  }, [materialId]);

  // Usar rangos dinámicos si disponibles, sino estáticos
  const rangosActivos = rangosDinamicos || getRangosEstaticos();
  const alertas = analizarDatos(datos, rangosActivos);

  return (
    <div className="bg-gradient-to-br from-[#044926]/5 to-[#29b34b]/5 border border-[#29b34b]/20 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setAbierto(!abierto)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[#29b34b]/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-[#29b34b]" />
          <span className="text-sm font-semibold text-[#044926]">Asistente IA</span>
          {alertas.length > 0 && (
            <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
              {alertas.length} sugerencia{alertas.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {abierto ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>

      {abierto && (
        <div className="px-4 pb-4 space-y-3">
          {/* Indicador de fuente de datos */}
          <div className="flex items-center gap-2 p-2 bg-white/60 rounded-lg text-xs">
            {fuenteRangos === 'calculado' ? (
              <>
                <Calculator size={12} className="text-[#29b34b]" />
                <span className="text-[#044926]">
                  Rangos calculados de <strong>{totalFichas} fichas</strong> de este material
                </span>
              </>
            ) : (
              <>
                <Database size={12} className="text-gray-400" />
                <span className="text-gray-500">
                  Rangos de referencia del estándar
                  {totalFichas > 0 && totalFichas < 2
                    ? ` (${totalFichas} ficha — se necesitan 2+ para calcular rangos)`
                    : ' (sin fichas previas de este material)'}
                </span>
              </>
            )}
          </div>

          {/* Sugerencias activas */}
          {alertas.length > 0 ? (
            alertas.map((alerta, i) => (
              <div
                key={i}
                className={`flex items-start gap-2 p-2.5 rounded-lg text-xs ${
                  alerta.tipo === 'warning' ? 'bg-amber-50 text-amber-800' :
                  alerta.tipo === 'info' ? 'bg-blue-50 text-blue-800' :
                  'bg-green-50 text-green-800'
                }`}
              >
                {alerta.tipo === 'warning' ? <AlertTriangle size={14} className="shrink-0 mt-0.5" /> :
                 alerta.tipo === 'info' ? <Info size={14} className="shrink-0 mt-0.5" /> :
                 <CheckCircle size={14} className="shrink-0 mt-0.5" />}
                <div className="flex-1">
                  <p>{alerta.mensaje}</p>
                  {alerta.sugerencia && onSugerencia && (
                    <button
                      onClick={() => onSugerencia(alerta.campo, alerta.valorSugerido)}
                      className="mt-1 text-xs font-medium underline hover:no-underline"
                    >
                      Aplicar sugerencia: {alerta.valorSugerido}
                    </button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="flex items-center gap-2 p-2.5 bg-green-50 rounded-lg text-xs text-green-800">
              <CheckCircle size={14} />
              <p>Todo se ve bien en esta sección.</p>
            </div>
          )}

          {/* Textos sugeridos para Manejo y Disposición */}
          {paso === 5 && (
            <div className="border-t border-[#29b34b]/10 pt-3">
              <p className="text-xs font-medium text-[#044926] mb-2">Textos sugeridos para {tipoContenido}</p>
              <div className="space-y-1.5">
                {Object.entries(TEXTOS_SUGERIDOS[tipoContenido] || TEXTOS_SUGERIDOS._default).map(([campo, texto]) => (
                  <button
                    key={campo}
                    onClick={() => onSugerencia && onSugerencia(campo, texto)}
                    className="w-full text-left p-2 bg-white border border-gray-100 rounded-lg text-xs text-gray-600 hover:border-[#29b34b]/30 hover:bg-[#29b34b]/5 transition-colors"
                  >
                    <span className="font-medium text-[#044926] capitalize">{campo.replace(/_/g, ' ')}:</span>{' '}
                    {texto.slice(0, 80)}...
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ========== INDICADOR DE PROGRESO ==========
export function IndicadorProgreso({ datos }) {
  const secciones = [
    { id: 'basico', label: 'Datos básicos', completo: !!(datos.materialId && datos.codigoLocal && datos.pais) },
    { id: 'caracteristicas', label: 'Características', completo: tieneValoresNumericos(datos.caracteristicas) },
    { id: 'contenido', label: 'Contenido', completo: tieneValoresNumericos(datos.contenido) },
    { id: 'empaque', label: 'Empaque', completo: tieneValoresNumericos(datos.empaque) },
    { id: 'microbiologia', label: 'Microbiología', completo: tieneValoresNumericos(datos.microbiologia) },
    { id: 'manejo', label: 'Manejo', completo: tieneTextosObligatorios(datos.manejo) },
  ];

  const completadas = secciones.filter((s) => s.completo).length;
  const porcentaje = Math.round((completadas / secciones.length) * 100);

  // Contenido ya no es requisito para Preliminar
  let nivelEstado = 'Borrador';
  if (secciones[0].completo && secciones[1].completo) {
    nivelEstado = 'Preliminar';
  }
  if (nivelEstado === 'Preliminar' && secciones[3].completo && secciones[5].completo) {
    nivelEstado = 'Vigente';
  }

  const coloresNivel = {
    Borrador: 'text-gray-500 bg-gray-100',
    Preliminar: 'text-yellow-700 bg-yellow-100',
    Vigente: 'text-green-700 bg-green-100',
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-900">Progreso de la ficha</p>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${coloresNivel[nivelEstado]}`}>
          Listo para: {nivelEstado}
        </span>
      </div>

      <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full rounded-full transition-all duration-500"
          style={{
            width: `${porcentaje}%`,
            backgroundColor: porcentaje === 100 ? '#29b34b' : porcentaje > 50 ? '#f59e0b' : '#ef4444',
          }}
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        {secciones.map((s) => (
          <div key={s.id} className="flex items-center gap-1.5 text-xs">
            {s.completo ? (
              <CheckCircle size={12} className="text-[#29b34b] shrink-0" />
            ) : (
              <div className="w-3 h-3 rounded-full border-2 border-gray-300 shrink-0" />
            )}
            <span className={s.completo ? 'text-gray-700' : 'text-gray-400'}>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ========== TIP CONTEXTUAL ==========
export function TipCampo({ campo }) {
  const tip = TIPS_CAMPOS[campo];
  if (!tip) return null;

  return (
    <div className="group relative inline-block ml-1">
      <Info size={12} className="text-gray-400 cursor-help" />
      <div className="hidden group-hover:block absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
        {tip}
        <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45 -mt-1" />
      </div>
    </div>
  );
}

// ========== HELPERS ==========
function analizarDatos(datos, rangos) {
  const alertas = [];
  if (!datos || typeof datos !== 'object') return alertas;

  for (const [campo, rango] of Object.entries(rangos)) {
    const valor = datos[campo];

    if (valor !== undefined && valor !== '' && valor !== null) {
      const numVal = parseFloat(valor);
      if (!isNaN(numVal)) {
        if (numVal < rango.min) {
          alertas.push({
            tipo: 'warning',
            campo,
            mensaje: `${formatearNombre(campo.replace('_valor', ''))}: valor ${numVal} está por debajo del rango típico (${rango.min}–${rango.max}).`,
            sugerencia: true,
            valorSugerido: rango.sugerido,
          });
        } else if (numVal > rango.max) {
          alertas.push({
            tipo: 'warning',
            campo,
            mensaje: `${formatearNombre(campo.replace('_valor', ''))}: valor ${numVal} está por encima del rango típico (${rango.min}–${rango.max}).`,
            sugerencia: true,
            valorSugerido: rango.sugerido,
          });
        }
      }
    }
  }

  return alertas;
}

function tieneValoresNumericos(datos) {
  if (!datos || typeof datos !== 'object') return false;
  return Object.entries(datos).some(
    ([k, v]) => k.endsWith('_valor') && v !== '' && v !== null && v !== undefined
  );
}

function tieneTextosObligatorios(datos) {
  if (!datos || typeof datos !== 'object') return false;
  const obligatorios = ['manejo', 'almacenamiento', 'transporte', 'vida_util', 'uso'];
  return obligatorios.every((c) => datos[c] && String(datos[c]).trim().length > 0);
}

function formatearNombre(campo) {
  return campo.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}