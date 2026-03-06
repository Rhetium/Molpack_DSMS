import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Save, AlertTriangle } from 'lucide-react';
import api from '../../../lib/api';

const CATEGORIAS = [
  'Estuche', 'Tapa', 'Separador', 'Bandeja', 'Porta vasos', 'Otro',
];

const CONTENIDOS = [
  'Huevos', 'Frutas', 'Potes de pintura', 'Vasos', 'Industrial', 'Otro',
];

const MATERIALES_BASE = [
  'Pulpa Moldeada', 'Cartón', 'Plástico', 'EPS', 'Otros',
];

const TIPOS_PRODUCTO = [
  'Producto Terminado', 'Materia Prima', 'Insumo', 'Empaque',
];

export default function MaterialCrearPage() {
  const navigate = useNavigate();
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [anomalias, setAnomalias] = useState([]);

  const [form, setForm] = useState({
    nombre_corporativo: '',
    contenido: '',
    categoria: '',
    material_base: '',
    capacidad_nominal: '',
    tipo_producto: '',
    estado_material: 'Activo',
    usuario_creador: 'marco.agrusa',
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setAnomalias([]);

    if (!form.nombre_corporativo.trim()) {
      setError('El nombre corporativo es obligatorio');
      return;
    }

    setGuardando(true);
    try {
      const payload = { ...form };
      // Limpiar campos vacíos
      Object.keys(payload).forEach((k) => {
        if (payload[k] === '') payload[k] = null;
      });
      payload.nombre_corporativo = form.nombre_corporativo;
      payload.estado_material = form.estado_material || 'Activo';
      payload.usuario_creador = form.usuario_creador;

      const res = await api.post('/material', payload);

      // Verificar anomalías en respuesta
      if (res.data.anomalias && res.data.anomalias.length > 0) {
        setAnomalias(res.data.anomalias);
      }

      navigate(`/materiales/${res.data.id_material_corporativo}`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al crear material';
      setError(msg);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Navegación */}
      <Link
        to="/materiales"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={16} />
        Volver a materiales
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Nuevo Material Comercial</h1>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      {/* Anomalías detectadas */}
      {anomalias.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-amber-600" />
            <p className="text-sm font-medium text-amber-800">
              Se detectaron {anomalias.length} anomalía(s)
            </p>
          </div>
          {anomalias.map((a, i) => (
            <p key={i} className="text-sm text-amber-700 ml-6">• {a.mensaje}</p>
          ))}
        </div>
      )}

      {/* Formulario */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        {/* Nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nombre Corporativo <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="nombre_corporativo"
            value={form.nombre_corporativo}
            onChange={handleChange}
            placeholder="Ej: Estuche 1x12 sin ventana S/I"
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Categoría + Contenido */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
            <select
              name="categoria"
              value={form.categoria}
              onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {CATEGORIAS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contenido</label>
            <select
              name="contenido"
              value={form.contenido}
              onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {CONTENIDOS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Material Base + Tipo Producto */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Material Base</label>
            <select
              name="material_base"
              value={form.material_base}
              onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {MATERIALES_BASE.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Producto</label>
            <select
              name="tipo_producto"
              value={form.tipo_producto}
              onChange={handleChange}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {TIPOS_PRODUCTO.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Capacidad Nominal */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Capacidad Nominal</label>
          <input
            type="text"
            name="capacidad_nominal"
            value={form.capacidad_nominal}
            onChange={handleChange}
            placeholder="Ej: 12 unidades, 1x30"
            className="w-full max-w-xs px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Botón */}
        <div className="pt-4 border-t border-gray-100">
          <button
            type="submit"
            disabled={guardando}
            className="flex items-center gap-2 bg-[#29b34b] text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-[#044926] disabled:opacity-50 transition-colors"
          >
            <Save size={16} />
            {guardando ? 'Creando...' : 'Crear Material'}
          </button>
        </div>
      </form>
    </div>
  );
}