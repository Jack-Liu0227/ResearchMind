import React, { useEffect, useState } from 'react'
import { hasBohriumCookie } from '../utils/cookieHelper'

/**
 * Bohrium 认证状态指示器
 *
 * ✅ 认证优先级：
 * 1. Cookie（实时、最新）- 每次都从 Cookie 读取
 * 2. 提示用户输入 - Cookie 不存在时提示用户登录 Bohrium
 * 3. 数据库（仅用于身份验证和历史记录，不用于计费）
 */
const BohriumAuthButton: React.FC = () => {
  const [authSource, setAuthSource] = useState<'cookie' | 'database' | null>(null)

  useEffect(() => {
    checkAuthSource()

    // 🔧 优化：每 30 秒检查一次（减少 API 请求）
    const interval = setInterval(checkAuthSource, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkAuthSource = async () => {
    try {
      // ✅ 优先检查 Cookie（主要认证来源）
      if (hasBohriumCookie()) {
        setAuthSource('cookie')
        console.log('✅ 检测到 Bohrium Cookie')
        return
      }

      // ⚠️ Cookie 不存在，显示警告（不再检查数据库）
      console.warn('⚠️ 未检测到 Bohrium Cookie，请登录 Bohrium 平台')
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
          Bohrium 已连接
        </span>
      </div>
    )
  }

  // ⚠️ Cookie 不存在，显示警告
  return (
    <div className="flex items-center space-x-2 px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-lg">
      <svg
        className="w-4 h-4 text-yellow-600"
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
      <span className="text-sm font-medium text-yellow-700">
        未检测到 Cookie
      </span>
    </div>
  )
}

export default BohriumAuthButton

