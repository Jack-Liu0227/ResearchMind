/**
 * RightPanel - container for structures, phonon images, and session files.
 */

import React, { useMemo, useState, useEffect } from 'react'
import { Download, ExternalLink, Image as ImageIcon, FileText, Table as TableIcon, ChevronDown, ChevronRight, CheckSquare, Square, BarChart3, Calendar, User, BookOpen } from 'lucide-react'
import StructureViewerThreeJS from './StructureViewerThreeJS'
import StructureList from './StructureList'
import FullscreenViewer from './FullscreenViewer'
import { CsvViewer, MarkdownViewer } from './FileViewer'
import { useAppStore, PhononImage } from '../store/useAppStore'
import { CrystalStructure, SessionFile } from '../types'
import toast from 'react-hot-toast'
import { resolveFileUrl } from '../utils/apiClient'
import { downloadFile, copyToClipboard } from '../utils'
import { API_CONFIG } from '../constants'
import { wsService } from '../services/websocket'

interface RightPanelProps {
  className?: string
  isVisible?: boolean
  onToggle?: () => void
}

const sanitizeRelativePath = (value?: string) => {
  if (!value) return undefined
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const withoutPrefix = trimmed.replace(/^([./\\])+/, '')
  return withoutPrefix.replace(/\\/g, '/')
}

const normalizeDownloadPath = (value: string): string => {
  if (/^https?:\/\//i.test(value)) {
    try {
      const u = new URL(value)
      const p = u.pathname || '/'
      if (p.startsWith('/api/')) {
        return value
      }
      let newPath = p
      if (p.startsWith('/download/')) {
        newPath = `/api${p}`
      } else {
        newPath = p.startsWith('/download') ? `/api${p}` : `/api/download${p.startsWith('/') ? '' : '/'}${p}`
      }
      return `${u.origin}${newPath}${u.search}${u.hash}`
    } catch {
      return value
    }
  }

  const withLeadingSlash = value.startsWith('/') ? value : `/${value}`

  if (withLeadingSlash.startsWith('/api/')) {
    return withLeadingSlash
  }

  if (withLeadingSlash.startsWith('/download/')) {
    return `/api${withLeadingSlash}`
  }

  if (withLeadingSlash.startsWith('/api/download/')) {
    return withLeadingSlash
  }

  return `/api/download${withLeadingSlash}`
}

const buildDownloadUrl = (file: SessionFile): string | undefined => {
  console.log('🔗 buildDownloadUrl - input file:', {
    id: file.id,
    type: file.type,
    name: file.name,
    downloadUrl: file.downloadUrl,
    filePath: file.filePath
  })

  const rawDownload = file.downloadUrl?.trim()
  if (rawDownload) {
    const result = resolveFileUrl(normalizeDownloadPath(rawDownload))
    console.log('🔗 buildDownloadUrl - using downloadUrl:', rawDownload, '->', result)
    return result
  }

  const normalized = sanitizeRelativePath(file.filePath)
  if (!normalized) {
    console.warn('⚠️ buildDownloadUrl - no valid path found for file:', file)
    return undefined
  }

  console.log('🔗 buildDownloadUrl - normalized filePath:', normalized)

  if (normalized.startsWith('api/')) {
    const result = resolveFileUrl(normalizeDownloadPath(`/${normalized}`))
    console.log('🔗 buildDownloadUrl - api/ path:', result)
    return result
  }

  if (normalized.startsWith('download/')) {
    const result = resolveFileUrl(normalizeDownloadPath(`/${normalized}`))
    console.log('🔗 buildDownloadUrl - download/ path:', result)
    return result
  }

  const result = resolveFileUrl(normalizeDownloadPath(`/download/${normalized}`))
  console.log('🔗 buildDownloadUrl - default /download/ path:', result)
  return result
}

const extractFileName = (value?: string, fallback = 'data-file') => {
  if (!value) return fallback
  const clean = value.split('?')[0]
  // 🔧 修复：同时支持 Windows (\) 和 Unix (/) 路径分隔符
  const segments = clean.split(/[/\\]/).filter(Boolean)
  return segments.pop() || fallback
}

const getFileDisplayName = (file: SessionFile) => {
  if (file.name && file.name.trim()) {
    const name = file.name.trim()
    // 🔧 修复：如果 name 是完整路径（包含 : 或 \ 或 /），提取文件名
    if (name.includes(':') || name.includes('\\') || name.includes('/')) {
      return extractFileName(name)
    }
    return name
  }
  return extractFileName(file.filePath || file.downloadUrl || undefined)
}

const formatFileType = (type: string) => {
  const lower = type.toLowerCase()
  if (lower.startsWith('csv')) return 'CSV'
  if (lower.startsWith('md')) return 'Markdown'
  if (lower.startsWith('pdf')) return 'PDF'
  if (lower.startsWith('zip')) return 'ZIP'
  if (lower.includes('image') || lower === 'png' || lower === 'jpg') return 'Image'
  return lower.toUpperCase()
}

const getFileIcon = (type: string) => {
  const lower = type.toLowerCase()
  if (lower.startsWith('csv')) return <TableIcon className="w-4 h-4 text-emerald-500" />
  if (lower.startsWith('md')) return <FileText className="w-4 h-4 text-indigo-500" />
  if (lower.startsWith('pdf')) return <FileText className="w-4 h-4 text-red-500" />
  if (lower.startsWith('zip')) return <FileText className="w-4 h-4 text-amber-500" />
  if (lower.startsWith('img') || lower === 'png' || lower === 'jpg' || lower === 'jpeg' || lower.includes('image')) {
    return <ImageIcon className="w-4 h-4 text-blue-500" />
  }
  return <FileText className="w-4 h-4 text-gray-500" />
}

const getImageUrl = (image: PhononImage): string | undefined => {
  if (image.base64) {
    return `data:image/png;base64,${image.base64}`
  }
  if (image.url) {
    return resolveFileUrl(image.url)
  }
  const normalizedPath = sanitizeRelativePath(image.path)
  if (normalizedPath) {
    return resolveFileUrl(`/images/${normalizedPath}`)
  }
  if (image.filename) {
    return resolveFileUrl(`/images/phonon/${image.filename}`)
  }
  return undefined
}

const RightPanel: React.FC<RightPanelProps> = ({
  className = '',
  isVisible = true,
  onToggle
}) => {
  const {
    currentSessionPhononImages,
    currentSessionFiles,
    currentStructure,
    currentSessionStructures,
    currentPapersCsvPath,
    currentPapersSessionId,
    currentPapersCount
  } = useAppStore()

  // 🔧 修复：按时间倒序排列图片（最新的在最前面）
  const sortedPhononImages = useMemo(() => {
    return [...currentSessionPhononImages].sort((a, b) => {
      const timeA = a.timestamp ? (typeof a.timestamp === 'string' ? new Date(a.timestamp).getTime() : a.timestamp) : 0
      const timeB = b.timestamp ? (typeof b.timestamp === 'string' ? new Date(b.timestamp).getTime() : b.timestamp) : 0
      return timeB - timeA  // 倒序：最新的在前
    })
  }, [currentSessionPhononImages])

  const [activeTab, setActiveTab] = useState<'structures' | 'images' | 'files' | 'papers'>('structures')

  const [fullscreenOpen, setFullscreenOpen] = useState(false)
  const [fullscreenType, setFullscreenType] = useState<'structure' | 'image'>('structure')
  const [fullscreenImageIndex, setFullscreenImageIndex] = useState(0)

  const openStructureFullscreen = () => {
    setFullscreenType('structure')
    setFullscreenOpen(true)
  }

  const openImageFullscreen = (index: number) => {
    setFullscreenType('image')
    setFullscreenImageIndex(index)
    setFullscreenOpen(true)
  }

  const dataFiles = useMemo(() => {
    const dedup = new Map<string, SessionFile>()

    const buildKey = (file: SessionFile) => {
      const normalizedPath = sanitizeRelativePath(file.filePath)
      if (normalizedPath) return normalizedPath
      if (file.downloadUrl) return file.downloadUrl.trim()
      if (file.id) return file.id
      return `${file.type || 'file'}:${file.name || 'unknown'}`
    }

    currentSessionFiles.forEach((file) => {
      if (!file) return
      const key = buildKey(file)
      if (!dedup.has(key)) {
        dedup.set(key, file)
      }
    })

    const sorted = Array.from(dedup.values()).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
    // 过滤掉 PDF，仅展示 CSV/MD/其他需要展示的文件
    return sorted.filter((f) => {
      const nameLike = (f.name || f.filePath || f.downloadUrl || '').toLowerCase()
      if (nameLike.endsWith('.pdf')) return false
      const type = (f.type || '').toLowerCase()
      if (type.startsWith('pdf')) return false
      return true
    })
  }, [currentSessionFiles])

  const structureCount = currentSessionStructures.length
  const displayedStructure = currentStructure || currentSessionStructures.slice(-1)[0] || null

  if (!isVisible) {
    return null;
  }

  return (
    <div className={`h-full flex flex-col bg-gray-50 ${className}`}>
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <h2 className="text-lg font-semibold text-gray-800">结构与数据</h2>
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

      <div className="flex border-b border-gray-200 flex-shrink-0">
        <button
          onClick={() => setActiveTab('structures')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'structures'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
          }`}
        >
          结构 ({structureCount})
        </button>
        <button
          onClick={() => setActiveTab('images')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'images'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
          }`}
        >
          图片 ({sortedPhononImages.length})
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'files'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
          }`}
        >
          数据 ({dataFiles.length})
        </button>
        <button
          onClick={() => setActiveTab('papers')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'papers'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
          }`}
        >
          文献 ({currentPapersCount})
        </button>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        {activeTab === 'structures' && (
          <StructuresTab
            structures={currentSessionStructures}
            currentStructure={displayedStructure}
            onFullscreen={openStructureFullscreen}
          />
        )}

        {activeTab === 'images' && (
          <PhononTab
            phononImages={sortedPhononImages}
            onImageFullscreen={openImageFullscreen}
            onDownloadImage={downloadFile}
          />
        )}

        {activeTab === 'files' && (
          <FilesTab files={dataFiles} />
        )}

        {activeTab === 'papers' && (
          <PapersTab />
        )}
      </div>

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

interface StructuresTabProps {
  structures: CrystalStructure[]
  currentStructure: CrystalStructure | null
  onFullscreen: () => void
}

const StructuresTab: React.FC<StructuresTabProps> = ({
  structures,
  currentStructure,
  onFullscreen
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const viewerContainerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (containerRef.current) {
      console.log('📦 StructuresTab container size:', {
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
        offsetHeight: containerRef.current.offsetHeight,
        scrollHeight: containerRef.current.scrollHeight
      });
    }
    if (viewerContainerRef.current) {
      console.log('🎨 Viewer container size:', {
        width: viewerContainerRef.current.clientWidth,
        height: viewerContainerRef.current.clientHeight,
        offsetHeight: viewerContainerRef.current.offsetHeight,
        scrollHeight: viewerContainerRef.current.scrollHeight
      });
    }
  }, [currentStructure]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', padding: '1rem', gap: '0.75rem' }}>
      <div style={{ flexShrink: 0, maxHeight: '40%' }} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-100 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-semibold text-gray-800">结构列表</h3>
            <span className="text-xs text-gray-500">({structures.length} 个)</span>
          </div>
          {structures.length > 0 && (
            <button
              onClick={onFullscreen}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              全屏查看
            </button>
          )}
        </div>
        <StructureList />
      </div>

      <div ref={viewerContainerRef} style={{ flex: 1, minHeight: '300px', display: 'flex', flexDirection: 'column' }} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        {currentStructure ? (
          <div style={{ width: '100%', height: '100%', flex: 1 }}>
            <StructureViewerThreeJS structure={currentStructure} />
          </div>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-center text-gray-500 py-12">
            <ImageIcon className="w-10 h-10 mb-3 text-gray-300" />
            <p className="text-sm font-medium text-gray-700">暂无可视化的结构</p>
            <p className="text-xs text-gray-400 mt-1">选择一个结构后将在此展示 3D 视图</p>
          </div>
        )}
      </div>
    </div>
  )
}

interface PhononTabProps {
  phononImages: PhononImage[]
  onImageFullscreen: (index: number) => void
  onDownloadImage: (data: Blob | string, filename: string, type?: string) => void
}


const PhononTab: React.FC<PhononTabProps> = ({ phononImages, onImageFullscreen, onDownloadImage }) => {
  // 🆕 状态：控制每个图片的原始数据展示
  const [expandedDataIndex, setExpandedDataIndex] = useState<number | null>(null)

  const handleDownload = async (image: PhononImage, fallbackName: string) => {
    try {
      if (image.base64) {
        onDownloadImage(image.base64, fallbackName, 'image/png')
        return
      }

      const url = getImageUrl(image)
      if (!url) {
        toast.error('No downloadable image found')
        return
      }

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('download failed')
      }
      const blob = await response.blob()
      onDownloadImage(blob, fallbackName, blob.type)
    } catch (error) {
      console.error('Failed to download phonon image:', error)
      toast.error('Image download failed, please try again later')
    }
  }

  const toggleDataExpansion = (index: number) => {
    setExpandedDataIndex(expandedDataIndex === index ? null : index)
  }

  if (!phononImages.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
        <ImageIcon className="w-10 h-10 mb-3 text-gray-300" />
        <p>No phonon images yet</p>
        <p className="text-xs text-gray-400 mt-1">Results will appear here after a phonon run</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {phononImages.map((image, index) => {
        const displayUrl = getImageUrl(image)
        const fallbackName = image.filename || image.name || `phonon_${index + 1}.png`
        const hasRawData = image.dispersionCsvPath || image.dosCsvPath
        const isDataExpanded = expandedDataIndex === index

        return (
          <div key={index} className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
            <div className="relative group">
              {displayUrl ? (
                <img
                  src={displayUrl}
                  alt={fallbackName}
                  className="w-full h-auto cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => onImageFullscreen(index)}
                />
              ) : (
                <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
                  Preview unavailable
                </div>
              )}
              <div className="absolute top-2 right-2 flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {/* 🆕 原始数据按钮 - 移到图像右上角，使用文字标识 */}
                {hasRawData && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleDataExpansion(index)
                    }}
                    className={`px-3 py-1.5 rounded transition-colors flex items-center space-x-1 text-sm font-medium ${
                      isDataExpanded
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-black bg-opacity-50 hover:bg-opacity-70 text-white'
                    }`}
                    title={isDataExpanded ? "隐藏原始数据" : "显示原始数据"}
                  >
                    <span>数据</span>
                    {isDataExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDownload(image, fallbackName)
                  }}
                  className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded"
                  title="Download image"
                >
                  <Download className="w-4 h-4" />
                </button>
                {displayUrl && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      window.open(displayUrl, '_blank')
                    }}
                    className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded"
                    title="Open in new tab"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
            <div className="p-3 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{fallbackName}</p>
                  {image.description && (
                    <p className="text-xs text-gray-500 mt-1">{image.description}</p>
                  )}
                </div>
              </div>
            </div>

            {/* 🆕 原始数据展示区域 */}
            {hasRawData && isDataExpanded && (
              <div className="border-t border-gray-200 bg-gray-50 p-3 space-y-3">
                {image.dispersionCsvPath && (
                  <div className="bg-white rounded p-2">
                    <h5 className="text-xs font-medium text-gray-700 mb-2">
                      {/* 显示完整文件名（不带扩展名） */}
                      {image.dispersionCsvPath.split('/').pop()?.replace(/\.csv$/i, '') || 'phonon_dispersion'}
                    </h5>
                    <CsvViewer
                      url={resolveFileUrl(image.dispersionCsvPath)}
                      filename={image.dispersionCsvPath.split('/').pop() || 'phonon_dispersion.csv'}
                      maxHeight="200px"
                      defaultExpanded={true}
                    />
                  </div>
                )}
                {image.dosCsvPath && (
                  <div className="bg-white rounded p-2">
                    <h5 className="text-xs font-medium text-gray-700 mb-2">
                      {/* 显示完整文件名（不带扩展名） */}
                      {image.dosCsvPath.split('/').pop()?.replace(/\.csv$/i, '') || 'phonon_dos'}
                    </h5>
                    <CsvViewer
                      url={resolveFileUrl(image.dosCsvPath)}
                      filename={image.dosCsvPath.split('/').pop() || 'phonon_dos.csv'}
                      maxHeight="200px"
                      defaultExpanded={true}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

interface FilesTabProps {
  files: SessionFile[]
}

const FilesTab: React.FC<FilesTabProps> = ({ files }) => {
  const [previewKey, setPreviewKey] = useState<string | null>(null)

  console.log('📁 FilesTab - rendering with files:', files.length)
  files.forEach((file, index) => {
    console.log(`📁 File ${index}:`, {
      id: file.id,
      type: file.type,
      name: file.name,
      downloadUrl: file.downloadUrl,
      filePath: file.filePath
    })
  })

  if (!files.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
        <FileText className="w-10 h-10 mb-3 text-gray-300" />
        <p>No analysis files yet</p>
        <p className="text-xs text-gray-400 mt-1">Generated CSV/MD/PDF/ZIP files will appear here</p>
      </div>
    )
  }

  const handleCopyLink = async (file: SessionFile) => {
    const url = buildDownloadUrl(file)
    if (!url) {
      toast.error('No downloadable link available')
      return
    }

    const finalUrl = resolveFileUrl(url)
    const success = await copyToClipboard(finalUrl)
    if (success) {
      toast.success('Link copied to clipboard')
    } else {
      const manual = window.prompt('Copy this link', finalUrl)
      if (manual !== null) {
        toast('Press Ctrl+C to copy the link', { icon: 'ℹ️' })
      }
    }
  }

  const handleOpen = (file: SessionFile, key: string) => {
    console.log('👁️ handleOpen - file:', file, 'key:', key)
    const url = buildDownloadUrl(file)
    console.log('👁️ handleOpen - built URL:', url)

    if (!url) {
      console.error('❌ handleOpen - no URL available for file:', file)
      toast.error('No downloadable link available')
      return
    }

    // Inline preview for CSV/MD within panel; otherwise open new tab
    const type = (file.type || '').toLowerCase()
    console.log('👁️ handleOpen - file type:', type)

    if (type.startsWith('csv') || type.startsWith('md') || type === 'csv' || type === 'md') {
      console.log('👁️ handleOpen - opening inline preview for:', type)
      setPreviewKey(key)
      return
    }

    const finalUrl = resolveFileUrl(url)
    console.log('👁️ handleOpen - opening in new tab:', finalUrl)
    window.open(finalUrl, '_blank')
  }

  const handleDownload = (file: SessionFile) => {
    const url = buildDownloadUrl(file)
    if (!url) {
      toast.error('No downloadable link available')
      return
    }
    const anchor = document.createElement('a')
    anchor.href = resolveFileUrl(url)
    anchor.setAttribute('download', getFileDisplayName(file))
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
  }

  return (
    <div className="flex-1 overflow-auto p-4 space-y-3">
      {files.map((file, index) => {
        const url = buildDownloadUrl(file)
        const displayName = getFileDisplayName(file)
        const sourceLabel = file.sourceMessageId ? `#${file.sourceMessageId.slice(-6)}` : 'system'
        const created = file.createdAt ? new Date(file.createdAt) : null
        const key = file.id || url || `${file.type || 'file'}-${displayName}-${index}`

        return (
          <React.Fragment key={key}>
          <div
            className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm hover:border-blue-300 transition-colors"
          >
            <div className="flex items-center space-x-3 min-w-0">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-50">
                {getFileIcon(file.type)}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate" title={displayName}>
                  {displayName}
                </p>
                <div className="flex items-center flex-wrap gap-2 text-xs text-gray-500 mt-1">
                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-blue-700 font-medium">
                    {formatFileType(file.type)}
                  </span>
                  <span>{sourceLabel}</span>
                  {created && <span>{created.toLocaleString()}</span>}
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2 flex-shrink-0">
              <button
                onClick={() => handleDownload(file)}
                className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-500 disabled:opacity-40 whitespace-nowrap"
                disabled={!url}
              >
                <Download className="w-4 h-4 mr-1" />
                Download
              </button>
              <button
                onClick={() => handleCopyLink(file)}
                className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 whitespace-nowrap"
              >
                Copy
              </button>
              <button
                onClick={() => handleOpen(file, key)}
                className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 disabled:opacity-40 whitespace-nowrap"
                disabled={!url}
              >
                <ExternalLink className="w-4 h-4 mr-1" />
                View
              </button>
            </div>
          </div>
          {previewKey === key && url && (
            <div className="mt-2">
              {(() => {
                const fileType = (file.type || '').toLowerCase()
                console.log('📄 Rendering preview for file:', {
                  key,
                  type: fileType,
                  url,
                  displayName
                })

                if (fileType.startsWith('csv') || fileType === 'csv') {
                  console.log('📊 Rendering CsvViewer for:', displayName)
                  return <CsvViewer url={url} filename={displayName} defaultExpanded={true} />
                } else if (fileType.startsWith('md') || fileType === 'md') {
                  console.log('📝 Rendering MarkdownViewer for:', displayName)
                  return <MarkdownViewer url={url} filename={displayName} defaultExpanded={true} />
                } else {
                  console.warn('⚠️ Unknown file type for preview:', fileType)
                  return null
                }
              })()}
            </div>
          )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

/**
 * 文献标签页组件
 */
const PapersTab: React.FC = () => {
  const { currentPapersCsvPath, currentPapersSessionId, currentPapersCount } = useAppStore()
  const [papers, setPapers] = useState<any[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState<'published' | 'score'>('published')
  const [filterSource, setFilterSource] = useState<string>('all')
  const [filterTopic, setFilterTopic] = useState<string>('all')  // 🆕 主题筛选
  const [groupByTopic, setGroupByTopic] = useState<boolean>(true)  // 🆕 是否按主题分组

  const csvFilePath = currentPapersCsvPath
  const sessionId = currentPapersSessionId

  // 🔧 持久化选择状态到 localStorage
  const STORAGE_KEY = `paper_selections_${sessionId}`

  // 🔧 从 localStorage 恢复选择状态
  useEffect(() => {
    if (sessionId) {
      const savedSelections = localStorage.getItem(STORAGE_KEY)
      if (savedSelections) {
        try {
          const parsed = JSON.parse(savedSelections)
          setSelectedIds(parsed)
          console.log('📥 恢复文献选择状态:', parsed.length, '篇')
        } catch (e) {
          console.error('恢复选择状态失败:', e)
        }
      }
    }
  }, [sessionId])

  // 🔧 保存选择状态到 localStorage
  useEffect(() => {
    if (sessionId && selectedIds.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedIds))
      console.log('💾 保存文献选择状态:', selectedIds.length, '篇')
    }
  }, [selectedIds, sessionId])

  // 加载文献列表
  useEffect(() => {
    if (csvFilePath && sessionId) {
      loadPapers()
    }
  }, [csvFilePath, sessionId])

  const loadPapers = async () => {
    if (!csvFilePath || !sessionId) return

    setLoading(true)
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/mcp/call_tool`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          tool_name: 'list_papers_from_csv',
          arguments: {
            csv_file_path: csvFilePath,
            session_id: sessionId,
          }
        })
      })

      const result = await response.json()

      // 🆕 调试：检查 API 响应
      console.log('🔍 API 响应:', {
        status: result.status,
        total_papers: result.total_papers,
        papers_count: result.papers?.length,
        first_paper_keys: result.papers?.[0] ? Object.keys(result.papers[0]) : 'No papers',
        first_paper_topic: result.papers?.[0]?.topic
      })

      if (result.status === 'success') {
        const newPapers = result.papers || []
        setPapers(newPapers)

        // 🆕 保留选择状态：过滤掉不存在的 paper_id
        const newPaperIds = new Set(newPapers.map((p: any) => p.paper_id))
        const validSelectedIds = selectedIds.filter(id => newPaperIds.has(id))
        if (validSelectedIds.length !== selectedIds.length) {
          setSelectedIds(validSelectedIds)
          console.log('📋 更新选择状态:', {
            before: selectedIds.length,
            after: validSelectedIds.length,
            removed: selectedIds.length - validSelectedIds.length
          })
        }

        // 调试：检查第一篇文献是否有 url 和 topic 字段
        if (newPapers.length > 0) {
          console.log('📚 加载文献示例:', {
            title: newPapers[0].title,
            url: newPapers[0].url,
            topic: newPapers[0].topic,
            hasUrl: !!newPapers[0].url,
            hasTopic: !!newPapers[0].topic,
            allFields: Object.keys(newPapers[0])
          })

          // 🆕 调试：检查所有文献的 topic 字段
          const topicsDebug = newPapers.map((p: any) => ({
            paper_id: p.paper_id,
            topic: p.topic,
            topicType: typeof p.topic
          }))
          console.log('🏷️ 所有文献的 topic 字段:', topicsDebug)
        }

        toast.success(`加载了 ${result.total_papers} 篇文献`)
      } else {
        toast.error(`加载失败: ${result.error || '未知错误'}`)
      }
    } catch (error: any) {
      console.error('Failed to load papers:', error)
      toast.error(`加载失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 筛选和排序
  const filteredPapers = papers
    .filter(p => filterSource === 'all' || p.source === filterSource)
    .filter(p => filterTopic === 'all' || (p.topic || '') === filterTopic)  // 🆕 主题筛选
    .sort((a, b) => {
      if (sortBy === 'published') {
        return new Date(b.published).getTime() - new Date(a.published).getTime()
      } else {
        return (b.score || 0) - (a.score || 0)
      }
    })

  // 获取唯一的来源列表
  const sources = Array.from(new Set(papers.map(p => p.source)))

  // 🆕 获取唯一的主题列表
  const topics = Array.from(new Set(papers.map(p => p.topic || '未分类')))
    .sort((a, b) => {
      // 未分类排在最后
      if (a === '未分类') return 1
      if (b === '未分类') return -1
      return a.localeCompare(b)
    })

  // 🆕 按主题分组
  const papersByTopic = filteredPapers.reduce((acc, paper) => {
    const topic = paper.topic || '未分类'
    if (!acc[topic]) {
      acc[topic] = []
    }
    acc[topic].push(paper)
    return acc
  }, {} as Record<string, any[]>)

  // 🆕 批量分析（新流程：直接传递 paper_ids）
  const handleBatchAnalysis = async () => {
    if (!csvFilePath) {
      toast.error('CSV 文件路径不存在')
      return
    }

    if (!sessionId) {
      toast.error('会话 ID 不存在')
      return
    }

    // 如果没有选择文献，询问用户是否使用所有文献
    if (selectedIds.length === 0) {
      const confirmed = window.confirm(
        `您没有选择任何文献，是否使用所有 ${papers.length} 篇文献进行分析？`
      )
      if (!confirmed) {
        return
      }
    }

    // 构造 paper_ids JSON 数组
    const paperIdsJson = JSON.stringify(selectedIds)

    // 通过 WebSocket 发送消息给 Agent 执行批量分析
    const message = selectedIds.length === 0
      ? `请对 CSV 文件中的所有文献进行批量分析，使用 batch_paper_analysis 工具，参数：
csv_file_path="${csvFilePath}"
paper_ids=[]
session_id="${sessionId}"`
      : `请对我选中的 ${selectedIds.length} 篇文献进行批量分析，使用 batch_paper_analysis 工具，参数：
csv_file_path="${csvFilePath}"
paper_ids=${paperIdsJson}
session_id="${sessionId}"`

    wsService.sendMessage(message, 'deep_research_agent', sessionId)
    toast.success(
      selectedIds.length === 0
        ? `已发送批量分析请求（所有 ${papers.length} 篇文献）`
        : `已发送批量分析请求（${selectedIds.length} 篇文献）`
    )
  }

  // 🆕 生成报告（新流程：直接传递 paper_ids）
  const handleGenerateReport = async () => {
    if (!csvFilePath) {
      toast.error('CSV 文件路径不存在')
      return
    }

    if (!sessionId) {
      toast.error('会话 ID 不存在')
      return
    }

    // 如果没有选择文献，询问用户是否使用所有文献
    if (selectedIds.length === 0) {
      const confirmed = window.confirm(
        `您没有选择任何文献，是否使用所有 ${papers.length} 篇文献生成报告？`
      )
      if (!confirmed) {
        return
      }
    }

    // 提示用户输入主题
    const topic = window.prompt('请输入研究主题：', '研究报告')
    if (!topic) return

    // 构造 paper_ids JSON 数组
    const paperIdsJson = JSON.stringify(selectedIds)

    // 通过 WebSocket 发送消息给 Agent 生成报告
    const message = selectedIds.length === 0
      ? `请基于 CSV 文件中的所有文献生成研究报告，主题是"${topic}"，使用 generate_research_report 工具，参数：
topic="${topic}"
csv_file_path="${csvFilePath}"
paper_ids=[]
session_id="${sessionId}"`
      : `请基于我选中的 ${selectedIds.length} 篇文献生成研究报告，主题是"${topic}"，使用 generate_research_report 工具，参数：
topic="${topic}"
csv_file_path="${csvFilePath}"
paper_ids=${paperIdsJson}
session_id="${sessionId}"`

    wsService.sendMessage(message, 'deep_research_agent', sessionId)
    toast.success(
      selectedIds.length === 0
        ? `已发送报告生成请求（主题：${topic}，所有 ${papers.length} 篇文献）`
        : `已发送报告生成请求（主题：${topic}，${selectedIds.length} 篇文献）`
    )
  }

  // 选择/取消选择文献（仅更新本地状态）
  const handleToggleSelect = (paperId: string) => {
    const newSelectedIds = selectedIds.includes(paperId)
      ? selectedIds.filter(id => id !== paperId)
      : [...selectedIds, paperId]

    setSelectedIds(newSelectedIds)
  }

  // 全选/取消全选（仅更新本地状态）
  const handleToggleSelectAll = () => {
    const newSelectedIds = selectedIds.length === filteredPapers.length ? [] : filteredPapers.map(p => p.paper_id)

    setSelectedIds(newSelectedIds)

    // 显示提示
    if (newSelectedIds.length > 0) {
      toast.info(`已选择 ${newSelectedIds.length} 篇文献（点击"确认选择"按钮同步）`)
    } else {
      toast.info('已清空选择')
    }
  }

  if (!csvFilePath || !sessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 p-4">
        <FileText className="w-10 h-10 mb-3 text-gray-300" />
        <p className="text-sm font-medium text-gray-700">暂无文献数据</p>
        <p className="text-xs text-gray-400 mt-1 text-center">
          执行文献检索后，结果将在此展示
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 p-4">
        <FileText className="w-10 h-10 mb-3 text-gray-300" />
        <p className="text-sm font-medium text-gray-700">暂无文献</p>
        <p className="text-xs text-gray-400 mt-1">文献列表为空</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex-shrink-0 px-4 py-3 border-b bg-gray-50 space-y-2">
        {/* 第一行：全选和统计 */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleToggleSelectAll}
            className="flex items-center gap-2 text-xs text-gray-700 hover:text-blue-600 transition-colors"
          >
            {selectedIds.length === filteredPapers.length && filteredPapers.length > 0 ? (
              <CheckSquare className="w-4 h-4" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            <span>全选</span>
          </button>

          <div className="text-xs text-gray-600">
            共 <span className="font-semibold text-gray-800">{papers.length}</span> 篇
            {selectedIds.length > 0 && (
              <span className="ml-2 text-blue-600">
                已选 <span className="font-semibold">{selectedIds.length}</span>
              </span>
            )}
          </div>
        </div>

        {/* 第二行：按来源筛选和排序 */}
        <div className="flex items-center gap-2">
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 flex-1"
          >
            <option value="all">全部来源</option>
            {sources.map(source => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'published' | 'score')}
            className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 flex-1"
          >
            <option value="published">按时间</option>
            <option value="score">按相关性</option>
          </select>
        </div>

        {/* 🆕 第三行：按主题筛选和分组切换（始终显示） */}
        <div className="flex items-center gap-2">
          <select
            value={filterTopic}
            onChange={(e) => setFilterTopic(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 flex-1"
          >
            <option value="all">全部主题 ({papers.length})</option>
            {topics.map(topic => {
              const count = papers.filter(p => (p.topic || '未分类') === topic).length
              return (
                <option key={topic} value={topic === '未分类' ? '' : topic}>
                  {topic} ({count})
                </option>
              )
            })}
          </select>

          {topics.length > 1 && (
            <button
              onClick={() => setGroupByTopic(!groupByTopic)}
              className={`text-xs px-3 py-1 rounded transition-colors ${
                groupByTopic
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {groupByTopic ? '分组显示' : '列表显示'}
            </button>
          )}
        </div>

        {/* 🆕 第四行：批量操作按钮（始终显示，支持未选择时使用所有文献） */}
        <div className="flex gap-2">
          <button
            onClick={handleBatchAnalysis}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            <BarChart3 className="w-3 h-3" />
            {selectedIds.length > 0 ? `批量分析 (${selectedIds.length})` : '分析全部'}
          </button>
          <button
            onClick={handleGenerateReport}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            <FileText className="w-3 h-3" />
            {selectedIds.length > 0 ? `生成报告 (${selectedIds.length})` : '报告全部'}
          </button>
        </div>
      </div>

      {/* 文献列表 */}
      <div className="flex-1 overflow-y-auto p-3">
        {groupByTopic && topics.length > 1 ? (
          // 🆕 分组显示
          <div className="space-y-4">
            {Object.entries(papersByTopic)
              .sort(([topicA], [topicB]) => {
                // 未分类排在最后
                if (topicA === '未分类') return 1
                if (topicB === '未分类') return -1
                return topicA.localeCompare(topicB)
              })
              .map(([topic, topicPapers]) => (
                <div key={topic} className="space-y-2">
                  {/* 主题标题 */}
                  <div className="sticky top-0 bg-gradient-to-r from-blue-50 to-indigo-50 px-3 py-2 rounded-lg border border-blue-200 shadow-sm z-10">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-blue-900">
                        {topic}
                      </h3>
                      <span className="text-xs text-blue-600 bg-white px-2 py-0.5 rounded-full">
                        {topicPapers.length} 篇
                      </span>
                    </div>
                  </div>
                  {/* 该主题下的文献列表 */}
                  <div className="space-y-2 pl-2">
                    {topicPapers.map((paper, index) => (
                      <PaperCardCompact
                        key={paper.paper_id}
                        paper={paper}
                        index={index + 1}
                        selected={selectedIds.includes(paper.paper_id)}
                        onToggleSelect={() => handleToggleSelect(paper.paper_id)}
                      />
                    ))}
                  </div>
                </div>
              ))}
          </div>
        ) : (
          // 列表显示
          <div className="space-y-2">
            {filteredPapers.map((paper, index) => (
              <PaperCardCompact
                key={paper.paper_id}
                paper={paper}
                index={index + 1}
                selected={selectedIds.includes(paper.paper_id)}
                onToggleSelect={() => handleToggleSelect(paper.paper_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 紧凑型文献卡片（适合侧边栏）- 知网风格
 */
interface PaperCardCompactProps {
  paper: any
  index: number
  selected: boolean
  onToggleSelect: () => void
}

const PaperCardCompact: React.FC<PaperCardCompactProps> = ({ paper, index, selected, onToggleSelect }) => {
  const [expanded, setExpanded] = useState(false)
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [detailedInfo, setDetailedInfo] = useState<any>(null)

  // 获取详细信息（通过 MCP API）
  const fetchDetails = async () => {
    if (detailedInfo) return

    // 如果没有 paper_id 或 source，直接使用现有信息
    if (!paper.paper_id && !paper.id) {
      setDetailedInfo({
        fullAbstract: paper.abstract || '暂无摘要',
        authors: paper.authors || [],
        published: paper.published || paper.publication_date || '未知'
      })
      return
    }

    setLoadingDetails(true)
    try {
      const paperId = paper.paper_id || paper.id
      const source = paper.source || 'arxiv'

      console.log('📖 获取文献详细信息:', { paperId, source })

      // 调用 MCP API 获取详细信息
      const response = await fetch(`${API_BASE_URL}/api/mcp/call_tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          server_name: 'paper_search',
          tool_name: 'get_paper_info',
          arguments: {
            paper_id: paperId,
            source: source
          }
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      console.log('✅ 获取详细信息成功:', result)

      if (result.status === 'success' || result.title) {
        setDetailedInfo({
          fullAbstract: result.abstract || paper.abstract || '暂无摘要',
          authors: result.authors || paper.authors || [],
          published: result.published || result.publication_date || paper.published || '未知',
          categories: result.categories || paper.categories || [],
          doi: result.doi || paper.doi,
          citations: result.citations
        })
      } else {
        // 如果 API 返回错误，使用现有信息
        console.warn('⚠️ API 返回错误，使用现有信息:', result.error)
        setDetailedInfo({
          fullAbstract: paper.abstract || '暂无摘要',
          authors: paper.authors || [],
          published: paper.published || paper.publication_date || '未知'
        })
      }
    } catch (error: any) {
      console.error('❌ 获取详细信息失败:', error)
      // 失败时使用现有信息，不显示错误提示
      setDetailedInfo({
        fullAbstract: paper.abstract || '暂无摘要',
        authors: paper.authors || [],
        published: paper.published || paper.publication_date || '未知'
      })
    } finally {
      setLoadingDetails(false)
    }
  }

  return (
    <div
      className={`
        border rounded-lg overflow-hidden transition-all duration-200
        ${selected
          ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-white shadow-md'
          : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm'
        }
      `}
    >
      <div className="p-3">
        <div className="flex items-start gap-2">
          {/* 序号 + 复选框 */}
          <div className="flex-shrink-0 flex items-center gap-1.5">
            <span className="text-[10px] font-medium text-gray-400 w-5 text-right">
              {index}
            </span>
            <button
              onClick={onToggleSelect}
              className="flex-shrink-0 transition-transform hover:scale-110"
            >
              {selected ? (
                <CheckSquare className="w-4 h-4 text-blue-600" />
              ) : (
                <Square className="w-4 h-4 text-gray-400 hover:text-blue-600" />
              )}
            </button>
          </div>

          {/* 内容 */}
          <div className="flex-1 min-w-0">
            {/* 标题 */}
            <div className="flex items-start gap-1 mb-1.5">
              {paper.url ? (
                <a
                  href={paper.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    e.stopPropagation() // 阻止事件冒泡到父元素
                    console.log('📖 打开文献链接:', paper.url)
                  }}
                  className="flex-1 font-semibold text-sm text-gray-900 leading-snug line-clamp-2 hover:text-blue-600 hover:underline cursor-pointer transition-colors"
                  title={`点击打开原文链接: ${paper.url}`}
                >
                  {paper.title}
                </a>
              ) : (
                <h4 className="flex-1 font-semibold text-sm text-gray-900 leading-snug line-clamp-2">
                  {paper.title}
                </h4>
              )}
              {paper.url && (
                <a
                  href={paper.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    e.stopPropagation() // 阻止事件冒泡
                    console.log('🔗 打开文献链接（图标）:', paper.url)
                  }}
                  className="flex-shrink-0 text-gray-400 hover:text-blue-600 transition-colors"
                  title="在新标签页打开"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            {/* 元信息行 */}
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-gray-600 mb-2">
              {/* 作者 */}
              {paper.authors && paper.authors.length > 0 && (
                <div className="flex items-center gap-1">
                  <User className="w-3 h-3 text-gray-400" />
                  <span className="truncate max-w-[120px]">
                    {paper.authors[0]}
                    {paper.authors.length > 1 && ` 等${paper.authors.length}人`}
                  </span>
                </div>
              )}

              {/* 日期 */}
              {paper.published && (
                <div className="flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-gray-400" />
                  <span>{paper.published.split('T')[0]}</span>
                </div>
              )}

              {/* 来源 */}
              <div className="flex items-center gap-1">
                <BookOpen className="w-3 h-3 text-gray-400" />
                <span className="font-medium text-blue-600">{paper.source}</span>
              </div>
            </div>

            {/* 摘要（可展开） */}
            {paper.abstract && (
              <div className="mb-2">
                <p className={`text-[11px] text-gray-600 leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>
                  {paper.abstract}
                </p>
                {paper.abstract.length > 100 && (
                  <button
                    onClick={() => {
                      setExpanded(!expanded)
                      if (!expanded && !detailedInfo) {
                        fetchDetails()
                      }
                    }}
                    className="text-[10px] text-blue-600 hover:text-blue-700 mt-0.5"
                  >
                    {expanded ? '收起' : '展开更多'}
                  </button>
                )}
              </div>
            )}

            {/* 标签和操作 */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 flex-wrap">
                {/* Open Access 标签 */}
                {paper.pdf_url && (
                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-medium rounded">
                    <FileText className="w-2.5 h-2.5" />
                    Open Access
                  </span>
                )}

                {/* 相关性评分 */}
                {paper.score !== null && paper.score !== undefined && (
                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-amber-100 text-amber-700 text-[10px] font-medium rounded">
                    ⭐ {paper.score.toFixed(2)}
                  </span>
                )}

                {/* 引用数（如果有详细信息） */}
                {detailedInfo?.citations !== undefined && (
                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-medium rounded">
                    📊 被引 {detailedInfo.citations}
                  </span>
                )}
              </div>

              {/* PDF 下载按钮 */}
              {paper.pdf_url && (
                <a
                  href={paper.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-blue-600 hover:text-blue-700 font-medium"
                >
                  下载PDF
                </a>
              )}
            </div>

            {/* 展开后的详细信息 */}
            {expanded && detailedInfo && (
              <div className="mt-2 pt-2 border-t border-gray-100 space-y-2">
                {/* 完整作者列表 */}
                {detailedInfo.authors && detailedInfo.authors.length > 1 && (
                  <div className="text-[11px]">
                    <span className="font-medium text-gray-700">作者: </span>
                    <span className="text-gray-600">{detailedInfo.authors.join(', ')}</span>
                  </div>
                )}

                {/* 分类/关键词 */}
                {detailedInfo.categories && detailedInfo.categories.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    <span className="text-[10px] text-gray-500">分类:</span>
                    {detailedInfo.categories.map((category: string, idx: number) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-[10px] rounded"
                      >
                        {category}
                      </span>
                    ))}
                  </div>
                )}

                {/* DOI */}
                {detailedInfo.doi && (
                  <div className="text-[11px]">
                    <span className="font-medium text-gray-700">DOI: </span>
                    <a
                      href={`https://doi.org/${detailedInfo.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {detailedInfo.doi}
                    </a>
                  </div>
                )}

                {/* 完整摘要（如果与原摘要不同） */}
                {detailedInfo.fullAbstract && detailedInfo.fullAbstract !== paper.abstract && (
                  <div className="text-[11px] text-gray-600 leading-relaxed">
                    <span className="font-medium text-gray-700">完整摘要: </span>
                    {detailedInfo.fullAbstract}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 选中状态指示条 */}
      {selected && (
        <div className="h-1 bg-gradient-to-r from-blue-500 to-blue-600"></div>
      )}
    </div>
  )
}

export default RightPanel


