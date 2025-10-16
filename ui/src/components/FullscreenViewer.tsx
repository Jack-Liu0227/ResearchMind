/**
 * FullscreenViewer - 全屏查看器组件
 * 支持 3D 结构查看器和声子谱图片的全屏显示
 * 功能：
 * 1. 全屏显示 3D 结构或图片
 * 2. 下载按钮（图片/CIF 文件）
 * 3. 左右切换图片
 * 4. ESC 键退出全屏
 */

import React, { useEffect, useState, useCallback } from 'react'
import { CrystalStructure } from '../types'
import { PhononImage } from '../store/useAppStore'
import StructureViewerThreeJS from './StructureViewerThreeJS'
import toast from 'react-hot-toast'

interface FullscreenViewerProps {
  isOpen: boolean
  onClose: () => void
  type: 'structure' | 'image'
  structure?: CrystalStructure | null
  images?: PhononImage[]
  currentImageIndex?: number
}

const FullscreenViewer: React.FC<FullscreenViewerProps> = ({
  isOpen,
  onClose,
  type,
  structure,
  images = [],
  currentImageIndex = 0
}) => {
  const [imageIndex, setImageIndex] = useState(currentImageIndex)

  // 同步外部传入的 currentImageIndex
  useEffect(() => {
    setImageIndex(currentImageIndex)
  }, [currentImageIndex])

  // ESC 键退出全屏
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (type === 'image' && images.length > 1) {
        if (e.key === 'ArrowLeft') {
          handlePrevImage()
        } else if (e.key === 'ArrowRight') {
          handleNextImage()
        }
      }
    }

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, type, images.length, imageIndex])

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

  // 下载 CIF 文件
  const downloadCIF = () => {
    if (!structure) {
      toast.error('无结构数据')
      return
    }

    // 统一使用 cifContent 字段
    const cifData = (structure as any).cifContent

    if (!cifData) {
      toast.error('无 CIF 数据可下载')
      console.error('结构数据:', structure)
      return
    }

    try {
      const blob = new Blob([cifData], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${structure.formula || 'structure'}.cif`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success(`已下载: ${structure.formula || 'structure'}.cif`)
    } catch (error) {
      console.error('下载 CIF 失败:', error)
      toast.error('下载 CIF 失败，请重试')
    }
  }

  // 切换到上一张图片
  const handlePrevImage = useCallback(() => {
    if (images.length === 0) return
    setImageIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1))
  }, [images.length])

  // 切换到下一张图片
  const handleNextImage = useCallback(() => {
    if (images.length === 0) return
    setImageIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1))
  }, [images.length])

  if (!isOpen) return null

  const currentImage = images[imageIndex]

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-95 flex flex-col">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between p-4 bg-black bg-opacity-50">
        {/* 标题 */}
        <div className="text-white">
          {type === 'structure' && structure && (
            <h2 className="text-xl font-semibold">{structure.formula}</h2>
          )}
          {type === 'image' && currentImage && (
            <div>
              <h2 className="text-xl font-semibold">
                {currentImage.filename || currentImage.name || currentImage.type}
              </h2>
              {images.length > 1 && (
                <p className="text-sm text-gray-300 mt-1">
                  {imageIndex + 1} / {images.length}
                </p>
              )}
            </div>
          )}
        </div>

        {/* 按钮组 */}
        <div className="flex items-center space-x-2">
          {/* 下载按钮 */}
          {type === 'structure' && structure && (
            <button
              onClick={downloadCIF}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex items-center space-x-2"
              title="下载 CIF 文件"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>下载 CIF</span>
            </button>
          )}
          {type === 'image' && currentImage && (
            <button
              onClick={() => downloadImage(
                currentImage.url || '',
                currentImage.filename || currentImage.name || `phonon_${imageIndex + 1}.png`
              )}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex items-center space-x-2"
              title="下载图片"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>下载图片</span>
            </button>
          )}

          {/* 关闭按钮 */}
          <button
            onClick={onClose}
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded flex items-center space-x-2"
            title="关闭 (ESC)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span>关闭</span>
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 relative flex items-center justify-center">
        {type === 'structure' && structure && (
          <div className="w-full h-full">
            <StructureViewerThreeJS structure={structure} />
          </div>
        )}

        {type === 'image' && currentImage && (
          <>
            {/* 图片 */}
            <img
              src={currentImage.url}
              alt={currentImage.filename || currentImage.name || currentImage.type}
              className="max-w-full max-h-full object-contain"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                console.error(`图片加载失败: ${currentImage.url}`)
                target.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(`
                  <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="300" fill="#1f2937"/>
                    <text x="200" y="150" font-family="Arial" font-size="14" fill="#9ca3af" text-anchor="middle">图片加载失败</text>
                  </svg>
                `)
              }}
            />

            {/* 左右切换按钮 */}
            {images.length > 1 && (
              <>
                {/* 上一张 */}
                <button
                  onClick={handlePrevImage}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-3 rounded-full"
                  title="上一张 (←)"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>

                {/* 下一张 */}
                <button
                  onClick={handleNextImage}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-3 rounded-full"
                  title="下一张 (→)"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </>
            )}
          </>
        )}
      </div>

      {/* 底部信息栏 */}
      {type === 'image' && currentImage && currentImage.description && (
        <div className="p-4 bg-black bg-opacity-50 text-white text-center">
          <p className="text-sm">{currentImage.description}</p>
        </div>
      )}

      {/* 键盘提示 */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black bg-opacity-50 text-white px-4 py-2 rounded text-sm">
        {type === 'image' && images.length > 1 ? (
          <span>← → 切换图片 | ESC 退出</span>
        ) : (
          <span>ESC 退出</span>
        )}
      </div>
    </div>
  )
}

export default FullscreenViewer

