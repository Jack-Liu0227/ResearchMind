/**
 * 用户信息页面
 * 
 * 显示用户信息、使用统计、登出功能
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

interface UserInfo {
  id: number
  access_key_masked: string
  client_name: string
  sku_id: string
  total_photons_used: number
  total_tokens_used: number
  created_at: string
  last_login_at: string | null
}

export default function UserProfilePage() {
  const navigate = useNavigate()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUserInfo()
  }, [])

  const fetchUserInfo = async () => {
    setLoading(true)
    try {
      // ✅ 基于 Cookie 认证，不需要 JWT Token
      const response = await fetch('/api/auth/me', {
        credentials: 'include'  // 发送 Cookie
      })

      if (response.ok) {
        const data = await response.json()
        setUserInfo(data)
      } else if (response.status === 401) {
        toast.error('未检测到 Cookie，请登录 Bohrium')
      } else {
        toast.error('获取用户信息失败')
      }
    } catch (error) {
      console.error('获取用户信息失败:', error)
      toast.error('网络错误')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      if (token) {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      }
    } catch (error) {
      console.error('登出失败:', error)
    } finally {
      // 清除本地存储
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
      
      toast.success('已登出')
      navigate('/login')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    )
  }

  if (!userInfo) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* 头部 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">用户信息</h1>
              <p className="text-gray-600">管理您的账户和使用统计</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              返回主页
            </button>
          </div>
        </div>

        {/* 用户信息卡片 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">账户信息</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-3 border-b border-gray-200">
              <span className="text-gray-600">用户 ID</span>
              <span className="font-medium text-gray-900">{userInfo.id}</span>
            </div>
            <div className="flex justify-between items-center py-3 border-b border-gray-200">
              <span className="text-gray-600">AccessKey</span>
              <span className="font-mono text-sm text-gray-900">{userInfo.access_key_masked}</span>
            </div>
            <div className="flex justify-between items-center py-3 border-b border-gray-200">
              <span className="text-gray-600">客户端名称</span>
              <span className="font-medium text-gray-900">{userInfo.client_name}</span>
            </div>
            <div className="flex justify-between items-center py-3 border-b border-gray-200">
              <span className="text-gray-600">SKU ID</span>
              <span className="font-medium text-gray-900">{userInfo.sku_id}</span>
            </div>
            <div className="flex justify-between items-center py-3">
              <span className="text-gray-600">注册时间</span>
              <span className="text-gray-900">{new Date(userInfo.created_at).toLocaleString('zh-CN')}</span>
            </div>
          </div>
        </div>

        {/* 使用统计卡片 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">使用统计</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-blue-600 text-sm font-medium">累计使用光子</span>
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <p className="text-3xl font-bold text-blue-900">{userInfo.total_photons_used.toFixed(2)}</p>
              <p className="text-xs text-blue-600 mt-1">Photons</p>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-green-600 text-sm font-medium">累计使用 Token</span>
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="text-3xl font-bold text-green-900">{userInfo.total_tokens_used.toLocaleString()}</p>
              <p className="text-xs text-green-600 mt-1">Tokens</p>
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">账户操作</h2>
          <div className="space-y-3">
            <button
              onClick={handleLogout}
              className="w-full bg-red-600 text-white py-3 rounded-lg font-medium hover:bg-red-700 transition-colors"
            >
              登出
            </button>
            <p className="text-xs text-gray-500 text-center">
              登出后需要重新输入 AccessKey 才能使用
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
