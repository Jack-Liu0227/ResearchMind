import React, { useState, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import RightPanel from './RightPanel'
import { ChevronLeft, ChevronRight, X, Database } from 'lucide-react'
import { useMediaQuery } from '../hooks/useMediaQuery'
import DraggableDataButton from './DraggableDataButton'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  console.log('Layout component rendering...')

  const { sidebarOpen, setSidebarOpen, rightPanelOpen, setRightPanelOpen, settings } = useAppStore()

  // 🆕 使用设置中的默认值初始化右侧边栏状态（已移至全局 store）
  // const [rightPanelOpen, setRightPanelOpen] = useState(settings.rightSidebarOpen ?? true)

  // 拖拽调整大小 - 从 localStorage 读取保存的宽度
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebarWidth')
    return saved ? parseInt(saved, 10) : 320
  })
  const [rightPanelWidth, setRightPanelWidth] = useState(() => {
    const saved = localStorage.getItem('rightPanelWidth')
    return saved ? parseInt(saved, 10) : 480
  })
  const [isResizingSidebar, setIsResizingSidebar] = useState(false)
  const [isResizingRightPanel, setIsResizingRightPanel] = useState(false)

  // 📱 Mobile detection
  const isMobile = useMediaQuery('(max-width: 768px)')

  // Close sidebar/panels automatically when switching to mobile to avoid clutter
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false)
      setRightPanelOpen(false)
    }
  }, [isMobile, setSidebarOpen])

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
        // 设置合理的最小宽度（150px）和最大宽度（窗口宽度的 50%）
        const minWidth = 150
        const maxWidth = window.innerWidth * 0.5
        const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth))
        setSidebarWidth(constrainedWidth)
      } else if (isResizingRightPanel) {
        const newWidth = window.innerWidth - e.clientX
        // 设置合理的最小宽度（150px）和最大宽度（窗口宽度的 50%）
        const minWidth = 150
        const maxWidth = window.innerWidth * 0.5
        const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth))
        setRightPanelWidth(constrainedWidth)
      }
    }

    const handleMouseUp = () => {
      // 保存宽度到 localStorage
      if (isResizingSidebar) {
        localStorage.setItem('sidebarWidth', sidebarWidth.toString())
      } else if (isResizingRightPanel) {
        localStorage.setItem('rightPanelWidth', rightPanelWidth.toString())
      }

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
  }, [isResizingSidebar, isResizingRightPanel, sidebarWidth, rightPanelWidth])

  return (
    <div className="fixed inset-0 w-full bg-transparent overflow-hidden">
      {/* 顶部导航栏 - Absolute positioning inside fixed container */}
      <div className="absolute top-0 left-0 right-0 h-14 z-[200]">
        <Navbar />
      </div>

      {/* 主要内容区域 - Absolute positioning to fill remaining space */}
      <div className="absolute inset-0 top-14 w-full flex overflow-hidden">
        {/* 左侧边栏 - 对话历史 */}
        {/* Desktop Sidebar */}
        {!isMobile && sidebarOpen && (
          <div
            className="glass-panel border-r border-white/20 flex-shrink-0 relative overflow-hidden"
            style={{ width: sidebarWidth }}
          >
            <Sidebar />
            {/* 拖拽条 */}
            <div
              className="absolute right-0 top-0 w-1 h-full cursor-col-resize bg-transparent z-20 group flex justify-center hover:bg-primary-400/50 transition-colors"
              onMouseDown={(e) => {
                e.preventDefault()
                setIsResizingSidebar(true)
              }}
              title="拖拽调整宽度"
            />
          </div>
        )}

        {/* Mobile Sidebar (Drawer) */}
        {isMobile && sidebarOpen && (
          <div className="fixed inset-0 z-[110] flex">
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
              onClick={() => setSidebarOpen(false)}
            />

            {/* Drawer Content */}
            <div className="relative w-4/5 max-w-xs glass-panel border-r border-white/20 h-full shadow-2xl flex flex-col animate-slide-in-left">
              <div className="absolute top-2 right-2 z-10">
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 hover:bg-white/50 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
              <Sidebar />
            </div>
          </div>
        )}

        {/* 左侧边栏折叠按钮 (Desktop Only) */}
        {!isMobile && (
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="absolute top-1/2 transform -translate-y-1/2 z-30 glass border border-white/40 rounded-full p-1.5 hover:bg-white transition-all shadow-lg text-primary-600 hover:scale-110"
            style={{ left: sidebarOpen ? `${sidebarWidth - 12}px` : '12px' }}
            title={sidebarOpen ? '隐藏对话历史' : '显示对话历史'}
          >
            {sidebarOpen ? (
              <ChevronLeft className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}

        {/* 中间主要内容区域 */}
        <div className={`flex-1 flex flex-col min-w-0 h-full overflow-hidden relative transition-all ${!isMobile ? 'glass-panel shadow-none' : 'bg-transparent'}`}>
          {children}
        </div>

        {/* 右侧面板 - 结构查看器 */}
        {/* Desktop RightPanel */}
        {!isMobile && rightPanelOpen && (
          <div
            className="glass-panel border-l border-white/20 flex-shrink-0 relative h-full overflow-hidden"
            style={{ width: rightPanelWidth }}
          >
            {/* 拖拽条 */}
            <div
              className="absolute left-0 top-0 w-1 h-full cursor-col-resize bg-transparent z-20 group flex justify-center hover:bg-primary-400/50 transition-colors"
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

        {/* Mobile RightPanel (Drawer) */}
        {isMobile && rightPanelOpen && (
          <div className="fixed inset-0 z-[250] flex justify-end">
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
              onClick={() => setRightPanelOpen(false)}
            />

            {/* Drawer Content */}
            <div className="relative w-4/5 max-w-md glass-panel border-l border-white/20 h-full shadow-2xl flex flex-col animate-slide-in-right">
              <RightPanel
                isVisible={true}
                onToggle={() => setRightPanelOpen(false)}
              />
            </div>
          </div>
        )}

        {/* 右侧面板折叠按钮 (Desktop Only) */}
        {!isMobile && (
          <button
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="absolute top-1/2 transform -translate-y-1/2 z-30 glass border border-white/40 rounded-full p-1.5 hover:bg-white transition-all shadow-lg text-primary-600 hover:scale-110"
            style={{ right: rightPanelOpen ? `${rightPanelWidth - 12}px` : '12px' }}
            title={rightPanelOpen ? '隐藏结构面板' : '显示结构面板'}
          >
            {rightPanelOpen ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* 📱 Mobile Floating Action Button (FAB) for Data Panel */}
      <DraggableDataButton
        visible={isMobile && !rightPanelOpen}
        onClick={() => setRightPanelOpen(true)}
      />
    </div>
  )
}

export default Layout