import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Network, Search, ZoomIn, ZoomOut, Maximize2, X, ChevronRight, Package, FileText, Layers } from 'lucide-react';
import api from '../../../lib/api';

// ─── Paleta ───────────────────────────────────────────────────────────────────
const COLOR_CATEGORIA   = { bg: '#1e40af', text: '#ffffff' }; // azul oscuro
const COLOR_MATERIAL    = { bg: '#044926', text: '#ffffff' }; // verde oscuro
const COLOR_FICHA_ESTADO = {
  Vigente:    '#29b34b',
  Preliminar: '#f59e0b',
  Obsoleto:   '#ef4444',
  Borrador:   '#9ca3af',
  'Revisión': '#f97316',
};

function colorNodo(n) {
  if (n.ktype === 'Categoria')        return COLOR_CATEGORIA;
  if (n.ktype === 'MaterialComercial') return COLOR_MATERIAL;
  return { bg: COLOR_FICHA_ESTADO[n.estado] ?? '#29b34b', text: '#ffffff' };
}

const COLOR_ENLACE = {
  categoria_material: '#93c5fd',
  pertenece_a: '#94a3b8',
  se_deriva_de: '#f59e0b',
};

// ─── Helpers de dibujo ────────────────────────────────────────────────────────
function dibujarRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

// ─── Dibujo de un nodo individual ────────────────────────────────────────────
// Calcula propiedades visuales según tipo de nodo
function _propNodo(n) {
  const isCat = n.ktype === 'Categoria';
  const isMat = n.ktype === 'MaterialComercial';

  let letra, letraPx, fontSizePx, maxLabelW, badgeCount;
  if (isCat) {
    letra = 'CAT'; letraPx = 10; fontSizePx = 11; maxLabelW = 140;
    badgeCount = n.materialesCount ?? 0;
  } else if (isMat) {
    letra = 'M'; letraPx = 11; fontSizePx = 10; maxLabelW = 120;
    badgeCount = n.fichasCount ?? 0;
  } else {
    letra = 'F'; letraPx = 9; fontSizePx = 8; maxLabelW = 120;
    badgeCount = 0;
  }

  return { isCat, isMat, letra, letraPx, fontSizePx, maxLabelW, badgeCount,
    fontWeight: isCat ? '600' : '500' };
}

function dibujarNodo(ctx, n, zoom, sel, match) {
  const cols = colorNodo(n);
  const r    = n.radio;
  const zs   = Math.max(zoom, 0.5);
  const p    = _propNodo(n);

  ctx.globalAlpha = match ? 1 : 0.15;

  // Halo de selección
  if (sel) {
    ctx.beginPath();
    if (n.es_rect) {
      dibujarRoundRect(ctx, n.x - r - 8, n.y - r * 0.6 - 8, (r + 8) * 2, (r * 0.6 + 8) * 2, 10);
    } else {
      ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
    }
    ctx.strokeStyle = cols.bg;
    ctx.lineWidth = 2.5 / zoom;
    ctx.setLineDash([4 / zoom, 3 / zoom]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Sombra + forma
  ctx.shadowColor = 'rgba(0,0,0,0.18)';
  ctx.shadowBlur = 8; ctx.shadowOffsetX = 2; ctx.shadowOffsetY = 2;
  ctx.beginPath();
  if (n.es_rect) {
    dibujarRoundRect(ctx, n.x - r, n.y - r * 0.6, r * 2, r * 1.2, 8);
  } else {
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
  }
  ctx.fillStyle = cols.bg;
  ctx.fill();
  ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0;
  ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0;
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2 / zoom;
  ctx.stroke();

  // Letra interior
  ctx.fillStyle = cols.text;
  ctx.font = `bold ${p.letraPx / zs}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(p.letra, n.x, n.y);

  // Badge de cantidad
  if (p.badgeCount > 0) {
    const badgeR = 8 / zs;
    const bx = n.x + r * 0.75, by = n.y - r * 0.75;
    ctx.beginPath();
    ctx.arc(bx, by, badgeR, 0, Math.PI * 2);
    ctx.fillStyle = '#f59e0b';
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${7 / zs}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(p.badgeCount), bx, by);
  }

  // Etiqueta con fondo
  const fontSize = p.fontSizePx / zs;
  const labelY   = n.y + r + (n.es_rect ? r * 0.6 : 0) + 14 / zs;
  ctx.font = `${p.fontWeight} ${fontSize}px sans-serif`;
  ctx.textAlign = 'center';
  let label = n.nombre;
  const maxW = p.maxLabelW / zs;
  while (ctx.measureText(label).width > maxW && label.length > 5) label = label.slice(0, -2) + '…';
  const tw  = ctx.measureText(label).width;
  const pad = 4 / zs;
  ctx.fillStyle = 'rgba(255,255,255,0.88)';
  ctx.fillRect(n.x - tw / 2 - pad, labelY - fontSize / 2 - pad / 2, tw + pad * 2, fontSize + pad);
  ctx.fillStyle = '#1f2937';
  ctx.fillText(label, n.x, labelY);

  ctx.globalAlpha = 1;
}

// ─── Componente principal ────────────────────────────────────────────────────
export default function GrafoPage() {
  const canvasRef  = useRef(null);
  const animRef    = useRef(null);
  const dragRef    = useRef(null);
  const panRef     = useRef(null);
  const nodosDragRef   = useRef([]);
  const enlacesDragRef = useRef([]);
  const sizeRef    = useRef({ w: 800, h: 600 });
  const needsRecenter = useRef(true);

  const [materiales, setMateriales] = useState([]);
  const [fichas,     setFichas]     = useState([]);
  const [nodos,      setNodos]      = useState([]);
  const [enlaces,    setEnlaces]    = useState([]);
  const [cargando,   setCargando]   = useState(true);

  const [modoVista,          setModoVista]          = useState('material'); // 'material' | 'categoria'
  const [nodoSeleccionado,   setNodoSeleccionado]   = useState(null);
  const [categoriaExpandida, setCategoriaExpandida] = useState(null);
  const [materialExpandido,  setMaterialExpandido]  = useState(null);
  const [busqueda,           setBusqueda]           = useState('');
  const [zoom, setZoom] = useState(1);
  const [pan,  setPan]  = useState({ x: 0, y: 0 });

  // ── Carga de datos ──────────────────────────────────────────────────────────
  useEffect(() => { cargarDatos(); }, []);

  async function cargarDatos() {
    setCargando(true);
    try {
      const [matRes, fichaRes] = await Promise.allSettled([
        api.get('/material'),
        api.get('/ficha'),
      ]);
      const mats  = matRes.status  === 'fulfilled' ? matRes.value.data  : [];
      const fichs = fichaRes.status === 'fulfilled' ? fichaRes.value.data : [];
      setMateriales(mats);
      setFichas(fichs);
      construirGrafo(mats, fichs, 'material', null, null);
    } catch (e) {
      console.error('Error cargando grafo:', e);
    } finally {
      setCargando(false);
    }
  }

  // ── Construcción del grafo ──────────────────────────────────────────────────
  function construirGrafo(mats, fichs, modo, catExp, matExp) {
    const todosNodos   = [];
    const todosEnlaces = [];
    const nodeMap      = new Map();
    const cx = sizeRef.current.w / 2;
    const cy = sizeRef.current.h / 2;

    if (modo === 'categoria') {
      // Nodos de categoría
      const categorias = [...new Set(mats.map(m => m.categoria || 'Sin categoría'))];
      categorias.forEach((cat, i) => {
        const angle  = (i / categorias.length) * 2 * Math.PI - Math.PI / 2;
        const radius = Math.min(sizeRef.current.w, sizeRef.current.h) * 0.28;
        const nodo = {
          id: `cat:${cat}`, nombre: cat, ktype: 'Categoria',
          radio: 32, es_rect: true,
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
          vx: 0, vy: 0, pinned: false, visible: true,
          materialesCount: mats.filter(m => (m.categoria || 'Sin categoría') === cat).length,
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);
      });

      // Nodos de material (inicialmente ocultos salvo si su categoría está expandida)
      mats.forEach((m, i) => {
        const cat = m.categoria || 'Sin categoría';
        const catNodo = nodeMap.get(`cat:${cat}`);
        const visible = catExp === cat;
        const angle   = (i / Math.max(mats.length, 1)) * 2 * Math.PI;
        const nodo = {
          id: m.id_material_corporativo, nombre: m.nombre_corporativo,
          ktype: 'MaterialComercial', estado: m.estado_material,
          categoria: m.categoria, contenido: m.contenido,
          radio: 20,
          x: catNodo ? catNodo.x + Math.cos(angle) * 90 : cx + Math.cos(angle) * 120,
          y: catNodo ? catNodo.y + Math.sin(angle) * 90 : cy + Math.sin(angle) * 120,
          vx: 0, vy: 0, pinned: false, visible,
          fichasCount: 0, categoriaId: `cat:${cat}`,
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);
        if (visible) {
          todosEnlaces.push({ source: `cat:${cat}`, target: m.id_material_corporativo, tipo: 'categoria_material' });
        }
      });
    } else {
      // Modo material: todos los materiales visibles en círculo
      mats.forEach((m, i) => {
        const angle  = (i / Math.max(mats.length, 1)) * 2 * Math.PI;
        const radius = Math.min(sizeRef.current.w, sizeRef.current.h) * 0.3;
        const nodo = {
          id: m.id_material_corporativo, nombre: m.nombre_corporativo,
          ktype: 'MaterialComercial', estado: m.estado_material,
          categoria: m.categoria, contenido: m.contenido,
          radio: 24,
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
          vx: 0, vy: 0, pinned: false, visible: true,
          fichasCount: 0,
        };
        todosNodos.push(nodo);
        nodeMap.set(nodo.id, nodo);
      });
    }

    // Nodos de ficha (ocultos hasta que se expanda su material)
    fichs.forEach((f) => {
      const parentMat = nodeMap.get(f.id_material_corporativo);
      const visible   = matExp === f.id_material_corporativo;
      const offAngle  = Math.random() * 2 * Math.PI;
      const offDist   = 55 + Math.random() * 35;
      const nodo = {
        id: f.id_ficha, nombre: f.codigo_ficha_local || f.codigo_material_local || 'Sin código',
        ktype: 'FichaTecnica', estado: f.estado_ficha,
        pais: f.pais, version: f.codigo_version,
        materialId: f.id_material_corporativo,
        radio: 13,
        x: parentMat ? parentMat.x + Math.cos(offAngle) * offDist : cx + Math.random() * 200,
        y: parentMat ? parentMat.y + Math.sin(offAngle) * offDist : cy + Math.random() * 200,
        vx: 0, vy: 0, pinned: false, visible,
      };
      todosNodos.push(nodo);
      nodeMap.set(nodo.id, nodo);

      if (parentMat) {
        parentMat.fichasCount = (parentMat.fichasCount || 0) + 1;
        todosEnlaces.push({ source: f.id_ficha, target: f.id_material_corporativo, tipo: 'pertenece_a' });
      }
    });

    needsRecenter.current = true;
    setNodos(todosNodos);
    setEnlaces(todosEnlaces);
    nodosDragRef.current   = todosNodos;
    enlacesDragRef.current = todosEnlaces;
  }

  // ── Cambio de modo ──────────────────────────────────────────────────────────
  function cambiarModo(nuevoModo) {
    if (nuevoModo === modoVista) return;
    setModoVista(nuevoModo);
    setCategoriaExpandida(null);
    setMaterialExpandido(null);
    setNodoSeleccionado(null);
    construirGrafo(materiales, fichas, nuevoModo, null, null);
  }

  // ── Expansión de categoría ──────────────────────────────────────────────────
  function toggleCategoria(catId) {
    const cat = catId.replace('cat:', '');
    const nueva = categoriaExpandida === cat ? null : cat;
    setCategoriaExpandida(nueva);
    setMaterialExpandido(null);
    construirGrafo(materiales, fichas, 'categoria', nueva, null);
  }

  // ── Expansión de material ───────────────────────────────────────────────────
  function toggleMaterial(materialId) {
    const nuevo = materialExpandido === materialId ? null : materialId;
    setMaterialExpandido(nuevo);

    if (modoVista === 'categoria') {
      construirGrafo(materiales, fichas, 'categoria', categoriaExpandida, nuevo);
    } else {
      setNodos((prev) => {
        const updated = prev.map((n) => {
          if (n.ktype === 'FichaTecnica' && n.materialId === materialId)
            return { ...n, visible: nuevo === materialId };
          if (nuevo && n.ktype === 'FichaTecnica' && n.materialId !== materialId)
            return { ...n, visible: false };
          return n;
        });
        nodosDragRef.current = updated;
        return updated;
      });
    }
  }

  // ── Simulación de fuerzas ───────────────────────────────────────────────────
  useEffect(() => {
    if (cargando || nodos.length === 0) return;
    let running = true;

    function tick() {
      if (!running) return;
      const ns = nodosDragRef.current;
      const es = enlacesDragRef.current;
      const nodeMap = new Map(ns.map(n => [n.id, n]));
      const visibles = ns.filter(n => n.visible);

      // Repulsión entre nodos visibles
      for (let i = 0; i < visibles.length; i++) {
        for (let j = i + 1; j < visibles.length; j++) {
          const a = visibles[i], b = visibles[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const minDist = a.radio + b.radio + 50;
          if (dist < minDist * 3) {
            const force = (700 / (dist * dist)) * 0.3;
            const fx = (dx / dist) * force, fy = (dy / dist) * force;
            if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
            if (!b.pinned) { b.vx += fx; b.vy += fy; }
          }
        }
      }

      // Atracción por enlaces
      es.forEach(e => {
        const s = nodeMap.get(e.source), t = nodeMap.get(e.target);
        if (!s || !t || !s.visible || !t.visible) return;
        const dx = t.x - s.x, dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const ideal = e.tipo === 'categoria_material' ? 110 : 80;
        const force = (dist - ideal) * 0.003;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        if (!s.pinned) { s.vx += fx; s.vy += fy; }
        if (!t.pinned) { t.vx -= fx; t.vy -= fy; }
      });

      // Gravedad al centro
      const { w, h } = sizeRef.current;
      visibles.forEach(n => {
        if (!n.pinned) {
          n.vx += (w / 2 - n.x) * 0.0005;
          n.vy += (h / 2 - n.y) * 0.0005;
        }
      });

      // Aplicar velocidad con damping
      ns.forEach(n => {
        if (!n.pinned && n.visible) {
          n.vx *= 0.85; n.vy *= 0.85;
          n.x += n.vx; n.y += n.vy;
        }
      });

      dibujar();
      animRef.current = requestAnimationFrame(tick);
    }

    animRef.current = requestAnimationFrame(tick);
    return () => { running = false; cancelAnimationFrame(animRef.current); };
  }, [cargando, nodos.length, modoVista, categoriaExpandida, materialExpandido, zoom, pan, nodoSeleccionado, busqueda]);

  // ── Dibujo en canvas ────────────────────────────────────────────────────────
  function dibujar() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;
    if (!container) return;

    const dpr = window.devicePixelRatio || 1;
    const cw = container.clientWidth, ch = container.clientHeight;
    if (cw > 0 && ch > 0 && (canvas.width !== cw * dpr || canvas.height !== ch * dpr)) {
      canvas.width = cw * dpr;
      canvas.height = ch * dpr;
    }
    sizeRef.current = { w: cw, h: ch };

    if (needsRecenter.current && cw > 0 && ch > 0) {
      needsRecenter.current = false;
      const vis = nodosDragRef.current.filter(n => n.visible);
      if (vis.length > 0) {
        let sumX = 0, sumY = 0;
        vis.forEach(n => { sumX += n.x; sumY += n.y; });
        const offX = cw / 2 - sumX / vis.length;
        const offY = ch / 2 - sumY / vis.length;
        nodosDragRef.current.forEach(n => { n.x += offX; n.y += offY; });
      }
    }

    const { w, h } = sizeRef.current;
    const ns = nodosDragRef.current;
    const es = enlacesDragRef.current;
    const nodeMap = new Map(ns.map(n => [n.id, n]));
    const busqLower = busqueda.toLowerCase();

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.translate(pan.x + w / 2, pan.y + h / 2);
    ctx.scale(zoom, zoom);
    ctx.translate(-w / 2, -h / 2);

    // Enlazar
    es.forEach(e => {
      const s = nodeMap.get(e.source), t = nodeMap.get(e.target);
      if (!s || !t || !s.visible || !t.visible) return;
      const color = COLOR_ENLACE[e.tipo] || '#cbd5e1';
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      const midX = (s.x + t.x) / 2, midY = (s.y + t.y) / 2 - 20;
      ctx.quadraticCurveTo(midX, midY, t.x, t.y);
      ctx.strokeStyle = color;
      ctx.lineWidth = (e.tipo === 'categoria_material' ? 2 : 1.5) / zoom;
      ctx.setLineDash(e.tipo === 'categoria_material' ? [6 / zoom, 3 / zoom] : []);
      ctx.globalAlpha = 0.55;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    });

    // Nodos
    ns.forEach(n => {
      if (!n.visible) return;
      const match = !busqueda || n.nombre.toLowerCase().includes(busqLower);
      dibujarNodo(ctx, n, zoom, nodoSeleccionado?.id === n.id, match);
    });

    ctx.restore();
  }

  // ── Interacción ─────────────────────────────────────────────────────────────
  function getMousePos(e) {
    const r = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }
  function screenToWorld(sx, sy) {
    const { w, h } = sizeRef.current;
    return { x: (sx - pan.x - w / 2) / zoom + w / 2, y: (sy - pan.y - h / 2) / zoom + h / 2 };
  }
  function findNodeAt(wx, wy) {
    const ns = nodosDragRef.current;
    for (let i = ns.length - 1; i >= 0; i--) {
      const n = ns[i];
      if (!n.visible) continue;
      if (n.es_rect) {
        const r = n.radio;
        if (wx >= n.x - r && wx <= n.x + r && wy >= n.y - r * 0.6 && wy <= n.y + r * 0.6) return n;
      } else {
        const dx = n.x - wx, dy = n.y - wy;
        if (dx * dx + dy * dy < (n.radio + 5) ** 2) return n;
      }
    }
    return null;
  }

  function handleMouseDown(e) {
    const pos = getMousePos(e), world = screenToWorld(pos.x, pos.y);
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
      const pos = getMousePos(e), world = screenToWorld(pos.x, pos.y);
      dragRef.current.nodo.x = world.x;
      dragRef.current.nodo.y = world.y;
      if (Math.abs(world.x - dragRef.current.startX) > 3 || Math.abs(world.y - dragRef.current.startY) > 3)
        dragRef.current.moved = true;
    } else if (panRef.current) {
      setPan({ x: e.clientX - panRef.current.startX, y: e.clientY - panRef.current.startY });
    }
  }
  function handleMouseUp() {
    if (dragRef.current) {
      const { nodo, moved } = dragRef.current;
      nodo.pinned = false;
      dragRef.current = null;
      if (!moved) {
        setNodoSeleccionado(nodo);
        if (nodo.ktype === 'Categoria')        toggleCategoria(nodo.id);
        else if (nodo.ktype === 'MaterialComercial') toggleMaterial(nodo.id);
      }
    }
    panRef.current = null;
  }
  function handleWheel(e) {
    e.preventDefault();
    setZoom(z => Math.min(Math.max(z * (e.deltaY > 0 ? 0.9 : 1.1), 0.3), 4));
  }

  function resetView() {
    setZoom(1); setPan({ x: 0, y: 0 });
    setCategoriaExpandida(null); setMaterialExpandido(null);
    setNodoSeleccionado(null);
    construirGrafo(materiales, fichas, modoVista, null, null);
  }

  // ── Contadores para leyenda ─────────────────────────────────────────────────
  const totalCategoria = [...new Set(materiales.map(m => m.categoria || 'Sin categoría'))].length;

  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grafo de Conocimiento</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {modoVista === 'categoria'
              ? 'Click en una categoría para ver sus materiales · Click en un material para ver sus fichas'
              : 'Click en un material para expandir sus fichas · Arrastra los nodos para reorganizar'}
          </p>
        </div>

        {/* Leyenda de estados */}
        <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
          {modoVista === 'categoria' && (
            <>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-2 rounded bg-[#1e40af]" /> Categorías ({totalCategoria})
              </span>
              <span className="text-gray-300">|</span>
            </>
          )}
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#044926]" /> Materiales ({materiales.length})
          </span>
          <span className="text-gray-300">|</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#29b34b]" /> Vigente</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#f59e0b]" /> Preliminar</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#ef4444]" /> Obsoleto</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#9ca3af]" /> Borrador</span>
          <span className="text-gray-300">|</span>
          <span>{fichas.length} fichas · {enlaces.length} relaciones</span>
        </div>
      </div>

      {/* Controles */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {/* Toggle de vista */}
        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
          <button
            onClick={() => cambiarModo('material')}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors ${
              modoVista === 'material' ? 'bg-[#044926] text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Package size={14} /> Por Material
          </button>
          <button
            onClick={() => cambiarModo('categoria')}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-l border-gray-200 ${
              modoVista === 'categoria' ? 'bg-[#1e40af] text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Layers size={14} /> Por Categoría
          </button>
        </div>

        {/* Búsqueda */}
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text" placeholder="Buscar nodo…"
            value={busqueda} onChange={e => setBusqueda(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b]"
          />
        </div>

        {/* Zoom + reset */}
        <div className="flex items-center gap-1">
          <button onClick={() => setZoom(z => Math.min(z * 1.3, 4))} className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50" title="Zoom in"><ZoomIn size={15} /></button>
          <button onClick={() => setZoom(z => Math.max(z * 0.7, 0.3))} className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50" title="Zoom out"><ZoomOut size={15} /></button>
          <button onClick={resetView} className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50" title="Resetear vista"><Maximize2 size={15} /></button>
        </div>
      </div>

      {/* Canvas + Panel detalle */}
      <div className="flex gap-4">
        <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden relative" style={{ height: '620px' }}>
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

          {cargando && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
              <div className="text-center">
                <div className="w-8 h-8 border-3 border-[#29b34b]/30 border-t-[#29b34b] rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-gray-500">Construyendo grafo…</p>
              </div>
            </div>
          )}
          {!cargando && nodos.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <Network size={48} className="mx-auto text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">No hay datos para mostrar</p>
              </div>
            </div>
          )}

          {/* Instrucción flotante */}
          {!cargando && nodos.length > 0 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/70 text-white text-xs px-4 py-2 rounded-full backdrop-blur-sm whitespace-nowrap">
              {modoVista === 'categoria' && !categoriaExpandida && 'Click en una categoría (CAT) para expandir sus materiales'}
              {modoVista === 'categoria' &&  categoriaExpandida && !materialExpandido && 'Click en un material para ver sus fichas · Click en CAT para colapsar'}
              {modoVista === 'material' && !materialExpandido && 'Click en un material para ver sus fichas · Scroll para zoom'}
              {materialExpandido && 'Click en el material para colapsar sus fichas'}
            </div>
          )}
        </div>

        {/* Panel detalle lateral */}
        {nodoSeleccionado && (
          <div className="w-72 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden shrink-0">
            <div
              className="flex items-center justify-between px-4 py-3 border-b"
              style={{ backgroundColor: colorNodo(nodoSeleccionado).bg + '18' }}
            >
              <div className="flex items-center gap-2">
                {nodoSeleccionado.ktype === 'Categoria' && <Layers size={16} className="text-[#1e40af]" />}
                {nodoSeleccionado.ktype === 'MaterialComercial' && <Package size={16} className="text-[#044926]" />}
                {nodoSeleccionado.ktype === 'FichaTecnica' && <FileText size={16} className="text-[#29b34b]" />}
                <span className="text-sm font-semibold text-gray-900">
                  {{ Categoria: 'Categoría', MaterialComercial: 'Material', FichaTecnica: 'Ficha Técnica' }[nodoSeleccionado.ktype]}
                </span>
              </div>
              <button onClick={() => setNodoSeleccionado(null)} className="p-1 text-gray-400 hover:text-gray-600"><X size={16} /></button>
            </div>

            <div className="p-4 space-y-3">
              <div>
                <p className="text-xs text-gray-500">Nombre</p>
                <p className="text-sm font-semibold text-gray-900">{nodoSeleccionado.nombre}</p>
              </div>

              {nodoSeleccionado.estado && (
                <div>
                  <p className="text-xs text-gray-500">Estado</p>
                  <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                    ['Vigente','Activo'].includes(nodoSeleccionado.estado) ? 'bg-green-100 text-green-700' :
                    nodoSeleccionado.estado === 'Preliminar' ? 'bg-yellow-100 text-yellow-700' :
                    nodoSeleccionado.estado === 'Borrador'   ? 'bg-gray-100 text-gray-600' :
                    'bg-red-100 text-red-700'
                  }`}>{nodoSeleccionado.estado}</span>
                </div>
              )}

              {nodoSeleccionado.ktype === 'Categoria' && (
                <div>
                  <p className="text-xs text-gray-500">Materiales</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.materialesCount} materiales</p>
                </div>
              )}
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
              {nodoSeleccionado.fichasCount > 0 && (
                <div>
                  <p className="text-xs text-gray-500">Fichas técnicas</p>
                  <p className="text-sm text-gray-700">{nodoSeleccionado.fichasCount} fichas</p>
                </div>
              )}
              <div>
                <p className="text-xs text-gray-500">Conexiones</p>
                <p className="text-sm text-gray-700">
                  {enlaces.filter(e => e.source === nodoSeleccionado.id || e.target === nodoSeleccionado.id).length} relaciones
                </p>
              </div>

              {nodoSeleccionado.ktype !== 'Categoria' && (
                <Link
                  to={nodoSeleccionado.ktype === 'MaterialComercial'
                    ? `/materiales/${nodoSeleccionado.id}`
                    : `/fichas/${nodoSeleccionado.id}`}
                  className="flex items-center justify-center gap-1 w-full text-sm font-medium text-white bg-[#044926] hover:bg-[#29b34b] py-2 rounded-lg transition-colors mt-2"
                >
                  Ver detalle <ChevronRight size={14} />
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
