import React, { useState, useRef, useEffect } from 'react'
import { X, Download, ZoomIn, ZoomOut, RotateCcw, Info, Maximize, Minimize, ExternalLink, Layout } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { API_CONFIG } from '../constants'
import { resolveFileUrl } from '../utils/apiClient'

interface PhononImage {
  name: string
  path?: string
  url?: string
  filename?: string
  type: 'phonon_dispersion' | 'phonon_dos' | 'phonon' | 'band' | 'dos' | string
  description?: string
  base64?: string
}

interface Props {
  images: PhononImage[]
  onClose: () => void
  className?: string
}

/**
 * 声子谱可视化组件
 * 支持声子色散关系图和声子态密度图的显示
 */
const PhononVisualization: React.FC<Props> = ({ images, onClose, className = '' }) => {
  const { setPhononDisplayMode } = useAppStore()
  
  const [selectedImageIndex, setSelectedImageIndex] = useState(0)
  const [scale, setScale] = useState(1)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [imageLoadError, setImageLoadError] = useState<boolean[]>([])
  const [showInfo, setShowInfo] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  
  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  // 重置图片加载错误状态
  useEffect(() => {
    setImageLoadError(new Array(images.length).fill(false))
    setSelectedImageIndex(0)
    setScale(1)
    setPosition({ x: 0, y: 0 })
  }, [images])

  // 键盘导航
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          if (isFullscreen) {
            setIsFullscreen(false)
          } else {
            onClose()
          }
          break
        case 'ArrowLeft':
          if (selectedImageIndex > 0) {
            setSelectedImageIndex(selectedImageIndex - 1)
            handleReset()
          }
          break
        case 'ArrowRight':
          if (selectedImageIndex < images.length - 1) {
            setSelectedImageIndex(selectedImageIndex + 1)
            handleReset()
          }
          break
        case '0':
        case 'Home':
          handleReset()
          break
        case 'f':
        case 'F':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault()
            setIsFullscreen(!isFullscreen)
          }
          break
        case 'F11':
          e.preventDefault()
          setIsFullscreen(!isFullscreen)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedImageIndex, images.length, onClose, isFullscreen])

  const currentImage = images[selectedImageIndex]

  // 获取图片显示名称
  const getDisplayName = (image: PhononImage): string => {
    if (image.name) {
      return image.name
        .replace(/relaxed_/g, '')
        .replace(/_/g, ' ')
        .replace(/band/gi, '能带')
        .replace(/dos/gi, '态密度')
        .replace(/phonon/gi, '声子')
        .replace(/dispersion/gi, '色散关系')
    }
    return '声子计算结果'
  }

  // 获取图片描述
  const getDescription = (image: PhononImage): string => {
    if (image.description) return image.description
    
    const name = image.name?.toLowerCase() || ''
    const type = image.type?.toLowerCase() || ''
    
    if (name.includes('band') || type.includes('dispersion')) {
      return '声子色散关系图：显示声子频率随波矢的变化，用于分析晶格振动模式和声学性质。'
    } else if (name.includes('dos') || type.includes('dos')) {
      return '声子态密度图：显示不同频率下的声子态密度分布，用于分析热力学性质。'
    }
    return '声子谱计算结果图像'
  }

  // 获取图片URL
  const getImageUrl = (image: PhononImage): string => {
    if (image.base64) return `data:image/png;base64,${image.base64}`

    // 统一使用 resolveFileUrl 处理相对路径
    if (image.url) return resolveFileUrl(image.url)
    if (image.filename) return resolveFileUrl(`/api/images/phonon_results/${image.filename}`)
    if (image.path) return resolveFileUrl(`/api/images/${image.path}`)
    return ''
  }

  // 处理图片加载错误
  const handleImageError = (index: number) => {
    const newErrors = [...imageLoadError]
    newErrors[index] = true
    setImageLoadError(newErrors)
  }

  // 鼠标拖拽处理
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  // 缩放控制
  const handleZoomIn = () => {
    setScale(prev => Math.min(prev * 1.2, 5))
  }

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev / 1.2, 0.1))
  }

  const handleReset = () => {
    setScale(1)
    setPosition({ x: 0, y: 0 })
  }

  // 切换全屏模式
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  // 切换到底部面板模式
  const switchToBottomPanel = () => {
    setPhononDisplayMode('bottom')
    onClose()
  }

  // 在新窗口中打开
  const openInNewWindow = () => {
    const imageUrl = getImageUrl(currentImage)
    if (imageUrl) {
      const newWindow = window.open('', '_blank', 'width=1200,height=800')
      if (newWindow) {
        newWindow.document.write(`
          <!DOCTYPE html>
          <html>
          <head>
            <title>${getDisplayName(currentImage)} - 声子谱</title>
            <style>
              body {
                margin: 0;
                padding: 20px;
                background: #000;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
              }
              img {
                max-width: 100%;
                max-height: 100vh;
                object-fit: contain;
              }
              .info {
                position: absolute;
                top: 20px;
                left: 20px;
                color: white;
                font-family: Arial, sans-serif;
                background: rgba(0,0,0,0.7);
                padding: 10px;
                border-radius: 5px;
              }
            </style>
          </head>
          <body>
            <div class="info">
              <h3>${getDisplayName(currentImage)}</h3>
              <p>声子谱计算结果</p>
            </div>
            <img src="${imageUrl}" alt="${getDisplayName(currentImage)}" />
          </body>
          </html>
        `)
        newWindow.document.close()
      }
    }
  }

  // 下载图片
  const handleDownload = async () => {
    if (!currentImage) return
    
    try {
      const url = getImageUrl(currentImage)
      const response = await fetch(url)
      const blob = await response.blob()
      const downloadUrl = URL.createObjectURL(blob)
      
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `${getDisplayName(currentImage).replace(/\s+/g, '_')}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(downloadUrl)
    } catch (error) {
      console.error('下载失败:', error)
    }
  }

  if (!images.length) return null

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-90 z-50 flex flex-col ${className}`}>
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between p-4 bg-gray-900 text-white">
        <div className="flex items-center space-x-4">
          <h2 className="text-xl font-semibold">声子谱可视化</h2>
          <span className="text-gray-300">
            {selectedImageIndex + 1} / {images.length}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="显示信息"
          >
            <Info className="w-5 h-5" />
          </button>
          
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="缩小"
          >
            <ZoomOut className="w-5 h-5" />
          </button>
          
          <span className="text-sm text-gray-300 min-w-[4rem] text-center">
            {Math.round(scale * 100)}%
          </span>
          
          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="放大"
          >
            <ZoomIn className="w-5 h-5" />
          </button>
          
          <button
            onClick={handleReset}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="重置视图"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title={isFullscreen ? "退出全屏 (Esc)" : "全屏显示 (F11)"}
          >
            {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
          </button>
          
          <button
            onClick={switchToBottomPanel}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="切换到底部面板模式"
          >
            <Layout className="w-5 h-5" />
          </button>
          
          <button
            onClick={openInNewWindow}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="在新窗口中打开"
          >
            <ExternalLink className="w-5 h-5" />
          </button>
          
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="下载图片"
          >
            <Download className="w-5 h-5" />
          </button>
          
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="关闭"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 flex">
        {/* 侧边栏 - 图片列表 */}
        {images.length > 1 && !isFullscreen && (
          <div className="w-80 bg-gray-800 p-4 overflow-y-auto">
            <h3 className="text-white font-medium mb-3">图片列表 ({images.length}张)</h3>
            <div className="space-y-2">
              {images.map((image, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedImageIndex(index)}
                  className={`w-full p-3 rounded text-left transition-colors ${
                    index === selectedImageIndex
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <div className="font-medium text-sm">
                    {getDisplayName(image)}
                  </div>
                  <div className="text-xs opacity-75 mt-1">
                    {image.type || 'phonon'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 主显示区域 */}
        <div className="flex-1 relative overflow-hidden">
          {/* 信息面板 */}
          {showInfo && (
            <div className="absolute top-4 left-4 bg-black bg-opacity-80 text-white p-4 rounded-lg max-w-md z-10">
              <h4 className="font-semibold mb-2">{getDisplayName(currentImage)}</h4>
              <p className="text-sm text-gray-300 mb-2">
                {getDescription(currentImage)}
              </p>
              <div className="text-xs text-gray-400">
                <div>类型: {currentImage.type || 'phonon'}</div>
                {currentImage.filename && (
                  <div>文件: {currentImage.filename}</div>
                )}
              </div>
            </div>
          )}

          {/* 图片显示区域 */}
          <div
            ref={containerRef}
            className="w-full h-full flex items-center justify-center cursor-move"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {currentImage && !imageLoadError[selectedImageIndex] ? (
              <img
                ref={imageRef}
                src={getImageUrl(currentImage)}
                alt={getDisplayName(currentImage)}
                className="max-w-none select-none"
                style={{
                  transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                  transformOrigin: 'center center'
                }}
                onError={() => handleImageError(selectedImageIndex)}
                onLoad={() => {
                  console.log('✅ 声子谱图片加载成功:', getImageUrl(currentImage))
                }}
                draggable={false}
              />
            ) : (
              <div className="text-white text-center">
                <div className="text-6xl mb-4">📊</div>
                <div className="text-xl mb-2">图片加载失败</div>
                <div className="text-gray-400 text-sm">
                  {getImageUrl(currentImage) || '无有效图片URL'}
                </div>
              </div>
            )}
          </div>

          {/* 使用说明 */}
          <div className="absolute bottom-4 right-4 bg-black bg-opacity-60 text-white text-xs p-2 rounded">
            拖拽移动 | 滚轮缩放 | 双击重置
            {isFullscreen && images.length > 1 && (
              <div className="mt-1 text-yellow-300">
                ← → 切换图片 | Esc 退出全屏
              </div>
            )}
          </div>

          {/* 全屏模式下的图片导航 */}
          {isFullscreen && images.length > 1 && (
            <div className="absolute top-1/2 left-4 transform -translate-y-1/2">
              <button
                onClick={() => {
                  if (selectedImageIndex > 0) {
                    setSelectedImageIndex(selectedImageIndex - 1)
                    handleReset()
                  }
                }}
                className={`p-3 bg-black bg-opacity-50 text-white rounded-full transition-all ${
                  selectedImageIndex === 0 
                    ? 'opacity-30 cursor-not-allowed' 
                    : 'hover:bg-opacity-70 cursor-pointer'
                }`}
                disabled={selectedImageIndex === 0}
                title="上一张图片 (←)"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            </div>
          )}

          {isFullscreen && images.length > 1 && (
            <div className="absolute top-1/2 right-4 transform -translate-y-1/2">
              <button
                onClick={() => {
                  if (selectedImageIndex < images.length - 1) {
                    setSelectedImageIndex(selectedImageIndex + 1)
                    handleReset()
                  }
                }}
                className={`p-3 bg-black bg-opacity-50 text-white rounded-full transition-all ${
                  selectedImageIndex === images.length - 1 
                    ? 'opacity-30 cursor-not-allowed' 
                    : 'hover:bg-opacity-70 cursor-pointer'
                }`}
                disabled={selectedImageIndex === images.length - 1}
                title="下一张图片 (→)"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}

          {/* 全屏模式下的图片计数器 */}
          {isFullscreen && images.length > 1 && (
            <div className="absolute bottom-4 left-4 bg-black bg-opacity-60 text-white text-sm p-2 rounded">
              {selectedImageIndex + 1} / {images.length}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PhononVisualization
