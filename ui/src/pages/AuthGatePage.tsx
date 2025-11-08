import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Key, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { APP_CONFIG } from '../constants'

type AuthStatus = 'checking' | 'auto_success' | 'need_manual' | 'manual_input' | 'saving' | 'success'

const AuthGatePage: React.FC = () => {
  const navigate = useNavigate()
  const [authStatus, setAuthStatus] = useState<AuthStatus>('checking')
  const [accessKey, setAccessKey] = useState('')
  const [skuId, setSkuId] = useState('10048')
  const [clientName, setClientName] = useState('ResearchMind')
  const [error, setError] = useState('')

  // 组件加载时尝试自动获取 Cookie 中的 AK
  useEffect(() => {
    checkAutoAuth()
  }, [])

  const checkAutoAuth = async () => {
    setAuthStatus('checking')
    try {
      // 获取 session_id
      const sessionId = localStorage.getItem('researchmind_session_id') || `session_${Date.now()}`
      localStorage.setItem('researchmind_session_id', sessionId)

      // 尝试从 Cookie 自动获取配置
      const response = await fetch(
        `/api/billing/config/save-from-cookie?user_id=${sessionId}`,
        {
          method: 'POST',
          credentials: 'include'
        }
      )

      if (response.ok) {
        const result = await response.json()
        
        if (result.has_config && result.config?.access_key) {
          // 自动获取成功
          console.log('✅ 自动从 Cookie 获取到 Bohrium 凭证')
          setAuthStatus('auto_success')
          
          // 2秒后跳转到主页面
          setTimeout(() => {
            navigate('/')
          }, 2000)
          return
        }
      }

      // 自动获取失败，需要手动输入
      console.log('ℹ️ Cookie 中未找到 Bohrium 凭证，需要手动输入')
      setAuthStatus('need_manual')
      
    } catch (error) {
      console.error('❌ 检查认证失败:', error)
      setAuthStatus('need_manual')
    }
  }

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!accessKey.trim()) {
      setError('请输入 Access Key')
      return
    }

    setAuthStatus('saving')
    setError('')

    try {
      const sessionId = localStorage.getItem('researchmind_session_id') || `session_${Date.now()}`
      
      const response = await fetch('/api/billing/config/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: sessionId,
          access_key: accessKey.trim(),
          sku_id: skuId.trim(),
          client_name: clientName.trim()
        })
      })

      if (response.ok) {
        const result = await response.json()
        
        if (result.success) {
          setAuthStatus('success')
          toast.success('凭证保存成功！')
          
          // 1秒后跳转到主页面
          setTimeout(() => {
            navigate('/')
          }, 1000)
        } else {
          setError(result.message || '保存失败')
          setAuthStatus('manual_input')
        }
      } else {
        setError('保存失败，请检查网络连接')
        setAuthStatus('manual_input')
      }
    } catch (error) {
      console.error('保存凭证失败:', error)
      setError('保存失败，请重试')
      setAuthStatus('manual_input')
    }
  }

  const showManualInput = () => {
    setAuthStatus('manual_input')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        {/* Logo 和标题 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{APP_CONFIG.NAME}</h1>
          <p className="text-gray-600">AI 驱动的科研助手</p>
        </div>

        {/* 检查中 */}
        {authStatus === 'checking' && (
          <div className="text-center py-8">
            <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">正在检查 Bohrium 认证...</p>
            <p className="text-sm text-gray-400 mt-2">尝试从 Cookie 自动获取凭证</p>
          </div>
        )}

        {/* 自动认证成功 */}
        {authStatus === 'auto_success' && (
          <div className="text-center py-8">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-gray-900 mb-2">认证成功！</p>
            <p className="text-gray-600">已自动获取您的 Bohrium 凭证</p>
            <p className="text-sm text-gray-400 mt-2">正在跳转到主页面...</p>
          </div>
        )}

        {/* 需要手动输入提示 */}
        {authStatus === 'need_manual' && (
          <div className="text-center py-6">
            <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-gray-900 mb-2">未检测到 Bohrium 凭证</p>
            <p className="text-gray-600 mb-4">请手动输入您的 Access Key</p>
            <button
              onClick={showManualInput}
              className="btn btn-primary"
            >
              <Key className="w-4 h-4 mr-2" />
              手动输入凭证
            </button>
          </div>
        )}

        {/* 手动输入表单 */}
        {(authStatus === 'manual_input' || authStatus === 'saving') && (
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Access Key <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                placeholder="请输入您的 Bohrium Access Key"
                className="input w-full"
                disabled={authStatus === 'saving'}
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                从 Bohrium 平台获取您的 Access Key
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                SKU ID
              </label>
              <input
                type="text"
                value={skuId}
                onChange={(e) => setSkuId(e.target.value)}
                placeholder="10048"
                className="input w-full"
                disabled={authStatus === 'saving'}
              />
              <p className="text-xs text-gray-500 mt-1">
                默认值：10048
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Client Name
              </label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="ResearchMind"
                className="input w-full"
                disabled={authStatus === 'saving'}
              />
              <p className="text-xs text-gray-500 mt-1">
                默认值：ResearchMind
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={authStatus === 'saving'}
              className="btn btn-primary w-full"
            >
              {authStatus === 'saving' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Key className="w-4 h-4 mr-2" />
                  保存并继续
                </>
              )}
            </button>
          </form>
        )}

        {/* 保存成功 */}
        {authStatus === 'success' && (
          <div className="text-center py-8">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-gray-900 mb-2">保存成功！</p>
            <p className="text-gray-600">正在跳转到主页面...</p>
          </div>
        )}

        {/* 帮助信息 */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            如何获取 Access Key？
            <a
              href="https://bohrium.dp.tech"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-600 ml-1"
            >
              访问 Bohrium 平台
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AuthGatePage

