import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        configure(proxy) {
          proxy.on('proxyReq', proxyReq => {
            proxyReq.setHeader('origin', 'http://localhost:5173')
          })
        },
      },
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
