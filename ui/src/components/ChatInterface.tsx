import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic, Square, X, Copy } from 'lucide-react'
import toast from 'react-hot-toast'

import MessageList from './MessageList'
import { useAppStore } from '../store/useAppStore'
import { wsService } from '../services/websocket'
import { APP_CONFIG, API_CONFIG } from '../constants'
import { parseCIF as apiParseCIF, checkAPIHealthSafe as checkAPIHealth, resolveFileUrl } from '../utils/apiClient'
import { copyToClipboard } from '../utils'

const ChatInterface: React.FC = () => {
  const {
    messages,
    currentAgent,
    currentSession,
    currentStructure,
    sessions,
    addMessage,
    connected,
    createSession,
    setCurrentSession,
    setCurrentStructure,
    addToCurrentSessionStructures,
    addToCurrentSessionFiles,
    isLoading,
    setIsLoading,
    loadingMessage,
    setLoadingMessage,
  } = useAppStore()

  const [inputValue, setInputValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[] | null>(null)
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
        toast.error('未连接到服务器，请检查后端服务是否正在运行')
      } else if (!currentAgent) {
        toast.error('⚠️ 请先选择一个智能体')
      }
      return
    }

    const messageContent = inputValue.trim()
    setInputValue('')

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
    setLoadingMessage(`${currentAgent?.name || '智能体'} 正在处理您的请求...`)

    // 显示 toast 提示
    toast.loading(`正在发送消息到 ${currentAgent?.name}...`, {
      id: 'send-message-toast',
    })

    try {
      // 如果是声子计算意图，且当前存在结构的 CIF 内容，则携带附件发送
      const isPhononIntent = /声子|phonon/i.test(messageContent)
      const cif = (currentStructure as any)?.cifContent
      if (isPhononIntent && cif) {
        wsService.sendChatWithAttachments({
          content: messageContent,
          agentId: currentAgent.id,
          sessionId: sessionToUse?.id,
          attachments: [
            { filename: `${(currentStructure as any)?.formula || 'structure'}.cif`, content: cif }
          ],
        })
      } else {
        // 通过 WebSocket 发送普通文本消息
        wsService.sendMessage(
          messageContent,
          currentAgent.id,
          sessionToUse?.id
        )
      }

      // 消息发送成功后，更新 toast
      toast.success('消息已发送，等待响应...', {
        id: 'send-message-toast',
      })
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('发送消息失败，请重试', {
        id: 'send-message-toast',
      })
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (uploadedFiles && uploadedFiles.length > 0) {
        handleSendWithFile()
      } else {
        handleSendMessage()
      }
    }
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const handleCopyInput = async () => {
    if (!inputValue.trim()) {
      toast.error('没有可复制的内容')
      return
    }

    const success = await copyToClipboard(inputValue)
    if (success) {
      toast.success('输入内容已复制')
    } else {
      toast.error('复制失败，请手动选择文本')
    }
  }

  // 简化文件选择判定，避免禁用按钮的条件判断出错
  const hasFiles = (uploadedFiles?.length || 0) > 0

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    const selected: File[] = []
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i]
      if (f.size > APP_CONFIG.MAX_FILE_SIZE) {
        toast.error(`文件大小超过限制，已跳过: ${f.name}`)
        continue
      }
      selected.push(f)
    }

    if (selected.length === 0) return
    setUploadedFiles(selected)
    toast.success(selected.length === 1 ? `已选择文件: ${selected[0].name}` : `已选择 ${selected.length} 个文件`)
  }

  const handleRemoveFile = () => {
    setUploadedFiles(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSendWithFile = async () => {
    if (!uploadedFiles || uploadedFiles.length === 0) {
      handleSendMessage()
      return
    }

    // 立即显示 loading 状态，提供即时反馈
    if (currentAgent) {
      setIsLoading(true)
      setLoadingMessage(`${currentAgent.name} 正在处理数据...`)
    }

    // 确保存在会话用于发送
    let sessionToUse = currentSession
    if (!sessionToUse && currentAgent) {
      // 优先复用当前智能体的最近会话，避免丢失上下文
      const lastForAgent = [...(sessions || [])].reverse().find(s => s.agentId === currentAgent.id)
      if (lastForAgent) {
        sessionToUse = lastForAgent
        setCurrentSession(lastForAgent)
        console.log('复用现有会话:', lastForAgent.id)
      } else {
        sessionToUse = createSession('新对话', currentAgent.id)
        setCurrentSession(sessionToUse)
        console.log('发送附件时自动创建会话:', sessionToUse.id)
      }
    }
    // 清空输入框并在聊天中显示用户消息（仅当有文字输入时）
    const pendingUserText = (inputValue || '').trim()
    if (pendingUserText) {
      addMessage({
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        content: pendingUserText,
        role: 'user' as const,
        timestamp: new Date(),
      })
    }
    setInputValue('')

    // 如果包含非 CIF 文件，根据当前 agent 决定处理方式
    const hasNonCif = uploadedFiles.some(f => !f.name.toLowerCase().endsWith('.cif'))
    if (hasNonCif) {
      const nonCifFiles = uploadedFiles.filter(f => !f.name.toLowerCase().endsWith('.cif'))

      // 如果是 deep_research_agent，通过 WebSocket 发送文件内容给 agent 处理
      if (currentAgent?.id === 'deep_research_agent') {
        try {
          // 读取文件内容并转换为 base64
          const fileAttachments: Array<{ filename: string; content: string; encoding: string; mime_type: string }> = []

          for (const file of nonCifFiles) {
            const arrayBuffer = await file.arrayBuffer()
            const base64 = btoa(
              new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
            )
            fileAttachments.push({
              filename: file.name,
              content: base64,
              encoding: 'base64',
              mime_type: file.type || 'application/octet-stream'
            })
          }

          // 通过 WebSocket 发送文件附件给 agent
          wsService.sendChatWithAttachments({
            content: (pendingUserText || '').trim() || '请分析这些上传的文献文件',
            agentId: currentAgent.id,
            sessionId: (sessionToUse || currentSession)?.id,
            attachments: fileAttachments,
          })

          toast.success(`已上传 ${nonCifFiles.length} 个文件，正在处理...`)
        } catch (err) {
          console.error('文件读取失败:', err)
          toast.error('文件读取失败，请重试')
        } finally {
          setUploadedFiles(null)
          if (fileInputRef.current) fileInputRef.current.value = ''
          setIsLoading(false)
          setLoadingMessage('')
        }
        return
      }

      // 其他 agent 或默认情况：走文档批量上传（服务端提取文本并返回链接）
      try {
        const form = new FormData()
        nonCifFiles.forEach(f => form.append('files', f))

        const uploadUrl = resolveFileUrl('/upload?type=documents')
        const resp = await fetch(uploadUrl, { method: 'POST', body: form })
        if (!resp.ok) {
          const text = await resp.text()
          throw new Error(text || `HTTP ${resp.status}`)
        }

        const data = await resp.json()
        const uploaded = Array.isArray(data.uploaded_files) ? data.uploaded_files : []

        // 推送所有返回的文件到会话文件列表
        uploaded.forEach((it: any) => {
          const lower = (it.filename || '').toLowerCase()
          if (lower.endsWith('.pdf')) return
          const type = lower.endsWith('.md') ? 'md' : lower.endsWith('.csv') ? 'csv' : 'data'
          addToCurrentSessionFiles({
            id: `doc:${it.paper_id || it.filename}`,
            type,
            name: it.filename || 'document',
            downloadUrl: it.download_url,
            filePath: it.file_path,
            createdAt: Date.now(),
            sourceMessageId: undefined,
          })
        })

        if (data.csv_download_url) {
          addToCurrentSessionFiles({
            id: `csv:${Date.now()}`,
            type: 'csv',
            name: data.csv_file_path ? (data.csv_file_path.split('/').pop() || 'uploaded_papers.csv') : 'uploaded_papers.csv',
            downloadUrl: data.csv_download_url,
            filePath: data.csv_file_path,
            createdAt: Date.now(),
            sourceMessageId: undefined,
          })
        }

        // 发送简短提示消息
        addMessage({
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content: `已处理 ${uploadedFiles.length} 个文档，生成可下载链接。`,
          role: 'assistant' as const,
          timestamp: new Date(),
        })
        toast.success(`已处理 ${uploadedFiles.length} 个文档，生成可下载链接`)
      } catch (err) {
        console.error('文档上传处理失败:', err)
        toast.error('文档处理失败，请重试')
      } finally {
        setUploadedFiles(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
        setIsLoading(false)
        setLoadingMessage('')
      }
      return
    }

    // 读取 CIF 文件内容并解析，同时作为附件发送给后端以便Agent处理
    try {
      const apiAvailable = await checkAPIHealth()
      const cifFiles = uploadedFiles.filter(f => f.name.toLowerCase().endsWith('.cif'))

      const attachments: Array<{ filename: string; content: string }> = []
      for (const file of cifFiles) {
        const fileContent = await file.text()
        attachments.push({ filename: file.name, content: fileContent })

        // 本地解析用于3D预览，不阻断发送
        try {
          let structure: any = null
          if (apiAvailable) {
            structure = await apiParseCIF(fileContent)
            const conventionalStructure = await apiParseCIF(fileContent, true)
            if (structure && conventionalStructure) {
              structure.source = {
                database: 'Upload',
                materialId: structure.id,
                retrievedAt: new Date(),
              }
              structure.cifContent = fileContent
              structure.metadata = {
                ...structure.metadata,
                conventionalStructure,
              }
            }
          }
          if (structure) {
            setCurrentStructure(structure)
            addToCurrentSessionStructures(structure)
            toast.success(`已加载结构 ${structure.formula}`)
          }
        } catch (error) {
          console.error('CIF 解析失败:', error)
          toast.error(`CIF 解析失败: ${file.name}`)
        }
      }

      // 将附件随同用户输入内容一起通过 WebSocket 发送到后端
      if (attachments.length > 0 && currentAgent) {
        wsService.sendChatWithAttachments({
          content: (pendingUserText || '').trim() || '请基于所附CIF进行分析',
          agentId: currentAgent.id,
          sessionId: (sessionToUse || currentSession)?.id,
          attachments,
        })
      }
    } finally {
      setUploadedFiles(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      setIsLoading(false)
      setLoadingMessage('')
    }
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

  // 监听 WebSocket 消息完成，停止 loading 状态
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage.role === 'assistant') {
        setIsLoading(false)
      }
    }
  }, [messages, setIsLoading])

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
      // 通过 WebSocket 重新发送消息
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
          {/* 文件上传控件 */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept=".txt,.pdf,.doc,.docx,.cif,.xyz,.pdb"
            multiple
          />

          {/* 已上传文件显示 */}
          {uploadedFiles && uploadedFiles.length > 0 && (
            <div className="mb-2 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
              <div className="flex items-center space-x-2">
                <Paperclip className="w-4 h-4 text-blue-600" />
                {uploadedFiles.length === 1 ? (
                  <>
                    <span className="text-sm text-blue-900">{uploadedFiles[0].name}</span>
                    <span className="text-xs text-blue-600">({(uploadedFiles[0].size / 1024).toFixed(1)} KB)</span>
                  </>
                ) : (
                  <span className="text-sm text-blue-900">{uploadedFiles.length} 个文件</span>
                )}
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
                onClick={hasFiles ? handleSendWithFile : handleSendMessage}
                disabled={(!inputValue.trim() && !hasFiles) || !currentAgent || !connected || isLoading}
                className="absolute right-2 bottom-2 p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title={hasFiles ? '发送消息和文件 (Enter)' : '发送消息 (Enter)'}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* 复制输入内容 */}
            <button
              onClick={handleCopyInput}
              className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="复制当前输入内容"
            >
              <Copy className="w-5 h-5" />
            </button>

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
                <span className="text-red-500">未连接到服务器</span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              {currentAgent && (
                <span className="text-primary-600">当前: {currentAgent.name}</span>
              )}
              {isLoading && (
                <span className="text-gray-400">{loadingMessage}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
