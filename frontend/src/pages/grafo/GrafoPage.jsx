import { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Network, Search, ZoomIn, ZoomOut, Maximize2, X, ChevronRight, Package, FileText } from 'lucide-react';
import api from '../../../lib/api';

const COLORES_KTYPE = {
  MaterialComercial: { bg: '#044926', text: '#ffffff' },
  FichaTecnica: { bg: '#29b34b', text: '#ffffff' },
};

const COLORES_ESTADO_FICHA = {
  Vigente: '#29b34b',
  Preliminar: '#f59e0b',
  Obsoleto: '#ef4444',
  Borrador: '#9ca3af',
  'Revisión': '#f97316',
};

function getColorNodo(nodo) {
  if (nodo.ktype === 'MaterialComercial') {
    return COLORES_KTYPE.MaterialComercial;
  }
  const bg = COLORES_ESTADO_FICHA[nodo.estado] || '#29b34b';
  return { bg, text: '#ffffff' };
}

const COLORES_RELACION = {
  pertenece_a: '#94a3b8',
  se_deriva_de: '#f59e0b',
  es_variante_de: '#06b6d4',
  relacionado_con: '#8b5cf6',
};

export default function GrafoPage() {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const [materiales, setMateriales] = useState([]);
  const [fichas, setFichas] = useState([]);
  const [nodos, setNodos] = useState([]);
  const [enlaces, setEnlaces] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [nodoSeleccionado, setNodoSeleccionado] = useState(null);
  const [nodoExpandido, setNodoExpandido] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  // Estado de interacción
  const dragRef = useRef(null);
  const panRef = useRef(null);
  const nodosDragRef = useRef([]);
  const enlacesDragRef = useRef([]);
  const sizeRef = useRef({ w: 800, h: 600 });
  const needsRecenter = useRef(true);

  // Cargar datos al montar
  useEffect(() => {
    cargarDatos();
  }, []);

  async function cargarDatos() {
    setCargando(true);
    try {
      const [matRes, fichaRes] = await Promise.allSettled([
        api.get('/material'),
        api.get('/ficha'),
      ]);

      const mats = matRes.status === 'fulfilled' ? matRes.value.data : [];
      const fichs = fichaRes.status === 'fulfilled' ? fichaRes.value.data : [];
      setMateriales(mats);
      setFichas(fichs);

      const todosNodos = [];
      const todosEnlaces = [];
      const nodeMap = new Map();

      // Materiales como nodos principales (grandes)
      mats.forEach((m, i) => {
        const angle = (i / Math.max(mats.length, 1)) * 2 * Math.PI;
        const radius = Math.min(sizeRef.current.w, sizeRef.current.h) * 0.3;
        const cx = sizeRef.current.w / 2;
        const cy = sizeRef.current.h / 2;
        const nodo = {
          id: m.id_material_corporativo,
          nombre: m.nombre_corporativo,
          ktype: 'MaterialComercial',
          estado: m.estado_material,
          categoria: m.categoria,
          contenido: m.contenido,
          radio: 24,
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
          vx: 0, vy: 0,
          pinned: false,
          visible: true,
          fichasCount: 0,
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);
      });

      // Fichas como nodos secundarios (pequeños, inicialmente ocultos)
      fichs.forEach((f) => {
        const parentMat = nodeMap.get(f.id_material_corporativo);
        const offsetAngle = Math.random() * 2 * Math.PI;
        const offsetDist = 60 + Math.random() * 40;
        const nodo = {
          id: f.id_ficha,
          nombre: f.codigo_ficha_local || f.codigo_material_local || 'Sin código',
          ktype: 'FichaTecnica',
          estado: f.estado_ficha,
          pais: f.pais,
          version: f.codigo_version,
          materialId: f.id_material_corporativo,
          radio: 14,
          x: parentMat ? parentMat.x + Math.cos(offsetAngle) * offsetDist : sizeRef.current.w / 2 + Math.random() * 200,
          y: parentMat ? parentMat.y + Math.sin(offsetAngle) * offsetDist : sizeRef.current.h / 2 + Math.random() * 200,
          vx: 0, vy: 0,
          pinned: false,
          visible: false, // Oculto hasta expandir material
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);

        if (parentMat) {
          parentMat.fichasCount++;
          todosEnlaces.push({
            source: f.id_ficha,
            target: f.id_material_corporativo,
            tipo: 'pertenece_a',
          });
        }
      });

      setNodos(todosNodos);
      setEnlaces(todosEnlaces);
      nodosDragRef.current = todosNodos;
      enlacesDragRef.current = todosEnlaces;
    } catch (error) {
      console.error('Error cargando grafo:', error);
    } finally {
      setCargando(false);
    }
  }

  // Expandir/colapsar fichas de un material
  function toggleExpandir(materialId) {
    const nuevoExpandido = nodoExpandido === materialId ? null : materialId;
    setNodoExpandido(nuevoExpandido);

    setNodos((prev) => {
      const updated = prev.map((n) => {
        if (n.ktype === 'FichaTecnica' && n.materialId === materialId) {
          return { ...n, visible: nuevoExpandido === materialId };
        }
        // Colapsar fichas de otros materiales si expandimos uno nuevo
        if (nuevoExpandido && n.ktype === 'FichaTecnica' && n.materialId !== materialId) {
          return { ...n, visible: false };
        }
        return n;
      });
      nodosDragRef.current = updated;
      return updated;
    });
  }

  // Simulación de fuerzas continua
  useEffect(() => {
    if (cargando || nodos.length === 0) return;

    let running = true;

    function tick() {
      if (!running) return;

      const ns = nodosDragRef.current;
      const es = enlacesDragRef.current;
      const nodeMap = new Map(ns.map((n) => [n.id, n]));
      const visibles = ns.filter((n) => n.visible);

      // Repulsión solo entre nodos visibles
      for (let i = 0; i < visibles.length; i++) {
        for (let j = i + 1; j < visibles.length; j++) {
          const a = visibles[i];
          const b = visibles[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const minDist = a.radio + b.radio + 40;
          if (dist < minDist * 3) {
            const force = (600 / (dist * dist)) * 0.3;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
            if (!b.pinned) { b.vx += fx; b.vy += fy; }
          }
        }
      }

      // Atracción por enlaces (solo si ambos visibles)
      es.forEach((e) => {
        const s = nodeMap.get(e.source);
        const t = nodeMap.get(e.target);
        if (!s || !t || !s.visible || !t.visible) return;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const idealDist = s.ktype === t.ktype ? 100 : 80;
        const force = (dist - idealDist) * 0.003;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (!s.pinned) { s.vx += fx; s.vy += fy; }
        if (!t.pinned) { t.vx -= fx; t.vy -= fy; }
      });

      // Gravedad suave al centro
      const cx = sizeRef.current.w / 2, cy = sizeRef.current.h / 2;
      visibles.forEach((n) => {
        if (!n.pinned) {
          n.vx += (cx - n.x) * 0.0005;
          n.vy += (cy - n.y) * 0.0005;
        }
      });

      // Aplicar velocidades con damping
      ns.forEach((n) => {
        if (!n.pinned && n.visible) {
          n.vx *= 0.85;
          n.vy *= 0.85;
          n.x += n.vx;
          n.y += n.vy;
        }
      });

      dibujar();
      animRef.current = requestAnimationFrame(tick);
    }

    animRef.current = requestAnimationFrame(tick);
    return () => { running = false; cancelAnimationFrame(animRef.current); };
  }, [cargando, nodos.length, nodoExpandido, zoom, pan, nodoSeleccionado, busqueda]);

  function dibujar() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;
    if (!container) return;

    // Auto-resize every frame
    const dpr = window.devicePixelRatio || 1;
    const cw = container.clientWidth;
    const ch = container.clientHeight;
    if (cw > 0 && ch > 0 && (canvas.width !== cw * dpr || canvas.height !== ch * dpr)) {
      canvas.width = cw * dpr;
      canvas.height = ch * dpr;
    }
    sizeRef.current = { w: cw, h: ch };

    // Recentrar nodos la primera vez que se detecta el tamaño real
    if (needsRecenter.current && cw > 0 && ch > 0) {
      needsRecenter.current = false;
      const ns = nodosDragRef.current;
      const visibles = ns.filter((n) => n.visible);
      if (visibles.length > 0) {
        // Calcular centro actual de los nodos
        let sumX = 0, sumY = 0;
        visibles.forEach((n) => { sumX += n.x; sumY += n.y; });
        const avgX = sumX / visibles.length;
        const avgY = sumY / visibles.length;
        const offsetX = cw / 2 - avgX;
        const offsetY = ch / 2 - avgY;
        ns.forEach((n) => { n.x += offsetX; n.y += offsetY; });
      }
    }
    const w = sizeRef.current.w;
    const h = sizeRef.current.h;
    const ns = nodosDragRef.current;
    const es = enlacesDragRef.current;
    const nodeMap = new Map(ns.map((n) => [n.id, n]));

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.translate(pan.x + w / 2, pan.y + h / 2);
    ctx.scale(zoom, zoom);
    ctx.translate(-sizeRef.current.w / 2, -sizeRef.current.h / 2);

    const busquedaLower = busqueda.toLowerCase();

    // Enlaces
    es.forEach((e) => {
      const s = nodeMap.get(e.source);
      const t = nodeMap.get(e.target);
      if (!s || !t || !s.visible || !t.visible) return;

      const color = COLORES_RELACION[e.tipo] || '#cbd5e1';
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);

      // Curva bezier para efecto de rama
      const midX = (s.x + t.x) / 2;
      const midY = (s.y + t.y) / 2 - 20;
      ctx.quadraticCurveTo(midX, midY, t.x, t.y);

      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5 / zoom;
      ctx.globalAlpha = 0.5;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Nodos
    ns.forEach((n) => {
      if (!n.visible) return;

      const matchBusqueda = !busqueda || n.nombre.toLowerCase().includes(busquedaLower);
      const esSeleccionado = nodoSeleccionado?.id === n.id;
      const esMaterial = n.ktype === 'MaterialComercial';
      const colores = getColorNodo(n);
      const r = n.radio / (zoom > 1 ? 1 : 1);

      ctx.globalAlpha = matchBusqueda ? 1 : 0.15;

      // Sombra
      ctx.shadowColor = 'rgba(0,0,0,0.15)';
      ctx.shadowBlur = 8;
      ctx.shadowOffsetX = 2;
      ctx.shadowOffsetY = 2;

      // Halo de selección
      if (esSeleccionado) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
        ctx.strokeStyle = colores.bg;
        ctx.lineWidth = 2.5 / zoom;
        ctx.setLineDash([4 / zoom, 3 / zoom]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Nodo principal
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = colores.bg;
      ctx.fill();
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;

      // Borde
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2 / zoom;
      ctx.stroke();

      // Letra tipo
      ctx.fillStyle = colores.text;
      ctx.font = `bold ${(esMaterial ? 11 : 9) / Math.max(zoom, 0.5)}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(esMaterial ? 'M' : 'F', n.x, n.y);

      // Badge con cantidad de fichas
      if (esMaterial && n.fichasCount > 0) {
        const badgeR = 8 / Math.max(zoom, 0.5);
        const bx = n.x + r * 0.7;
        const by = n.y - r * 0.7;
        ctx.beginPath();
        ctx.arc(bx, by, badgeR, 0, Math.PI * 2);
        ctx.fillStyle = '#f59e0b';
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${7 / Math.max(zoom, 0.5)}px sans-serif`;
        ctx.fillText(String(n.fichasCount), bx, by);
      }

      // Nombre del nodo
      const fontSize = (esMaterial ? 10 : 8) / Math.max(zoom, 0.5);
      ctx.font = `500 ${fontSize}px sans-serif`;
      ctx.fillStyle = '#1f2937';
      ctx.textAlign = 'center';

      const labelY = n.y + r + 14 / Math.max(zoom, 0.5);
      const maxLabelWidth = 120 / Math.max(zoom, 0.5);
      let labelText = n.nombre;
      while (ctx.measureText(labelText).width > maxLabelWidth && labelText.length > 5) {
        labelText = labelText.slice(0, -2) + '…';
      }

      // Fondo del label
      const textWidth = ctx.measureText(labelText).width;
      const padding = 4 / Math.max(zoom, 0.5);
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.fillRect(
        n.x - textWidth / 2 - padding,
        labelY - fontSize / 2 - padding / 2,
        textWidth + padding * 2,
        fontSize + padding
      );

      ctx.fillStyle = '#1f2937';
      ctx.fillText(labelText, n.x, labelY);

      ctx.globalAlpha = 1;
    });

    ctx.restore();
  }

  // ========== INTERACCIÓN ==========

  function getMousePos(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  function screenToWorld(sx, sy) {
    const w = sizeRef.current.w;
    const h = sizeRef.current.h;
    return {
      x: (sx - pan.x - w / 2) / zoom + sizeRef.current.w / 2,
      y: (sy - pan.y - h / 2) / zoom + sizeRef.current.h / 2,
    };
  }

  function findNodeAt(wx, wy) {
    const ns = nodosDragRef.current;
    for (let i = ns.length - 1; i >= 0; i--) {
      const n = ns[i];
      if (!n.visible) continue;
      const dx = n.x - wx;
      const dy = n.y - wy;
      if (dx * dx + dy * dy < (n.radio + 5) * (n.radio + 5)) {
        return n;
      }
    }
    return null;
  }

  function handleMouseDown(e) {
    const pos = getMousePos(e);
    const world = screenToWorld(pos.x, pos.y);
    const nodo = findNodeAt(world.x, world.y);

    if (nodo) {
      dragRef.current = { nodo, startX: world.x, startY: world.y, moved: false };
      nodo.pinned = true;
    } else {
      panRef.current = { startX: e.clientX - pan.x, startY: e.clientY - pan.y };
    }
  }

  function handleMouseMove(e) {
    if (dragRef.current) {
      const pos = getMousePos(e);
      const world = screenToWorld(pos.x, pos.y);
      dragRef.current.nodo.x = world.x;
      dragRef.current.nodo.y = world.y;
      const dx = world.x - dragRef.current.startX;
      const dy = world.y - dragRef.current.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.moved = true;
    } else if (panRef.current) {
      setPan({ x: e.clientX - panRef.current.startX, y: e.clientY - panRef.current.startY });
    }
  }

  function handleMouseUp(e) {
    if (dragRef.current) {
      const nodo = dragRef.current.nodo;
      const moved = dragRef.current.moved;
      nodo.pinned = false;
      dragRef.current = null;

      if (!moved) {
        // Click sin arrastrar
        setNodoSeleccionado(nodo);
        if (nodo.ktype === 'MaterialComercial') {
          toggleExpandir(nodo.id);
        }
      }
    }
    panRef.current = null;
  }

  function handleWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(Math.max(z * delta, 0.3), 4));
  }

  function resetView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setNodoExpandido(null);
    setNodoSeleccionado(null);
    setNodos((prev) => {
      const updated = prev.map((n) =>
        n.ktype === 'FichaTecnica' ? { ...n, visible: false } : n
      );
      nodosDragRef.current = updated;
      return updated;
    });
  }

  // Resize canvas
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grafo de Conocimiento</h1>
          <p className="text-sm text-gray-500 mt-1">
            Haz click en un material para expandir sus fichas. Arrastra los nodos para reorganizar.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#044926]" /> Materiales ({materiales.length})
          </span>
          <span className="text-gray-300">|</span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#29b34b]" /> Vigente
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#f59e0b]" /> Preliminar
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#ef4444]" /> Obsoleto
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#9ca3af]" /> Borrador
          </span>
          <span className="text-gray-300">|</span>
          <span>{fichas.length} fichas · {enlaces.length} relaciones</span>
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
            onClick={() => setZoom((z) => Math.min(z * 1.3, 4))}
            className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
            title="Zoom in"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z * 0.7, 0.3))}
            className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
            title="Zoom out"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={resetView}
            className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
            title="Resetear vista"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </div>

      {/* Canvas + Panel detalle */}
      <div className="flex gap-4">
        {/* Canvas */}
        <div
          className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden relative"
          style={{ height: '600px' }}
        >
          {/* Canvas siempre montado */}
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            className="absolute inset-0 w-full h-full"
            style={{ cursor: dragRef.current ? 'grabbing' : 'grab' }}
          />

          {/* Overlay: spinner o vacío */}
          {cargando && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
              <div className="text-center">
                <div className="w-8 h-8 border-3 border-[#29b34b]/30 border-t-[#29b34b] rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-gray-500">Construyendo grafo...</p>
              </div>
            </div>
          )}
          {!cargando && nodos.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
              <div className="text-center">
                <Network size={48} className="mx-auto text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">No hay datos para mostrar</p>
              </div>
            </div>
          )}

          {/* Instrucción flotante */}
          {!cargando && nodos.length > 0 && !nodoExpandido && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/70 text-white text-xs px-4 py-2 rounded-full backdrop-blur-sm">
              Click en un material para ver sus fichas · Arrastra para mover · Scroll para zoom
            </div>
          )}
        </div>

        {/* Panel detalle */}
        {nodoSeleccionado && (
          <div className="w-72 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden shrink-0">
            <div
              className="flex items-center justify-between px-4 py-3 border-b"
              style={{ backgroundColor: getColorNodo(nodoSeleccionado).bg + '15' }}
            >
              <div className="flex items-center gap-2">
                {nodoSeleccionado.ktype === 'MaterialComercial' ? (
                  <Package size={16} className="text-[#044926]" />
                ) : (
                  <FileText size={16} className="text-[#29b34b]" />
                )}
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
                <p className="text-sm font-semibold text-gray-900">{nodoSeleccionado.nombre}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Estado</p>
                <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                  nodoSeleccionado.estado === 'Vigente' ? 'bg-green-100 text-green-700' :
                  nodoSeleccionado.estado === 'Activo' ? 'bg-green-100 text-green-700' :
                  nodoSeleccionado.estado === 'Preliminar' ? 'bg-yellow-100 text-yellow-700' :
                  nodoSeleccionado.estado === 'Borrador' ? 'bg-gray-100 text-gray-600' :
                  'bg-red-100 text-red-700'
                }`}>
                  {nodoSeleccionado.estado}
                </span>
              </div>
              {nodoSeleccionado.categoria && (
                <div>
                  <p className="text-xs text-gray-500">Categoría</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.categoria}</p>
                </div>
              )}
              {nodoSeleccionado.contenido && (
                <div>
                  <p className="text-xs text-gray-500">Contenido</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.contenido}</p>
                </div>
              )}
              {nodoSeleccionado.pais && (
                <div>
                  <p className="text-xs text-gray-500">País</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.pais}</p>
                </div>
              )}
              {nodoSeleccionado.version !== undefined && (
                <div>
                  <p className="text-xs text-gray-500">Versión</p>
                  <p className="text-sm text-gray-700">v{nodoSeleccionado.version}</p>
                </div>
              )}
              {nodoSeleccionado.ktype === 'MaterialComercial' && (
                <div>
                  <p className="text-xs text-gray-500">Fichas técnicas</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.fichasCount} fichas</p>
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
                className="flex items-center justify-center gap-1 w-full text-sm font-medium text-white bg-[#044926] hover:bg-[#29b34b] py-2 rounded-lg transition-colors mt-2"
              >
                Ver detalle <ChevronRight size={14} />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}