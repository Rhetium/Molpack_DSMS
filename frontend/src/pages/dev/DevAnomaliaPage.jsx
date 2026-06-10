/**
 * Dashboard de Desarrollo — Diagnóstico de Detectores de Anomalías
 * SOLO PARA DESARROLLO. No forma parte del producto final.
 *
 * Muestra el resultado paso a paso de cada uno de los 6 detectores
 * al analizarse una ficha técnica específica.
 */
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Bug, Search, ChevronDown, ChevronUp, AlertTriangle,
  CheckCircle, XCircle, Info, Activity, Cpu, Layers,
} from 'lucide-react';
import api from '../../../lib/api';

const COLORES_SEVERIDAD = {
  ok:          'text-green-600 bg-green-50 border-green-200',
  advertencia: 'text-amber-700 bg-amber-50 border-amber-200',
  critica:     'text-red-700 bg-red-50 border-red-200',
};

const ICONOS_SEVERIDAD = {
  ok:          <CheckCircle size={14} className="text-green-500" />,
  advertencia: <AlertTriangle size={14} className="text-amber-500" />,
  critica:     <XCircle size={14} className="text-red-500" />,
};

function Badge({ texto, color = 'gray' }) {
  const clases = {
    green:  'bg-green-100 text-green-700',
    amber:  'bg-amber-100 text-amber-700',
    red:    'bg-red-100 text-red-700',
    gray:   'bg-gray-100 text-gray-600',
    blue:   'bg-blue-100 text-blue-700',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${clases[color] ?? clases.gray}`}>
      {texto}
    </span>
  );
}

function Seccion({ titulo, icono: Icono, color = '#044926', anomalias = 0, children }) {
  const [abierto, setAbierto] = useState(true);
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-4">
      <button
        onClick={() => setAbierto(!abierto)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg" style={{ backgroundColor: color + '18' }}>
            <Icono size={16} style={{ color }} />
          </div>
          <span className="text-sm font-semibold text-gray-900">{titulo}</span>
          {anomalias > 0
            ? <Badge texto={`${anomalias} anomalía${anomalias > 1 ? 's' : ''}`} color="red" />
            : <Badge texto="Sin anomalías" color="green" />}
        </div>
        {abierto ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>
      {abierto && <div className="px-5 pb-5 border-t border-gray-100 pt-4">{children}</div>}
    </div>
  );
}

function TablaSimple({ filas, columnas }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-xs">
        <thead className="bg-gray-50">
          <tr>
            {columnas.map((c) => (
              <th key={c.key} className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wide">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {filas.map((fila, i) => (
            <tr key={i} className={fila._highlight ? 'bg-amber-50' : 'hover:bg-gray-50'}>
              {columnas.map((c) => (
                <td key={c.key} className="px-3 py-2 text-gray-700">
                  {c.render ? c.render(fila[c.key], fila) : (fila[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Detector 1: Z-Score ─────────────────────────────────────────────────────
function DetectorZScore({ d }) {
  return (
    <Seccion titulo={d.nombre} icono={Activity} color="#7c3aed" anomalias={d.anomalias_generadas}>
      <div className="text-xs text-gray-500 mb-3">
        Fichas de referencia: <strong>{d.n_fichas_referencia}</strong> (mínimo: {d.minimo_requerido})
        {!d.activo && <Badge texto="INACTIVO — fichas insuficientes" color="gray" />}
      </div>
      {d.campos.length === 0
        ? <p className="text-xs text-gray-400 italic">Sin campos analizados.</p>
        : (
          <TablaSimple
            filas={d.campos.map((c) => ({ ...c, _highlight: c.anomalia }))}
            columnas={[
              { key: 'nombre', label: 'Campo' },
              { key: 'valor', label: 'Valor' },
              { key: 'media_historica', label: 'Media hist.' },
              { key: 'std_historica', label: 'Desv. est.' },
              { key: 'zscore', label: 'Z-Score', render: (v) => <strong>{v}</strong> },
              {
                key: 'severidad',
                label: 'Resultado',
                render: (sev) => (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs ${COLORES_SEVERIDAD[sev] ?? COLORES_SEVERIDAD.ok}`}>
                    {ICONOS_SEVERIDAD[sev]} {sev}
                  </span>
                ),
              },
              { key: 'n_muestras', label: 'N muestras' },
            ]}
          />
        )}
    </Seccion>
  );
}

// ── Detector 2: Unidades ────────────────────────────────────────────────────
function DetectorUnidades({ d }) {
  return (
    <Seccion titulo={d.nombre} icono={Layers} color="#0891b2" anomalias={d.anomalias_generadas}>
      {d.campos.length === 0
        ? <p className="text-xs text-gray-400 italic">Sin campos de unidad analizados.</p>
        : (
          <TablaSimple
            filas={d.campos.map((c) => ({ ...c, _highlight: c.anomalia }))}
            columnas={[
              { key: 'nombre', label: 'Campo' },
              { key: 'unidad_actual', label: 'Unidad ficha' },
              { key: 'unidad_mayoritaria', label: 'Unidad histórica' },
              { key: 'porcentaje_mayoritaria', label: '% uso histórico', render: (v) => `${(v * 100).toFixed(0)}%` },
              { key: 'n_muestras', label: 'N muestras' },
              {
                key: 'anomalia',
                label: 'Resultado',
                render: (v) => v
                  ? <Badge texto="Inconsistente" color="amber" />
                  : <Badge texto="OK" color="green" />,
              },
            ]}
          />
        )}
    </Seccion>
  );
}

// ── Detector 3: Duplicados semánticos ───────────────────────────────────────
function DetectorDuplicados({ d }) {
  return (
    <Seccion titulo={d.nombre} icono={Search} color="#d97706" anomalias={d.anomalias_generadas}>
      <div className="space-y-2 mb-4 text-xs">
        <div><span className="text-gray-500">Nombre KItem:</span> <code className="bg-gray-100 px-1 rounded">{d.embedding_kitem_nombre}</code></div>
        <div><span className="text-gray-500">Descripción KItem:</span> <code className="bg-gray-100 px-1 rounded">{d.embedding_kitem_descripcion}</code></div>
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Tiene embedding:</span>
          {d.tiene_embedding ? <Badge texto="Sí" color="green" /> : <Badge texto="No — búsqueda imposible" color="red" />}
        </div>
        <div className="text-gray-500">Umbral duplicado: advertencia ≥ {d.umbral_advertencia} | crítico ≥ {d.umbral_critico}</div>
      </div>
      {d.error && <div className="text-xs text-red-600 bg-red-50 rounded p-2 mb-3">Error: {d.error}</div>}
      {d.similares.length === 0
        ? <p className="text-xs text-gray-400 italic">Sin fichas similares encontradas (umbral 0.5).</p>
        : (
          <TablaSimple
            filas={d.similares.map((s) => ({ ...s, _highlight: s.es_duplicado }))}
            columnas={[
              { key: 'nombre', label: 'Ficha similar' },
              { key: 'similitud', label: 'Similitud', render: (v) => <strong>{(v * 100).toFixed(1)}%</strong> },
              {
                key: 'severidad',
                label: 'Clasificación',
                render: (sev) => (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs ${COLORES_SEVERIDAD[sev] ?? COLORES_SEVERIDAD.ok}`}>
                    {ICONOS_SEVERIDAD[sev]} {sev}
                  </span>
                ),
              },
            ]}
          />
        )}
    </Seccion>
  );
}

// ── Detector 4: Clasificación cruzada ──────────────────────────────────────
function DetectorClasificacion({ d }) {
  return (
    <Seccion titulo={d.nombre} icono={AlertTriangle} color="#dc2626" anomalias={d.anomalias_generadas}>
      <div className="text-xs text-gray-500 mb-3">
        Material: <strong>{d.material_analizado}</strong> | Categoría declarada: <Badge texto={d.categoria_declarada} color="blue" /> | Umbral: {d.umbral}
      </div>
      {d.error && <div className="text-xs text-red-600 bg-red-50 rounded p-2 mb-3">Error: {d.error}</div>}
      {d.materiales_similares.length === 0
        ? <p className="text-xs text-gray-400 italic">Sin materiales similares encontrados.</p>
        : (
          <TablaSimple
            filas={d.materiales_similares.map((m) => ({ ...m, _highlight: m.es_clasificacion_cruzada }))}
            columnas={[
              { key: 'nombre', label: 'Material similar' },
              { key: 'categoria', label: 'Categoría' },
              { key: 'similitud', label: 'Similitud', render: (v) => `${(v * 100).toFixed(1)}%` },
              { key: 'categoria_diferente', label: 'Cat. diferente', render: (v) => v ? <Badge texto="Sí" color="amber" /> : <Badge texto="No" color="green" /> },
              { key: 'es_clasificacion_cruzada', label: 'Anomalía', render: (v) => v ? <Badge texto="Sí" color="red" /> : <Badge texto="No" color="green" /> },
            ]}
          />
        )}
    </Seccion>
  );
}

// ── Detector 5: Perfil numérico cruzado ────────────────────────────────────
function DetectorPerfil({ d }) {
  return (
    <Seccion titulo={d.nombre} icono={Layers} color="#7c3aed" anomalias={d.anomalias_generadas}>
      {d.error && <div className="text-xs text-red-600 bg-red-50 rounded p-2 mb-3">Error: {d.error}</div>}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">Vector numérico de la ficha ({d.n_campos_vector ?? 0} campos)</p>
          <div className="bg-gray-50 rounded p-3 font-mono text-xs max-h-40 overflow-y-auto">
            {Object.entries(d.vector_ficha ?? {}).map(([k, v]) => (
              <div key={k}><span className="text-gray-400">{k}:</span> {v}</div>
            ))}
            {Object.keys(d.vector_ficha ?? {}).length === 0 && <span className="text-gray-400 italic">Sin campos numéricos</span>}
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">Distancias a centroides de categorías</p>
          {d.ranking.length === 0
            ? <p className="text-xs text-gray-400 italic">Sin perfiles calculados.</p>
            : (
              <div className="space-y-2">
                {d.ranking.map((r) => (
                  <div key={r.categoria} className={`flex items-center justify-between px-3 py-2 rounded border text-xs ${
                    r.categoria === d.categoria_declarada ? 'border-blue-300 bg-blue-50' : 'border-gray-200'
                  }`}>
                    <span className="font-medium">
                      {r.categoria}
                      {r.categoria === d.categoria_declarada && <span className="ml-1 text-blue-500">(declarada)</span>}
                    </span>
                    <span className="font-mono">{r.distancia}</span>
                  </div>
                ))}
              </div>
            )}
        </div>
      </div>
      {d.ratio !== undefined && (
        <div className="text-xs text-gray-600 bg-amber-50 border border-amber-200 rounded p-3">
          Ratio distancia_cercana/distancia_declarada: <strong>{d.ratio}</strong>
          {' '}(umbral advertencia: {d.umbral_advertencia}, crítico: {d.umbral_critico})
          {' '}→ Categoría sugerida: <strong>{d.categoria_sugerida}</strong>
        </div>
      )}
    </Seccion>
  );
}

// ── Detector 6: Isolation Forest ────────────────────────────────────────────
function DetectorML({ d }) {
  return (
    <Seccion titulo={d.nombre} icono={Cpu} color="#059669" anomalias={d.anomalias_generadas}>
      <div className="grid grid-cols-2 gap-4 text-xs mb-4">
        <div>
          <p className="text-gray-500 mb-1">Modelo de categoría</p>
          {d.modelo_categoria_disponible
            ? <Badge texto="Disponible" color="green" />
            : <Badge texto="No entrenado" color="gray" />}
        </div>
        <div>
          <p className="text-gray-500 mb-1">Modelo global</p>
          {d.modelo_global_disponible
            ? <Badge texto="Disponible" color="green" />
            : <Badge texto="No entrenado" color="gray" />}
        </div>
      </div>
      {d.error && <div className="text-xs text-red-600 bg-red-50 rounded p-2 mb-3">Error: {d.error}</div>}
      {d.razon_inactivo && <p className="text-xs text-gray-400 italic">{d.razon_inactivo}</p>}
      {d.score !== undefined && (
        <div className="space-y-3">
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-xs text-gray-500">Score Isolation Forest</span>
              <p className="text-lg font-bold text-gray-900 font-mono">{d.score}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500">Resultado</span>
              <p className="mt-0.5">
                {d.es_anomalo
                  ? <Badge texto="ANÓMALO" color="red" />
                  : <Badge texto="Normal" color="green" />}
              </p>
            </div>
            <div>
              <span className="text-xs text-gray-500">Modelo usado</span>
              <p className="text-xs font-medium text-gray-700">{d.modelo_usado}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500">Fichas entrenamiento</span>
              <p className="text-xs font-medium text-gray-700">{d.n_fichas_entrenamiento}</p>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Campos analizados ({d.campos_analizados?.length ?? 0})</p>
            <div className="flex flex-wrap gap-1">
              {(d.campos_analizados ?? []).map((c) => (
                <span key={c} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-mono">{c}</span>
              ))}
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Umbrales: advertencia &lt; {d.umbral_advertencia} | crítico &lt; {d.umbral_critico}
          </div>
        </div>
      )}
    </Seccion>
  );
}

// ── Componente principal ─────────────────────────────────────────────────────
const RENDER_DETECTOR = { D1: DetectorZScore, D2: DetectorUnidades, D3: DetectorDuplicados, D4: DetectorClasificacion, D5: DetectorPerfil, D6: DetectorML };

export default function DevAnomaliaPage() {
  const [searchParams] = useSearchParams();
  const [idFicha, setIdFicha]   = useState(searchParams.get('ficha') || '');
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError]       = useState(null);

  // Auto-ejecutar si viene el UUID por query param
  useEffect(() => {
    const id = searchParams.get('ficha');
    if (id) ejecutar(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ejecutar(idOverride) {
    const uuid = (idOverride || idFicha).trim();
    if (!uuid) return;
    if (idOverride) setIdFicha(idOverride);
    setCargando(true);
    setResultado(null);
    setError(null);
    try {
      const res = await api.get(`/anomalias/debug/${uuid}`);
      setResultado(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Banner dev */}
      <div className="flex items-center gap-2 mb-6 px-4 py-3 bg-amber-50 border border-amber-300 rounded-xl text-amber-800 text-sm font-medium">
        <Bug size={16} />
        Modo Desarrollador — Esta página no forma parte del producto final.
      </div>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">Diagnóstico de Detectores</h1>
      <p className="text-sm text-gray-500 mb-6">Analiza una ficha y ve los datos intermedios de cada uno de los 6 detectores de anomalías.</p>

      {/* Input */}
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          placeholder="UUID de la ficha técnica"
          value={idFicha}
          onChange={(e) => setIdFicha(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ejecutar()}
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
        />
        <button
          onClick={ejecutar}
          disabled={cargando || !idFicha.trim()}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#044926] text-white rounded-lg text-sm font-medium hover:bg-[#29b34b] disabled:opacity-40 transition-colors"
        >
          <Search size={15} />
          {cargando ? 'Analizando…' : 'Analizar'}
        </button>
      </div>

      {error && (
        <div className="mb-6 px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">{error}</div>
      )}

      {resultado && (
        <>
          {/* Resumen general */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Ficha', valor: resultado.codigo_ficha_local },
              { label: 'Estado', valor: resultado.estado_ficha },
              { label: 'Material', valor: resultado.material.nombre },
              { label: 'Categoría', valor: resultado.material.categoria },
            ].map(({ label, valor }) => (
              <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="text-sm font-semibold text-gray-900 truncate">{valor}</p>
              </div>
            ))}
          </div>

          {/* Info embedding */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Info size={15} className="text-[#044926]" />
              <h2 className="text-sm font-semibold text-gray-900">Estado del Embedding</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-gray-500">Nombre KItem: </span>
                <code className="bg-gray-100 px-1.5 py-0.5 rounded">{resultado.embedding.nombre_kitem}</code>
              </div>
              <div>
                <span className="text-gray-500">Tiene embedding: </span>
                {resultado.embedding.tiene_embedding
                  ? <Badge texto="Sí — búsqueda semántica activa" color="green" />
                  : <Badge texto="No — pasar a Preliminar para generarlo" color="red" />}
              </div>
              <div className="md:col-span-2">
                <span className="text-gray-500">Descripción KItem: </span>
                <code className="bg-gray-100 px-1.5 py-0.5 rounded">{resultado.embedding.descripcion_kitem}</code>
              </div>
            </div>
          </div>

          {/* Resumen de anomalías */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">Detectores (6)</h2>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              Total potencial:
              <strong className={resultado.resumen.total_anomalias_potenciales > 0 ? 'text-red-600' : 'text-green-600'}>
                {resultado.resumen.total_anomalias_potenciales} anomalía{resultado.resumen.total_anomalias_potenciales !== 1 ? 's' : ''}
              </strong>
            </div>
          </div>

          {/* Un componente por detector */}
          {resultado.detectores.map((d) => {
            const Comp = RENDER_DETECTOR[d.id];
            return Comp ? <Comp key={d.id} d={d} /> : null;
          })}
        </>
      )}
    </div>
  );
}
