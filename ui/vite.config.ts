import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the parent directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')

  return {
    plugins: [react()],
    envDir: '../', // load env files from repository root
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: parseInt(env.VITE_FRONTEND_PORT || '50010', 10),
      host: env.VITE_FRONTEND_HOST || '127.0.0.1',
      strictPort: true,
      open: false,
      cors: true,
      allowedHosts: true,
      hmr: {

        overlay: true,
        timeout: 30_000,
        // Let Vite determine host/port automatically based on window.location
        // This is crucial for working behind reverse proxies (Nginx/Bohrium)
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
      // https: false, // Removed to fix type error
      // Proxy configuration for local development or when accessing Vite directly
      proxy: {
        '/api': {
          target: `http://${env.RESEARCHMIND_HTTP_HOST || '127.0.0.1'}:${env.RESEARCHMIND_HTTP_PORT || '50002'}`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/ws': {
          target: `ws://${env.RESEARCHMIND_WS_HOST || '127.0.0.1'}:${env.RESEARCHMIND_WS_PORT || '50003'}`,
          ws: true,
          changeOrigin: true,
        },
      },
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
      force: false
    },
    // 添加此配置以解决内容长度不匹配问题
    preview: {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    }
  }
})