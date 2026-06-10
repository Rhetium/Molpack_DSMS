import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '../lib/auth';
import MainLayout from './layouts/MainLayout';
import LoginPage from './pages/auth/LoginPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import MaterialesPage from './pages/materiales/MaterialesPage';
import MaterialDetallePage from './pages/materiales/MaterialDetallePage';
import MaterialCrearPage from './pages/materiales/MaterialCrearPage';
import MaterialEditarPage from './pages/materiales/MaterialEditarPage';
import FichasPage from './pages/fichas/FichasPage';
import FichaDetallePage from './pages/fichas/FichaDetallePage';
import FichaCrearPage from './pages/fichas/FichaCrearPage';
import FichaEditarPage from './pages/fichas/FichaEditarPage';
import AnomaliasPage from './pages/anomalias/AnomaliasPage';
import AuditoriaPage from './pages/auditoria/AuditoriaPage';
import GrafoPage from './pages/grafo/GrafoPage';
import DevAnomaliaPage from './pages/dev/DevAnomaliaPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function RutaProtegida({ children }) {
  const { user, cargando } = useAuth();

  if (cargando) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-3 border-[#29b34b]/30 border-t-[#29b34b] rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <RutaProtegida>
                  <MainLayout />
                </RutaProtegida>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/materiales" element={<MaterialesPage />} />
              <Route path="/materiales/nuevo" element={<MaterialCrearPage />} />
              <Route path="/materiales/:id" element={<MaterialDetallePage />} />
              <Route path="/materiales/:id/editar" element={<MaterialEditarPage />} />
              <Route path="/fichas" element={<FichasPage />} />
              <Route path="/fichas/nueva" element={<FichaCrearPage />} />
              <Route path="/fichas/:id" element={<FichaDetallePage />} />
              <Route path="/fichas/:id/editar" element={<FichaEditarPage />} />
              <Route path="/anomalias" element={<AnomaliasPage />} />
              <Route path="/auditoria" element={<AuditoriaPage />} />
              <Route path="/grafo" element={<GrafoPage />} />
              <Route path="/dev/anomalias" element={<DevAnomaliaPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;