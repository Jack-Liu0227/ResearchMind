/**
 * 主应用组件
 *
 * ✅ 认证方式：完全基于 Cookie（不使用 JWT Token）
 * ✅ 登录门户：阻塞式，用户必须先登录才能进入主界面
 * ✅ 数据库：仅用于统计和历史记录
 */

import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import DiagnosticPage from './pages/DiagnosticPage'
import UserProfilePage from './pages/UserProfilePage'
import LoginGateway from './components/LoginGateway'

import StorageValidator from './components/StorageValidator'
import { useAutoSave } from './hooks/useAutoSave'

const routerFutureFlags = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const

function App() {
  console.log('App component rendering...')

  // 启用自动保存功能
  useAutoSave(30000) // 30秒自动保存一次

  // 认证状态
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // 添加错误边界
  try {
    return (
      <StorageValidator>
        {/* 登录门户（阻塞式） */}
        {!isAuthenticated && (
          <LoginGateway onAuthenticated={() => setIsAuthenticated(true)} />
        )}

        {/* 主应用界面 */}
        <div className="min-h-screen bg-gray-50">
          <Router future={routerFutureFlags}>
            <Routes>
              {/* 诊断页面 */}
              <Route path="/diagnostic" element={<DiagnosticPage />} />

              {/* 所有页面都可访问（基于 Cookie 认证） */}
              <Route path="/" element={<Layout><ChatPage /></Layout>} />
              <Route path="/settings" element={<Layout><SettingsPage /></Layout>} />
              <Route path="/profile" element={<Layout><UserProfilePage /></Layout>} />
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
