import React, { useEffect, useState } from 'react'

/**
 * Bohrium 认证状态指示器
 *
 * 根据 Cookie 中的 appAccessKey 判断是否为用户账户
 * - 有 Cookie: 显示"用户账户"
 * - 无 Cookie: 显示"开发者账户 (测试中)"
 */
const BohriumAuthButton: React.FC = () => {
  const [hasUserCredentials, setHasUserCredentials] = useState(false)

  useEffect(() => {
    // 检查 Cookie 中是否有用户的 appAccessKey
    const checkUserCredentials = () => {
      const cookies = document.cookie.split(';')
      const hasAccessKey = cookies.some(cookie =>
        cookie.trim().startsWith('appAccessKey=')
      )
      setHasUserCredentials(hasAccessKey)
    }

    checkUserCredentials()

    // 每 5 秒检查一次（防止用户手动设置 Cookie）
    const interval = setInterval(checkUserCredentials, 5000)
    return () => clearInterval(interval)
  }, [])

  if (hasUserCredentials) {
    // 用户已登录：显示用户账户
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
          用户账户
        </span>
      </div>
    )
  }

  // 开发模式：显示开发者账户
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
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
      <span className="text-sm font-medium text-blue-700">
        开发者账户
      </span>
      <span className="text-xs text-blue-500">
        (测试中)
      </span>
    </div>
  )
}

export default BohriumAuthButton

