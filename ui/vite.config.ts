import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  envDir: '../', // 指向根目录读取.env文件
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: parseInt(process.env.VITE_FRONTEND_PORT || '50001'),
    host: process.env.VITE_FRONTEND_HOST || '0.0.0.0',
    strictPort: true,
    open: false, // 改为false，避免自动打开浏览器
    cors: true,
    allowedHosts: ['all'],
    hmr: {
      overlay: true,
      timeout: 30000,
      // 支持跨主机访问时的 HMR 配置
      host: process.env.VITE_HMR_HOST || 'localhost',
      port: parseInt(process.env.VITE_HMR_PORT || process.env.VITE_FRONTEND_PORT || '50001'),
      protocol: process.env.VITE_HMR_PROTOCOL || 'ws',
    },
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['framer-motion', 'lucide-react'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom'],
  },
})