import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  envDir: '../', // load env files from repository root
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: parseInt(process.env.VITE_FRONTEND_PORT || '50010', 10),
    host: process.env.VITE_FRONTEND_HOST || '127.0.0.1',
    strictPort: true,
    open: false,
    cors: true,
    allowedHosts: true,
    hmr: {
      overlay: true,
      timeout: 30_000,
      host: process.env.VITE_HMR_HOST || undefined,
      port: parseInt(
        process.env.VITE_HMR_PORT ||
          process.env.VITE_FRONTEND_PORT ||
          process.env.VITE_API_PORT ||
          '50010',
        10,
      ),
      protocol: process.env.VITE_HMR_PROTOCOL || 'ws',
    },
    watch: {
      usePolling: true,
      interval: 1000,
    },
    // 解决 ERR_CONTENT_LENGTH_MISMATCH 问题
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      'Transfer-Encoding': 'chunked'
    },
    // 禁用压缩，让 Nginx 处理
    middlewareMode: false,
    // 强制使用 HTTP/1.1
    https: false,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,  // 禁用 sourcemap 以减少内存使用
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['framer-motion', 'lucide-react'],
          'three-vendor': ['three', '@react-three/fiber', '@react-three/drei'],
        },
      },
    },
    // 减少内存使用
    minify: 'esbuild',  // 使用 esbuild 而不是 terser，更快且内存占用更少
    target: 'es2015',   // 降低目标版本以减少转换开销
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom'],
    // 强制预构建所有依赖，避免运行时优化导致的内容长度问题
    force: false,
    // 禁用依赖发现
    disabled: false,
  },
  // 添加此配置以解决内容长度不匹配问题
  preview: {
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  }
})