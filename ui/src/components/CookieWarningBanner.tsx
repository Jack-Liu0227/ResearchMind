/**
 * Cookie 警告横幅
 * 
 * 当检测不到 Bohrium Cookie 时显示警告，并提供手动输入 AccessKey 的选项
 */

import React, { useState, useEffect } from 'react'
import { hasBohriumCookie } from '../utils/cookieHelper'
import toast from 'react-hot-toast'

const CookieWarningBanner: React.FC = () => {
  const [showBanner, setShowBanner] = useState(false)
  const [showInputModal, setShowInputModal] = useState(false)
  const [accessKey, setAccessKey] = useState('')
  const [clientName, setClientName] = useState('ResearchMind')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // 检查 Cookie 状态
    const checkCookie = () => {
      const hasCookie = hasBohriumCookie()
      setShowBanner(!hasCookie)
      
      if (!hasCookie) {
        console.warn('⚠️ 未检测到 Bohrium Cookie，计费功能将无法使用')
      }
    }

    checkCookie()
    
    // 每 30 秒检查一次
    const interval = setInterval(checkCookie, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleManualInput = async () => {
    if (!accessKey.trim()) {
      toast.error('请输入 AccessKey')
      return
    }

    setLoading(true)
    try {
      // ✅ 直接设置 Cookie（不调用后端接口）
      const expiryDays = 30
      const expiryDate = new Date()
      expiryDate.setDate(expiryDate.getDate() + expiryDays)

      document.cookie = `appAccessKey=${accessKey.trim()}; expires=${expiryDate.toUTCString()}; path=/`
      document.cookie = `clientName=${clientName.trim()}; expires=${expiryDate.toUTCString()}; path=/`

      toast.success('AccessKey 已保存到 Cookie！')
      setShowInputModal(false)
      setShowBanner(false)

      // 刷新页面以重新建立 WebSocket 连接
      setTimeout(() => window.location.reload(), 1000)
    } catch (error) {
      console.error('保存 AccessKey 失败:', error)
      toast.error('保存失败，请检查浏览器设置')
    } finally {
      setLoading(false)
    }
  }

  if (!showBanner) {
    return null
  }

  return (
    <>
      {/* 警告横幅 */}
      <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-3">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-3">
            <svg
              className="w-5 h-5 text-yellow-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-yellow-800">
                未检测到 Bohrium Cookie
              </p>
              <p className="text-xs text-yellow-700">
                计费功能需要 Bohrium Cookie。请登录 Bohrium 平台或手动输入 AccessKey。
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <a
              href="https://bohrium.dp.tech"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-yellow-800 hover:text-yellow-900 underline"
            >
              登录 Bohrium
            </a>
            <button
              onClick={() => setShowInputModal(true)}
              className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
            >
              手动输入
            </button>
          </div>
        </div>
      </div>

      {/* 手动输入模态框 */}
      {showInputModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              手动输入 Bohrium AccessKey
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AccessKey *
                </label>
                <input
                  type="text"
                  value={accessKey}
                  onChange={(e) => setAccessKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="请输入您的 Bohrium AccessKey"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  客户端名称
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="ResearchMind"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowInputModal(false)}
                className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={handleManualInput}
                disabled={loading}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? '提交中...' : '确定'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default CookieWarningBanner

