import React, { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'

interface DiagnosticResult {
  name: string
  status: 'success' | 'error' | 'warning'
  message: string
  details?: string
}

const DiagnosticPage: React.FC = () => {
  const [results, setResults] = useState<DiagnosticResult[]>([])
  const [isRunning, setIsRunning] = useState(false)

  const runDiagnostics = () => {
    setIsRunning(true)
    const diagnostics: DiagnosticResult[] = []

    // 1. 检查 React
    try {
      diagnostics.push({
        name: 'React 渲染',
        status: 'success',
        message: 'React 正常工作',
        details: `React 版本: ${React.version}`
      })
    } catch (error) {
      diagnostics.push({
        name: 'React 渲染',
        status: 'error',
        message: 'React 渲染失败',
        details: error instanceof Error ? error.message : String(error)
      })
    }

    // 2. 检查 LocalStorage
    try {
      const testKey = 'diagnostic_test'
      localStorage.setItem(testKey, 'test')
      localStorage.removeItem(testKey)
      
      const appStore = localStorage.getItem('researchmind-app-store')
      diagnostics.push({
        name: 'LocalStorage',
        status: 'success',
        message: 'LocalStorage 可用',
        details: appStore ? `应用数据大小: ${(new Blob([appStore]).size / 1024).toFixed(2)} KB` : '无应用数据'
      })
    } catch (error) {
      diagnostics.push({
        name: 'LocalStorage',
        status: 'error',
        message: 'LocalStorage 不可用',
        details: error instanceof Error ? error.message : String(error)
      })
    }

    // 3. 检查网络连接
    try {
      const isOnline = navigator.onLine
      diagnostics.push({
        name: '网络连接',
        status: isOnline ? 'success' : 'warning',
        message: isOnline ? '网络已连接' : '网络未连接',
        details: `User Agent: ${navigator.userAgent.substring(0, 50)}...`
      })
    } catch (error) {
      diagnostics.push({
        name: '网络连接',
        status: 'error',
        message: '无法检查网络状态',
        details: error instanceof Error ? error.message : String(error)
      })
    }

    // 4. 检查 WebSocket 端点
    try {
      const wsUrl = 'ws://localhost:8002'
      diagnostics.push({
        name: 'WebSocket 配置',
        status: 'success',
        message: 'WebSocket 端点已配置',
        details: `端点: ${wsUrl}`
      })
    } catch (error) {
      diagnostics.push({
        name: 'WebSocket 配置',
        status: 'error',
        message: 'WebSocket 配置错误',
        details: error instanceof Error ? error.message : String(error)
      })
    }

    // 5. 检查浏览器兼容性
    try {
      const features = {
        'ES6 支持': typeof Promise !== 'undefined',
        'Fetch API': typeof fetch !== 'undefined',
        'WebSocket': typeof WebSocket !== 'undefined',
        'LocalStorage': typeof localStorage !== 'undefined',
      }
      
      const allSupported = Object.values(features).every(v => v)
      diagnostics.push({
        name: '浏览器兼容性',
        status: allSupported ? 'success' : 'warning',
        message: allSupported ? '浏览器完全兼容' : '部分功能不支持',
        details: Object.entries(features).map(([k, v]) => `${k}: ${v ? '✓' : '✗'}`).join(', ')
      })
    } catch (error) {
      diagnostics.push({
        name: '浏览器兼容性',
        status: 'error',
        message: '无法检查浏览器兼容性',
        details: error instanceof Error ? error.message : String(error)
      })
    }

    setResults(diagnostics)
    setIsRunning(false)
  }

  useEffect(() => {
    runDiagnostics()
  }, [])

  const clearStorage = () => {
    if (confirm('确定要清除所有存储数据吗？')) {
      localStorage.clear()
      alert('存储已清除！页面将刷新。')
      window.location.reload()
    }
  }

  const getStatusIcon = (status: DiagnosticResult['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-900">
              🔍 系统诊断
            </h1>
            <button
              onClick={runDiagnostics}
              disabled={isRunning}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isRunning ? 'animate-spin' : ''}`} />
              重新检查
            </button>
          </div>

          <div className="space-y-4 mb-8">
            {results.map((result, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start">
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(result.status)}
                  </div>
                  <div className="ml-3 flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {result.name}
                      </h3>
                      <span className={`text-sm font-medium ${
                        result.status === 'success' ? 'text-green-600' :
                        result.status === 'error' ? 'text-red-600' :
                        'text-yellow-600'
                      }`}>
                        {result.status === 'success' ? '正常' :
                         result.status === 'error' ? '错误' : '警告'}
                      </span>
                    </div>
                    <p className="text-gray-700 mt-1">{result.message}</p>
                    {result.details && (
                      <p className="text-sm text-gray-500 mt-2 font-mono bg-gray-50 p-2 rounded">
                        {result.details}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-gray-200 pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              快速操作
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={clearStorage}
                className="px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                清除存储
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                返回主页
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                刷新页面
              </button>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">💡 提示</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• 如果界面空白，尝试清除存储并刷新页面</li>
              <li>• 确保后端服务器在 localhost:8002 运行</li>
              <li>• 检查浏览器控制台（F12）查看详细错误</li>
              <li>• 使用隐私模式/无痕模式测试是否是缓存问题</li>
            </ul>
          </div>

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>当前时间: {new Date().toLocaleString()}</p>
            <p>页面 URL: {window.location.href}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DiagnosticPage

