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

interface CsvViewerProps {
  url: string
  filename?: string
  maxHeight?: string
  defaultExpanded?: boolean
}

interface CsvData {
  headers: string[]
  rows: string[][]
}

export const CsvViewer: React.FC<CsvViewerProps> = ({
  url,
  filename,
  maxHeight = '400px',
  defaultExpanded = true
}) => {
  const [csvData, setCsvData] = useState<CsvData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadCsvData()
  }, [url])

  const loadCsvData = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Failed to load CSV: ${response.statusText}`)
      }

      const text = await response.text()
      const parsed = parseCsv(text)
      setCsvData(parsed)
    } catch (err) {
      console.error('Failed to load CSV:', err)
      setError(err instanceof Error ? err.message : 'Failed to load CSV')
    } finally {
      setLoading(false)
    }
  }

  const parseCsv = (text: string): CsvData => {
    const lines = text.split('\n').filter(line => line.trim())
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
          current += '"'
          i++
        } else {
          inQuotes = !inQuotes
        }
      } else if (char === ',' && !inQuotes) {
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
      const response = await fetch(url)
      const blob = await response.blob()
      const downloadUrl = URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = filename || 'data.csv'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(downloadUrl)

      toast.success('CSV文件已下载')
    } catch (error) {
      console.error('Download failed:', error)
      toast.error('下载失败')
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
              <table className="w-full text-sm">
                <thead className="bg-gray-100 sticky top-0">
                  <tr>
                    {csvData.headers.map((header, index) => (
                      <th
                        key={index}
                        className="px-4 py-2 text-left font-medium text-gray-700 border-b border-gray-200 whitespace-nowrap"
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
                          className="px-4 py-2 text-gray-700 border-b border-gray-100"
                        >
                          <div className="max-w-md overflow-hidden text-ellipsis">
                            {cell}
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
            {isExpanded && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleDownload}
                  className="flex items-center space-x-1 px-3 py-1 text-sm text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>下载</span>
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="p-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                  title="全屏查看"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Table */}
          {isExpanded && (
            <div
              className="overflow-auto"
              style={{ maxHeight }}
            >
            <table className="w-full text-sm">
              <thead className="bg-gray-100 sticky top-0">
                <tr>
                  {csvData.headers.map((header, index) => (
                    <th
                      key={index}
                      className="px-4 py-2 text-left font-medium text-gray-700 border-b border-gray-200 whitespace-nowrap"
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
                        className="px-4 py-2 text-gray-700 border-b border-gray-100"
                      >
                        <div className="max-w-md overflow-hidden text-ellipsis">
                          {cell}
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

