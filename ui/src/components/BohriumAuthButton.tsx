import React from 'react'

/**
 * Bohrium 认证状态指示器（简化版）
 *
 * 当前使用开发者 AK 进行测试，显示计费来源
 * 未来可扩展为完整的 OAuth 登录功能
 */
const BohriumAuthButton: React.FC = () => {
  // 简化版：显示当前使用开发者 AK
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

