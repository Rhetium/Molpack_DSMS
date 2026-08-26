import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['.ngrok-free.dev'],
    proxy: {
      // Sin `rewrite`: el backend ya expone todo bajo /api (app/main.py),
      // asi la ruta es identica en desarrollo y en produccion.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
