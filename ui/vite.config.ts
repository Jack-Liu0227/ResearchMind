import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// 获取允许的主机列表
function getAllowedHosts(): string[] {
  // 如果设置了 VITE_ALLOWED_HOSTS，使用逗号分隔的列表
  if (process.env.VITE_ALLOWED_HOSTS) {
    return process.env.VITE_ALLOWED_HOSTS.split(',').map(h => h.trim())
  }

  // 默认允许所有主机
  return ['all']
}

export default defineConfig({
  plugins: [react()],
  envDir: '../', // 指向根目录读取.env文件
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // Listen on configured host and port
    // When behind Nginx reverse proxy, this allows the proxy to connect
    port: parseInt(process.env.VITE_FRONTEND_PORT || '50010'),
    host: process.env.VITE_FRONTEND_HOST || '127.0.0.1',
    strictPort: true, // 使用指定的端口，如果被占用则失败
    open: false, // 改为false，避免自动打开浏览器
    cors: true,
    // Allow all hosts - set to true to disable Host header validation
    // This is safe when behind a reverse proxy that validates the Host header
    allowedHosts: true,
    hmr: {
      overlay: true,
      timeout: 30000,
      // HMR configuration for frontend UI
      // 在远程部署时，使用客户端访问的域名
      host: process.env.VITE_HMR_HOST || undefined,
      port: parseInt(process.env.VITE_HMR_PORT || process.env.VITE_API_PORT || '50001'),
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