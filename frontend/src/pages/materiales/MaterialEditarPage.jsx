import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Save, AlertTriangle } from 'lucide-react';
import api from '../../../lib/api';

const CATEGORIAS = ['Estuche', 'Tapa', 'Separador', 'Bandeja', 'Porta vasos', 'Otro'];
const CONTENIDOS = [
  'Huevos', 'Frutas y Verduras', 'Pinturas y recubrimientos', 'Vasos',
  'Botellas', 'Alimentos frescos', 'Industrial', 'Otro',
];

const CARACTERISTICAS = [
  'Bipartido', 'Con división', 'Con tapa', 'Con ventana', 'Elíptico',
  'Llana', 'No aplica', 'Profunda', 'Sin división', 'Sin etiqueta', 'Sin ventana',
];
const MATERIALES_BASE = ['Pulpa Moldeada', 'Cartón', 'Plástico', 'EPS', 'Otros'];
const TIPOS_PRODUCTO = ['Producto Terminado', 'Materia Prima', 'Insumo', 'Empaque'];

export default function MaterialEditarPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [anomalias, setAnomalias] = useState([]);

  const [form, setForm] = useState({
    nombre_corporativo: '',
    contenido: '',
    categoria: '',
    sector: '',
    caracteristica: '',
    material_base: '',
    capacidad_nominal: '',
    tipo_producto: '',
    estado_material: '',
  });

  useEffect(() => {
    async function cargar() {
      try {
        const res = await api.get(`/material/${id}`);
        const m = res.data;
        setForm({
          nombre_corporativo: m.nombre_corporativo || '',
          contenido: m.contenido || '',
          categoria: m.categoria || '',
          sector: m.sector || '',
          caracteristica: m.caracteristica || '',
          material_base: m.material_base || '',
          capacidad_nominal: m.capacidad_nominal || '',
          tipo_producto: m.tipo_producto || '',
          estado_material: m.estado_material || '',
        });
      } catch (err) {
        setError('Error cargando material');
      } finally {
        setCargando(false);
      }
    }
    cargar();
  }, [id]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setAnomalias([]);
    setGuardando(true);

    try {
      const payload = {};
      Object.entries(form).forEach(([k, v]) => {
        if (v !== '' && v !== null) payload[k] = v;
      });

      const res = await api.patch(`/material/${id}`, {
        ...payload,
        usuario: 'marco.agrusa',
      });

      if (res.data.anomalias && res.data.anomalias.length > 0) {
        setAnomalias(res.data.anomalias);
      }

      navigate(`/materiales/${id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al actualizar');
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) {
    return <div className="text-center py-12 text-sm text-gray-500">Cargando...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Link to={`/materiales/${id}`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={16} /> Volver al material
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Editar Material</h1>

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
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nombre Corporativo</label>
          <input type="text" name="nombre_corporativo" value={form.nombre_corporativo} onChange={handleChange}
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
            <select name="categoria" value={form.categoria} onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Seleccionar...</option>
              {CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contenido</label>
            <select name="contenido" value={form.contenido} onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Seleccionar...</option>
              {CONTENIDOS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Material Base</label>
            <select name="material_base" value={form.material_base} onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Seleccionar...</option>
              {MATERIALES_BASE.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Producto</label>
            <select name="tipo_producto" value={form.tipo_producto} onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Seleccionar...</option>
              {TIPOS_PRODUCTO.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sector</label>
            <input type="text" name="sector" value={form.sector} onChange={handleChange}
              placeholder="Ej: Alimentos, Farmacéutico"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Característica</label>
            <select name="caracteristica" value={form.caracteristica} onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Seleccionar...</option>
              {CARACTERISTICAS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Capacidad Nominal</label>
            <input type="text" name="capacidad_nominal" value={form.capacidad_nominal} onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <div className="pt-4 border-t border-gray-100">
          <button type="submit" disabled={guardando}
            className="flex items-center gap-2 bg-[#29b34b] text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926] disabled:opacity-50 transition-colors">
            <Save size={16} />
            {guardando ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </form>
    </div>
  );
}