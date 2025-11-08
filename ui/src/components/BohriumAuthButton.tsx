import React, { useEffect, useState } from 'react'

/**
 * Bohrium 认证状态指示器
 *
 * 显示用户的 Bohrium 认证状态
 */
const BohriumAuthButton: React.FC = () => {
  const [authSource, setAuthSource] = useState<'cookie' | 'manual' | null>(null)

  useEffect(() => {
    checkAuthSource()

    // 每 5 秒检查一次
    const interval = setInterval(checkAuthSource, 5000)
    return () => clearInterval(interval)
  }, [])

  const checkAuthSource = async () => {
    try {
      // 先检查 Cookie
      const cookies = document.cookie.split(';')
      const hasAccessKey = cookies.some(cookie =>
        cookie.trim().startsWith('appAccessKey=')
      )

      if (hasAccessKey) {
        setAuthSource('cookie')
        return
      }

      // 检查是否有手动配置
      const sessionId = localStorage.getItem('researchmind_session_id')
      if (sessionId) {
        const response = await fetch(`/api/billing/config/${sessionId}`)
        if (response.ok) {
          const result = await response.json()
          if (result.has_config) {
            setAuthSource('manual')
            return
          }
        }
      }

      setAuthSource(null)
    } catch (error) {
      console.error('检查认证来源失败:', error)
      setAuthSource(null)
    }
  }

  if (authSource === 'cookie') {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg">
        <svg
          className="w-4 h-4 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className="text-sm font-medium text-green-700">
          Bohrium 账户
        </span>
      </div>
    )
  }

  if (authSource === 'manual') {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg">
        <svg
          className="w-4 h-4 text-blue-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
          />
        </svg>
        <span className="text-sm font-medium text-blue-700">
          手动配置
        </span>
      </div>
    )
  }

  return null
}

export default BohriumAuthButton

