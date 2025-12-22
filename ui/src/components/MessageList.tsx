import React, { useEffect, useRef, useState } from 'react'
import { Bot, User, Copy, ThumbsUp, ThumbsDown, RotateCcw, Download, ChevronDown, ChevronRight } from 'lucide-react'
import { Message } from '../types'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { ensureValidTimestamp, downloadFile, copyToClipboard } from '../utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'
import toast from 'react-hot-toast'
import { useAppStore } from '../store/useAppStore'
import { hasStructureData, smartParseStructure } from '../utils/structureParser'
import { CrystalStructure } from '../types'
import { CsvViewer, MarkdownViewer } from './FileViewer'
import { API_CONFIG } from '../constants'
import { resolveFileUrl } from '../utils/apiClient'
import MessageBillingBadge from './MessageBillingBadge'
import { ToolExecutionCard } from './ToolExecutionCard'

/**
 * Tool Calls 折叠显示组件
 * 默认展开所有工具调用，显示输出结果
 */
const ToolCallsDisplay: React.FC<{ toolCalls: any[] }> = ({ toolCalls }) => {
  // 默认折叠所有工具调用，仅当用户点击时展开
  const [expandedCalls, setExpandedCalls] = useState<Set<number>>(new Set())

  const toggleCall = (index: number) => {
    const newExpanded = new Set(expandedCalls)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedCalls(newExpanded)
  }

  if (!toolCalls || toolCalls.length === 0) return null

  return (
    <div className="mt-3 space-y-2">
      <div className="text-xs font-semibold text-gray-600 mb-2">🔧 工具调用记录</div>
      {toolCalls.map((call, index) => {
        const isExpanded = expandedCalls.has(index)

        return (
          <div key={index} className="border border-black/5 rounded-lg overflow-hidden bg-white/40 backdrop-blur-sm">
            {/* 工具调用头部 */}
            <button
              onClick={() => toggleCall(index)}
              className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center space-x-2">
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-500" />
                )}
                <span className="text-sm font-medium text-gray-700">{call.name}</span>
                {call.status && (
                  <span className={`text-xs px-2 py-0.5 rounded ${call.status === 'success' ? 'bg-green-100 text-green-700' :
                    call.status === 'error' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                    {call.status}
                  </span>
                )}
              </div>
              {call.timestamp && (
                <span className="text-xs text-gray-500">{new Date(call.timestamp).toLocaleTimeString()}</span>
              )}
            </button>

            {/* 工具调用详情 */}
            {isExpanded && (
              <div className="px-3 py-2 border-t border-black/5 bg-white/30">
                {/* 输入参数 */}
                {call.input && Object.keys(call.input).length > 0 && (
                  <div className="mb-3">
                    <div className="text-xs font-semibold text-gray-600 mb-1">📥 输入参数</div>
                    <pre className="text-xs bg-gray-50 p-2 rounded border border-gray-200 overflow-x-auto">
                      {JSON.stringify(call.input, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 输出结果 */}
                {call.output !== undefined && (
                  <div>
                    <div className="text-xs font-semibold text-gray-600 mb-1">📤 输出结果</div>
                    <pre className="text-xs bg-gray-50 p-2 rounded border border-gray-200 overflow-x-auto max-h-60">
                      {typeof call.output === 'string'
                        ? call.output
                        : JSON.stringify(call.output, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 错误信息 */}
                {call.error && (
                  <div className="mt-2">
                    <div className="text-xs font-semibold text-red-600 mb-1">❌ 错误信息</div>
                    <pre className="text-xs bg-red-50 p-2 rounded border border-red-200 overflow-x-auto">
                      {call.error}
                    </pre>
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

/**
 * 从文本中提取多个 CIF 块
 */
function extractCIFBlocks(text: string): string[] {
  const blocks: string[] = []

  // 查找所有 CIF 代码块（在 ```cif 和 ``` 之间）
  const cifRegex = /```cif\n([\s\S]*?)```/g
  let match

  while ((match = cifRegex.exec(text)) !== null) {
    blocks.push(match[1].trim())
  }

  // 如果没有找到代码块，尝试查找 data_ 开头的块
  if (blocks.length === 0) {
    const dataBlocks = text.split(/(?=data_)/)
    for (const block of dataBlocks) {
      if (block.trim().startsWith('data_') && block.includes('_cell_length_a')) {
        blocks.push(block.trim())
      }
    }
  }

  // 如果还是没有找到，返回整个文本
  if (blocks.length === 0 && text.includes('_cell_length_a')) {
    blocks.push(text)
  }

  return blocks
}

/**
 * 文件链接类型定义
 */
interface FileLink {
  type: 'csv' | 'md'
  url: string
  filename?: string
  content?: string
}

/**
 * 从消息内容中提取文件下载链接
 */
function extractFileLinks(content: string, metadata?: any): FileLink[] {
  const links: FileLink[] = []

  // 从metadata中提取
  if (metadata) {
    console.log('📄 extractFileLinks - metadata:', metadata)

    // 文献搜索的 CSV 文件
    if (metadata.csv_download_url) {
      const resolvedCsvUrl = resolveFileUrl(metadata.csv_download_url)
      console.log('📄 Found CSV URL:', metadata.csv_download_url, '->', resolvedCsvUrl)
      links.push({
        type: 'csv',
        url: resolvedCsvUrl,
        filename: metadata.csv_file_path ? metadata.csv_file_path.split('/').pop() : undefined,
        content: typeof metadata.csv_inline_content === 'string' ? metadata.csv_inline_content : undefined
      })
    }

    // 🆕 热导率计算结果 CSV 文件（单个计算）
    if (metadata.kappa_results_csv_url) {
      const resolvedCsvUrl = resolveFileUrl(metadata.kappa_results_csv_url)
      console.log('📄 Found Kappa Results CSV URL:', metadata.kappa_results_csv_url, '->', resolvedCsvUrl)
      links.push({
        type: 'csv',
        url: resolvedCsvUrl,
        filename: metadata.kappa_results_csv_path ? metadata.kappa_results_csv_path.split('/').pop() : 'kappa_results.csv',
        content: typeof metadata.kappa_results_csv_content === 'string' ? metadata.kappa_results_csv_content : undefined
      })
    }

    // 🆕 批量热导率计算结果 CSV 文件
    if (metadata.kappa_batch_csv_url) {
      const resolvedCsvUrl = resolveFileUrl(metadata.kappa_batch_csv_url)
      console.log('📄 Found Batch Kappa Results CSV URL:', metadata.kappa_batch_csv_url, '->', resolvedCsvUrl)
      links.push({
        type: 'csv',
        url: resolvedCsvUrl,
        filename: metadata.kappa_batch_csv_path ? metadata.kappa_batch_csv_path.split('/').pop() : 'kappa_batch_results.csv',
        content: typeof metadata.kappa_batch_csv_content === 'string' ? metadata.kappa_batch_csv_content : undefined
      })
    }

    // 🆕 声子色散数据 CSV 文件
    if (metadata.phonon_dispersion_csv_url) {
      const resolvedCsvUrl = resolveFileUrl(metadata.phonon_dispersion_csv_url)
      console.log('📄 Found Phonon Dispersion CSV URL:', metadata.phonon_dispersion_csv_url, '->', resolvedCsvUrl)
      links.push({
        type: 'csv',
        url: resolvedCsvUrl,
        filename: metadata.phonon_dispersion_csv_path ? metadata.phonon_dispersion_csv_path.split('/').pop() : 'phonon_dispersion.csv',
        content: typeof metadata.phonon_dispersion_csv_content === 'string' ? metadata.phonon_dispersion_csv_content : undefined
      })
    }

    // 🆕 声子态密度数据 CSV 文件
    if (metadata.phonon_dos_csv_url) {
      const resolvedCsvUrl = resolveFileUrl(metadata.phonon_dos_csv_url)
      console.log('📄 Found Phonon DOS CSV URL:', metadata.phonon_dos_csv_url, '->', resolvedCsvUrl)
      links.push({
        type: 'csv',
        url: resolvedCsvUrl,
        filename: metadata.phonon_dos_csv_path ? metadata.phonon_dos_csv_path.split('/').pop() : 'phonon_dos.csv',
        content: typeof metadata.phonon_dos_csv_content === 'string' ? metadata.phonon_dos_csv_content : undefined
      })
    }

    // 文献搜索的 Markdown 文件
    if (metadata.md_download_url) {
      const resolvedMdUrl = resolveFileUrl(metadata.md_download_url)
      console.log('📄 Found MD URL:', metadata.md_download_url, '->', resolvedMdUrl)
      const mdFilePath = metadata.summary_file_path || metadata.report_file_path
      links.push({
        type: 'md',
        url: resolvedMdUrl,
        filename: mdFilePath ? mdFilePath.split('/').pop() : undefined,
        content: typeof metadata.md_inline_content === 'string' ? metadata.md_inline_content : undefined
      })
    }
  } else {
    console.log('📄 extractFileLinks - no metadata provided')
  }

  // 从文本中提取URL（备用方案）
  const apiUrl = API_CONFIG.BASE_URL
  const urlRegex = new RegExp(`${apiUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\/api\\/download\\/[^\\s)]+\\.(csv|md)`, 'g')
  let match
  while ((match = urlRegex.exec(content)) !== null) {
    const url = match[0]
    const ext = match[1] as 'csv' | 'md'

    // 避免重复
    if (!links.some(link => link.url === url)) {
      links.push({
        type: ext,
        url: resolveFileUrl(url),
        filename: url.split('/').pop()
      })
    }
  }

  return links
}

/**
 * 从文本中提取图片数据（声子谱等计算结果图片）
 */
function extractImageData(text: string): Array<{ path: string, base64: string, name: string }> {
  const imageData: Array<{ path: string, base64: string, name: string }> = []

  // 方法1: 查找日志中的图片路径和 base64 数据
  const lines = text.split('\n')

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // 查找图片路径行 - 支持更多格式
    const pathPatterns = [
      /encoded path=([^\s]+\.png)/i,
      /图片路径[：:]\s*([^\s]+\.png)/i,
      /保存到[：:]\s*([^\s]+\.png)/i,
      /generated plot[：:]\s*([^\s]+\.png)/i,
      /phonon.*plot.*[：:]\s*([^\s]+\.png)/i
    ]

    let imagePath = ''
    for (const pattern of pathPatterns) {
      const match = line.match(pattern)
      if (match) {
        imagePath = match[1]
        break
      }
    }

    if (imagePath) {
      const fileName = imagePath.split(/[/\\]/).pop() || `图片${i + 1}`

      // 查找后续的 base64 数据（可能在接下来的几行中）
      let base64Data = ''
      for (let j = i + 1; j < Math.min(i + 30, lines.length); j++) {
        const nextLine = lines[j].trim()
        // 检查是否是 base64 数据（通常很长且包含字母数字和+/=）
        if (nextLine.length > 100 && /^[A-Za-z0-9+/=]+$/.test(nextLine)) {
          base64Data = nextLine
          break
        }
      }

      if (base64Data) {
        imageData.push({
          path: imagePath,
          base64: base64Data,
          name: fileName
        })
      }
    }
  }

  // 方法2: 查找直接的 base64 图片数据（如果有的话）
  const base64ImageRegex = /data:image\/png;base64,([A-Za-z0-9+/=]+)/g
  let match: RegExpExecArray | null
  while ((match = base64ImageRegex.exec(text)) !== null) {
    imageData.push({
      path: 'embedded_image',
      base64: match[1],
      name: `嵌入图片${imageData.length + 1}`
    })
  }

  // 方法3: 查找独立的长 base64 字符串
  const standaloneBase64Regex = /^[A-Za-z0-9+/=]{100,}$/gm
  while ((match = standaloneBase64Regex.exec(text)) !== null) {
    // 避免重复添加
    const matchStr = match[0]
    if (!imageData.some(img => img.base64 === matchStr)) {
      imageData.push({
        path: 'standalone_base64',
        base64: matchStr,
        name: `Base64图片${imageData.length + 1}`
      })
    }
  }

  // 已提取图片数据

  return imageData
}

interface MessageListProps {
  messages: Message[]
  onRegenerate?: (messageId: string) => void
}

interface MessageItemProps {
  message: Message
  onRegenerate?: (messageId: string) => void
}

// 从 Markdown 表格提取数据并转换为 CSV
const extractTableDataFromMarkdown = (markdown: string): string[][] | null => {
  const lines = markdown.split('\n')
  const tableLines: string[] = []
  let inTable = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      // 跳过分隔行 (如 |---|---|)
      if (!/^\|[\s\-:]+\|$/.test(trimmed)) {
        inTable = true
        tableLines.push(trimmed)
      }
    } else if (inTable) {
      break // 表格结束
    }
  }

  if (tableLines.length === 0) return null

  // 解析表格数据
  const tableData = tableLines.map(line => {
    return line
      .split('|')
      .slice(1, -1) // 移除首尾的空字符串
      .map(cell => cell.trim())
  })

  return tableData
}

// 将表格数据转换为 CSV 格式
const convertTableToCSV = (tableData: string[][]): string => {
  return tableData
    .map(row =>
      row.map(cell => {
        // 如果单元格包含逗号、引号或换行符，需要用引号包裹
        if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
          return `"${cell.replace(/"/g, '""')}"`
        }
        return cell
      }).join(',')
    )
    .join('\n')
}

const MessageItem: React.FC<MessageItemProps> = React.memo(({ message, onRegenerate }) => {
  const isUser = message.role === 'user'
  const {
    setCurrentStructure,
    setCurrentSessionStructures
  } = useAppStore()

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      toast.success('已复制到剪贴板')
    } catch (error) {
      toast.error('复制失败')
    }
  }

  const handleDownloadTable = () => {
    try {
      const tableData = extractTableDataFromMarkdown(message.content)
      if (!tableData) {
        toast.error('未找到表格数据')
        return
      }

      const csv = convertTableToCSV(tableData)
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      downloadFile(csv, `table_${timestamp}.csv`, 'text/csv;charset=utf-8;')
      toast.success('表格已下载')
    } catch (error) {
      console.error('下载表格失败:', error)
      toast.error('下载表格失败')
    }
  }

  const handleLike = () => {
    toast.success('感谢您的反馈')
  }

  const handleDislike = () => {
    toast.success('感谢您的反馈，我们会持续改进')
  }

  const handleRegenerate = () => {
    if (onRegenerate) {
      onRegenerate(message.id)
    } else {
      toast('重新生成功能开发中...', { icon: 'ℹ️' })
    }
  }

  // 检测消息中是否包含表格
  const hasTable = message.content.includes('|') && message.content.split('\n').some(line =>
    line.trim().startsWith('|') && line.trim().endsWith('|')
  )

  // 检测并提取结构数据
  useEffect(() => {
    if (isUser) return

    // 方法1: 从 metadata 中获取结构数据
    if (message.metadata?.structureData) {
      setCurrentStructure(message.metadata.structureData)
      setCurrentSessionStructures([message.metadata.structureData])  // 使用数组替换而不是追加
      toast.success('已加载晶体结构到3D视图')
      return
    }

    // 方法2: 从消息内容中解析结构数据
    if (hasStructureData(message.content)) {
      // 尝试解析多个 CIF 结构（数据库查询可能返回多个结构）
      const cifBlocks = extractCIFBlocks(message.content)

      if (cifBlocks.length > 1) {
        // 多个结构：添加到列表
        const structures = cifBlocks
          .map((cif, index) => {
            const structure = smartParseStructure(cif, { database: detectDatabaseFromMessage(message.content) })
            if (structure) {
              // 确保每个结构有唯一的ID
              structure.id = `${structure.id || 'structure'}_${index}_${Date.now()}`
            }
            return structure
          })
          .filter(s => s !== null) as CrystalStructure[]

        // 去重：基于多个特征的严格去重
        const uniqueStructures = structures.filter((structure, index, arr) => {
          return arr.findIndex(s => {
            // 1. 检查化学式
            if (s.formula !== structure.formula) return false

            // 2. 检查空间群（如果存在）
            if (s.spaceGroup && structure.spaceGroup && s.spaceGroup !== structure.spaceGroup) {
              return false
            }

            // 3. 检查晶格参数（如果存在）
            if (s.latticeParameters && structure.latticeParameters) {
              const threshold = 0.001  // 严格的阈值
              const aMatch = Math.abs(s.latticeParameters.a - structure.latticeParameters.a) < threshold
              const bMatch = Math.abs(s.latticeParameters.b - structure.latticeParameters.b) < threshold
              const cMatch = Math.abs(s.latticeParameters.c - structure.latticeParameters.c) < threshold

              if (!aMatch || !bMatch || !cMatch) return false
            }

            // 4. 检查原子数
            if (s.atoms?.length !== structure.atoms?.length) return false

            // 5. 检查体积（如果存在）
            if (s.properties?.volume && structure.properties?.volume) {
              const volumeThreshold = 0.01
              if (Math.abs(s.properties.volume - structure.properties.volume) > volumeThreshold) {
                return false
              }
            }

            return true
          }) === index
        })

        if (uniqueStructures.length > 0) {
          // 为每个结构添加消息来源标识
          const structuresWithSource = uniqueStructures.map(structure => ({
            ...structure,
            messageId: message.id,
            timestamp: Date.now()
          }))

          setCurrentSessionStructures(structuresWithSource)
          setCurrentStructure(structuresWithSource[0])
          toast.success(`已加载 ${structuresWithSource.length} 个晶体结构到3D视图`)
        }
      } else {
        // 单个结构：直接加载
        const structure = smartParseStructure(message.content, { database: detectDatabaseFromMessage(message.content) })
        if (structure) {
          // 确保结构有唯一ID和消息来源
          const structureWithSource = {
            ...structure,
            id: `${structure.id || 'structure'}_${Date.now()}`,
            metadata: {
              ...structure.metadata,
              messageId: message.id,
              timestamp: Date.now()
            }
          }

          setCurrentStructure(structureWithSource)
          setCurrentSessionStructures([structureWithSource])  // 使用数组替换而不是追加
          toast.success(`已加载 ${structureWithSource.formula} 晶体结构到3D视图`)
        }
      }
    }
  }, [message, isUser, setCurrentStructure, setCurrentSessionStructures])

  // 🆕 如果是工具执行消息，使用专门的工具执行卡片组件
  if (message.type === 'tool_execution' && message.toolExecution) {
    return (
      <div className="flex justify-center mb-6">
        <div className="w-full max-w-[80%]">
          <ToolExecutionCard
            toolName={message.toolExecution.toolName}
            input={message.toolExecution.input}
            output={message.toolExecution.output}
            status={message.toolExecution.status}
            timestamp={ensureValidTimestamp(message.timestamp).toISOString()}
            error={message.toolExecution.error}
          />
        </div>
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* 头像 */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-9 h-9 rounded-full flex items-center justify-center shadow-lg transform transition-transform hover:scale-105 ${isUser
            ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white ring-2 ring-white/20'
            : 'bg-gradient-to-br from-white to-gray-100 text-primary-600 border border-white/50'
            }`}>
            {isUser ? (
              <User className="w-5 h-5" />
            ) : (
              <Bot className="w-5 h-5" />
            )}
          </div>
        </div>

        {/* 消息内容 */}
        <div className={`flex-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {/* 消息头部信息 */}
          <div className={`flex items-center mb-1 text-xs text-gray-500 ${isUser ? 'justify-end' : 'justify-start'
            }`}>
            <span>
              {isUser ? '你' : (message.agentName || '智能体')}
            </span>
            <span className="mx-1">•</span>
            <span>
              {formatDistanceToNow(ensureValidTimestamp(message.timestamp), {
                addSuffix: true,
                locale: zhCN
              })}
            </span>
          </div>

          {/* 消息气泡 */}
          <div className={`relative rounded-2xl px-5 py-4 shadow-sm transition-all ${isUser
            ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-primary-500/20 rounded-tr-sm'
            : 'bg-white/80 backdrop-blur-md border border-slate-200/50 text-slate-800 shadow-sm rounded-tl-sm'
            }`}>
            {/* 消息内容 */}
            <div className="prose prose-sm max-w-none">
              {isUser ? (
                <div className="whitespace-pre-wrap">{message.content}</div>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, className, children, ...props }: any) {
                      const inline = !className
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={tomorrow as any}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-md"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      )
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>

            {/* Tool Calls 显示 */}
            {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
              <ToolCallsDisplay toolCalls={message.toolCalls} />
            )}

            {/* 简化的晶体结构提示 */}
            {message.metadata?.structureData && (
              <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center text-sm text-blue-700">
                  <Bot className="w-4 h-4 mr-2" />
                  已生成晶体结构：{message.metadata.structureData.formula}，请查看右侧3D视图
                </div>
              </div>
            )}

            {/* 计算结果图片展示（受 uiConfig.showFilesInChat 控制） */}
            {(() => {
              // 🔧 从 store 获取配置
              const showFilesInChat = useAppStore.getState().uiConfig.showFilesInChat

              // 如果配置为不显示，则跳过
              if (!showFilesInChat) {
                return null
              }

              // 从消息内容和metadata中提取图片数据
              let imageData = extractImageData(message.content)

              // 检查metadata中是否有图片数据
              if (message.metadata?.images && Array.isArray(message.metadata.images)) {
                imageData = [...imageData, ...message.metadata.images]
              }

              if (imageData.length === 0) return null

              return (
                <div className="mt-3">
                  <div className="text-sm font-medium text-gray-700 mb-2">
                    计算结果图片
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {imageData.map((image, index) => {
                      // 使用原始文件名（去除扩展名）
                      let displayName = image.name.replace(/\.(png|jpg|jpeg)$/i, '')

                      return (
                        <div key={index} className="bg-white/50 backdrop-blur-sm border border-white/40 rounded-lg p-3 shadow-sm">
                          <div className="text-sm font-medium text-gray-700 mb-2">
                            {displayName}
                          </div>
                          <img
                            src={
                              (image as any).url           // 优先使用完整URL（已通过 resolveFileUrl 处理）
                                ? resolveFileUrl((image as any).url)
                                : image.base64              // base64格式
                                  ? `data:image/png;base64,${image.base64}`
                                  : image.path                // 路径格式
                                    ? resolveFileUrl(`/images/${image.path}`)
                                    : ''
                            }
                            alt={displayName}
                            className="h-auto rounded border"
                            style={{
                              width: '60%',           // 图片宽度为对话框的 60%
                              maxWidth: '100%',       // 不超过容器宽度
                              objectFit: 'contain'    // 保持宽高比
                            }}
                            onError={(e) => {
                              console.error('Failed to load image:', image.path || (image as any).url)
                              const target = e.target as HTMLImageElement
                              target.style.display = 'none'
                            }}
                          />
                          <div className="mt-2 flex items-center space-x-2">
                            <button
                              onClick={async () => {
                                try {
                                  const srcUrl = (image as any).url
                                    ? resolveFileUrl((image as any).url)
                                    : image.path
                                      ? resolveFileUrl(`/images/${image.path}`)
                                      : ''
                                  if (!srcUrl && !image.base64) {
                                    toast.error('没有可下载的图片')
                                    return
                                  }
                                  if (image.base64) {
                                    await downloadFile(`data:image/png;base64,${image.base64}`, (image.name || `image_${index + 1}.png`))
                                  } else {
                                    // 使用 <a> 标签下载，避免 CORS 问题
                                    const a = document.createElement('a')
                                    a.href = srcUrl
                                    a.download = image.name || `image_${index + 1}.png`
                                    a.target = '_blank'
                                    document.body.appendChild(a)
                                    a.click()
                                    document.body.removeChild(a)
                                  }
                                  toast.success('图片已下载')
                                } catch (err) {
                                  console.error('下载图片失败:', err)
                                  toast.error('下载失败，请稍后重试')
                                }
                              }}
                              className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-500"
                            >
                              下载
                            </button>
                            <button
                              onClick={async () => {
                                // 优先使用后端提供的 url；否则根据类型和文件名构造
                                const buildUrl = () => {
                                  const rawUrl = (image as any).url
                                  if (rawUrl && typeof rawUrl === 'string') {
                                    return resolveFileUrl(rawUrl)
                                  }
                                  const rawPath = (image as any).path as string | undefined
                                  const filename = (image as any).filename || (rawPath ? rawPath.split(/[/\\]/).pop() : undefined)
                                  if (!filename) return ''
                                  const t = String((image as any).type || '').toLowerCase()
                                  const kind = t.includes('phonon')
                                    ? 'phonon'
                                    : t.includes('generated') || t.includes('structure')
                                      ? 'generated_structures'
                                      : 'images'
                                  return resolveFileUrl(`/images/${kind}/${filename}`)
                                }
                                const srcUrl = buildUrl()
                                if (!srcUrl || !srcUrl.trim()) {
                                  toast.error('没有可复制的链接')
                                  return
                                }
                                const success = await copyToClipboard(srcUrl)
                                if (success) {
                                  toast.success('链接已复制到剪贴板')
                                } else {
                                  // 最终兜底：显示可复制提示框
                                  const manual = window.prompt('复制此链接到剪贴板', srcUrl)
                                  if (manual !== null) {
                                    toast('请使用 Ctrl+C 复制链接', { icon: 'ℹ️' })
                                  }
                                }
                              }}
                              className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                            >
                              复制链接
                            </button>
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {(image.path || (image as any).url || image.name || 'unknown').split(/[/\\]/).pop()}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })()}

            {/* 引用信息 */}
            {message.metadata?.citations && message.metadata.citations.length > 0 && (
              <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                <div className="text-sm font-medium text-blue-700 mb-2">
                  参考文献
                </div>
                <div className="space-y-1">
                  {message.metadata.citations.map((citation, index) => (
                    <div key={index} className="text-sm text-blue-600">
                      <span className="font-medium">{citation.title}</span>
                      <span className="text-blue-500 ml-2">
                        {citation.authors.join(', ')} ({citation.year})
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* CSV和Markdown文件展示（受 uiConfig.showFilesInChat 控制） */}
            {(() => {
              // 🔧 从 store 获取配置
              const showFilesInChat = useAppStore.getState().uiConfig.showFilesInChat

              console.log('📄 MessageItem - message.metadata:', message.metadata)
              console.log('📄 MessageItem - showFilesInChat:', showFilesInChat)

              const fileLinks = extractFileLinks(message.content, message.metadata)
              console.log('📄 MessageItem - fileLinks:', fileLinks)

              // 如果配置为不显示，则跳过
              if (!showFilesInChat) {
                console.log('📄 MessageItem - files hidden by config')
                return null
              }

              if (fileLinks.length === 0) {
                console.log('📄 MessageItem - no file links found')
                return null
              }

              console.log('📄 MessageItem - rendering', fileLinks.length, 'file links')
              return (
                <div className="mt-3 space-y-3">
                  {fileLinks.map((file, index) => (
                    <div key={index}>
                      {file.type === 'csv' ? (
                        <CsvViewer
                          url={file.url}
                          filename={file.filename}
                          inlineContent={file.content}
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
              )
            })()}
          </div>

          {/* 计费信息徽章 */}
          {(() => {
            const shouldShow = !isUser && message.billing && (message.billing.tokens || 0) > 0
            console.log('💎 [MessageBillingBadge] 消息:', message.id, '是否显示:', shouldShow, 'billing:', message.billing)
            return shouldShow ? (
              <MessageBillingBadge
                tokens={message.billing?.tokens}
                photons={message.billing?.photons}
                modelName={message.billing?.model_name}
                compact={true}
              />
            ) : null
          })()}

          {/* 操作按钮 */}
          <div className={`flex items-center mt-2 space-x-2 ${isUser ? 'justify-end' : ''}`}>
            {/* 复制按钮 - 双方都显示 */}
            <button
              onClick={handleCopy}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
              title="复制消息"
            >
              <Copy className="w-3 h-3" />
            </button>

            {/* 表格下载 - 仅当有表格时显示 */}
            {hasTable && (
              <button
                onClick={handleDownloadTable}
                className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="下载表格"
              >
                <Download className="w-3 h-3" />
              </button>
            )}

            {/* 仅智能体消息显示的按钮 */}
            {!isUser && (
              <>
                <button
                  onClick={handleLike}
                  className="p-1 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                  title="有用"
                >
                  <ThumbsUp className="w-3 h-3" />
                </button>
                <button
                  onClick={handleDislike}
                  className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="无用"
                >
                  <ThumbsDown className="w-3 h-3" />
                </button>
                <button
                  onClick={handleRegenerate}
                  className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  title="重新生成"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  // 🔧 优化：自定义比较函数，防止不必要的重新渲染
  return prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.role === nextProps.message.role &&
    prevProps.onRegenerate === nextProps.onRegenerate
})

interface LoadingMessageProps {
  message?: string
}

const LoadingMessage: React.FC<LoadingMessageProps> = ({ message = '⏳ 智能体正在思考...' }) => {
  const [seconds, setSeconds] = useState(0)
  const [showWarning, setShowWarning] = useState(false)

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds(prev => {
        const next = prev + 1
        // 超过120秒显示提示
        if (next >= 90) setShowWarning(true)
        return next
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  // 根据消息内容生成更友好的辅助提示
  const getHelpText = () => {
    const lowerMsg = message.toLowerCase()
    if (lowerMsg.includes('搜索')) return '🔍 正在搜索相关文献...'
    if (lowerMsg.includes('分析')) return '📊 正在分析数据...'
    if (lowerMsg.includes('生成')) return '✨ 正在生成结果...'
    if (lowerMsg.includes('计算')) return '🧮 正在进行计算...'
    if (lowerMsg.includes('弛豫')) return '🔄 正在进行结构弛豫...'
    if (lowerMsg.includes('声子')) return '🎵 正在计算声子谱...'
    if (lowerMsg.includes('报告')) return '📝 正在生成研究报告...'
    if (lowerMsg.includes('工具')) return '🛠️ 正在调用工具...'
    if (lowerMsg.includes('连接')) return '🔌 正在建立连接...'
    if (lowerMsg.includes('上传')) return '📤 正在上传文件...'
    return '⏳ 后端正在处理，请稍候...'
  }

  // 格式化时间显示
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m > 0 ? `${m}分` : ''}${s}秒`
  }

  return (
    <div className="flex justify-start mb-6">
      <div className="flex max-w-[80%]">
        {/* 头像 */}
        <div className="flex-shrink-0 mr-3">
          <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center animate-pulse">
            <Bot className="w-4 h-4" />
          </div>
        </div>

        {/* 加载动画 */}
        <div className="flex-1">
          <div className="bg-gradient-to-r from-primary-50 to-blue-50 border-2 border-primary-200 shadow-md rounded-lg px-4 py-3">
            <div className="flex flex-col space-y-2">
              {/* 主提示信息 */}
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-primary-700">{message}</span>
                  {seconds > 5 && (
                    <span className="text-xs text-primary-400 mt-0.5">已耗时: {formatTime(seconds)}</span>
                  )}
                </div>
              </div>

              {/* 进度条 */}
              <div className="w-full bg-primary-100 rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-primary-500 rounded-full animate-pulse" style={{ width: '60%' }}></div>
              </div>

              {/* 辅助提示 - 根据消息内容动态显示 */}
              <div className="text-xs text-primary-600 flex items-center space-x-1">
                <svg className="w-3 h-3 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>{getHelpText()}</span>
              </div>

              {/* 提示信息 - 仅在超时后显示 */}
              {showWarning && (
                <div className="text-xs text-orange-500 mt-1 animate-fade-in bg-orange-50 p-1.5 rounded border border-orange-100">
                  <div className="font-semibold mb-0.5">⚠️ 响应时间较长</div>
                  <div>如果长时间未完成，建议：</div>
                  <ul className="list-disc list-inside ml-1 text-orange-600/80">
                    <li>检查网络连接是否正常</li>
                    <li>如果是复杂任务（如生成报告，声子谱计算，结构生成），请耐心等待</li>
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const MessageList: React.FC<MessageListProps> = React.memo(({ messages, onRegenerate }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { isLoading, loadingMessage } = useAppStore()

  // 调试：监听消息变化
  useEffect(() => {
    console.log('📋 MessageList - messages updated:', messages.length, 'messages')
    messages.forEach(msg => {
      if (msg.metadata?.csv_download_url || msg.metadata?.md_download_url) {
        console.log('📋 Message with file metadata:', {
          id: msg.id,
          role: msg.role,
          csv: msg.metadata?.csv_download_url,
          md: msg.metadata?.md_download_url
        })
      }
    })
  }, [messages])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="max-w-4xl mx-auto p-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Bot className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium mb-2">开始新对话</h3>
              <p className="text-sm">
                选择一个智能体，然后输入您的问题开始对话
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageItem key={message.id} message={message} onRegenerate={onRegenerate} />
            ))}
            {isLoading && <LoadingMessage message={loadingMessage} />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
    </div>
  )
})

/**
 * 从消息内容中检测数据库来源
 */
function detectDatabaseFromMessage(content: string): string | undefined {
  const lowerContent = content.toLowerCase()

  if (lowerContent.includes('materials project') || lowerContent.includes('mp-')) {
    return 'MP'
  }
  if (lowerContent.includes('oqmd') || lowerContent.includes('open quantum')) {
    return 'OQMD'
  }
  if (lowerContent.includes('crystallography open database') || lowerContent.includes('cod')) {
    return 'COD'
  }
  if (lowerContent.includes('aflow') || lowerContent.includes('automatic flow')) {
    return 'AFLOW'
  }
  if (lowerContent.includes('generated') || lowerContent.includes('crystallm')) {
    return 'Generated'
  }

  return undefined
}

export default MessageList
