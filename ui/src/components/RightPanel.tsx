/**
 * RightPanel - container for structures, phonon images, and session files.
 */

import React, { useMemo, useState, useEffect } from 'react'
import { Download, ExternalLink, Image as ImageIcon, FileText, Table as TableIcon, ChevronDown, ChevronRight, CheckSquare, Square, BarChart3, Calendar, User, BookOpen, Award, RefreshCw, AlertCircle } from 'lucide-react'
import StructureViewerThreeJS from './StructureViewerThreeJS'
import StructureList from './StructureList'
import FullscreenViewer from './FullscreenViewer'
import { CsvViewer, MarkdownViewer } from './FileViewer'
import { useAppStore, PhononImage } from '../store/useAppStore'
import { CrystalStructure, SessionFile } from '../types'
import toast from 'react-hot-toast'
import { resolveFileUrl } from '../utils/apiClient'
import { downloadFile, copyToClipboard } from '../utils'
import { getJournalInfo, JournalInfo } from '../services/easyScholarService'
import { API_CONFIG } from '../constants'
import { wsService } from '../services/websocket'
import BatchAnalysisPanel from './BatchAnalysisPanel'

interface RightPanelProps {
  className?: string
  isVisible?: boolean
  onToggle?: () => void
}

const sanitizeRelativePath = (value?: string) => {
  if (!value) return undefined
  const trimmed = value.trim()
  if (!trimmed) return undefined

  // 规范化路径分隔符
  let normalized = trimmed.replace(/\\/g, '/')

  // 🔧 处理绝对路径：提取 session_data/ 后面的部分
  if (normalized.includes('session_data/')) {
    const parts = normalized.split('session_data/')
    if (parts.length > 1 && parts[1]) {
      normalized = parts[1]
      console.log('🔧 sanitizeRelativePath - extracted from session_data/:', normalized)
    }
  }
  // 处理 Windows 绝对路径（如 D:/...）
  else if (/^[A-Za-z]:\//.test(normalized)) {
    // 尝试提取 papers/ 或其他已知目录后面的部分
    if (normalized.includes('/papers/')) {
      const parts = normalized.split('/papers/')
      if (parts.length > 1 && parts[1]) {
        normalized = 'papers/' + parts[1]
        console.log('🔧 sanitizeRelativePath - extracted from /papers/:', normalized)
      }
    } else {
      // 如果无法识别，只使用文件名
      const filename = normalized.split('/').pop()
      if (filename) {
        normalized = filename
        console.warn('⚠️ sanitizeRelativePath - could not extract relative path, using filename:', normalized)
      }
    }
  }

  // 移除前导的 ./ 和 /
  const withoutPrefix = normalized.replace(/^([./])+/, '')
  return withoutPrefix
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
  // 🔧 移除自动恢复选择状态的功能
  // 用户需要手动选择文献，系统不应该自动选中任何文献

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

        // 🔧 清空选择状态（加载新文献时不保留选择）
        if (selectedIds.length > 0) {
          setSelectedIds([])
          console.log('📋 清空选择状态（加载新文献）')
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

        {/* 🆕 批量分析面板（集成进度追踪） */}
        <BatchAnalysisPanel
          csvFilePath={csvFilePath}
          sessionId={sessionId}
          selectedPaperIds={selectedIds}
          totalPapers={papers.length}
        />
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
  const [loadingJournal, setLoadingJournal] = useState(false)
  const [journalInfo, setJournalInfo] = useState<JournalInfo | null>(null)
  const [journalInfoFetched, setJournalInfoFetched] = useState(false)  // 标记是否已尝试获取

  // 获取详细信息（直接使用 paper 对象中的数据）
  const fetchDetails = async () => {
    if (detailedInfo) return

    console.log('📖 加载文献详细信息:', {
      paper_id: paper.paper_id || paper.id,
      source: paper.source,
      has_abstract: !!paper.abstract
    })

    // 直接使用 paper 对象中的数据，不调用 API
    setLoadingDetails(true)
    try {
      setDetailedInfo({
        fullAbstract: paper.abstract || '暂无摘要',
        authors: paper.authors || [],
        published: paper.published || paper.publication_date || '未知',
        categories: paper.categories || [],
        doi: paper.doi,
        citations: paper.citations
      })
      console.log('✅ 文献详细信息加载成功')
    } catch (error: any) {
      console.error('❌ 加载文献详细信息失败:', error)
      // 失败时也设置基本信息
      setDetailedInfo({
        fullAbstract: paper.abstract || '暂无摘要',
        authors: paper.authors || [],
        published: paper.published || paper.publication_date || '未知'
      })
    } finally {
      setLoadingDetails(false)
    }
  }

  // 🆕 获取期刊信息（通过 EasyScholar API）
  const fetchJournalInfo = async (silent = false) => {
    if (journalInfo || loadingJournal || journalInfoFetched) return

    // 🔍 调试：打印文献的所有字段
    console.log('🔍 [调试] 文献数据完整字段:', {
      paper_id: paper.paper_id,
      title: paper.title,
      journal_name: paper.journal_name,
      source: paper.source,
      url: paper.url,
      doi: paper.doi,
      all_fields: Object.keys(paper)
    })

    // 🆕 特殊来源处理：arXiv 预印本
    if (paper.source === 'arxiv' || paper.url?.includes('arxiv.org')) {
      console.log('📄 [期刊信息] 检测到 arXiv 预印本，跳过期刊信息获取')
      setJournalInfoFetched(true)
      return
    }

    // 🆕 特殊来源处理：Tavily 网页搜索（智能识别）
    // 注意：Tavily 来源的期刊信息提取已经在 extractJournalNameFromURL() 中实现
    // 这里不需要特殊处理，直接跳过到通用逻辑
    if (paper.source === 'tavily' || paper.source === 'tavily_academic') {
      console.log('🔍 [Tavily] 检测到 Tavily 来源，将使用通用期刊信息提取逻辑')
    }

    // 尝试从文献信息中提取期刊名称
    let journalName = paper.journal_name
    let extractionMethod = 'journal_name 字段'

    console.log('🔍 [期刊信息] 初始期刊名称:', journalName, '来源:', paper.source)

    // 如果没有期刊名称，尝试从其他字段提取
    if (!journalName && paper.source) {
      // 过滤掉数据源名称（不是期刊名称）
      const dataSources = ['semantic_scholar', 'tavily_academic', 'tavily', 'arxiv', 'pubmed', 'google_scholar', 'cnki', 'upload']
      const sourceLower = paper.source.toLowerCase()

      // 只有当 source 不是数据源名称时，才使用它作为期刊名称
      if (!dataSources.includes(sourceLower)) {
        journalName = paper.source
        extractionMethod = 'source 字段'
        console.log('📚 [期刊信息] 从 source 字段提取期刊名称:', journalName)
      } else {
        console.log('⚠️ [期刊信息] source 字段是数据源名称，跳过:', paper.source)
      }
    }

    // 如果还是没有，尝试从 URL 提取（改进版：支持 DOI 提取和 Semantic Scholar API）
    if (!journalName && paper.url) {
      console.log('🔍 [提取] 尝试从 URL 提取期刊名称:', paper.url)
      console.log('🔍 [提取] 传递参数:', {
        url: paper.url,
        paper_id: paper.paper_id,
        source: paper.source,
        doi: paper.doi
      })
      setLoadingJournal(true)

      try {
        // 动态导入 extractJournalNameFromURL 函数
        const { extractJournalNameFromURL } = await import('../services/easyScholarService')

        // 传递额外参数：paper_id、source 和 doi
        const extractedName = await extractJournalNameFromURL(
          paper.url,
          paper.paper_id,  // Semantic Scholar Paper ID
          paper.source,    // 数据源
          paper.doi        // DOI（如果有）
        )

        if (extractedName) {
          journalName = extractedName
          extractionMethod = 'URL 提取（通过 DOI/CrossRef/Semantic Scholar API）'
          console.log('✅ [提取] 从 URL 提取期刊名称成功:', journalName)
        } else {
          console.warn('⚠️ [提取] extractJournalNameFromURL 返回空值')
        }
      } catch (error) {
        console.error('❌ [提取] 从 URL 提取期刊名称失败:', error)
      } finally {
        setLoadingJournal(false)
      }
    }

    if (!journalName) {
      console.warn('⚠️ [期刊信息] 无法获取期刊名称，已尝试的字段:', {
        journal_name: paper.journal_name,
        source: paper.source,
        url: paper.url
      })

      if (!silent) {
        toast.error('无法获取期刊名称（缺少 journal_name、source 或可解析的 URL）')
      }
      setJournalInfoFetched(true)
      return
    }

    console.log('📚 [期刊信息] 期刊名称:', journalName, '（来源:', extractionMethod, '）')

    setLoadingJournal(true)
    try {
      console.log('📡 [API] 调用 EasyScholar API...')
      console.log('📡 [API] 期刊名称:', journalName)
      const info = await getJournalInfo(journalName)

      console.log('📡 [API] getJournalInfo 返回值:', info)
      console.log('📡 [API] 返回值类型:', typeof info)
      console.log('📡 [API] 返回值详情:', JSON.stringify(info, null, 2))

      if (info) {
        console.log('✅ [API] 期刊信息获取成功:', info)
        console.log('✅ [API] 设置 journalInfo 状态...')
        setJournalInfo(info)
        console.log('✅ [API] journalInfo 状态已设置')
        if (!silent) {
          toast.success(`期刊信息获取成功（${extractionMethod}）`)
        }
      } else {
        console.warn('⚠️ [API] 未找到期刊信息，期刊名称:', journalName)
        if (!silent) {
          toast.error(`未找到期刊信息：${journalName}`)
        }
      }
    } catch (error) {
      console.error('❌ [API] 获取期刊信息失败:', error)
      if (!silent) {
        toast.error(`获取期刊信息失败: ${error instanceof Error ? error.message : '未知错误'}`)
      }
    } finally {
      setLoadingJournal(false)
      setJournalInfoFetched(true)
      console.log('🏁 [API] 期刊信息获取流程结束')
    }
  }

  // 🆕 组件加载时自动获取期刊信息（不需要等待展开）
  useEffect(() => {
    if (!journalInfoFetched && !journalInfo) {
      fetchJournalInfo(true)  // 静默获取，不显示 toast
    }
  }, [])

  // 🔍 监听 journalInfo 状态变化
  useEffect(() => {
    console.log('🔄 [状态] journalInfo 状态变化:', journalInfo)
    console.log('🔄 [状态] journalInfo 详情:', JSON.stringify(journalInfo, null, 2))
  }, [journalInfo])

  // 🆕 检查 journalInfo 是否有任何有用的数据
  const hasUsefulJournalInfo = (info: any): boolean => {
    if (!info) return false

    // 检查是否有任何核心指标
    return !!(
      info.impact_factor !== undefined ||
      info.five_year_impact_factor !== undefined ||
      info.jcr_quartile ||
      info.cas_quartile ||
      info.sci ||
      info.ssci ||
      info.ei ||
      info.cscd ||
      info.pku_core ||
      info.nju_core ||
      info.sci_tech_core ||
      info.publisher ||
      info.country
    )
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

                {/* 🆕 期刊信息标签 - 紧凑视图显示核心信息（温和配色）*/}
                {hasUsefulJournalInfo(journalInfo) && (
                  <>
                    {/* 影响因子 - 温和的蓝色 */}
                    {journalInfo.impact_factor !== undefined && (
                      <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-semibold rounded border border-blue-200">
                        IF {journalInfo.impact_factor.toFixed(1)}
                      </span>
                    )}

                    {/* SCI/SSCI 分区 - 温和的紫色 */}
                    {journalInfo.jcr_quartile && (
                      <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-purple-50 text-purple-700 text-[10px] font-semibold rounded border border-purple-200">
                        {journalInfo.sci ? 'SCI' : journalInfo.ssci ? 'SSCI' : 'JCR'} {journalInfo.jcr_quartile}
                      </span>
                    )}

                    {/* 中科院分区 - 温和的红色 */}
                    {journalInfo.cas_quartile && (
                      <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-rose-50 text-rose-700 text-[10px] font-semibold rounded border border-rose-200">
                        中科院 {journalInfo.cas_quartile}
                        {journalInfo.cas_small_category && ` ${journalInfo.cas_small_category}`}
                      </span>
                    )}

                    {/* Top 期刊标识 - 温和的金色 */}
                    {journalInfo.cas_top && (
                      <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-semibold rounded border border-amber-200">
                        <Award className="w-2.5 h-2.5" />
                        TOP
                      </span>
                    )}
                  </>
                )}

                {/* 🆕 特殊来源标识 */}
                {(() => {
                  // arXiv 预印本标识
                  if (paper.source === 'arxiv' || paper.url?.includes('arxiv.org')) {
                    return (
                      <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-orange-100 text-orange-700 text-[10px] font-medium rounded">
                        📄 预印本 (arXiv)
                      </span>
                    )
                  }

                  // Tavily 来源标识
                  if (paper.source === 'tavily' || paper.source === 'tavily_academic') {
                    // 如果有期刊信息，不显示来源标识（已经有期刊信息了）
                    if (journalInfo) return null

                    // 检查是否为学术出版商
                    const getPublisherNameSync = (url: string): string | null => {
                      const publishers: Record<string, string[]> = {
                        'ScienceDirect': ['sciencedirect.com'],
                        'Springer': ['springer.com'],
                        'Wiley': ['wiley.com'],
                        'IEEE': ['ieeexplore.ieee.org'],
                        'Nature': ['nature.com/articles'],
                        'ACM': ['dl.acm.org'],
                      }

                      const urlLower = url.toLowerCase()
                      for (const [name, patterns] of Object.entries(publishers)) {
                        if (patterns.some(p => urlLower.includes(p))) return name
                      }
                      return null
                    }

                    const publisher = paper.url ? getPublisherNameSync(paper.url) : null

                    if (publisher) {
                      return (
                        <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-teal-100 text-teal-700 text-[10px] font-medium rounded">
                          📚 学术来源 ({publisher})
                        </span>
                      )
                    } else {
                      return (
                        <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] font-medium rounded">
                          🌐 网页来源 (Tavily)
                        </span>
                      )
                    }
                  }

                  return null
                })()}

                {/* 🆕 加载中提示 */}
                {loadingJournal && !journalInfo && (
                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-gray-100 text-gray-500 text-[10px] font-medium rounded">
                    <div className="animate-spin rounded-full h-2 w-2 border border-gray-400 border-t-transparent"></div>
                    获取期刊信息中...
                  </span>
                )}

                {/* 🆕 期刊信息获取失败提示 + 重试按钮 */}
                {!loadingJournal && !journalInfo && journalInfoFetched && (paper.journal_name || paper.source || paper.url) &&
                 paper.source !== 'arxiv' && !paper.url?.includes('arxiv.org') && (
                  <button
                    onClick={() => {
                      setJournalInfoFetched(false)
                      fetchJournalInfo(false)
                    }}
                    className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-orange-100 text-orange-700 text-[10px] font-medium rounded hover:bg-orange-200 transition-colors"
                    title="点击重试获取期刊信息"
                  >
                    <RefreshCw className="w-2.5 h-2.5" />
                    重试获取期刊信息
                  </button>
                )}

                {/* 🆕 无法获取期刊名称的提示 */}
                {!loadingJournal && !journalInfo && journalInfoFetched && !paper.journal_name && !paper.source && !paper.url && (
                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-gray-100 text-gray-500 text-[10px] font-medium rounded" title="文献数据中缺少期刊名称、来源或 URL 字段">
                    <AlertCircle className="w-2.5 h-2.5" />
                    无期刊信息
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
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

                {/* 🆕 期刊详细信息 - 默认展开显示完整信息 */}
                {(hasUsefulJournalInfo(journalInfo) || loadingJournal) && (
                  <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg p-3 space-y-2">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Award className="w-4 h-4 text-indigo-600" />
                      <span className="text-[12px] font-semibold text-indigo-900">期刊信息</span>
                    </div>

                    {loadingJournal ? (
                      <div className="text-[11px] text-gray-500 text-center py-2">
                        正在获取期刊信息...
                      </div>
                    ) : hasUsefulJournalInfo(journalInfo) ? (
                      <>
                        {/* 期刊名称 */}
                        {journalInfo.journal_name && (
                          <div className="text-[11px] pb-1 border-b border-indigo-100">
                            <span className="font-medium text-gray-700">期刊名称: </span>
                            <span className="text-gray-900 font-medium">{journalInfo.journal_name}</span>
                          </div>
                        )}

                        {/* 🆕 核心指标卡片 - 温和配色 */}
                        <div className="grid grid-cols-2 gap-2">
                          {/* 影响因子 */}
                          {journalInfo.impact_factor !== undefined && (
                            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-3 shadow-sm border border-blue-200">
                              <div className="text-blue-600 text-[10px] mb-1 font-medium">影响因子 (IF)</div>
                              <div className="text-blue-700 font-bold text-[18px]">{journalInfo.impact_factor.toFixed(2)}</div>
                            </div>
                          )}

                          {/* 5年影响因子 */}
                          {journalInfo.five_year_impact_factor !== undefined && (
                            <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-lg p-3 shadow-sm border border-indigo-200">
                              <div className="text-indigo-600 text-[10px] mb-1 font-medium">5年IF</div>
                              <div className="text-indigo-700 font-bold text-[18px]">{journalInfo.five_year_impact_factor.toFixed(2)}</div>
                            </div>
                          )}
                        </div>

                        {/* 🆕 分区信息 - 温和配色 */}
                        <div className="grid grid-cols-2 gap-2">
                          {/* JCR/SCI 分区 */}
                          {journalInfo.jcr_quartile && (
                            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-3 shadow-sm border border-purple-200">
                              <div className="text-purple-600 text-[10px] mb-1 font-medium">
                                {journalInfo.sci ? 'SCI 分区' : journalInfo.ssci ? 'SSCI 分区' : 'JCR 分区'}
                              </div>
                              <div className="text-purple-700 font-bold text-[18px]">{journalInfo.jcr_quartile}</div>
                              {journalInfo.jcr_category && (
                                <div className="text-purple-600 text-[9px] mt-1 truncate" title={journalInfo.jcr_category}>
                                  {journalInfo.jcr_category}
                                </div>
                              )}
                            </div>
                          )}

                          {/* 中科院分区 */}
                          {journalInfo.cas_quartile && (
                            <div className="bg-gradient-to-br from-rose-50 to-rose-100 rounded-lg p-3 shadow-sm border border-rose-200">
                              <div className="text-rose-600 text-[10px] mb-1 font-medium flex items-center gap-1">
                                <span>中科院分区</span>
                                {journalInfo.cas_top && (
                                  <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[8px] font-bold rounded border border-amber-300">TOP</span>
                                )}
                              </div>
                              <div className="text-rose-700 font-bold text-[18px]">{journalInfo.cas_quartile}</div>
                              {journalInfo.cas_small_category && (
                                <div className="text-rose-600 text-[9px] mt-1 truncate" title={journalInfo.cas_small_category}>
                                  {journalInfo.cas_small_category}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* 🆕 收录索引 - 温和标签 */}
                        {(journalInfo.sci || journalInfo.ei || journalInfo.ssci || journalInfo.cscd ||
                          journalInfo.pku_core || journalInfo.nju_core || journalInfo.sci_tech_core) && (
                          <div className="pt-2 border-t border-indigo-100">
                            <div className="text-[10px] text-gray-600 mb-1.5 font-medium">📚 收录索引</div>
                            <div className="flex flex-wrap gap-1.5">
                              {journalInfo.sci && (
                                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-semibold rounded border border-blue-200">SCI</span>
                              )}
                              {journalInfo.ei && (
                                <span className="px-2 py-0.5 bg-green-50 text-green-700 text-[10px] font-semibold rounded border border-green-200">EI</span>
                              )}
                              {journalInfo.ssci && (
                                <span className="px-2 py-0.5 bg-purple-50 text-purple-700 text-[10px] font-semibold rounded border border-purple-200">SSCI</span>
                              )}
                              {journalInfo.cscd && (
                                <span className="px-2 py-0.5 bg-orange-50 text-orange-700 text-[10px] font-semibold rounded border border-orange-200">CSCD</span>
                              )}
                              {journalInfo.pku_core && (
                                <span className="px-2 py-0.5 bg-pink-50 text-pink-700 text-[10px] font-semibold rounded border border-pink-200">北大核心</span>
                              )}
                              {journalInfo.nju_core && (
                                <span className="px-2 py-0.5 bg-rose-50 text-rose-700 text-[10px] font-semibold rounded border border-rose-200">南大核心</span>
                              )}
                              {journalInfo.sci_tech_core && (
                                <span className="px-2 py-0.5 bg-cyan-50 text-cyan-700 text-[10px] font-semibold rounded border border-cyan-200">科技核心</span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* 其他信息 */}
                        {(journalInfo.issn || journalInfo.publisher || journalInfo.country) && (
                          <div className="pt-1 border-t border-indigo-100 text-[10px] text-gray-600 space-y-0.5">
                            {journalInfo.issn && (
                              <div>
                                <span className="font-medium">ISSN: </span>
                                <span>{journalInfo.issn}</span>
                                {journalInfo.eissn && <span className="ml-2">E-ISSN: {journalInfo.eissn}</span>}
                              </div>
                            )}
                            {journalInfo.publisher && (
                              <div>
                                <span className="font-medium">出版商: </span>
                                <span>{journalInfo.publisher}</span>
                              </div>
                            )}
                            {journalInfo.country && (
                              <div>
                                <span className="font-medium">国家: </span>
                                <span>{journalInfo.country}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    ) : journalInfoFetched ? (
                      <div className="text-[11px] text-gray-400 text-center py-2">
                        暂无期刊信息
                      </div>
                    ) : null}
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


