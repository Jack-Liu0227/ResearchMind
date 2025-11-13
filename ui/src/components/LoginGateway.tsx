/**
 * 登录门户组件（阻塞式）
 *
 * ✅ 用户必须输入 AccessKey 才能进入主界面
 * ✅ 如果 Cookie 存在，自动跳过门户
 * ✅ 全屏覆盖，优雅的动画效果
 * ✅ 登录成功后立即触发 WebSocket 重新认证
 */

import { useState, useEffect } from 'react'
import { hasBohriumCookie } from '../utils/cookieHelper'
import { wsService } from '../services/websocket'
import toast from 'react-hot-toast'

interface LoginGatewayProps {
  onAuthenticated: () => void
}

const LoginGateway: React.FC<LoginGatewayProps> = ({ onAuthenticated }) => {
  const [accessKey, setAccessKey] = useState('')
  const [clientName, setClientName] = useState('researchmind-uuid1759932177')
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // 检查 Cookie 是否存在
    const checkCookie = async () => {
      // 延迟 500ms，显示加载动画
      await new Promise(resolve => setTimeout(resolve, 500))
      
      if (hasBohriumCookie()) {
        console.log('✅ 检测到 Cookie，自动跳过登录门户')
        onAuthenticated()
      } else {
        console.log('⚠️ 未检测到 Cookie，显示登录门户')
        setChecking(false)
      }
    }

    checkCookie()
  }, [onAuthenticated])

  const handleLogin = async () => {
    if (!accessKey.trim()) {
      toast.error('请输入 AccessKey')
      return
    }

    setLoading(true)
    try {
      // ✅ 直接设置 Cookie（30 天有效期）
      const expiryDays = 30
      const expiryDate = new Date()
      expiryDate.setDate(expiryDate.getDate() + expiryDays)

      document.cookie = `appAccessKey=${accessKey.trim()}; expires=${expiryDate.toUTCString()}; path=/`
      document.cookie = `clientName=${clientName.trim()}; expires=${expiryDate.toUTCString()}; path=/`

      console.log('✅ Cookie 已设置:', {
        appAccessKey: accessKey.substring(0, 8) + '...',
        clientName: clientName
      })

      toast.success('登录成功！正在连接服务器...')

      // ✅ 立即触发 WebSocket 重新连接并认证
      console.log('🔐 开始连接 WebSocket...')

      try {
        // 如果已连接，先断开
        if (wsService.isConnected) {
          console.log('🔌 断开现有 WebSocket 连接...')
          wsService.disconnect()
          // 等待 100ms 确保断开完成
          await new Promise(resolve => setTimeout(resolve, 100))
        }

        // 重新连接（会自动发送认证消息，包含新的 Cookie 凭证）
        console.log('🔌 正在连接 WebSocket...')
        await wsService.connect()
        console.log('✅ WebSocket 连接成功，已发送认证消息')

        toast.success('已连接到 Bohrium 服务器！')
      } catch (wsError) {
        console.error('❌ WebSocket 连接失败:', wsError)
        toast.error('连接服务器失败，请稍后重试')
      }

      // 延迟 500ms，显示成功动画，然后触发认证
      setTimeout(() => {
        console.log('🔐 触发认证回调')
        onAuthenticated()
      }, 500)
    } catch (error) {
      console.error('保存 AccessKey 失败:', error)
      toast.error('登录失败，请检查浏览器设置')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleLogin()
    }
  }

  // 检查中，显示加载动画
  if (checking) {
    return (
      <div className="fixed inset-0 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center z-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600 text-lg">正在检查认证状态...</p>
        </div>
      </div>
    )
  }

  // 显示登录门户
  return (
    <div className="fixed inset-0 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 animate-slide-up">
        {/* Logo 和标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-full mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">ResearchMind</h1>
          <p className="text-gray-600">请登录以继续使用</p>
        </div>

        {/* 输入表单 */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bohrium AccessKey <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="请输入您的 AccessKey"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              客户端名称（可选）
            </label>
            <input
              type="text"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="researchmind-uuid1759932177"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              disabled={loading}
            />
          </div>
        </div>

        {/* 按钮组 */}
        <div className="mt-6 space-y-3">
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '登录中...' : '登录'}
          </button>

          <a
            href="https://bohrium.dp.tech"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-4 rounded-lg transition-colors"
          >
            访问 Bohrium 平台
          </a>
        </div>

        {/* 提示信息 */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-gray-600">
            💡 <strong>提示：</strong>如果您已在浏览器中登录 Bohrium，Cookie 会自动填充，无需手动输入。
          </p>
        </div>
      </div>
    </div>
  )
}

export default LoginGateway

