import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor REQUEST: agregar token JWT a cada petición
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('dsms_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor RESPONSE: manejar errores y expiración de token
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const mensaje = error.response?.data?.detail || 'Error de conexión con el servidor';

    // Token expirado o inválido → cerrar sesión
    if (status === 401) {
      localStorage.removeItem('dsms_token');
      localStorage.removeItem('dsms_user');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }

    console.error('API Error:', mensaje);
    return Promise.reject(error);
  }
);

export default api;