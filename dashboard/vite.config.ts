import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// base './' para que el build funcione desde cualquier ruta.
// El proxy solo aplica al servidor de desarrollo (npm run dev).
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
