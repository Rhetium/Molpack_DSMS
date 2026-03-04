import { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Network, Search, ZoomIn, ZoomOut, Maximize2, Info, X } from 'lucide-react';
import api from '../../../lib/api';

const COLORES_KTYPE = {
  MaterialComercial: '#044926',
  FichaTecnica: '#29b34b',
};

const COLORES_RELACION = {
  pertenece_a: '#6366f1',
  se_deriva_de: '#f59e0b',
  es_variante_de: '#06b6d4',
  relacionado_con: '#8b5cf6',
};

const LABELS_RELACION = {
  pertenece_a: 'Pertenece a',
  se_deriva_de: 'Se deriva de',
  es_variante_de: 'Es variante de',
  relacionado_con: 'Relacionado con',
};

export default function GrafoPage() {
  const [materiales, setMateriales] = useState([]);
  const [fichas, setFichas] = useState([]);
  const [nodos, setNodos] = useState([]);
  const [enlaces, setEnlaces] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [nodoSeleccionado, setNodoSeleccionado] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);
  const simulationRef = useRef(null);

  useEffect(() => {
    cargarGrafoCompleto();
  }, []);

  async function cargarGrafoCompleto() {
    setCargando(true);
    try {
      // Cargar todos los kitems
      const [matRes, fichaRes] = await Promise.allSettled([
        api.get('/material'),
        api.get('/ficha'),
      ]);

      const mats = matRes.status === 'fulfilled' ? matRes.value.data : [];
      const fichs = fichaRes.status === 'fulfilled' ? fichaRes.value.data : [];
      setMateriales(mats);
      setFichas(fichs);

      // Construir nodos
      const todosNodos = [];
      const nodeMap = new Map();

      mats.forEach((m) => {
        const nodo = {
          id: m.id_material_corporativo,
          nombre: m.nombre_corporativo,
          ktype: 'MaterialComercial',
          estado: m.estado_material,
          categoria: m.categoria,
          x: 0, y: 0, vx: 0, vy: 0,
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);
      });

      fichs.forEach((f) => {
        const nodo = {
          id: f.id_ficha,
          nombre: f.codigo_ficha_local || f.codigo_material_local,
          ktype: 'FichaTecnica',
          estado: f.estado_ficha,
          pais: f.pais,
          version: f.codigo_version,
          materialId: f.id_material_corporativo,
          x: 0, y: 0, vx: 0, vy: 0,
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);
      });

      // Construir enlaces basados en relaciones ficha->material
      const todosEnlaces = [];
      fichs.forEach((f) => {
        if (f.id_material_corporativo && nodeMap.has(f.id_material_corporativo)) {
          todosEnlaces.push({
            source: f.id_ficha,
            target: f.id_material_corporativo,
            tipo: 'pertenece_a',
          });
        }
      });

      // Cargar relaciones del grafo para cada material
      for (const m of mats) {
        try {
          const grafoRes = await api.get(`/dsms/kitems/${m.id_material_corporativo}/relaciones`);
          const relaciones = grafoRes.data || [];
          relaciones.forEach((rel) => {
            const yaExiste = todosEnlaces.some(
              (e) =>
                (e.source === rel.source.id && e.target === rel.target.id) ||
                (e.source === rel.target.id && e.target === rel.source.id)
            );
            if (!yaExiste && nodeMap.has(rel.source.id) && nodeMap.has(rel.target.id)) {
              todosEnlaces.push({
                source: rel.source.id,
                target: rel.target.id,
                tipo: rel.tipo_relacion,
              });
            }
          });
        } catch {
          // Ignorar errores individuales
        }
      }

      // Posicionar nodos con layout de fuerza simple
      posicionarNodos(todosNodos, todosEnlaces);

      setNodos(todosNodos);
      setEnlaces(todosEnlaces);
    } catch (error) {
      console.error('Error cargando grafo:', error);
    } finally {
      setCargando(false);
    }
  }

  function posicionarNodos(nodos, enlaces) {
    const width = 800;
    const height = 600;

    // Posición inicial aleatoria
    nodos.forEach((n, i) => {
      const angle = (i / nodos.length) * 2 * Math.PI;
      const radius = 150 + Math.random() * 100;
      n.x = width / 2 + Math.cos(angle) * radius;
      n.y = height / 2 + Math.sin(angle) * radius;
    });

    const nodeById = new Map(nodos.map((n) => [n.id, n]));

    // Simulación simple de fuerzas
    for (let tick = 0; tick < 200; tick++) {
      // Repulsión entre nodos
      for (let i = 0; i < nodos.length; i++) {
        for (let j = i + 1; j < nodos.length; j++) {
          const dx = nodos[j].x - nodos[i].x;
          const dy = nodos[j].y - nodos[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 800 / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          nodos[i].x -= fx;
          nodos[i].y -= fy;
          nodos[j].x += fx;
          nodos[j].y += fy;
        }
      }

      // Atracción por enlaces
      enlaces.forEach((e) => {
        const source = nodeById.get(e.source);
        const target = nodeById.get(e.target);
        if (!source || !target) return;
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 120) * 0.01;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        source.x += fx;
        source.y += fy;
        target.x -= fx;
        target.y -= fy;
      });

      // Gravedad al centro
      nodos.forEach((n) => {
        n.x += (width / 2 - n.x) * 0.01;
        n.y += (height / 2 - n.y) * 0.01;
      });
    }
  }

  const nodosFiltrados = busqueda
    ? nodos.filter((n) => n.nombre.toLowerCase().includes(busqueda.toLowerCase()))
    : nodos;

  const nodoIdsVisibles = new Set(nodosFiltrados.map((n) => n.id));
  const enlacesFiltrados = busqueda
    ? enlaces.filter((e) => nodoIdsVisibles.has(e.source) && nodoIdsVisibles.has(e.target))
    : enlaces;

  const nodeById = new Map(nodos.map((n) => [n.id, n]));

  function handleMouseDown(e) {
    if (e.target.tagName === 'svg' || e.target.tagName === 'g') {
      setDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    }
  }

  function handleMouseMove(e) {
    if (dragging) {
      setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  }

  function handleMouseUp() {
    setDragging(false);
  }

  function handleWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(Math.max(z * delta, 0.2), 5));
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grafo de Conocimiento</h1>
          <p className="text-sm text-gray-500 mt-1">
            Visualización de relaciones entre materiales y fichas técnicas
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {nodos.length} nodos · {enlaces.length} relaciones
          </span>
        </div>
      </div>

      {/* Controles */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar nodo..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
          />
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom((z) => Math.min(z * 1.3, 5))}
            className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z * 0.7, 0.2))}
            className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }}
            className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex items-center gap-6 mb-4 px-2">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="font-medium">Nodos:</span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#044926]" /> Material
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#29b34b]" /> Ficha Técnica
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="font-medium">Relaciones:</span>
          {Object.entries(LABELS_RELACION).map(([tipo, label]) => (
            <span key={tipo} className="flex items-center gap-1.5">
              <span className="w-4 h-0.5 rounded" style={{ backgroundColor: COLORES_RELACION[tipo] }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Canvas del grafo */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden relative" style={{ height: '600px' }}>
        {cargando ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-8 h-8 border-3 border-[#29b34b]/30 border-t-[#29b34b] rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-gray-500">Construyendo grafo...</p>
            </div>
          </div>
        ) : nodos.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Network size={48} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">No hay datos para mostrar el grafo</p>
              <p className="text-xs text-gray-400 mt-1">Crea materiales y fichas técnicas para ver sus relaciones</p>
            </div>
          </div>
        ) : (
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox="0 0 800 600"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            style={{ cursor: dragging ? 'grabbing' : 'grab' }}
          >
            <g transform={`translate(${offset.x}, ${offset.y}) scale(${zoom})`}>
              {/* Enlaces */}
              {enlacesFiltrados.map((e, i) => {
                const source = nodeById.get(e.source);
                const target = nodeById.get(e.target);
                if (!source || !target) return null;
                const midX = (source.x + target.x) / 2;
                const midY = (source.y + target.y) / 2;
                return (
                  <g key={`edge-${i}`}>
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={COLORES_RELACION[e.tipo] || '#cbd5e1'}
                      strokeWidth={1.5}
                      strokeOpacity={0.6}
                    />
                    <text
                      x={midX}
                      y={midY - 4}
                      textAnchor="middle"
                      fontSize={7}
                      fill={COLORES_RELACION[e.tipo] || '#94a3b8'}
                      opacity={zoom > 0.7 ? 1 : 0}
                    >
                      {LABELS_RELACION[e.tipo] || e.tipo}
                    </text>
                  </g>
                );
              })}

              {/* Nodos */}
              {nodosFiltrados.map((nodo) => {
                const esMaterial = nodo.ktype === 'MaterialComercial';
                const radio = esMaterial ? 18 : 12;
                const color = COLORES_KTYPE[nodo.ktype] || '#6b7280';
                const esSeleccionado = nodoSeleccionado?.id === nodo.id;

                return (
                  <g
                    key={nodo.id}
                    onClick={() => setNodoSeleccionado(nodo)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Halo selección */}
                    {esSeleccionado && (
                      <circle
                        cx={nodo.x}
                        cy={nodo.y}
                        r={radio + 5}
                        fill="none"
                        stroke={color}
                        strokeWidth={2}
                        strokeDasharray="4 2"
                        opacity={0.6}
                      />
                    )}
                    {/* Nodo */}
                    <circle
                      cx={nodo.x}
                      cy={nodo.y}
                      r={radio}
                      fill={color}
                      stroke="white"
                      strokeWidth={2}
                      opacity={0.9}
                    />
                    {/* Icono tipo */}
                    <text
                      x={nodo.x}
                      y={nodo.y + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={esMaterial ? 10 : 8}
                      fill="white"
                      fontWeight="bold"
                    >
                      {esMaterial ? 'M' : 'F'}
                    </text>
                    {/* Label */}
                    {zoom > 0.5 && (
                      <text
                        x={nodo.x}
                        y={nodo.y + radio + 12}
                        textAnchor="middle"
                        fontSize={8}
                        fill="#374151"
                        fontWeight="500"
                      >
                        {nodo.nombre.length > 20 ? nodo.nombre.slice(0, 20) + '...' : nodo.nombre}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        )}

        {/* Panel de detalle del nodo seleccionado */}
        {nodoSeleccionado && (
          <div className="absolute top-4 right-4 w-72 bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100"
              style={{ backgroundColor: COLORES_KTYPE[nodoSeleccionado.ktype] + '10' }}>
              <div className="flex items-center gap-2">
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
                  style={{ backgroundColor: COLORES_KTYPE[nodoSeleccionado.ktype] }}
                >
                  {nodoSeleccionado.ktype === 'MaterialComercial' ? 'M' : 'F'}
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {nodoSeleccionado.ktype === 'MaterialComercial' ? 'Material' : 'Ficha Técnica'}
                </span>
              </div>
              <button
                onClick={() => setNodoSeleccionado(null)}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <p className="text-xs text-gray-500">Nombre</p>
                <p className="text-sm font-medium text-gray-900">{nodoSeleccionado.nombre}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Estado</p>
                <p className="text-sm text-gray-700">{nodoSeleccionado.estado}</p>
              </div>
              {nodoSeleccionado.pais && (
                <div>
                  <p className="text-xs text-gray-500">País</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.pais}</p>
                </div>
              )}
              {nodoSeleccionado.version && (
                <div>
                  <p className="text-xs text-gray-500">Versión</p>
                  <p className="text-sm text-gray-700">v{nodoSeleccionado.version}</p>
                </div>
              )}
              {nodoSeleccionado.categoria && (
                <div>
                  <p className="text-xs text-gray-500">Categoría</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.categoria}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-gray-500">Conexiones</p>
                <p className="text-sm text-gray-700">
                  {enlaces.filter((e) => e.source === nodoSeleccionado.id || e.target === nodoSeleccionado.id).length} relaciones
                </p>
              </div>
              <Link
                to={
                  nodoSeleccionado.ktype === 'MaterialComercial'
                    ? `/materiales/${nodoSeleccionado.id}`
                    : `/fichas/${nodoSeleccionado.id}`
                }
                className="block text-center text-sm font-medium text-[#044926] hover:text-[#29b34b] pt-2 border-t border-gray-100"
              >
                Ver detalle completo
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}