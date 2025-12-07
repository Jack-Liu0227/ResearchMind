/**
 * CsvViewer - CSV文件查看器组件
 * 功能：
 * 1. 可滚动的表格预览
 * 2. 下载按钮
 * 3. 自动从URL加载CSV数据
 */

import React, { useEffect, useState, useRef } from 'react'
import { Download, AlertCircle, Loader2, Maximize2, Minimize2, Move, X, ChevronDown, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { resolveFileUrl } from '../../utils/apiClient'
import { copyToClipboard } from '../../utils'

interface CsvViewerProps {
  url: string
  filename?: string
  maxHeight?: string
  defaultExpanded?: boolean
  inlineContent?: string
}

interface CsvData {
  headers: string[]
  rows: string[][]
}

export const CsvViewer: React.FC<CsvViewerProps> = ({
  url,
  filename,
  maxHeight = '400px',
  defaultExpanded = false,  // 默认折叠
  inlineContent
}) => {
  const [csvData, setCsvData] = useState<CsvData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [expandedCells, setExpandedCells] = useState<Set<string>>(new Set())
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const hasInlineContent = typeof inlineContent === 'string' && inlineContent.trim().length > 0

    if (hasInlineContent) {
      try {
        setLoading(true)
        setError(null)
        const parsed = parseCsv(inlineContent!)
        setCsvData(parsed)
      } catch (err) {
        console.error('⚠️ Failed to parse inline CSV content:', err)
        setCsvData(null)
        setError(err instanceof Error ? err.message : 'Failed to parse CSV content')
      } finally {
        setLoading(false)
      }
    } else {
      loadCsvData()
    }
  }, [url, inlineContent])

  const loadCsvData = async () => {
    try {
      setLoading(true)
      setError(null)

      // 处理相对路径 URL
      const resolvedUrl = resolveFileUrl(url)
      console.log('📊 CsvViewer - Loading CSV from URL:', resolvedUrl)
      console.log('📊 CsvViewer - Original URL:', url)

      const response = await fetch(resolvedUrl, {
        method: 'GET',
        headers: {
          'Accept': 'text/csv, text/plain, */*'
        }
      })

      console.log('📊 CsvViewer - Response status:', response.status, response.statusText)
      console.log('📊 CsvViewer - Response headers:', {
        'content-type': response.headers.get('content-type'),
        'content-length': response.headers.get('content-length')
      })

      if (!response.ok) {
        console.error(`❌ CSV load failed: ${response.status} ${response.statusText}`)
        throw new Error(`Failed to load CSV: ${response.status} ${response.statusText}`)
      }

      const text = await response.text()
      console.log(`📊 CsvViewer - CSV loaded successfully, size: ${text.length} bytes`)
      console.log(`📊 CsvViewer - CSV content preview (first 200 chars):`, text.substring(0, 200))

      if (!text.trim()) {
        console.warn('⚠️ CSV file is empty')
        throw new Error('CSV file is empty')
      }

      const parsed = parseCsv(text)
      console.log(`📊 CsvViewer - CSV parsed: ${parsed.headers.length} columns, ${parsed.rows.length} rows`)
      console.log(`📊 CsvViewer - Headers:`, parsed.headers)
      setCsvData(parsed)
    } catch (err) {
      console.error('❌ Failed to load CSV:', err)
      console.error('❌ Error details:', {
        url,
        resolvedUrl: resolveFileUrl(url),
        filename,
        error: err instanceof Error ? err.message : String(err),
        stack: err instanceof Error ? err.stack : undefined
      })

      // 提供更友好的错误信息
      let errorMessage = 'Failed to load CSV'
      if (err instanceof Error) {
        if (err.message.includes('404')) {
          errorMessage = 'CSV file not found (404). The file may have been moved or deleted.'
        } else if (err.message.includes('403')) {
          errorMessage = 'Access denied (403). You may not have permission to access this file.'
        } else if (err.message.includes('500')) {
          errorMessage = 'Server error (500). Please try again later.'
        } else {
          errorMessage = err.message
        }
      }

      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const parseCsv = (text: string): CsvData => {
    // 使用更智能的方式解析 CSV，正确处理引号内的换行符
    const lines: string[] = []
    let currentLine = ''
    let inQuotes = false

    for (let i = 0; i < text.length; i++) {
      const char = text[i]
      const nextChar = text[i + 1]

      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          // 转义的引号
          currentLine += '"'
          i++
        } else {
          // 切换引号状态
          inQuotes = !inQuotes
        }
        currentLine += char
      } else if (char === '\n' && !inQuotes) {
        // 只有在引号外的换行符才是真正的行分隔符
        if (currentLine.trim()) {
          lines.push(currentLine)
        }
        currentLine = ''
      } else if (char === '\r' && nextChar === '\n' && !inQuotes) {
        // 处理 Windows 风格的换行符 \r\n
        if (currentLine.trim()) {
          lines.push(currentLine)
        }
        currentLine = ''
        i++ // 跳过 \n
      } else {
        currentLine += char
      }
    }

    // 添加最后一行
    if (currentLine.trim()) {
      lines.push(currentLine)
    }

    if (lines.length === 0) {
      return { headers: [], rows: [] }
    }

    const headers = parseCsvLine(lines[0])
    const rows = lines.slice(1).map(line => parseCsvLine(line))

    return { headers, rows }
  }

  const parseCsvLine = (line: string): string[] => {
    const result: string[] = []
    let current = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i++) {
      const char = line[i]
      const nextChar = line[i + 1]

      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          // 转义的引号（两个连续的引号表示一个引号字符）
          current += '"'
          i++
        } else {
          // 切换引号状态
          inQuotes = !inQuotes
        }
      } else if (char === ',' && !inQuotes) {
        // 只有在引号外的逗号才是字段分隔符
        result.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }

    result.push(current.trim())
    return result
  }

  const handleDownload = async () => {
    try {
      if (inlineContent && inlineContent.trim().length > 0) {
        const blob = new Blob([inlineContent], { type: 'text/csv;charset=utf-8;' })
        const downloadUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = downloadUrl
        a.download = filename || 'data.csv'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(downloadUrl)
      } else {
        const resolvedUrl = resolveFileUrl(url)
        const response = await fetch(resolvedUrl)
        if (!response.ok) {
          throw new Error(`Download failed: ${response.statusText}`)
        }
        const blob = await response.blob()
        const downloadUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = downloadUrl
        a.download = filename || 'data.csv'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(downloadUrl)
      }

      toast.success('CSV文件已下载')
    } catch (error) {
      console.error('Download failed:', error)
      toast.error('下载失败')
    }
  }

  const handleCopyLink = async () => {
    try {
      const resolvedUrl = resolveFileUrl(url)
      const success = await copyToClipboard(resolvedUrl)
      if (success) {
        toast.success('链接已复制到剪贴板')
      } else {
        toast.error('复制失败，请手动复制链接')
      }
    } catch (err) {
      console.error('复制链接失败:', err)
      toast.error('复制失败')
    }
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (isFullscreen && e.target === e.currentTarget) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
    }
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, dragStart])

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
    if (!isFullscreen) {
      // 进入全屏时，居中显示
      setPosition({ x: 0, y: 0 })
    }
  }

  const toggleCellExpansion = (rowIndex: number, cellIndex: number) => {
    const key = `${rowIndex}-${cellIndex}`
    const newExpanded = new Set(expandedCells)
    if (newExpanded.has(key)) {
      newExpanded.delete(key)
    } else {
      newExpanded.add(key)
    }
    setExpandedCells(newExpanded)
  }

  const isCellExpanded = (rowIndex: number, cellIndex: number) => {
    return expandedCells.has(`${rowIndex}-${cellIndex}`)
  }

  const shouldTruncate = (text: string, maxLength: number = 200) => {
    return text && text.length > maxLength
  }

  const renderCellContent = (cell: string, rowIndex: number, cellIndex: number) => {
    const isExpanded = isCellExpanded(rowIndex, cellIndex)
    const needsTruncate = shouldTruncate(cell)

    if (!needsTruncate) {
      return <span className="whitespace-pre-wrap">{cell}</span>
    }

    return (
      <div className="group">
        <div className={isExpanded ? 'whitespace-pre-wrap' : 'line-clamp-4'}>
          {cell}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            toggleCellExpansion(rowIndex, cellIndex)
          }}
          className="mt-1 text-xs text-blue-600 hover:text-blue-800 hover:underline focus:outline-none inline-flex items-center gap-1"
        >
          {isExpanded ? (
            <>
              <ChevronRight className="w-3 h-3" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              展开全部 ({cell.length} 字符)
            </>
          )}
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 bg-gray-50 rounded-lg border border-gray-200">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600 mr-2" />
        <span className="text-gray-600">加载CSV数据...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center p-4 bg-red-50 rounded-lg border border-red-200">
        <AlertCircle className="w-5 h-5 text-red-600 mr-2 flex-shrink-0" />
        <span className="text-red-700">{error}</span>
      </div>
    )
  }

  if (!csvData || csvData.headers.length === 0) {
    return (
      <div className="flex items-center p-4 bg-yellow-50 rounded-lg border border-yellow-200">
        <AlertCircle className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" />
        <span className="text-yellow-700">CSV文件为空</span>
      </div>
    )
  }

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-8"
    : "border border-gray-200 rounded-lg overflow-hidden bg-white"

  const innerClasses = isFullscreen
    ? "bg-white rounded-lg shadow-2xl max-w-7xl w-full max-h-full flex flex-col"
    : ""

  const containerStyle = isFullscreen && position.x !== 0 && position.y !== 0
    ? { transform: `translate(${position.x}px, ${position.y}px)` }
    : {}

  return (
    <>
      {isFullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-90"
          onClick={() => setIsFullscreen(false)}
        >
          <div
            ref={containerRef}
            className="bg-white w-full h-full flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200 flex-shrink-0"
            >
              <div className="flex items-center space-x-3">
                <span className="text-sm font-medium text-gray-700">
                  {filename || 'CSV数据'}
                </span>
                <span className="text-xs text-gray-500">
                  ({csvData.rows.length} 行)
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleDownload}
                  className="flex items-center space-x-1 px-3 py-1.5 text-sm text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>下载</span>
                </button>
                <button
                  onClick={handleCopyLink}
                  className="flex items-center space-x-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                  title="复制链接"
                >
                  <span>复制</span>
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                  title="退出全屏"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-auto flex-1">
              <table className="w-full text-sm table-auto">
                <thead className="bg-gray-100 sticky top-0 z-10">
                  <tr>
                    {csvData.headers.map((header, index) => (
                      <th
                        key={index}
                        className="px-4 py-2 text-left font-medium text-gray-700 border-b border-gray-200 whitespace-nowrap min-w-[120px]"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {csvData.rows.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                    >
                      {row.map((cell, cellIndex) => (
                        <td
                          key={cellIndex}
                          className="px-4 py-2 text-gray-700 border-b border-gray-100 align-top"
                        >
                          <div className="min-w-[200px] max-w-[600px] break-words whitespace-pre-wrap">
                            {renderCellContent(cell, rowIndex, cellIndex)}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {!isFullscreen && (
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <span>{filename || 'CSV数据'}</span>
              <span className="text-xs text-gray-500">
                ({csvData.rows.length} 行)
              </span>
            </button>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleDownload}
                className="flex items-center space-x-1 px-3 py-1 text-sm text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>下载</span>
              </button>
              <button
                onClick={handleCopyLink}
                className="flex items-center space-x-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                title="复制链接"
              >
                <span>复制</span>
              </button>
              <button
                onClick={toggleFullscreen}
                className="p-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                title="全屏查看"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Table */}
          {isExpanded && (
            <div
              className="overflow-auto"
              style={{ maxHeight }}
            >
            <table className="w-full text-sm table-auto">
              <thead className="bg-gray-100 sticky top-0 z-10">
                <tr>
                  {csvData.headers.map((header, index) => (
                    <th
                      key={index}
                      className="px-4 py-2 text-left font-medium text-gray-700 border-b border-gray-200 whitespace-nowrap min-w-[120px]"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvData.rows.map((row, rowIndex) => (
                  <tr
                    key={rowIndex}
                    className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                  >
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-4 py-2 text-gray-700 border-b border-gray-100 align-top"
                      >
                        <div className="min-w-[200px] max-w-[600px] break-words whitespace-pre-wrap">
                          {renderCellContent(cell, rowIndex, cellIndex)}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </div>
      )}
    </>
  )
}

