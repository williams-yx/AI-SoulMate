import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import wasm from 'vite-plugin-wasm'
import topLevelAwait from 'vite-plugin-top-level-await'

export default defineConfig({
  plugins: [vue(), wasm(), topLevelAwait()],
  server: {
    host: true,
    port: 8080,
    allowedHosts: ['59.110.238.204', 'aiinfomate.com', 'www.aiinfomate.com'],
    // Windows/Docker 下 bind mount 文件变更可能不触发，用轮询保证 HMR 生效
    watch: {
      usePolling: true,
      interval: 500
    },
    proxy: {
      // 让前端通过 /api 访问后端，避免 CORS/端口问题
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:3000',
        changeOrigin: true
      },
      '/uploads': {
        target: process.env.VITE_API_TARGET || 'http://localhost:3000',
        changeOrigin: true
      }
    }
  }
})
