import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Pair 16: backend runs on http://127.0.0.1:9160 (PORT_BASE 9000 + 16*10).
// Frontend runs on 5173 (Vite default) or 3000 -- backend CORS already allows both.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})
