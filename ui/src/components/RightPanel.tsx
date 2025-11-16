/**
 * RightPanel - container for structures, phonon images, and session files.
 */

import React, { useMemo, useState } from 'react'
import { Download, ExternalLink, Image as ImageIcon, FileText, Table as TableIcon, ChevronDown, ChevronRight } from 'lucide-react'
import StructureViewerThreeJS from './StructureViewerThreeJS'
import StructureList from './StructureList'
import FullscreenViewer from './FullscreenViewer'
import { CsvViewer, MarkdownViewer } from './FileViewer'
import { useAppStore, PhononImage } from '../store/useAppStore'
import { CrystalStructure, SessionFile } from '../types'
import toast from 'react-hot-toast'
import { resolveFileUrl } from '../utils/apiClient'
import { downloadFile, copyToClipboard } from '../utils'

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
  const segments = clean.split('/').filter(Boolean)
  return segments.pop() || fallback
}

const getFileDisplayName = (file: SessionFile) => {
  if (file.name && file.name.trim()) {
    return file.name.trim()
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
    currentSessionStructures
  } = useAppStore()

  const [activeTab, setActiveTab] = useState<'structures' | 'images' | 'files'>('structures')

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
          图片 ({currentSessionPhononImages.length})
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
            phononImages={currentSessionPhononImages}
            onImageFullscreen={openImageFullscreen}
            onDownloadImage={downloadFile}
          />
        )}

        {activeTab === 'files' && (
          <FilesTab files={dataFiles} />
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
                    <h5 className="text-xs font-medium text-gray-700 mb-2">声子色散数据</h5>
                    <CsvViewer
                      url={resolveFileUrl(image.dispersionCsvPath)}
                      filename="phonon_dispersion.csv"
                      maxHeight="200px"
                      defaultExpanded={true}
                    />
                  </div>
                )}
                {image.dosCsvPath && (
                  <div className="bg-white rounded p-2">
                    <h5 className="text-xs font-medium text-gray-700 mb-2">声子态密度数据</h5>
                    <CsvViewer
                      url={resolveFileUrl(image.dosCsvPath)}
                      filename="phonon_dos.csv"
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

export default RightPanel


