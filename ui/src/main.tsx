import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'
import { initStorage } from './utils/storage'

// 初始化存储系统（自动修复侧边栏状态）
// 🔧 添加浏览器环境检查，防止 SSR Hydration 错误
if (typeof window !== 'undefined') {
  try {
    initStorage()
  } catch (error) {
    console.error('存储初始化失败:', error)
    // 清除损坏的数据
    try {
      localStorage.clear()
      console.log('✅ 已清除损坏的存储数据，请刷新页面')
    } catch (e) {
      console.error('清除存储失败:', e)
    }
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // 内存优化：减少缓存时间和缓存数量
      gcTime: 5 * 60 * 1000,  // 5分钟后清理未使用的缓存（原 cacheTime）
      staleTime: 2 * 60 * 1000,  // 2分钟后数据标记为过期
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  // 暂时禁用 StrictMode 以解决 WebSocket 重复连接问题
  // <React.StrictMode>
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-center"
        containerStyle={{
          zIndex: 99999,
        }}
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#22c55e',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </QueryClientProvider>
  </ErrorBoundary>
  // </React.StrictMode>,
)