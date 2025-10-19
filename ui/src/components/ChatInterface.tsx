import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic, Square, X } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { wsService } from '../services/websocket'
import MessageList from './MessageList'
import toast from 'react-hot-toast'
import { APP_CONFIG } from '../constants'
import { parseCIF as localParseCIF, isValidCIF } from '../utils/cifParser'
import { parseCIF as apiParseCIF, checkAPIHealth } from '../utils/apiClient'

const ChatInterface: React.FC = () => {
  const {
    messages,
    currentAgent,
    currentSession,
    addMessage,
    connected,
    createSession,
    setCurrentSession,
    setCurrentStructure,
    clearCurrentSessionStructures,
    addToCurrentSessionStructures,
    isLoading,
    setIsLoading,
    loadingMessage,
    setLoadingMessage
  } = useAppStore()
  
  const [inputValue, setInputValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [inputValue])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentAgent || !connected) {
      if (!connected) {
        toast.error('❌ 未连接到服务器，请检查后端服务是否正在运行')
      } else if (!currentAgent) {
        toast.error('⚠️ 请先选择一个智能体')
      }
      return
    }

    const messageContent = inputValue.trim()
    setInputValue('')

    // 只在没有上传文件的情况下清除结构数据，避免清除刚上传的CIF结构
    // clearCurrentSessionStructures() - 注释掉，改为由具体场景控制

    // 如果没有当前会话，创建一个新会话
    let sessionToUse = currentSession
    if (!sessionToUse && currentAgent) {
      sessionToUse = createSession('新对话', currentAgent.id)
      setCurrentSession(sessionToUse)
      console.log('发送消息时自动创建会话:', sessionToUse.id)
    }

    // 添加用户消息
    const userMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content: messageContent,
      role: 'user' as const,
      timestamp: new Date(),
    }
    addMessage(userMessage)

    // 立即显示加载提示，提供即时反馈
    setIsLoading(true)
    setLoadingMessage(`⏳ ${currentAgent?.name || '智能体'} 正在处理您的请求...`)

    // 显示toast提示
    toast.loading(`正在发送消息到 ${currentAgent?.name}...`, {
      id: 'send-message-toast',
    })

    try {
      // 通过WebSocket发送消息
      wsService.sendMessage(
        messageContent,
        currentAgent.id,
        sessionToUse?.id
      )

      // 消息发送成功后，更新toast
      toast.success('✅ 消息已发送，等待响应...', {
        id: 'send-message-toast',
      })
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('❌ 发送消息失败，请重试', {
        id: 'send-message-toast',
      })
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (uploadedFile) {
        handleSendWithFile()
      } else {
        handleSendMessage()
      }
    }
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // 检查文件大小
    if (file.size > APP_CONFIG.MAX_FILE_SIZE) {
      toast.error(`文件大小超过限制 (最大 ${APP_CONFIG.MAX_FILE_SIZE / 1024 / 1024}MB)`)
      return
    }

    // 检查文件类型
    const fileExt = ('.' + file.name.split('.').pop()?.toLowerCase()) as typeof APP_CONFIG.SUPPORTED_FILE_TYPES[number]
    if (!APP_CONFIG.SUPPORTED_FILE_TYPES.includes(fileExt)) {
      toast.error(`不支持的文件类型。支持的类型: ${APP_CONFIG.SUPPORTED_FILE_TYPES.join(', ')}`)
      return
    }

    setUploadedFile(file)
    toast.success(`已选择文件: ${file.name}`)
  }

  const handleRemoveFile = () => {
    setUploadedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSendWithFile = async () => {
    if (!uploadedFile) {
      handleSendMessage()
      return
    }

    // 立即显示loading状态，提供即时反馈
    if (currentAgent) {
      setIsLoading(true)
      setLoadingMessage(`${currentAgent.name} 正在处理数据...`)
    }

    // 读取文件内容
    const reader = new FileReader()
    reader.onload = async (e) => {
      const fileContent = e.target?.result as string

      // 检查是否是 CIF 文件
      const isCIF = uploadedFile.name.toLowerCase().endsWith('.cif')
      if (isCIF && isValidCIF(fileContent)) {
        // 解析 CIF 文件 (优先使用 API)
        try {
          const apiAvailable = await checkAPIHealth()
          let structure = null

          if (apiAvailable) {
            // 使用 API 解析 (原胞)
            console.log('使用 API 解析 CIF 文件 (原胞)')
            structure = await apiParseCIF(fileContent)

            // 同时获取惯胞数据,保存到 metadata
            console.log('获取惯胞数据')
            const conventionalStructure = await apiParseCIF(fileContent, true)

            if (structure && conventionalStructure) {
              // 标记为上传的结构
              structure.source = {
                database: 'Upload',  // 标记为用户上传
                materialId: structure.id,
                retrievedAt: new Date()
              }

              // 保存 CIF 内容（统一使用 cifContent）
              structure.cifContent = fileContent
              structure.metadata = {
                ...structure.metadata,
                conventionalStructure: conventionalStructure  // 保存惯胞数据
              }
            }
          } else {
            // 回退到本地解析
            console.log('API 不可用,使用本地方法解析 CIF 文件')
            structure = localParseCIF(fileContent)

            if (structure) {
              // 标记为上传的结构
              structure.source = {
                database: 'Upload',  // 标记为用户上传
                materialId: structure.id,
                retrievedAt: new Date()
              }

              // 统一使用 cifContent 字段
              structure.cifContent = fileContent
            }
          }

          if (structure) {
            // 更新 3D 视图
            setCurrentStructure(structure)

            // 添加到当前会话结构列表
            addToCurrentSessionStructures(structure)

            toast.success(`已加载 ${structure.formula} 晶体结构到3D视图`)
          } else {
            toast.error('CIF 文件解析失败')
          }
        } catch (error) {
          console.error('CIF 解析失败:', error)
          toast.error('CIF 文件解析失败')
        }
      }

      // 构建包含文件信息的消息
      const messageWithFile = `${inputValue}\n\n[附件: ${uploadedFile.name}]\n\`\`\`\n${fileContent.substring(0, 1000)}${fileContent.length > 1000 ? '...' : ''}\n\`\`\``

      // 发送消息
      const messageContent = inputValue.trim() || `已上传文件: ${uploadedFile.name}`
      setInputValue('')
      setUploadedFile(null)

      // 如果没有当前会话，创建一个新会话
      let sessionToUse = currentSession
      if (!sessionToUse && currentAgent) {
        sessionToUse = createSession('新对话', currentAgent.id)
        setCurrentSession(sessionToUse)
      }

      // 添加用户消息
      const userMessage = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        content: messageWithFile,
        role: 'user' as const,
        timestamp: new Date(),
      }
      addMessage(userMessage)

      try {
        // 通过WebSocket发送消息（包含文件内容）
        wsService.sendMessage(
          `${messageContent}\n\n[文件内容]\n${fileContent}`,
          currentAgent?.id || '',
          sessionToUse?.id
        )
      } catch (error) {
        console.error('Failed to send message with file:', error)
        toast.error('发送消息失败')
        setIsLoading(false)
      }
    }

    reader.onerror = () => {
      toast.error('读取文件失败')
    }

    reader.readAsText(uploadedFile)
  }

  const toggleRecording = () => {
    if (isRecording) {
      // TODO: 停止录音
      setIsRecording(false)
      toast.success('录音已停止')
    } else {
      // TODO: 开始录音
      setIsRecording(true)
      toast.success('开始录音...')
    }
  }

  // 监听WebSocket消息完成，停止loading状态
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage.role === 'assistant') {
        setIsLoading(false)
      }
    }
  }, [messages])

  // 重新生成消息
  const handleRegenerate = async (messageId: string) => {
    if (!currentAgent || !connected || !currentSession) {
      toast.error('无法重新生成：未连接或未选择会话')
      return
    }

    // 找到要重新生成的消息
    const messageIndex = messages.findIndex(msg => msg.id === messageId)
    if (messageIndex === -1 || messages[messageIndex].role !== 'assistant') {
      toast.error('无法重新生成此消息')
      return
    }

    // 找到对应的用户消息（应该在 assistant 消息之前）
    let userMessageContent = ''
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        userMessageContent = messages[i].content
        break
      }
    }

    if (!userMessageContent) {
      toast.error('未找到对应的用户消息')
      return
    }

    setIsLoading(true)
    toast('正在重新生成...', { icon: 'ℹ️' })

    try {
      // 通过WebSocket重新发送消息
      wsService.sendMessage(
        userMessageContent,
        currentAgent.id,
        currentSession.id
      )
    } catch (error) {
      console.error('Failed to regenerate message:', error)
      toast.error('重新生成失败')
      setIsLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* 消息列表 */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages} onRegenerate={handleRegenerate} />
      </div>

      {/* 输入区域 */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="max-w-4xl mx-auto">
          {/* 文件上传提示 */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept=".txt,.pdf,.doc,.docx,.cif,.xyz,.pdb"
          />

          {/* 已上传文件显示 */}
          {uploadedFile && (
            <div className="mb-2 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
              <div className="flex items-center space-x-2">
                <Paperclip className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-900">{uploadedFile.name}</span>
                <span className="text-xs text-blue-600">
                  ({(uploadedFile.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <button
                onClick={handleRemoveFile}
                className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                title="移除文件"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* 输入框容器 */}
          <div className="relative flex items-end space-x-3">
            {/* 附件按钮 */}
            <button
              onClick={handleFileUpload}
              className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="上传文件"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            {/* 输入框 */}
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  currentAgent 
                    ? `向 ${currentAgent.name} 发送消息...` 
                    : '请先选择智能体...'
                }
                className="w-full resize-none border border-gray-300 rounded-lg px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent max-h-32 scrollbar-thin"
                rows={1}
                disabled={!currentAgent || !connected}
              />
              
              {/* 发送按钮 */}
              <button
                onClick={uploadedFile ? handleSendWithFile : handleSendMessage}
                disabled={(!inputValue.trim() && !uploadedFile) || !currentAgent || !connected || isLoading}
                className="absolute right-2 bottom-2 p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title={uploadedFile ? "发送消息和文件 (Enter)" : "发送消息 (Enter)"}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* 语音按钮 */}
            <button
              onClick={toggleRecording}
              className={`flex-shrink-0 p-2 rounded-lg transition-colors ${
                isRecording 
                  ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                  : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
              }`}
              title={isRecording ? '停止录音' : '开始录音'}
            >
              {isRecording ? (
                <Square className="w-5 h-5" />
              ) : (
                <Mic className="w-5 h-5" />
              )}
            </button>
          </div>

          {/* 提示信息 */}
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <div className="flex items-center space-x-4">
              <span>按 Enter 发送，Shift + Enter 换行</span>
              {!connected && (
                <span className="text-red-500">● 未连接到服务器</span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              {currentAgent && (
                <span className="text-primary-600">
                  当前: {currentAgent.name}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface