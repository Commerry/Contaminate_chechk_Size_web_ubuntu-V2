import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // เปิดให้เครื่องอื่นเข้าถึงได้
    port: 64020,
    proxy: {
      '/api': {
        target: 'http://localhost:64021',
        changeOrigin: true
      },
      '/socket.io': {
        target: 'http://localhost:64021',
        changeOrigin: true,
        ws: true
      }
    }
  }
})
