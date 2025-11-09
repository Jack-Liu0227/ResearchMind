/**
 * 登录页面
 * 
 * 支持两种登录方式：
 * 1. Cookie 自动登录（从 Bohrium 网站获取）
 * 2. 手动输入 AccessKey 登录
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const navigate = useNavigate()
  const [loginMethod, setLoginMethod] = useState<'auto' | 'manual'>('auto')
  const [loading, setLoading] = useState(false)
  
  // 手动登录表单
  const [accessKey, setAccessKey] = useState('')
  const [clientName, setClientName] = useState('ResearchMind')
  const [skuId, setSkuId] = useState('10048')

  useEffect(() => {
    // 页面加载时尝试 Cookie 自动登录
    tryAutoLogin()
  }, [])

  const tryAutoLogin = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/auth/login-from-cookie', {
        method: 'POST',
        credentials: 'include'  // 重要：发送 Cookie
      })

      if (response.ok) {
        const result = await response.json()
        
        if (result.success && result.token) {
          // 保存 Token 到 localStorage
          localStorage.setItem('auth_token', result.token)
          localStorage.setItem('user_info', JSON.stringify(result.user))
          
          toast.success('自动登录成功！')
          
          // 跳转到主页
          setTimeout(() => navigate('/'), 1000)
          return
        }
      }

      // Cookie 登录失败，切换到手动登录
      console.log('Cookie 登录失败，请手动输入 AccessKey')
      setLoginMethod('manual')
      
    } catch (error) {
      console.error('自动登录失败:', error)
      setLoginMethod('manual')
    } finally {
      setLoading(false)
    }
  }

  const handleManualLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!accessKey.trim()) {
      toast.error('请输入 AccessKey')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          access_key: accessKey.trim(),
          client_name: clientName.trim(),
          sku_id: skuId.trim()
        })
      })

      const result = await response.json()

      if (result.success && result.token) {
        // 保存 Token 到 localStorage
        localStorage.setItem('auth_token', result.token)
        localStorage.setItem('user_info', JSON.stringify(result.user))
        
        toast.success('登录成功！')
        
        // 跳转到主页
        setTimeout(() => navigate('/'), 1000)
      } else {
        toast.error(result.message || '登录失败')
      }
      
    } catch (error) {
      console.error('登录失败:', error)
      toast.error('登录失败，请检查网络连接')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">ResearchMind</h1>
          <p className="text-gray-600">AI 驱动的科研助手</p>
        </div>

        {/* 自动登录中 */}
        {loginMethod === 'auto' && loading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
            <p className="text-gray-600">正在尝试自动登录...</p>
            <p className="text-sm text-gray-500 mt-2">从 Bohrium Cookie 读取凭证</p>
          </div>
        )}

        {/* 手动登录表单 */}
        {loginMethod === 'manual' && (
          <form onSubmit={handleManualLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bohrium AccessKey *
              </label>
              <input
                type="text"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="请输入您的 Bohrium AccessKey"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                在 <a href="https://bohrium.dp.tech" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">Bohrium 平台</a> 获取
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                客户端名称
              </label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="ResearchMind"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                SKU ID
              </label>
              <input
                type="text"
                value={skuId}
                onChange={(e) => setSkuId(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="10048"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '登录中...' : '登录'}
            </button>

            <div className="text-center">
              <button
                type="button"
                onClick={tryAutoLogin}
                className="text-sm text-indigo-600 hover:underline"
              >
                重新尝试 Cookie 自动登录
              </button>
            </div>
          </form>
        )}

        {/* 帮助信息 */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-medium text-blue-900 mb-2">💡 登录说明</h3>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>• 如果您已登录 Bohrium 网站，系统会自动读取 Cookie 登录</li>
            <li>• 如果自动登录失败，请手动输入 AccessKey</li>
            <li>• AccessKey 可在 Bohrium 平台的个人设置中获取</li>
            <li>• 登录后，您的凭证将安全保存在本地</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
