import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import DiagnosticPage from './pages/DiagnosticPage'
import AuthGatePage from './pages/AuthGatePage'

import StorageValidator from './components/StorageValidator'
import { useAutoSave } from './hooks/useAutoSave'
import { useState, useEffect } from 'react'

const routerFutureFlags = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const

// 受保护的路由组件
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const sessionId = localStorage.getItem('researchmind_session_id') || `session_${Date.now()}`
      localStorage.setItem('researchmind_session_id', sessionId)

      // 检查是否有用户配置
      const response = await fetch(`/api/billing/config/${sessionId}`)

      if (response.ok) {
        const result = await response.json()
        setIsAuthenticated(result.has_config && !!result.config?.access_key_masked)
      } else {
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('认证检查失败:', error)
      setIsAuthenticated(false)
    }
  }

  // 检查中，显示加载状态
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">正在检查认证状态...</p>
        </div>
      </div>
    )
  }

  // 未认证，跳转到认证页面
  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }

  // 已认证，显示内容
  return <>{children}</>
}

function App() {
  console.log('App component rendering...')

  // 启用自动保存功能
  useAutoSave(30000) // 30秒自动保存一次

  // 添加错误边界
  try {
    return (
      <StorageValidator>
        <div className="min-h-screen bg-gray-50">
          <Router future={routerFutureFlags}>
            <Routes>
              {/* 认证页面 - 不需要认证 */}
              <Route path="/auth" element={<AuthGatePage />} />

              {/* 诊断页面 - 不需要认证 */}
              <Route path="/diagnostic" element={<DiagnosticPage />} />

              {/* 受保护的页面 - 需要认证 */}
              <Route path="/" element={<ProtectedRoute><Layout><ChatPage /></Layout></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Layout><SettingsPage /></Layout></ProtectedRoute>} />
            </Routes>
          </Router>
        </div>
      </StorageValidator>
    )
  } catch (error) {
    console.error('App rendering error:', error)
    return (
      <div className="min-h-screen bg-red-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl">
          <h1 className="text-2xl font-bold text-red-600 mb-4">应用渲染错误</h1>
          <p className="text-gray-700 mb-4">应用在渲染时遇到错误，请查看浏览器控制台获取详细信息。</p>
          <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
            {error instanceof Error ? error.message : String(error)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            刷新页面
          </button>
        </div>
      </div>
    )
  }
}

export default App
