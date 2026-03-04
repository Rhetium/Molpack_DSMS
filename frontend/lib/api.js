import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para manejar errores globalmente
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const mensaje = error.response?.data?.detail || 'Error de conexión con el servidor';
    console.error('API Error:', mensaje);
    return Promise.reject(error);
  }
);

export default api;