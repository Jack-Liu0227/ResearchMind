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
