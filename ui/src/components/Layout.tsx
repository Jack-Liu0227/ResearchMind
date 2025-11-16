import React, { useState, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import RightPanel from './RightPanel'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  console.log('Layout component rendering...')

  const { sidebarOpen, setSidebarOpen, settings } = useAppStore()

  // 🆕 使用设置中的默认值初始化右侧边栏状态
  const [rightPanelOpen, setRightPanelOpen] = useState(settings.rightSidebarOpen ?? true)

  // 拖拽调整大小
  const [sidebarWidth, setSidebarWidth] = useState(320) // 左侧边栏宽度
  const [rightPanelWidth, setRightPanelWidth] = useState(480) // 右侧面板宽度（增加到 480px 以完整显示所有按钮）
  const [isResizingSidebar, setIsResizingSidebar] = useState(false)
  const [isResizingRightPanel, setIsResizingRightPanel] = useState(false)

  // 🆕 当设置变化时，同步更新侧边栏状态
  useEffect(() => {
    setSidebarOpen(settings.leftSidebarOpen ?? true)
  }, [settings.leftSidebarOpen, setSidebarOpen])

  useEffect(() => {
    setRightPanelOpen(settings.rightSidebarOpen ?? true)
  }, [settings.rightSidebarOpen])

  // 拖拽事件处理
  React.useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingSidebar) {
        const newWidth = e.clientX
        setSidebarWidth(Math.max(200, Math.min(600, newWidth)))
      } else if (isResizingRightPanel) {
        const newWidth = window.innerWidth - e.clientX
        setRightPanelWidth(Math.max(200, Math.min(600, newWidth)))
      }
    }

    const handleMouseUp = () => {
      setIsResizingSidebar(false)
      setIsResizingRightPanel(false)
    }

    if (isResizingSidebar || isResizingRightPanel) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingSidebar, isResizingRightPanel])

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部导航栏 */}
      <Navbar />

      {/* 主要内容区域 */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* 左侧边栏 - 对话历史 */}
        {sidebarOpen && (
          <div
            className="border-r border-gray-200 bg-white flex-shrink-0 relative"
            style={{ width: sidebarWidth }}
          >
            <Sidebar />
            {/* 拖拽条 */}
            <div
              className="absolute right-0 top-0 w-1 h-full cursor-col-resize bg-transparent hover:bg-blue-500 transition-colors z-20"
              onMouseDown={(e) => {
                e.preventDefault()
                setIsResizingSidebar(true)
              }}
              title="拖拽调整宽度"
            />
          </div>
        )}

        {/* 左侧边栏折叠按钮 */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="absolute top-1/2 transform -translate-y-1/2 z-10 bg-white border border-gray-200 rounded-r-lg p-1 hover:bg-gray-50 transition-colors shadow-sm"
          style={{ left: sidebarOpen ? `${sidebarWidth}px` : '0' }}
          title={sidebarOpen ? '隐藏对话历史' : '显示对话历史'}
        >
          {sidebarOpen ? (
            <ChevronLeft className="w-4 h-4 text-gray-600" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-600" />
          )}
        </button>

        {/* 中间主要内容区域 */}
        <div className="flex-1 flex flex-col min-w-0 bg-white overflow-y-auto">
          {children}
        </div>

        {/* 右侧面板 - 结构查看器 */}
        {rightPanelOpen && (
          <div
            className="border-l border-gray-200 bg-white flex-shrink-0 relative h-full"
            style={{ width: rightPanelWidth }}
          >
            {/* 拖拽条 */}
            <div
              className="absolute left-0 top-0 w-1 h-full cursor-col-resize bg-transparent hover:bg-blue-500 transition-colors z-20"
              onMouseDown={(e) => {
                e.preventDefault()
                setIsResizingRightPanel(true)
              }}
              title="拖拽调整宽度"
            />
            <RightPanel
              isVisible={true}
              onToggle={() => setRightPanelOpen(false)}
            />
          </div>
        )}

        {/* 右侧面板折叠按钮 */}
        <button
          onClick={() => setRightPanelOpen(!rightPanelOpen)}
          className="absolute top-1/2 transform -translate-y-1/2 z-10 bg-white border border-gray-200 rounded-l-lg p-1 hover:bg-gray-50 transition-colors shadow-sm"
          style={{ right: rightPanelOpen ? `${rightPanelWidth}px` : '0' }}
          title={rightPanelOpen ? '隐藏结构面板' : '显示结构面板'}
        >
          {rightPanelOpen ? (
            <ChevronRight className="w-4 h-4 text-gray-600" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-gray-600" />
          )}
        </button>
      </div>
    </div>
  )
}

export default Layout