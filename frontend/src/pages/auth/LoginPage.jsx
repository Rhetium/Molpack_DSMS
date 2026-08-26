import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, LogIn } from 'lucide-react';
import api from '../../../lib/api';
import { useAuth } from '../../../lib/auth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!usuario.trim() || !password.trim()) {
      setError('Ingresa usuario y contraseña');
      return;
    }

    setCargando(true);

    try {
      const res = await api.post('/auth/login', {
        usuario: usuario,
        password: password,
      });

      const data = res.data;

      if (data.exito) {
        login({
          usuario: data.usuario,
          nombre: data.nombre,
          rol: data.rol,
          iniciales: data.iniciales,
          email: data.email,
          metodo: data.metodo,
        }, data.token);
        navigate('/');
      } else {
        const intentos = data.intentos_restantes;
        const msg = data.mensaje || 'Credenciales inválidas.';
        setError(intentos !== undefined && intentos <= 3
          ? `${msg} (${intentos} intentos restantes)`
          : msg
        );
      }
    } catch (err) {
      const status = err.response?.status;
      if (status === 429) {
        setError(err.response.data.detail || 'Demasiados intentos. Espera unos minutos.');
      } else {
        const msg = err.response?.data?.detail || err.response?.data?.mensaje || 'Error de conexión con el servidor.';
        setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
      }
    }

    setCargando(false);
  }

  return (
    <div className="min-h-screen flex">
      {/* Panel izquierdo — Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#044926] relative overflow-hidden flex-col items-center justify-center">
        {/* Patrón decorativo */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 -left-10 w-72 h-72 rounded-full border-2 border-white" />
          <div className="absolute top-40 left-20 w-96 h-96 rounded-full border border-white" />
          <div className="absolute -bottom-20 right-10 w-80 h-80 rounded-full border-2 border-white" />
          <div className="absolute bottom-40 -right-10 w-60 h-60 rounded-full border border-white" />
        </div>

        {/* Contenido branding */}
        <div className="relative z-10 text-center px-16">
          <img
            src="/LOGO WHITE VERTICAL.png"
            alt="Molpack"
            className="h-48 mx-auto mb-10 drop-shadow-lg"
          />
          <div className="w-16 h-0.5 bg-[#29b34b] mx-auto mb-8" />
          <h2 className="text-2xl font-light text-white/90 leading-relaxed mb-4">
            Dataspace Management System
          </h2>
          <p className="text-sm text-white/50 max-w-sm mx-auto leading-relaxed">
            Gestión inteligente de fichas técnicas, materiales y trazabilidad
            para la industria de empaques de pulpa moldeada.
          </p>
        </div>

        {/* Footer branding */}
        <div className="absolute bottom-8 text-center">
          <p className="text-xs text-white/30">Molpack Corporation S.A.S.</p>
        </div>
      </div>

      {/* Panel derecho — Formulario */}
      <div className="flex-1 flex items-center justify-center px-6 bg-gray-50">
        <div className="w-full max-w-sm">
          {/* Logo móvil */}
          <div className="lg:hidden mb-10 text-center">
            <img src="/LOGO MOLPACK 450x240pixeles.png" alt="Molpack" className="h-12 mx-auto mb-4" />
          </div>

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Iniciar Sesión</h1>
            <p className="text-sm text-gray-500 mt-2">
              Accede al sistema de gestión de fichas técnicas
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
              {error}
            </div>
          )}

          {/* Formulario */}
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Usuario
              </label>
              <input
                type="text"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                placeholder="nombre.apellido"
                autoComplete="username"
                className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b] focus:border-transparent transition-shadow"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={mostrarPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
                  className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#29b34b] focus:border-transparent transition-shadow"
                />
                <button
                  type="button"
                  onClick={() => setMostrarPassword(!mostrarPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {mostrarPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={cargando}
              className="w-full flex items-center justify-center gap-2 bg-[#044926] text-white py-3 rounded-lg text-sm font-semibold hover:bg-[#29b34b] disabled:opacity-50 transition-colors"
            >
              {cargando ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <LogIn size={18} />
                  Ingresar
                </>
              )}
            </button>
          </div>

          {/* Credenciales demo */}
          <div className="mt-8 p-4 bg-white border border-gray-200 rounded-lg">
            <p className="text-xs font-medium text-gray-500 mb-2">Credenciales de prueba</p>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Admin:</span>
                <code className="text-xs bg-gray-50 px-2 py-0.5 rounded text-gray-700">marco.agrusa / molpack2025</code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Admin:</span>
                <code className="text-xs bg-gray-50 px-2 py-0.5 rounded text-gray-700">admin / admin</code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Demo:</span>
                <code className="text-xs bg-gray-50 px-2 py-0.5 rounded text-gray-700">demo / demo</code>
              </div>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-gray-400 mt-8">
            Molpack DSMS v1.0
          </p>
        </div>
      </div>
    </div>
  );
}