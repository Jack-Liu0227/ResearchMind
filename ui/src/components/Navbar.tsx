import React, { useState } from 'react'
import { Menu, Settings, Wifi, WifiOff, Bot, Database, BarChart3, DollarSign, MoreVertical, X, ChevronRight, ChevronDown, RefreshCw, ArrowLeft } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import BillingIndicator from './BillingIndicator'
import BohriumAuthButton from './BohriumAuthButton'
import BillingStatsPanel from './BillingStatsPanel'

const Navbar: React.FC = () => {
  const {
    sidebarOpen,
    setSidebarOpen,
    setRightPanelOpen,
    connected,
    currentAgent,
    billingData,
    agents,
    setCurrentAgent
  } = useAppStore()

  const location = useLocation()
  const navigate = useNavigate()
  // 判断是否在主页 (chat page is home)
  const isHomePage = location.pathname === '/' || location.pathname === '/chat'

  const [showBillingStats, setShowBillingStats] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isAgentMenuOpen, setIsAgentMenuOpen] = useState(false)

  return (
    <nav className="h-14 bg-white border-b border-gray-200 px-4 transition-all fixed top-0 left-0 right-0 z-[100]">
      <div className="h-full max-w-[1920px] mx-auto flex items-center justify-between">

        {/* 1. 左侧区域：侧边栏开关 + Agent Switcher */}
        <div className="flex items-center gap-4">
          {/* 侧边栏开关 或 返回按钮 */}
          {isHomePage ? (
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/20 rounded-xl transition-all text-gray-700 active:scale-95"
              title="切换侧边栏"
            >
              <Menu className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-white/20 rounded-xl transition-all text-gray-700 active:scale-95 flex items-center gap-1"
              title="返回主界面"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="text-sm font-medium hidden sm:block">返回</span>
            </button>
          )}

          {/* Agent Switcher (Universal) */}
          <div className="relative">
            <button
              onClick={() => setIsAgentMenuOpen(!isAgentMenuOpen)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/40 active:bg-white/60 transition-all border border-transparent hover:border-white/20"
            >
              <div className={`flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-tr ${currentAgent ? 'from-primary-500 to-primary-600' : 'from-gray-500 to-gray-600'} text-white shadow-lg shadow-primary-500/20`}>
                <Bot className="w-5 h-5" />
              </div>
              <div className="flex flex-col items-start text-left">
                <span className="text-[10px] text-gray-500 leading-none mb-0.5 font-medium hidden sm:block">ResearchMind AI</span>
                <span className="text-sm font-bold text-gray-800 flex items-center gap-1 leading-none">
                  {currentAgent?.name || '选择智能体'}
                  <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform duration-300 ${isAgentMenuOpen ? 'rotate-180' : ''}`} />
                </span>
              </div>
            </button>

            {/* Agent Dropdown Menu */}
            {isAgentMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40 bg-transparent"
                  onClick={() => setIsAgentMenuOpen(false)}
                />
                <div className="absolute top-full left-0 mt-2 w-72 bg-white/90 backdrop-blur-xl border border-white/40 rounded-xl shadow-2xl z-50 overflow-hidden animate-slide-up origin-top-left ring-1 ring-black/5">
                  <div className="p-1 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
                      <span>切换智能体</span>
                      {agents.length > 0 && <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded-full text-gray-500">{agents.length}</span>}
                    </div>
                    {agents.map((agent) => (
                      <button
                        key={agent.id}
                        onClick={() => {
                          setCurrentAgent(agent);
                          setIsAgentMenuOpen(false);
                        }}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-all text-left group ${currentAgent?.id === agent.id
                          ? 'bg-primary-50 text-primary-900 shadow-sm ring-1 ring-primary-100'
                          : 'hover:bg-white/60 hover:shadow-sm text-gray-700'
                          }`}
                      >
                        <div className={`p-1.5 rounded-lg transition-colors ${currentAgent?.id === agent.id ? 'bg-primary-100 text-primary-600' : 'bg-gray-100/50 text-gray-500 group-hover:bg-white group-hover:text-primary-500'}`}>
                          <Bot className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate">{agent.name}</div>
                          <div className="text-xs text-gray-400 truncate opacity-0 group-hover:opacity-100 transition-opacity h-4">{agent.description?.slice(0, 20)}...</div>
                        </div>
                        {currentAgent?.id === agent.id && (
                          <div className="ml-auto flex-shrink-0">
                            <span className="block w-2 h-2 rounded-full bg-primary-500 shadow-sm ring-2 ring-white" />
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 3. 右侧区域：操作按钮 */}
        <div className="flex items-center gap-1 sm:gap-2">

          {/* 移动端 & PC 通用：数据面板开关 */}
          <button
            onClick={() => setRightPanelOpen(!useAppStore.getState().rightPanelOpen)}
            className={`p-2 rounded-xl transition-all active:scale-95 flex items-center gap-1.5 ${useAppStore.getState().rightPanelOpen
              ? 'bg-primary-50 text-primary-600 shadow-inner'
              : 'hover:bg-white/20 text-gray-600'
              }`}
            title="数据面板"
          >
            <Database className="w-5 h-5" />
            <span className="hidden lg:inline text-sm font-medium">数据</span>
          </button>

          {/* 分隔线 */}
          <div className="h-5 w-px bg-gray-300/50 hidden md:block mx-1" />

          {/* 移动端：更多菜单 */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 hover:bg-white/20 rounded-xl transition-all text-gray-600 active:scale-95"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
          </div>

          {/* PC端：常规按钮组 */}
          <div className="hidden md:flex items-center space-x-2">
            <BohriumAuthButton />
            <div className="h-6 w-px bg-gray-300" />
            <BillingIndicator />
            {billingData && <div className="h-6 w-px bg-gray-300" />}
            <button
              onClick={() => setShowBillingStats(true)}
              className="p-2 hover:bg-gray-100 rounded-md transition-colors"
              title="查看详细计费统计"
            >
              <BarChart3 className="w-5 h-5 text-purple-600" />
            </button>
            <div className="h-6 w-px bg-gray-300" />
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
            <Link to="/pricing" className="p-2 hover:bg-gray-100 rounded-md transition-colors" title="收费标准">
              <DollarSign className="w-5 h-5 text-green-600" />
            </Link>
            <Link to="/storage-test" className="p-2 hover:bg-gray-100 rounded-md transition-colors" title="存储测试">
              <Database className="w-5 h-5" />
            </Link>
            <Link to="/settings" className="p-2 hover:bg-gray-100 rounded-md transition-colors" title="设置">
              <Settings className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="absolute top-14 left-0 right-0 glass-panel border-b border-white/20 shadow-xl z-50 md:hidden p-4 flex flex-col space-y-4 animate-in slide-in-from-top-5 duration-200">
          <div className="flex justify-between items-center bg-gray-50 p-3 rounded-lg">
            <span className="text-sm font-medium text-gray-700">登录状态</span>
            <BohriumAuthButton />
          </div>

          <div className="flex justify-between items-center bg-gray-50 p-3 rounded-lg">
            <span className="text-sm font-medium text-gray-700">连接状态</span>
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
          </div>

          <div className="bg-gray-50 p-3 rounded-lg space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">计费信息</span>
              <button
                onClick={() => {
                  setShowBillingStats(true)
                  setMobileMenuOpen(false)
                }}
                className="text-xs text-purple-600 font-medium"
              >
                详细统计
              </button>
            </div>
            <BillingIndicator />
          </div>

          {/* 数据面板快捷入口 */}
          <button
            onClick={() => {
              setRightPanelOpen(true)
              setMobileMenuOpen(false)
            }}
            className="w-full p-3 bg-blue-50/50 border border-blue-200 rounded-lg hover:bg-blue-100/50 transition-colors flex items-center justify-between"
          >
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-medium text-blue-700">查看结构与数据</span>
            </div>
            <ChevronRight className="w-4 h-4 text-blue-600" />
          </button>

          <div className="grid grid-cols-3 gap-2">
            <Link
              to="/pricing"
              onClick={() => setMobileMenuOpen(false)}
              className="flex flex-col items-center justify-center p-3 bg-gray-50/50 rounded-lg hover:bg-gray-100/50 border border-gray-100"
            >
              <DollarSign className="w-5 h-5 text-green-600 mb-1" />
              <span className="text-xs text-gray-600">收费标准</span>
            </Link>

            <Link
              to="/storage-test"
              onClick={() => setMobileMenuOpen(false)}
              className="flex flex-col items-center justify-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <Database className="w-5 h-5 text-gray-600 mb-1" />
              <span className="text-xs text-gray-600">存储测试</span>
            </Link>

            <Link
              to="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="flex flex-col items-center justify-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <Settings className="w-5 h-5 text-gray-600 mb-1" />
              <span className="text-xs text-gray-600">设置</span>
            </Link>
          </div>
        </div>
      )}

      {/* 计费统计面板 */}
      <BillingStatsPanel
        isOpen={showBillingStats}
        onClose={() => setShowBillingStats(false)}
      />
    </nav>
  )
}

export default Navbar