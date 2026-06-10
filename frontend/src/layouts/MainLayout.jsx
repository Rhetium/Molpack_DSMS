import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  FileText,
  AlertTriangle,
  History,
  Menu,
  X,
  LogOut,
  Network,
} from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../../lib/auth';

const navegacion = [
  { nombre: 'Dashboard', ruta: '/', icono: LayoutDashboard },
  { nombre: 'Materiales', ruta: '/materiales', icono: Package },
  { nombre: 'Fichas Técnicas', ruta: '/fichas', icono: FileText },
  { nombre: 'Anomalías', ruta: '/anomalias', icono: AlertTriangle },
  { nombre: 'Auditoría', ruta: '/auditoria', icono: History },
  { nombre: 'Grafo', ruta: '/grafo', icono: Network },
];

export default function MainLayout() {
  const [sidebarAbierto, setSidebarAbierto] = useState(false);
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Overlay móvil */}
      {sidebarAbierto && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarAbierto(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full w-64
          bg-[#044926] text-white
          transform transition-transform duration-200 ease-in-out
          lg:translate-x-0
          ${sidebarAbierto ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img src="../../public/LOGO MONO MOLPACK.png" alt="Molpack" className="w-8 h-8 rounded-lg" />
            <div>
              <h1 className="text-sm font-bold text-white">DSMS</h1>
              <p className="text-xs text-white/50">Molpack Corporation</p>
            </div>
          </div>
          <button
            className="lg:hidden p-1 text-white/50 hover:text-white"
            onClick={() => setSidebarAbierto(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navegación */}
        <nav className="p-3 space-y-1 mt-2">
          {navegacion.map((item) => (
            <NavLink
              key={item.ruta}
              to={item.ruta}
              onClick={() => setSidebarAbierto(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#29b34b] text-white'
                    : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <item.icono size={18} />
              {item.nombre}
            </NavLink>
          ))}
        </nav>

        {/* Usuario placeholder */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#29b34b] rounded-full flex items-center justify-center">
                <span className="text-xs font-bold text-white">{user?.iniciales || 'US'}</span>
              </div>
              <div>
                <p className="text-sm font-medium text-white">{user?.nombre || 'Usuario'}</p>
                <p className="text-xs text-white/50">{user?.rol || 'Sin rol'}</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Cerrar sesión"
              className="p-1.5 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Contenido principal */}
      <div className="lg:ml-64">
        {/* Header */}
        <header className="sticky top-0 z-30 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center">
            <button
              className="lg:hidden p-2 -ml-2 text-gray-500 hover:text-gray-700"
              onClick={() => setSidebarAbierto(true)}
            >
              <Menu size={20} />
            </button>
            <p className="ml-4 lg:ml-0 text-sm text-gray-500">
              Dataspace Management System
            </p>
          </div>
          <img src="../../public/LOGO MOLPACK 450x240pixeles.png" alt="Molpack" className="h-24 hidden sm:block" />
        </header>

        {/* Contenido de la página */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}