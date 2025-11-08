import React, { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Clock, FileText, Download } from 'lucide-react'
import { CsvViewer } from './FileViewer/CsvViewer'
import { MarkdownViewer } from './FileViewer/MarkdownViewer'

interface ToolExecutionCardProps {
  toolName: string
  input?: Record<string, any>
  output?: Record<string, any>
  status: 'pending' | 'success' | 'error'
  timestamp: string
  error?: string
}

/**
 * 工具执行卡片组件
 * 
 * 显示 Google ADK 工具调用的完整信息：
 * - 工具名称和调用时间
 * - 输入参数（可折叠）
 * - 执行状态（pending/success/error）
 * - 输出结果（可折叠）
 * - 生成的文件（CSV、Markdown 等）
 */
export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({
  toolName,
  input,
  output,
  status,
  timestamp,
  error
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showInput, setShowInput] = useState(false)

  // 状态图标和颜色
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-500 animate-pulse" />
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'success':
        return '执行成功'
      case 'error':
        return '执行失败'
      case 'pending':
        return '执行中...'
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'border-green-200 bg-green-50'
      case 'error':
        return 'border-red-200 bg-red-50'
      case 'pending':
        return 'border-yellow-200 bg-yellow-50'
    }
  }

  // 提取文件链接
  const extractFileLinks = () => {
    if (!output) return []

    const files: Array<{ type: 'csv' | 'md', url: string, filename?: string, content?: string }> = []

    // CSV 文件
    if (output.csv_download_url) {
      files.push({
        type: 'csv',
        url: output.csv_download_url,
        filename: output.csv_file_path?.split('/').pop(),
        content: output.csv_inline_content
      })
    }

    // Markdown 文件
    if (output.md_download_url) {
      files.push({
        type: 'md',
        url: output.md_download_url,
        filename: output.summary_file_path?.split('/').pop() || output.report_file_path?.split('/').pop(),
        content: output.md_inline_content
      })
    }

    return files
  }

  // 🆕 提取文本输出内容（除了文件链接之外的其他字段）
  const extractTextOutput = () => {
    if (!output) return null

    // 文件相关字段（不显示在文本输出中）
    const fileFields = new Set([
      'csv_download_url', 'csv_file_path', 'csv_inline_content',
      'md_download_url', 'summary_file_path', 'report_file_path', 'md_inline_content',
      'phonon_band_plot_path', 'phonon_dos_plot_path',
      'phonon_band_plot_available', 'phonon_dos_plot_available',
      'images'  // 图片单独处理
    ])

    // 提取非文件字段
    const textFields: Record<string, any> = {}
    Object.entries(output).forEach(([key, value]) => {
      if (!fileFields.has(key) && value !== null && value !== undefined) {
        textFields[key] = value
      }
    })

    return Object.keys(textFields).length > 0 ? textFields : null
  }

  const fileLinks = extractFileLinks()
  const textOutput = extractTextOutput()

  return (
    <div className={`border rounded-lg p-4 mb-3 ${getStatusColor()}`}>
      {/* 工具调用头部 */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 flex-1">
          {getStatusIcon()}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900">🔧 {toolName}</span>
              <span className="text-xs text-gray-500">{getStatusText()}</span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {new Date(timestamp).toLocaleTimeString('zh-CN')}
            </div>
          </div>
        </div>
        
        {/* 展开/折叠按钮 */}
        {(input || output || error) && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </button>
        )}
      </div>

      {/* 展开内容 */}
      {isExpanded && (
        <div className="mt-4 space-y-3">
          {/* 输入参数 */}
          {input && Object.keys(input).length > 0 && (
            <div>
              <button
                onClick={() => setShowInput(!showInput)}
                className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                {showInput ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                输入参数
              </button>
              {showInput && (
                <pre className="mt-2 p-3 bg-white rounded border border-gray-200 text-xs overflow-x-auto">
                  {JSON.stringify(input, null, 2)}
                </pre>
              )}
            </div>
          )}

          {/* 错误信息 */}
          {error && (
            <div className="p-3 bg-red-100 border border-red-200 rounded text-sm text-red-700">
              <strong>错误：</strong> {error}
            </div>
          )}

          {/* 🆕 文本输出内容 */}
          {textOutput && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-700">📝 输出信息：</div>
              <div className="p-3 bg-white rounded border border-gray-200 text-sm space-y-2">
                {/* 优先显示 message 字段 */}
                {textOutput.message && (
                  <div className="text-gray-800">
                    <strong>消息：</strong> {textOutput.message}
                  </div>
                )}

                {/* 显示其他字段 */}
                {Object.entries(textOutput).map(([key, value]) => {
                  if (key === 'message') return null  // message 已经单独显示

                  // 格式化字段名
                  const fieldName = key
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (l) => l.toUpperCase())

                  // 格式化值
                  let displayValue: string
                  if (typeof value === 'boolean') {
                    displayValue = value ? '✅ 是' : '❌ 否'
                  } else if (typeof value === 'object') {
                    displayValue = JSON.stringify(value, null, 2)
                  } else {
                    displayValue = String(value)
                  }

                  return (
                    <div key={key} className="text-gray-700 text-xs">
                      <strong>{fieldName}:</strong> {displayValue}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* 生成的文件 */}
          {fileLinks.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-700">📄 生成的文件：</div>
              {fileLinks.map((file, index) => (
                <div key={index}>
                  {file.type === 'csv' ? (
                    <CsvViewer
                      url={file.url}
                      filename={file.filename}
                      inlineContent={file.content}
                      defaultExpanded={false}
                    />
                  ) : (
                    <MarkdownViewer
                      url={file.url}
                      filename={file.filename}
                      inlineContent={file.content}
                      defaultExpanded={false}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

