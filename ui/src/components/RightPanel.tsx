/**
 * RightPanel - 右侧面板容器组件
 * 集成StructureViewer3D和声子谱图像显示，提供响应式布局
 */

import React, { useState, useEffect } from 'react'
import { CrystalStructure } from '../types'
import StructureViewerThreeJS from './StructureViewerThreeJS'
import StructureList from './StructureList'
import { PhononViewer } from './PhononViewer'
import FullscreenViewer from './FullscreenViewer'
import { structureDataManager } from '../services/StructureDataManager'
import { useAppStore, PhononImage } from '../store/useAppStore'
import { getPhononExamples } from '../utils/apiClient'
import toast from 'react-hot-toast'

interface RightPanelProps {
  className?: string
  isVisible?: boolean
  onToggle?: () => void
}

interface StructureListItem {
  id: string
  formula: string
  source: string
  timestamp: string
  atomCount: number
}

const RightPanel: React.FC<RightPanelProps> = ({
  className = '',
  isVisible = true,
  onToggle
}) => {
  // 从 store 获取当前会话的声子谱图片和结构数据
  const { currentSessionPhononImages, currentStructure } = useAppStore()

  const [selectedStructure, setSelectedStructure] = useState<CrystalStructure | null>(null)
  const [structureList, setStructureList] = useState<StructureListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'structures' | 'phonon'>('structures')

  // 全屏查看器状态
  const [fullscreenOpen, setFullscreenOpen] = useState(false)
  const [fullscreenType, setFullscreenType] = useState<'structure' | 'image'>('structure')
  const [fullscreenImageIndex, setFullscreenImageIndex] = useState(0)

  // 加载结构数据和声子谱结果
  // useEffect(() => {
  //   // loadStructures()  // 暂时禁用,数据通过WebSocket传递
  //   // loadPhononResults()  // 不再需要加载示例图片，使用 currentSessionPhononImages
  // }, [])

  const loadStructures = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await structureDataManager.fetchLatestStructures()

      if (response.success) {
        const listItems: StructureListItem[] = response.structures.map(structure => ({
          id: structure.id,
          formula: structure.formula,
          source: typeof structure.source === 'object' && structure.source?.database
            ? structure.source.database
            : (typeof structure.source === 'string' ? structure.source : 'Unknown'),
          timestamp: structure.metadata?.timestamp ? new Date(structure.metadata.timestamp).toLocaleString() : 'Unknown',
          atomCount: structure.atoms.length
        }))

        setStructureList(listItems)

        // 自动选择第一个结构
        if (response.structures.length > 0 && !selectedStructure) {
          setSelectedStructure(response.structures[0])
        }
      } else {
        // 静默处理错误,不影响示例数据显示
        console.warn('加载结构数据失败:', response.error)
      }
    } catch (err) {
      // 静默处理错误,不影响示例数据显示
      console.warn('加载结构数据异常:', err)
    } finally {
      setLoading(false)
    }
  }

  // 不再需要加载示例图片，使用 currentSessionPhononImages
  // const loadPhononResults = async () => {
  //   ...
  // }

  const handleStructureSelect = async (structureId: string) => {
    const response = await structureDataManager.fetchLatestStructures()
    
    if (response.success) {
      const structure = response.structures.find(s => s.id === structureId)
      if (structure) {
        setSelectedStructure(structure)
      }
    }
  }

  const handleRefresh = () => {
    loadStructures()
    // loadPhononResults() // 移除未定义的函数调用
  }

  // 下载图片
  const downloadImage = async (url: string, filename: string) => {
    try {
      const response = await fetch(url)
      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(blobUrl)
      toast.success(`已下载: ${filename}`)
    } catch (error) {
      console.error('下载失败:', error)
      toast.error('下载失败，请重试')
    }
  }

  // 打开全屏查看器 - 结构
  const openStructureFullscreen = () => {
    setFullscreenType('structure')
    setFullscreenOpen(true)
  }

  // 打开全屏查看器 - 图片
  const openImageFullscreen = (index: number) => {
    setFullscreenType('image')
    setFullscreenImageIndex(index)
    setFullscreenOpen(true)
  }



  return (
    <div
      className={`h-full flex flex-col ${className}`}
    >
      {/* 面板头部 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <h2 className="text-lg font-semibold text-gray-800">结构查看器</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            className="p-1 hover:bg-gray-200 rounded transition-colors"
            title="刷新数据"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          {onToggle && (
            <button
              onClick={onToggle}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title="隐藏面板"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* 标签页 */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('structures')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'structures'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
          }`}
        >
          结构列表 ({structureList.length})
        </button>
        <button
          onClick={() => setActiveTab('phonon')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'phonon'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
          }`}
        >
          声子谱 ({currentSessionPhononImages.length})
        </button>
      </div>

      {/* 面板内容 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'structures' && (
          <StructuresTab
            structureList={structureList}
            selectedStructure={selectedStructure}
            onStructureSelect={handleStructureSelect}
            loading={loading}
            error={error}
            onFullscreen={openStructureFullscreen}
          />
        )}

        {activeTab === 'phonon' && (
          <PhononTab
            phononImages={currentSessionPhononImages}
            loading={loading}
            error={error}
            onImageFullscreen={openImageFullscreen}
            onDownloadImage={downloadImage}
          />
        )}
      </div>

      {/* 全屏查看器 */}
      <FullscreenViewer
        isOpen={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        type={fullscreenType}
        structure={fullscreenType === 'structure' ? currentStructure : null}
        images={fullscreenType === 'image' ? currentSessionPhononImages : []}
        currentImageIndex={fullscreenImageIndex}
      />
    </div>
  )
}

// 结构列表标签页
interface StructuresTabProps {
  structureList: StructureListItem[]
  selectedStructure: CrystalStructure | null
  onStructureSelect: (id: string) => void
  loading: boolean
  error: string | null
  onFullscreen: () => void
}

const StructuresTab: React.FC<StructuresTabProps> = ({
  structureList,
  selectedStructure,
  onStructureSelect,
  loading,
  error,
  onFullscreen
}) => {
  // 从store获取结构数据
  const { currentStructure, currentSessionStructures } = useAppStore()

  // 上下拖拽调整
  const [listHeight, setListHeight] = useState(30) // 百分比
  const [isResizing, setIsResizing] = useState(false)

  // 拖拽事件处理
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return

      const container = document.getElementById('structures-tab-container')
      if (!container) return

      const rect = container.getBoundingClientRect()
      const newHeight = ((e.clientY - rect.top) / rect.height) * 100
      setListHeight(Math.max(15, Math.min(70, newHeight)))
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'row-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing])

  console.log('🏗️ StructuresTab - currentStructure:', currentStructure)
  console.log('🏗️ StructuresTab - currentSessionStructures:', currentSessionStructures.length)

  // 如果没有结构数据，显示占位符
  if (!currentStructure) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <p className="text-lg font-medium">暂无结构数据</p>
          <p className="text-sm mt-2">请上传 CIF 文件或使用 Database Agent 查询结构</p>
        </div>
      </div>
    )
  }

  // 使用完整的3D查看器组件
  return (
    <div
      id="structures-tab-container"
      className="flex-1 flex flex-col overflow-hidden bg-white"
    >
      {/* 上半部分 - 结构列表 */}
      <div
        className="overflow-auto flex-shrink-0 bg-white"
        style={{ height: `${listHeight}%` }}
      >
        <StructureList />
      </div>

      {/* 拖拽条 - 美化设计 */}
      <div
        className="h-2 bg-gradient-to-b from-gray-100 to-gray-200 hover:from-blue-400 hover:to-blue-600 cursor-row-resize transition-all duration-200 flex-shrink-0 relative group"
        onMouseDown={(e) => {
          e.preventDefault()
          setIsResizing(true)
        }}
        title="拖拽调整大小"
      >
        {/* 拖拽指示器 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex space-x-1">
            <div className="w-8 h-0.5 bg-gray-400 group-hover:bg-white rounded transition-colors"></div>
          </div>
        </div>
      </div>

      {/* 下半部分 - 3D 查看器 */}
      <div className="flex-1 overflow-hidden relative group bg-gray-900">
        <StructureViewerThreeJS structure={currentStructure} />
        {/* 全屏按钮 */}
        <button
          onClick={onFullscreen}
          className="absolute top-2 right-2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded opacity-0 group-hover:opacity-100 transition-opacity"
          title="全屏查看"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      </div>
    </div>
  )
}

// 声子谱标签页
interface PhononTabProps {
  phononImages: any[]
  loading: boolean
  error: string | null
  onImageFullscreen: (index: number) => void
  onDownloadImage: (url: string, filename: string) => void
}

const PhononTab: React.FC<PhononTabProps> = ({
  phononImages: propsPhononImages,
  loading,
  error,
  onImageFullscreen,
  onDownloadImage
}) => {
  // 从store中获取声子谱数据
  const { phononImages: storePhononImages } = useAppStore()

  // 示例声子谱图片(用于演示)
  const examplePhononImages: PhononImage[] = [
    {
      name: "示例: 声子色散关系",
      type: "phonon_dispersion",
      url: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`
        <svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
          <rect width="600" height="400" fill="#f3f4f6"/>
          <text x="300" y="180" font-family="Arial, sans-serif" font-size="24" fill="#6b7280" text-anchor="middle">示例声子色散关系图</text>
          <text x="300" y="220" font-family="Arial, sans-serif" font-size="14" fill="#9ca3af" text-anchor="middle">请使用Simulation Agent计算声子谱</text>
        </svg>
      `),
      description: "使用Simulation Agent计算声子谱后,图片将显示在这里"
    },
    {
      name: "示例: 声子态密度",
      type: "phonon_dos",
      url: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`
        <svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
          <rect width="600" height="400" fill="#eff6ff"/>
          <text x="300" y="180" font-family="Arial, sans-serif" font-size="24" fill="#3b82f6" text-anchor="middle">示例声子态密度图</text>
          <text x="300" y="220" font-family="Arial, sans-serif" font-size="14" fill="#60a5fa" text-anchor="middle">计算结束后将显示到这里</text>
        </svg>
      `),
      description: "声子态密度图将在计算完成后显示"
    }
  ]

  // 只使用当前会话的声子谱图片（propsPhononImages 就是 currentSessionPhononImages）
  const phononImages = propsPhononImages
  console.log('🎵 PhononTab - 当前会话声子谱图片数:', phononImages.length)
  // 在新标签页中打开图片
  const openImageInNewTab = (imageUrl: string, imageName: string) => {
    const newWindow = window.open('', '_blank')
    if (newWindow) {
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>${imageName}</title>
            <style>
              body {
                margin: 0;
                padding: 20px;
                background: #1a1a1a;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                font-family: Arial, sans-serif;
              }
              img {
                max-width: 95%;
                max-height: 90vh;
                object-fit: contain;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
              }
              .title {
                color: white;
                margin-bottom: 20px;
                font-size: 18px;
                text-align: center;
              }
              .controls {
                margin-top: 20px;
                display: flex;
                gap: 10px;
              }
              button {
                padding: 8px 16px;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
              }
              button:hover {
                background: #2563eb;
              }
            </style>
          </head>
          <body>
            <div class="title">${imageName}</div>
            <img src="${imageUrl}" alt="${imageName}" />
            <div class="controls">
              <button onclick="window.print()">打印</button>
              <button onclick="window.close()">关闭</button>
            </div>
          </body>
        </html>
      `)
      newWindow.document.close()
    }
  }

  // 只显示当前会话的声子谱图片，不显示示例数据
  const displayImages = phononImages

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
      {loading && (
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">加载中...</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border-l-4 border-red-400 mb-4">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* 图片列表 */}
      <div className="space-y-4">
        {displayImages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
            <p>暂无声子谱数据</p>
            <p className="text-xs mt-1">请使用Simulation Agent计算声子谱</p>
          </div>
        ) : (
          displayImages.map((image: any, index: number) => (
            <div key={index} className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
              <div className="relative group">
                <img
                  src={image.url}
                  alt={image.name || image.type || `声子谱图像 ${index + 1}`}
                  className="w-full h-auto cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => onImageFullscreen(index)}
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    console.error(`图片加载失败: ${image.url}`)
                    target.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(`
                      <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
                        <rect width="400" height="300" fill="#f3f4f6"/>
                        <text x="200" y="150" font-family="Arial" font-size="14" fill="#9ca3af" text-anchor="middle">图片加载失败</text>
                      </svg>
                    `)
                    target.alt = '图片加载失败'
                  }}
                />
                {/* 按钮组 */}
                <div className="absolute top-2 right-2 flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {/* 下载按钮 */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDownloadImage(
                        image.url,
                        image.filename || image.name || `phonon_${index + 1}.png`
                      )
                    }}
                    className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded"
                    title="下载图片"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </button>
                  {/* 全屏按钮 */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onImageFullscreen(index)
                    }}
                    className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded"
                    title="全屏查看"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="p-3 bg-gray-50">
                <p className="text-sm font-medium text-gray-900">
                  {image.filename || image.name || image.type || `声子谱图像 ${index + 1}`}
                </p>
                {image.description && (
                  <p className="text-xs text-gray-500 mt-1">
                    {image.description}
                  </p>
                )}
                {image.timestamp && (
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(image.timestamp).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default RightPanel