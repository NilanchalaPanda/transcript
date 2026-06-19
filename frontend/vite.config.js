import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Allow external access
    allowedHosts: [
      '.ngrok-free.app', // Allow all ngrok free tier hosts
      '.ngrok-free.dev', // Allow all ngrok free tier hosts (new domain)
      '.ngrok.io',       // Allow all ngrok paid tier hosts
      '.ngrok.app',      // Allow all ngrok app hosts
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      }
    }
  }
})
