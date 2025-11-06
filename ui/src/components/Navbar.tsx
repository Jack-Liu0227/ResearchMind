import React, { useState } from 'react'
import { Menu, Settings, Wifi, WifiOff, Bot, Database, BarChart3 } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { Link } from 'react-router-dom'
import BillingIndicator from './BillingIndicator'
import BohriumAuthButton from './BohriumAuthButton'
import BillingStatsPanel from './BillingStatsPanel'

const Navbar: React.FC = () => {
  const {
    sidebarOpen,
    setSidebarOpen,
    connected,
    currentAgent,
    billingData
  } = useAppStore()

  const [showBillingStats, setShowBillingStats] = useState(false)

  return (
    <nav className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
      {/* 左侧控制按钮 */}
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          title="切换侧边栏"
        >
          <Menu className="w-5 h-5" />
        </button>
        
        <div className="h-6 w-px bg-gray-300" />
        
        {/* 当前智能体显示 */}
        <div className="flex items-center space-x-2 px-3 py-1 bg-primary-50 rounded-full">
          <Bot className="w-4 h-4 text-primary-600" />
          <span className="text-sm font-medium text-primary-700">
            {currentAgent?.name || '未选择智能体'}
          </span>
        </div>
      </div>

      {/* 中间标题 */}
      <div className="flex-1 text-center">
        <h1 className="text-lg font-semibold text-gray-900">
          ResearchMind AI 研究助手
        </h1>
      </div>

      {/* 右侧状态和控制 */}
      <div className="flex items-center space-x-2">
        {/* Bohrium OAuth 登录按钮 */}
        <BohriumAuthButton />

        {/* 分隔线 */}
        <div className="h-6 w-px bg-gray-300" />

        {/* 计费指示器 */}
        <BillingIndicator billingData={billingData || undefined} />

        {billingData && <div className="h-6 w-px bg-gray-300" />}

        {/* 计费统计按钮 */}
        <button
          onClick={() => setShowBillingStats(true)}
          className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          title="查看详细计费统计"
        >
          <BarChart3 className="w-5 h-5 text-purple-600" />
        </button>

        <div className="h-6 w-px bg-gray-300" />

        {/* 连接状态 */}
        <div className="flex items-center space-x-1">
          {connected ? (
            <Wifi className="w-4 h-4 text-green-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500" />
          )}
          <span className={`text-xs ${connected ? 'text-green-600' : 'text-red-600'}`}>
            {connected ? '已连接' : '未连接'}
          </span>
        </div>

        <div className="h-6 w-px bg-gray-300" />

        {/* 存储测试按钮 */}
        <Link
          to="/storage-test"
          className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          title="存储测试"
        >
          <Database className="w-5 h-5" />
        </Link>

        {/* 设置按钮 */}
        <Link
          to="/settings"
          className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          title="设置"
        >
          <Settings className="w-5 h-5" />
        </Link>
      </div>

      {/* 计费统计面板 */}
      <BillingStatsPanel
        isOpen={showBillingStats}
        onClose={() => setShowBillingStats(false)}
      />
    </nav>
  )
}

export default Navbar