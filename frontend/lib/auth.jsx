import { useState, useEffect, createContext, useContext } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('dsms_token');
    const stored = localStorage.getItem('dsms_user');

    if (token && stored) {
      try {
        const userData = JSON.parse(stored);
        // Verificar expiración del token decodificando el payload
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000;
        if (Date.now() < exp) {
          setUser(userData);
        } else {
          localStorage.removeItem('dsms_token');
          localStorage.removeItem('dsms_user');
        }
      } catch {
        localStorage.removeItem('dsms_token');
        localStorage.removeItem('dsms_user');
      }
    }
    setCargando(false);
  }, []);

  function login(userData, token) {
    localStorage.setItem('dsms_token', token);
    localStorage.setItem('dsms_user', JSON.stringify(userData));
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem('dsms_token');
    localStorage.removeItem('dsms_user');
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, cargando, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return ctx;
}