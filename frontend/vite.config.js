import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import mockApi from './mock-api-plugin.js'

// Vite 构建配置
// 1) @ 别名指向 src
// 2) 开发服务器代理 /api 到后端（后端未启动时使用 mock）
// 3) 构建输出到 dist/
export default defineConfig({
  plugins: [vue(), mockApi()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    open: false,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'graph-vendor': ['@antv/g6', 'echarts', 'vue-echarts'],
          'ui-vendor': ['element-plus', '@element-plus/icons-vue']
        }
      }
    }
  }
})
