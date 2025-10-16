/**
 * MarkdownViewer - Markdown文件查看器组件
 * 功能：
 * 1. 渲染Markdown内容
 * 2. 目录导航（自动提取标题）
 * 3. 可折叠/展开
 * 4. 下载按钮
 */

import React, { useEffect, useState, useRef } from 'react'
import { Download, AlertCircle, Loader2, ChevronDown, ChevronRight, List, Maximize2, X, Move } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'
import toast from 'react-hot-toast'

interface MarkdownViewerProps {
  url: string
  filename?: string
  defaultExpanded?: boolean
  maxHeight?: string
}

interface TocItem {
  id: string
  level: number
  text: string
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({
  url,
  filename,
  defaultExpanded = true,  // 默认展开
  maxHeight = '600px'
}) => {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [showToc, setShowToc] = useState(false)
  const [toc, setToc] = useState<TocItem[]>([])
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const contentRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadMarkdown()
  }, [url])

  useEffect(() => {
    if (content) {
      extractToc(content)
    }
  }, [content])

  const loadMarkdown = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Failed to load Markdown: ${response.statusText}`)
      }

      const text = await response.text()
      setContent(text)
    } catch (err) {
      console.error('Failed to load Markdown:', err)
      setError(err instanceof Error ? err.message : 'Failed to load Markdown')
    } finally {
      setLoading(false)
    }
  }

  const extractToc = (markdown: string) => {
    const headingRegex = /^(#{1,6})\s+(.+)$/gm
    const items: TocItem[] = []
    let match

    while ((match = headingRegex.exec(markdown)) !== null) {
      const level = match[1].length
      const text = match[2].trim()
      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
      
      items.push({ id, level, text })
    }

    setToc(items)
  }

  const scrollToHeading = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleDownload = async () => {
    try {
      const response = await fetch(url)
      const blob = await response.blob()
      const downloadUrl = URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = filename || 'document.md'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(downloadUrl)

      toast.success('Markdown文件已下载')
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
      setPosition({ x: 0, y: 0 })
      setExpanded(true) // 全屏时自动展开
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 bg-gray-50 rounded-lg border border-gray-200">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600 mr-2" />
        <span className="text-gray-600">加载Markdown文档...</span>
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

  return (
    <>
      {/* 全屏模式 */}
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
                <span className="text-sm font-medium text-gray-700">{filename || 'Markdown文档'}</span>
              </div>

              <div className="flex items-center space-x-2">
                {toc.length > 0 && (
                  <button
                    onClick={() => setShowToc(!showToc)}
                    className={`flex items-center space-x-1 px-3 py-1.5 text-sm rounded transition-colors ${
                      showToc
                        ? 'text-primary-700 bg-primary-100'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <List className="w-4 h-4" />
                    <span>目录</span>
                  </button>
                )}
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

            {/* Content */}
            <div className="flex flex-1 overflow-hidden">
              {/* Table of Contents */}
              {showToc && toc.length > 0 && (
                <div className="w-64 border-r border-gray-200 bg-gray-50 overflow-y-auto">
                  <div className="p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">目录</h3>
                    <nav className="space-y-1">
                      {toc.map((item, index) => (
                        <button
                          key={index}
                          onClick={() => scrollToHeading(item.id)}
                          className="block w-full text-left text-sm text-gray-600 hover:text-primary-600 hover:bg-white px-2 py-1 rounded transition-colors"
                          style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                        >
                          {item.text}
                        </button>
                      ))}
                    </nav>
                  </div>
                </div>
              )}

              {/* Markdown Content */}
              <div className="flex-1 overflow-y-auto p-6" ref={contentRef}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ node, ...props }) => <h1 id={props.children?.toString().toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')} style={{ fontSize: '2rem', fontWeight: 'bold', marginTop: '2rem', marginBottom: '1rem', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '0.5rem' }} {...props} />,
                    h2: ({ node, ...props }) => <h2 id={props.children?.toString().toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')} style={{ fontSize: '1.5rem', fontWeight: 'bold', marginTop: '1.5rem', marginBottom: '0.75rem', color: '#111827' }} {...props} />,
                    h3: ({ node, ...props }) => <h3 id={props.children?.toString().toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')} style={{ fontSize: '1.25rem', fontWeight: '600', marginTop: '1rem', marginBottom: '0.5rem', color: '#111827' }} {...props} />,
                    h4: ({ node, ...props }) => <h4 id={props.children?.toString().toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')} style={{ fontSize: '1.125rem', fontWeight: '600', marginTop: '0.75rem', marginBottom: '0.5rem', color: '#111827' }} {...props} />,
                    h5: ({ node, ...props }) => <h5 id={props.children?.toString().toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')} style={{ fontSize: '1rem', fontWeight: '600', marginTop: '0.5rem', marginBottom: '0.25rem', color: '#111827' }} {...props} />,
                    h6: ({ node, ...props }) => <h6 id={props.children?.toString().toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')} style={{ fontSize: '0.875rem', fontWeight: '600', marginTop: '0.5rem', marginBottom: '0.25rem', color: '#111827' }} {...props} />,
                    p: ({ node, ...props }) => <p style={{ marginBottom: '1rem', color: '#374151', lineHeight: '1.75' }} {...props} />,
                    ul: ({ node, ...props }) => <ul style={{ marginBottom: '1rem', marginLeft: '1.5rem', listStyleType: 'disc', color: '#374151' }} {...props} />,
                    ol: ({ node, ...props }) => <ol style={{ marginBottom: '1rem', marginLeft: '1.5rem', listStyleType: 'decimal', color: '#374151' }} {...props} />,
                    li: ({ node, ...props }) => <li style={{ marginBottom: '0.25rem' }} {...props} />,
                    a: ({ node, ...props }) => <a style={{ color: '#2563eb', textDecoration: 'underline' }} {...props} />,
                    blockquote: ({ node, ...props }) => <blockquote style={{ borderLeft: '4px solid #d1d5db', paddingLeft: '1rem', fontStyle: 'italic', color: '#6b7280', margin: '1rem 0' }} {...props} />,
                    strong: ({ node, ...props }) => <strong style={{ fontWeight: 'bold' }} {...props} />,
                    em: ({ node, ...props }) => <em style={{ fontStyle: 'italic' }} {...props} />,
                    code: ({ node, inline, className, children, ...props }: any) => {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={tomorrow}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ borderRadius: '0.5rem', margin: '1rem 0' }}
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code style={{ backgroundColor: '#f3f4f6', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', fontSize: '0.875rem', fontFamily: 'monospace', color: '#1f2937' }} {...props}>
                          {children}
                        </code>
                      )
                    },
                    table: ({ node, ...props }) => (
                      <div style={{ overflowX: 'auto', margin: '1rem 0' }}>
                        <table style={{ minWidth: '100%', borderCollapse: 'collapse', border: '1px solid #e5e7eb' }} {...props} />
                      </div>
                    ),
                    thead: ({ node, ...props }) => <thead style={{ backgroundColor: '#f9fafb' }} {...props} />,
                    tbody: ({ node, ...props }) => <tbody style={{ backgroundColor: 'white' }} {...props} />,
                    tr: ({ node, ...props }) => <tr style={{ borderBottom: '1px solid #e5e7eb' }} {...props} />,
                    th: ({ node, ...props }) => <th style={{ padding: '0.5rem 1rem', textAlign: 'left', fontSize: '0.75rem', fontWeight: '500', color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }} {...props} />,
                    td: ({ node, ...props }) => <td style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', color: '#374151' }} {...props} />,
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 普通模式 */}
      {!isFullscreen && (
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              {expanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <span>{filename || 'Markdown文档'}</span>
            </button>

            <div className="flex items-center space-x-2">
              {toc.length > 0 && expanded && (
                <button
                  onClick={() => setShowToc(!showToc)}
                  className={`flex items-center space-x-1 px-3 py-1 text-sm rounded transition-colors ${
                    showToc
                      ? 'text-primary-700 bg-primary-100'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <List className="w-4 h-4" />
                  <span>目录</span>
                </button>
              )}
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
          </div>

          {/* Content */}
          {expanded && (
            <div className="flex">
              {/* Table of Contents */}
              {showToc && toc.length > 0 && (
                <div className="w-64 border-r border-gray-200 bg-gray-50 overflow-y-auto" style={{ maxHeight }}>
                  <div className="p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">目录</h3>
                    <nav className="space-y-1">
                      {toc.map((item, index) => (
                        <button
                          key={index}
                          onClick={() => scrollToHeading(item.id)}
                          className="block w-full text-left text-sm text-gray-600 hover:text-primary-600 hover:bg-white px-2 py-1 rounded transition-colors"
                          style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                        >
                          {item.text}
                        </button>
                      ))}
                    </nav>
                  </div>
                </div>
              )}

              {/* Markdown Content */}
              <div
                ref={contentRef}
                className="flex-1 overflow-y-auto p-6"
                style={{ maxHeight }}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ node, children, ...props }) => {
                      const text = String(children)
                      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
                      return <h1 id={id} style={{ fontSize: '2rem', fontWeight: 'bold', marginTop: '2rem', marginBottom: '1rem', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '0.5rem' }} {...props}>{children}</h1>
                    },
                    h2: ({ node, children, ...props }) => {
                      const text = String(children)
                      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
                      return <h2 id={id} style={{ fontSize: '1.5rem', fontWeight: 'bold', marginTop: '1.5rem', marginBottom: '0.75rem', color: '#111827' }} {...props}>{children}</h2>
                    },
                    h3: ({ node, children, ...props }) => {
                      const text = String(children)
                      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
                      return <h3 id={id} style={{ fontSize: '1.25rem', fontWeight: '600', marginTop: '1rem', marginBottom: '0.5rem', color: '#111827' }} {...props}>{children}</h3>
                    },
                    h4: ({ node, children, ...props }) => {
                      const text = String(children)
                      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
                      return <h4 id={id} style={{ fontSize: '1.125rem', fontWeight: '600', marginTop: '0.75rem', marginBottom: '0.5rem', color: '#111827' }} {...props}>{children}</h4>
                    },
                    h5: ({ node, children, ...props }) => {
                      const text = String(children)
                      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
                      return <h5 id={id} style={{ fontSize: '1rem', fontWeight: '600', marginTop: '0.5rem', marginBottom: '0.25rem', color: '#111827' }} {...props}>{children}</h5>
                    },
                    h6: ({ node, children, ...props }) => {
                      const text = String(children)
                      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
                      return <h6 id={id} style={{ fontSize: '0.875rem', fontWeight: '600', marginTop: '0.5rem', marginBottom: '0.25rem', color: '#111827' }} {...props}>{children}</h6>
                    },
                    p: ({ node, ...props }) => <p style={{ marginBottom: '1rem', color: '#374151', lineHeight: '1.75' }} {...props} />,
                    ul: ({ node, ...props }) => <ul style={{ marginBottom: '1rem', marginLeft: '1.5rem', listStyleType: 'disc', color: '#374151' }} {...props} />,
                    ol: ({ node, ...props }) => <ol style={{ marginBottom: '1rem', marginLeft: '1.5rem', listStyleType: 'decimal', color: '#374151' }} {...props} />,
                    li: ({ node, ...props }) => <li style={{ marginBottom: '0.25rem' }} {...props} />,
                    a: ({ node, ...props }) => <a style={{ color: '#2563eb', textDecoration: 'underline' }} {...props} />,
                    blockquote: ({ node, ...props }) => <blockquote style={{ borderLeft: '4px solid #d1d5db', paddingLeft: '1rem', fontStyle: 'italic', color: '#6b7280', margin: '1rem 0' }} {...props} />,
                    strong: ({ node, ...props }) => <strong style={{ fontWeight: 'bold' }} {...props} />,
                    em: ({ node, ...props }) => <em style={{ fontStyle: 'italic' }} {...props} />,
                    code({ node, className, children, ...props }: any) {
                      const inline = !className
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={tomorrow as any}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ borderRadius: '0.5rem', margin: '1rem 0' }}
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code style={{ backgroundColor: '#f3f4f6', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', fontSize: '0.875rem', fontFamily: 'monospace', color: '#1f2937' }} {...props}>
                          {children}
                        </code>
                      )
                    },
                    table: ({ node, ...props }) => (
                      <div style={{ overflowX: 'auto', margin: '1rem 0' }}>
                        <table style={{ minWidth: '100%', borderCollapse: 'collapse', border: '1px solid #e5e7eb' }} {...props} />
                      </div>
                    ),
                    thead: ({ node, ...props }) => <thead style={{ backgroundColor: '#f9fafb' }} {...props} />,
                    tbody: ({ node, ...props }) => <tbody style={{ backgroundColor: 'white' }} {...props} />,
                    tr: ({ node, ...props }) => <tr style={{ borderBottom: '1px solid #e5e7eb' }} {...props} />,
                    th: ({ node, ...props }) => <th style={{ padding: '0.5rem 1rem', textAlign: 'left', fontSize: '0.75rem', fontWeight: '500', color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }} {...props} />,
                    td: ({ node, ...props }) => <td style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', color: '#374151' }} {...props} />,
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  )
}

