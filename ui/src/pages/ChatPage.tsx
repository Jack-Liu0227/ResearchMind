import React, { useEffect, useRef } from 'react'
import { useAppStore } from '../store/useAppStore'
import { SessionFile, Message } from '../types'
import { wsService } from '../services/websocket'
import ChatInterface from '../components/ChatInterface'
import AgentSelector from '../components/AgentSelector'
import PhononVisualization from '../components/PhononVisualization'
import toast from 'react-hot-toast'
import { smartParseStructure, hasStructureData } from '../utils/structureParser'
import { resolveFileUrl } from '../utils/apiClient'

const ChatPage: React.FC = () => {
  console.log('ChatPage rendering...')

  const {
    currentSession,
    currentAgent,
    setConnected,
    addMessage,
    updateMessage,
    createSession,
    setCurrentSession,
    setAgents,
    setCurrentStructure,
    addToStructureList,
    addToCurrentSessionStructures,
    addToCurrentSessionFiles,
    agents,
    setIsLoading,
    setLoadingMessage,
    phononImages,
    showPhononVisualization,
    setPhononImages,
    setCurrentSessionPhononImages,
    addToCurrentSessionPhononImages,
    setShowPhononVisualization,
    sessions,
    updateBillingData,
    setUserBillingStats,
    setGlobalBillingStats,
    setPapersData,
    messages,
    isLoading,
    setMessages,
    connected
  } = useAppStore()

  const pendingFileMetadataRef = useRef<any[]>([])
  const historyRequestRef = useRef<string | null>(null)

  // 恢复上次会话
  useEffect(() => {
    if (!currentSession && sessions.length > 0) {
      // 尝试从 sessionStorage 获取最后活跃的 session_id
      const lastSessionId = sessionStorage.getItem('last_active_session_id')
      let restoredSession = null

      if (lastSessionId) {
        restoredSession = sessions.find(s => s.id === lastSessionId)
      }

      // 如果没有记录或找不到，则使用最后一个会话
      if (!restoredSession) {
        restoredSession = sessions[sessions.length - 1]
      }

      console.log('🔄 Restoring session:', restoredSession.id)
      setCurrentSession(restoredSession)
    }
  }, [currentSession, sessions, setCurrentSession])

  // 记录当前会话 ID
  useEffect(() => {
    if (currentSession) {
      sessionStorage.setItem('last_active_session_id', currentSession.id)
    }
  }, [currentSession])

  // 🆕 确保连接后加载历史记录（解决刷新页面记录丢失问题）
  useEffect(() => {
    if (connected && currentSession?.id) {
      console.log('🔄 [ChatPage] 连接已建立，请求同步历史记录:', currentSession.id)
      wsService.send({ 
        type: 'get_history', 
        data: { 
          sessionId: currentSession.id,
          agentId: currentAgent?.id || currentSession.agentId
        } 
      })
    }
  }, [connected, currentSession?.id])

  const normalizePath = (input?: string): string | undefined => {
    if (!input) return undefined
    let value = input.trim().replace(/\\/g, '/')
    if (!value) return undefined

    if (value.includes('session_data/')) {
      value = value.split('session_data/')[1]
    } else if (/^[A-Za-z]:\//.test(value)) {
      if (value.includes('/papers/')) {
        value = `papers/${value.split('/papers/')[1]}`
      } else {
        const filename = value.split('/').pop()
        value = filename || value
      }
    }

    return value.replace(/^([./])+/, '')
  }

  const normalizePapersCsvPath = (input?: string): string | undefined => {
    if (!input) return undefined
    let value = input.trim().replace(/\\/g, '/')
    if (!value) return undefined

    if (value.includes('/api/download/')) {
      const parts = value.split('/api/download/')
      if (parts.length > 1) {
        value = parts[1]
      }
    }

    if (value.includes('session_data/')) {
      value = value.split('session_data/')[1]
    }

    if (value.startsWith('api/download/')) {
      value = value.replace(/^api\/download\//, '')
    } else if (value.startsWith('download/')) {
      value = value.replace(/^download\//, '')
    }

    return value.replace(/^([./])+/, '')
  }

  const normalizeDownloadUrl = (rawUrl?: string, filePath?: string): string | undefined => {
    if (rawUrl && rawUrl.trim().length > 0) {
      return resolveFileUrl(rawUrl.trim())
    }
    const normalizedPath = normalizePath(filePath)
    if (normalizedPath) {
      return resolveFileUrl(`/download/${normalizedPath}`)
    }
    return undefined
  }

  const extractFileName = (input?: string, fallback?: string) => {
    if (!input) return fallback || '数据文件'
    const clean = input.split('?')[0]
    const segments = clean.split('/').filter(Boolean)
    return segments.pop() || fallback || '数据文件'
  }

  const buildMessagesFromHistory = (history: any[]): Message[] => {
    if (!Array.isArray(history)) {
      return []
    }

    return history
      .map((item, idx) => {
        const roleRaw = item?.role || item?.author || ''
        const role = roleRaw === 'model' ? 'assistant' : roleRaw
        const parts = Array.isArray(item?.parts) ? item.parts : []
        const content = parts
          .map((part: any) => part?.text || part?.content || '')
          .filter((text: string) => text && typeof text === 'string')
          .join('')
          .trim()

        if (!content || (role !== 'user' && role !== 'assistant')) {
          return null
        }

        return {
          id: `history_${idx}_${Date.now()}`,
          content,
          role,
          timestamp: new Date(item?.timestamp || Date.now()),
          type: 'text',
        } as Message
      })
      .filter(Boolean) as Message[]
  }

  const createSessionFilesFromMetadata = (metadata: any, sourceMessageId?: string): SessionFile[] => {
    if (!metadata) {
      return []
    }

    const timestamp = Date.now()

    const files: SessionFile[] = []

    const pushFile = (
      type: string,
      url?: string,
      rawPath?: string,
      explicitName?: string
    ) => {
      const normalizedPath = normalizePath(rawPath)
      const downloadUrl = normalizeDownloadUrl(url, normalizedPath)

      if (!downloadUrl && !normalizedPath) {
        return
      }

      const idSeed = normalizedPath || downloadUrl || `${type}-${timestamp}`
      const id = `${type}:${idSeed}`

      if (files.some((file) => file.id === id)) {
        return
      }

      files.push({
        id,
        type,
        name: explicitName || extractFileName(normalizedPath || downloadUrl, type.toUpperCase()),
        downloadUrl,
        filePath: normalizedPath,
        sourceMessageId,
        createdAt: timestamp,
        extra: metadata,
      })
    }

    pushFile(
      'csv',
      metadata.csv_download_url || metadata.csv_url,
      metadata.csv_file_path,
      metadata.csv_filename
    )

    pushFile(
      'md',
      metadata.md_download_url || metadata.summary_download_url,
      metadata.summary_file_path || metadata.report_file_path,
      metadata.md_filename
    )

    pushFile(
      'pdf',
      metadata.pdf_download_url,
      metadata.pdf_file_path,
      metadata.pdf_filename
    )

    pushFile(
      'zip',
      metadata.zip_download_url,
      metadata.zip_file_path,
      metadata.zip_filename
    )

    // 🆕 热导率计算结果 CSV 文件
    pushFile(
      'csv',
      metadata.kappa_results_csv_url,
      metadata.kappa_results_csv_path,
      metadata.kappa_results_csv_path ? extractFileName(metadata.kappa_results_csv_path) : undefined
    )

    pushFile(
      'csv',
      metadata.kappa_batch_csv_url,
      metadata.kappa_batch_csv_path,
      metadata.kappa_batch_csv_path ? extractFileName(metadata.kappa_batch_csv_path) : undefined
    )

    // 🆕 声子计算结果 CSV 文件
    pushFile(
      'csv',
      metadata.phonon_dispersion_csv_url,
      metadata.phonon_dispersion_csv_path,
      metadata.phonon_dispersion_csv_path ? extractFileName(metadata.phonon_dispersion_csv_path) : undefined
    )

    pushFile(
      'csv',
      metadata.phonon_dos_csv_url,
      metadata.phonon_dos_csv_path,
      metadata.phonon_dos_csv_path ? extractFileName(metadata.phonon_dos_csv_path) : undefined
    )

    // 注意：CIF 文件不在数据栏显示，只有 CSV 和 MD 文件需要显示

    console.log('📄 [createSessionFilesFromMetadata] 创建了', files.length, '个文件:', files.map(f => f.name))
    return files
  }

  const createSessionFilesFromPhononData = (phononData: any, sourceMessageId?: string): SessionFile[] => {
    if (!phononData) {
      return []
    }

    const files: SessionFile[] = []
    const timestamp = Date.now()

    const push = (entry: Partial<SessionFile> & { id?: string }) => {
      const normalizedPath = normalizePath(entry.filePath)
      const downloadUrl = normalizeDownloadUrl(entry.downloadUrl, normalizedPath)
      if (!downloadUrl && !normalizedPath) {
        return
      }

      const idSeed = entry.id || normalizedPath || downloadUrl || `${entry.type || 'data'}-${timestamp}`
      if (files.some((file) => file.id === idSeed)) {
        return
      }

      files.push({
        id: idSeed,
        type: entry.type || 'data',
        name: entry.name || extractFileName(normalizedPath || downloadUrl, '数据文件'),
        downloadUrl,
        filePath: normalizedPath,
        sourceMessageId,
        createdAt: timestamp,
        extra: entry.extra ?? phononData,
      })
    }

    createSessionFilesFromMetadata(phononData, sourceMessageId).forEach((file) => push(file))

    if (Array.isArray(phononData.files)) {
      phononData.files.forEach((item: any) => {
        if (!item) return
        push({
          id: item.id,
          type: item.type || 'data',
          name: item.name || item.filename,
          downloadUrl: item.downloadUrl || item.url,
          filePath: item.filePath,
          extra: item,
        })
      })
    }

    if (phononData.zip_download_url || phononData.zip_file_path) {
      push({
        type: 'zip',
        name: phononData.zip_filename,
        downloadUrl: phononData.zip_download_url,
        filePath: phononData.zip_file_path,
      })
    }

    return files
  }

  useEffect(() => {
    // 初始化WebSocket连接
    const initWebSocket = async () => {
      // 检查是否已经连接，避免重复连接
      if (wsService.isConnected) {
        console.log('🔌 WebSocket 已经连接，跳过重复连接')
        return
      }

      try {
        console.log('🔌 正在连接 WebSocket...')
        await wsService.connect()
        console.log('✅ WebSocket 连接成功')
        setConnected(true)
        toast.success('已连接到服务器')
      } catch (error) {
        console.error('❌ WebSocket 连接失败:', error)
        setConnected(false)
        toast.error('连接服务器失败，请确保后端服务器正在运行 (端口 50003)')
      }
    }

    initWebSocket()

    // 监听WebSocket消息
    const unsubscribeMessage = wsService.onMessage((message) => {
      console.log('📥 [WebSocket接收]', message.type, '数据大小:', JSON.stringify(message).length, '字符')
      console.log('📥 [WebSocket接收] 完整消息:', message)

      if (message.type === 'message' && message.data) {
        // 🆕 收到 agent 的回复消息，立即显示内容
        // 保持 loading 状态，等待 complete 状态才关闭（表示还在处理中）

        // 如果消息有内容，添加到消息列表
        if (message.data.content && message.data.content.trim()) {
          const newMessage = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            content: message.data.content,
            role: 'assistant' as const,
            timestamp: new Date(message.data.timestamp || Date.now()),
            agentId: message.data.agentId,
            // 🔧 修复：使用 getState() 获取最新 agentName，避免闭包导致的旧名称 ("文献研究助手")
            agentName: useAppStore.getState().currentAgent?.name || message.data.agentName,
            type: (message.data.type || 'text') as 'text' | 'structure' | 'analysis' | 'error',
            metadata: message.data.metadata,
          }
          addMessage(newMessage)

          // 🆕 更新 loading 消息，提示用户正在查看实时输出
          if (isLoading) {
            setLoadingMessage('正在继续处理...')
          }

          if (pendingFileMetadataRef.current.length > 0) {
            console.log('📄 [pending metadata] 发现', pendingFileMetadataRef.current.length, '个待处理的文件元数据')
            let mergedMetadata = { ...(newMessage.metadata || {}) }
            const bufferedFiles: SessionFile[] = []
            while (pendingFileMetadataRef.current.length > 0) {
              const pendingMetadata = pendingFileMetadataRef.current.shift()
              if (!pendingMetadata) {
                continue
              }
              console.log('📄 [pending metadata] 处理元数据:', pendingMetadata)
              mergedMetadata = {
                ...mergedMetadata,
                ...pendingMetadata
              }
              bufferedFiles.push(...createSessionFilesFromMetadata(pendingMetadata, newMessage.id))
            }
            console.log('📄 [pending metadata] 总共创建了', bufferedFiles.length, '个文件')
            updateMessage(newMessage.id, {
              metadata: mergedMetadata
            })
            bufferedFiles.forEach((file) => {
              console.log('📄 [pending metadata] 添加文件到右侧面板:', file.name, file.id)
              addToCurrentSessionFiles(file)
            })
          }

          // 🆕 收到内容后，保持loading状态，等待complete状态
          // 这样用户可以看到实时输出，同时知道处理还未完成

          // 如果消息包含结构数据，更新当前结构
          if (message.data.metadata?.structureData) {
            setCurrentStructure(message.data.metadata.structureData)
            addToStructureList(message.data.metadata.structureData)
            addToCurrentSessionStructures(message.data.metadata.structureData)
            toast.success('已加载分子结构')
          } else if (message.data.metadata?.frontend_structures && Array.isArray(message.data.metadata.frontend_structures)) {
            // 处理新的frontend_structures格式 - 批量添加生成的结构
            const structures = message.data.metadata.frontend_structures
            structures.forEach((structure: any) => {
              addToStructureList(structure)
              addToCurrentSessionStructures(structure)
            })
            if (structures.length > 0) {
              setCurrentStructure(structures[0]) // 设置第一个为当前结构
              toast.success(`已加载 ${structures.length} 个生成的晶体结构`)
            }
          } else if (hasStructureData(message.data.content)) {
            // 尝试从消息内容中解析结构数据
            const structure = smartParseStructure(message.data.content)
            if (structure) {
              setCurrentStructure(structure)
              addToStructureList(structure)
              addToCurrentSessionStructures(structure)
              toast.success(`已加载 ${structure.formula} 晶体结构`)
            }
          }
        }
      } else if (message.type === 'structure' && message.data) {
        // 处理专门的结构消息
        setCurrentStructure(message.data)
        addToStructureList(message.data)
        addToCurrentSessionStructures(message.data)
        toast.success('已加载分子结构')
      } else if (message.type === 'agents_list' && message.data?.agents) {
        // 更新可用的Agent列表
        setAgents(message.data.agents)
      } else if (message.type === 'connection' && message.data) {
        toast.success(message.data.message || '连接成功')
      } else if (message.type === 'error' && message.data) {
        // 重置loading状态并显示错误消息
        setIsLoading(false)
        setLoadingMessage('')

        const errorMessage = message.data.message || '发生未知错误'
        const errorDetails = message.data.details || ''

        // 添加错误消息到聊天记录
        const errorContent = errorDetails
          ? `❌ **错误**: ${errorMessage}\n\n**详情**: ${errorDetails}`
          : `❌ **错误**: ${errorMessage}`

        const errorMsg = {
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content: errorContent,
          role: 'assistant' as const,
          timestamp: new Date(),
          agentId: currentAgent?.id,
          agentName: currentAgent?.name,
          type: 'error' as const,
        }
        addMessage(errorMsg)

        // 显示toast提示
        toast.error(`❌ ${errorMessage}`, {
          duration: 6000,
          icon: '❌',
        })
      } else if (message.type === 'status' && message.data) {
        // 处理状态消息
        console.log('📊 [状态消息] 收到状态:', message.data.status, '数据:', message.data)

        if (message.data.status === 'complete') {
          console.log('✅ [状态消息] 处理完成，停止 loading')
          setIsLoading(false)
          setLoadingMessage('')

          // 更新计费数据
          if (message.data.billing) {
            console.log('💎 [计费] 收到计费数据:', message.data.billing)
            console.log('💎 [计费] charged 字段值:', message.data.billing.charged)
            console.log('💎 [计费] billing_source 字段值:', message.data.billing.billing_source)
            updateBillingData(message.data.billing)

            // 将本次对话的计费信息添加到最后一条 assistant 消息
            if (message.data.billing.current_tokens && message.data.billing.current_tokens > 0) {
              const lastAssistantMessage = messages
                .slice()
                .reverse()
                .find(msg => msg.role === 'assistant')

              if (lastAssistantMessage) {
                console.log('💎 [计费] 更新消息计费:', lastAssistantMessage.id, {
                  tokens: message.data.billing.current_tokens,
                  photons: message.data.billing.current_photons,
                  model_name: message.data.billing.model_name
                })
                updateMessage(lastAssistantMessage.id, {
                  billing: {
                    tokens: message.data.billing.current_tokens,
                    photons: message.data.billing.current_photons,
                    model_name: message.data.billing.model_name
                  }
                })
              } else {
                console.warn('💎 [计费] 未找到最后一条 assistant 消息')
              }
            } else {
              console.log('💎 [计费] 本次对话无 token 消耗')
            }
          } else {
            console.warn('💎 [计费] 完成消息中没有计费数据')
          }

          toast.success('✅ 处理完成', {
            id: 'agent-processing-toast',
            duration: 3000, // 显示3秒后消失
            icon: '✅',
          })
        } else if (message.data.status === 'processing') {
          setIsLoading(true)
          const processingMsg = message.data.message || '正在处理您的请求...'
          // 添加更详细的处理信息
          const detailedMsg = message.data.details
            ? `⏳ ${processingMsg} (${message.data.details})`
            : `⏳ ${processingMsg}`

          setLoadingMessage(detailedMsg)

          // 显示toast提示（不自动消失，等待complete状态）
          toast.loading(detailedMsg, {
            id: 'agent-processing-toast',
            duration: Infinity, // 不自动消失
          })
        } else if (message.data.status === 'waiting') {
          // 处理等待状态
          setIsLoading(true)
          const waitingMsg = message.data.message || '等待处理...'
          setLoadingMessage(`⏳ ${waitingMsg}`)

          toast.loading(`⏳ ${waitingMsg}`, {
            id: 'agent-processing-toast',
            duration: Infinity, // 不自动消失
          })
        } else if (message.data.status === 'error') {
          // 处理错误状态
          setIsLoading(false)
          setLoadingMessage('')

          const errorMsg = message.data.message || '发生错误'
          toast.error(`❌ ${errorMsg}`, {
            id: 'agent-processing-toast',
            duration: 6000, // 显示6秒后消失
          })
        } else if (message.data.status === 'thinking') {
          setIsLoading(true)
          const thinkingMsg = message.data.message || '智能体正在思考...'
          // 添加更详细的思考信息
          const detailedMsg = message.data.details
            ? `${thinkingMsg} (${message.data.details})`
            : thinkingMsg
          setLoadingMessage(detailedMsg)
        } else if (message.data.status === 'working') {
          setIsLoading(true)
          // 显示工具调用状态，提取工具名称
          const toolMessage = message.data.message || '智能体正在工作...'
          const detailedMsg = message.data.details
            ? `${toolMessage} (${message.data.details})`
            : toolMessage
          setLoadingMessage(detailedMsg)
        }
      } else if ((message.type as any) === 'agent_thinking' && message.data) {
        // 处理agent_thinking消息（工具调用详情）
        setIsLoading(true)
        const thinking = message.data.thinking || '正在处理...'
        // 如果thinking包含工具名称，显示更友好的提示
        if (thinking.includes('Using tool:')) {
          const toolName = thinking.replace('Using tool:', '').trim()
          setLoadingMessage(`🔧 正在使用工具: ${toolName}`)
        } else if (thinking.includes('search')) {
          setLoadingMessage(`🔍 ${thinking}`)
        } else if (thinking.includes('generate')) {
          setLoadingMessage(`✨ ${thinking}`)
        } else if (thinking.includes('analyze')) {
          setLoadingMessage(`📊 ${thinking}`)
        } else {
          setLoadingMessage(thinking)
        }
      } else if (message.type === 'structure_data' && message.data?.structures) {
        // 检查会话ID是否匹配
        const messageSessionId = message.data.sessionId || message.sessionId
        const currentSessionId = currentSession?.id

        console.log('🏗️ 收到结构数据:', message.data.structures.length, '个结构')
        console.log('🏗️ 消息会话ID:', messageSessionId)
        console.log('🏗️ 当前会话ID:', currentSessionId)

        // 如果会话ID不匹配，先切换到数据所属的会话，然后再添加数据
        if (messageSessionId && currentSessionId && messageSessionId !== currentSessionId) {
          console.log('🔄 会话ID不匹配，自动切换到数据所属会话:', messageSessionId)
          const targetSession = sessions.find(s => s.id === messageSessionId)
          if (targetSession) {
            setCurrentSession(targetSession)
            toast(`已自动切换到会话: ${messageSessionId.slice(-8)}`, { icon: '🔄' })

            // 等待会话切换完成后再添加数据
            setTimeout(() => {
              const structures = message.data.structures
              structures.forEach((structure: any) => {
                console.log('➕ 添加结构到会话:', structure.id || 'no-id', structure.formula || 'no-formula')
                addToCurrentSessionStructures(structure)
              })
              if (structures.length > 0) {
                setCurrentStructure(structures[0])
                console.log('✅ 设置当前结构:', structures[0].formula || 'no-formula')
                toast.success(`已加载 ${structures.length} 个结构到3D视图`)
              }
            }, 100)
            return
          } else {
            console.warn('⚠️ 未找到目标会话:', messageSessionId)
          }
        }

        // 处理结构数据（会话ID匹配的情况）
        const structures = message.data.structures
        console.log('🏗️ 结构详细信息:', structures)

        structures.forEach((structure: any) => {
          console.log('➕ 添加结构到当前会话:', structure.id || 'no-id', structure.formula || 'no-formula')
          console.log('📁 cif_file_path:', structure.cif_file_path || 'N/A')  // 🆕 调试日志
          // 只添加到当前会话结构列表，不添加到全局列表
          addToCurrentSessionStructures(structure)
        })

        if (structures.length > 0) {
          setCurrentStructure(structures[0])
          console.log('✅ 设置当前结构:', structures[0].formula || 'no-formula')
          toast.success(`已加载 ${structures.length} 个结构到3D视图`)
        }
      } else if (message.type === 'image_data' && message.data?.images) {
        // 检查会话ID是否匹配
        const messageSessionId = message.data.sessionId || message.sessionId
        const currentSessionId = currentSession?.id

        console.log('🖼️ 收到图片数据:', message.data.images.length, '个图片')
        console.log('🖼️ 消息会话ID:', messageSessionId)
        console.log('🖼️ 当前会话ID:', currentSessionId)

        // 如果会话ID不匹配，先切换到数据所属的会话，然后再添加数据
        if (messageSessionId && currentSessionId && messageSessionId !== currentSessionId) {
          console.log('🔄 会话ID不匹配，自动切换到数据所属会话:', messageSessionId)
          const targetSession = sessions.find(s => s.id === messageSessionId)
          if (targetSession) {
            setCurrentSession(targetSession)
            toast(`已自动切换到会话: ${messageSessionId.slice(-8)}`, { icon: '🔄' })

            // 等待会话切换完成后再添加数据
            setTimeout(() => {
              const images = message.data.images
              images.forEach((image: any) => {
                addToCurrentSessionPhononImages(image)
              })

              // 🆕 将图片附加到最后一条 assistant 消息
              const state = useAppStore.getState()
              const msgs = state.messages
              const assistantMsgs = msgs.filter(m => m.role === 'assistant')
              const lastAssistant = assistantMsgs[assistantMsgs.length - 1]
              if (lastAssistant) {
                updateMessage(lastAssistant.id, {
                  metadata: {
                    ...(lastAssistant.metadata || {}),
                    images: images
                  }
                })
              }

              toast.success(`已加载 ${images.length} 个声子谱图片`)
            }, 100)
            return
          } else {
            console.warn('⚠️ 未找到目标会话:', messageSessionId)
          }
        }

        // 处理图片数据（会话ID匹配的情况）
        const images = message.data.images
        console.log('🖼️ 图片详细信息:', images)

        // 将图片数据以增量方式添加到当前会话的声子谱图片列表（限制最多10个）
        images.forEach((image: any) => {
          addToCurrentSessionPhononImages(image)
        })

        // 🆕 将图片附加到最后一条 assistant 消息的 metadata 中，以便在对话界面显示
        const storeState = useAppStore.getState()
        const allMessages = storeState.messages
        const assistantMessages = allMessages.filter(m => m.role === 'assistant')
        const lastAssistantMessage = assistantMessages[assistantMessages.length - 1]

        if (lastAssistantMessage) {
          console.log('🖼️ 将图片附加到 assistant 消息:', lastAssistantMessage.id)
          updateMessage(lastAssistantMessage.id, {
            metadata: {
              ...(lastAssistantMessage.metadata || {}),
              images: images
            }
          })
          toast.success(`已加载 ${images.length} 个声子谱图片`)
        } else {
          console.warn('⚠️ 未找到 assistant 消息，无法附加图片到对话')
          toast.success(`已加载 ${images.length} 个声子谱图片，请在右侧面板查看`)
        }

        // 不自动显示全屏，让用户在右侧面板查看
        // setShowPhononVisualization(true)
      } else if ((message.type as any) === 'tool_execution' && message.data) {
        // 🆕 处理工具执行消息
        console.log('🔧 收到工具执行消息:', message.data)
        console.log('🔧 消息类型:', message.type)
        console.log('🔧 当前消息列表长度:', useAppStore.getState().messages.length)

        const toolExecutionData = message.data
        const toolMessageId = `tool_${toolExecutionData.toolName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

        // 检查是否已存在该工具的消息（用于更新状态）
        const storeState = useAppStore.getState()
        const existingToolMessage = storeState.messages.find(
          m => m.type === 'tool_execution' &&
            m.toolExecution?.toolName === toolExecutionData.toolName &&
            m.toolExecution?.status === 'pending'
        )

        if (existingToolMessage && toolExecutionData.status !== 'pending') {
          // 更新现有的工具执行消息
          console.log('🔧 更新工具执行状态:', existingToolMessage.id, toolExecutionData.status)
          updateMessage(existingToolMessage.id, {
            toolExecution: {
              toolName: toolExecutionData.toolName,
              input: toolExecutionData.input,
              output: toolExecutionData.output,
              status: toolExecutionData.status,
              error: toolExecutionData.error
            },
            metadata: toolExecutionData.output || {}
          })

          // 如果工具执行成功且生成了文件，添加到会话文件列表
          if (toolExecutionData.status === 'success' && toolExecutionData.output) {
            const generatedFiles = createSessionFilesFromMetadata(toolExecutionData.output, existingToolMessage.id)
            generatedFiles.forEach((file) => addToCurrentSessionFiles(file))

            // 🆕 如果是 search_papers 工具，设置文献数据到 store
            if (toolExecutionData.toolName === 'search_papers' &&
              toolExecutionData.output.csv_file_path &&
              toolExecutionData.output.total_papers_in_csv) {
              const sessionId = toolExecutionData.output.session_id || toolExecutionData.sessionId || currentSession?.id || 'default'
              const csvPath = normalizePapersCsvPath(toolExecutionData.output.csv_file_path)
              if (csvPath) {
                setPapersData(
                  csvPath,
                  sessionId,
                  toolExecutionData.output.total_papers_in_csv
                )
                console.log('📚 设置文献数据到 store:', {
                  originalPath: toolExecutionData.output.csv_file_path,
                  csvPath: csvPath,
                  sessionId: sessionId,
                  count: toolExecutionData.output.total_papers_in_csv
                })
              }
            }
            if ((toolExecutionData.toolName === 'ingest_uploaded_papers' ||
              toolExecutionData.toolName === 'ingest_uploaded_documents') &&
              toolExecutionData.output.csv_file_path &&
              toolExecutionData.output.total_papers_in_csv) {
              const sessionId = toolExecutionData.output.session_id || toolExecutionData.sessionId || currentSession?.id || 'default'
              const csvPath = normalizePapersCsvPath(toolExecutionData.output.csv_file_path)
              if (csvPath) {
                setPapersData(
                  csvPath,
                  sessionId,
                  toolExecutionData.output.total_papers_in_csv
                )
                console.log('Set uploaded papers data into store:', {
                  csvPath: csvPath,
                  sessionId: sessionId,
                  count: toolExecutionData.output.total_papers_in_csv
                })
              }
            }
            if (toolExecutionData.toolName === 'batch_paper_analysis' ||
              toolExecutionData.toolName === 'generate_research_report') {
              setIsLoading(false)
              setLoadingMessage('')
              toast.dismiss('agent-processing-toast')
            }
          }
        } else {
          // 创建新的工具执行消息
          console.log('🔧 创建新的工具执行消息:', toolMessageId)
          const toolMessage = {
            id: toolMessageId,
            content: `工具调用: ${toolExecutionData.toolName}`,
            role: 'tool' as const,
            timestamp: new Date(toolExecutionData.timestamp || Date.now()),
            agentId: toolExecutionData.agentId,
            type: 'tool_execution' as const,
            toolExecution: {
              toolName: toolExecutionData.toolName,
              input: toolExecutionData.input,
              output: toolExecutionData.output,
              status: toolExecutionData.status,
              error: toolExecutionData.error
            },
            metadata: toolExecutionData.output || {}
          }

          console.log('🔧 添加工具执行消息到消息列表')
          addMessage(toolMessage)

          // 验证消息是否被正确添加
          setTimeout(() => {
            const updatedState = useAppStore.getState()
            const addedMessage = updatedState.messages.find(m => m.id === toolMessageId)
            console.log('🔧 验证消息添加:', {
              messageId: toolMessageId,
              found: !!addedMessage,
              type: addedMessage?.type,
              totalMessages: updatedState.messages.length
            })
          }, 100)

          // 如果工具执行成功且生成了文件，添加到会话文件列表
          if (toolExecutionData.status === 'success' && toolExecutionData.output) {
            const generatedFiles = createSessionFilesFromMetadata(toolExecutionData.output, toolMessageId)
            generatedFiles.forEach((file) => addToCurrentSessionFiles(file))

            // 🆕 如果是 search_papers 工具，设置文献数据到 store
            if (toolExecutionData.toolName === 'search_papers' &&
              toolExecutionData.output.csv_file_path &&
              toolExecutionData.output.total_papers_in_csv) {
              const sessionId = toolExecutionData.output.session_id || toolExecutionData.sessionId || currentSession?.id || 'default'
              const csvPath = normalizePapersCsvPath(toolExecutionData.output.csv_file_path)
              if (csvPath) {
                setPapersData(
                  csvPath,
                  sessionId,
                  toolExecutionData.output.total_papers_in_csv
                )
                console.log('📚 设置文献数据到 store:', {
                  csvPath: csvPath,
                  sessionId: sessionId,
                  count: toolExecutionData.output.total_papers_in_csv
                })
              }
            }
            if ((toolExecutionData.toolName === 'ingest_uploaded_papers' ||
              toolExecutionData.toolName === 'ingest_uploaded_documents') &&
              toolExecutionData.output.csv_file_path &&
              toolExecutionData.output.total_papers_in_csv) {
              const sessionId = toolExecutionData.output.session_id || toolExecutionData.sessionId || currentSession?.id || 'default'
              const csvPath = normalizePapersCsvPath(toolExecutionData.output.csv_file_path)
              if (csvPath) {
                setPapersData(
                  csvPath,
                  sessionId,
                  toolExecutionData.output.total_papers_in_csv
                )
                console.log('Set uploaded papers data into store:', {
                  csvPath: csvPath,
                  sessionId: sessionId,
                  count: toolExecutionData.output.total_papers_in_csv
                })
              }
            }
          }
        }
      } else if ((message.type as any) === 'file_data' && message.data?.files) {
        // 🆕 处理独立的文件数据消息（热导率 CSV、批量计算结果等）
        console.log('📄 收到文件数据:', message.data.files)
        const files = message.data.files

        if (Array.isArray(files)) {
          files.forEach((fileData: any) => {
            const file: SessionFile = {
              id: fileData.id || `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
              type: fileData.type || 'csv',
              name: fileData.name || fileData.filename || '数据文件',
              downloadUrl: fileData.downloadUrl || fileData.url,
              filePath: fileData.filePath,
              inlineContent: fileData.inlineContent,
              sourceMessageId: messages[messages.length - 1]?.id,
              createdAt: fileData.createdAt || Date.now(),
              extra: fileData.extra || {}
            }

            console.log('📄 添加文件到右侧面板:', file.name)
            addToCurrentSessionFiles(file)
          })

          toast.success(`已生成 ${files.length} 个数据文件，可在右侧面板查看`, {
            duration: 4000,
            icon: '📄'
          })
        }
      } else if ((message.type as any) === 'file_metadata' && message.data?.metadata) {
        // 处理文件元数据（CSV和MD文件链接）
        console.log('📄 收到文件元数据:', message.data.metadata)
        const storeState = useAppStore.getState()
        const allMessages = storeState.messages
        console.log('📄 当前消息数:', allMessages.length)
        console.log('📄 所有消息:', allMessages.map(m => ({ id: m.id, role: m.role, metadata: m.metadata })))

        // 找到最后一条assistant消息，而不是最后一条消息
        // 因为最后一条消息可能是status消息或其他消息
        const assistantMessages = allMessages.filter(m => m.role === 'assistant')
        console.log('📄 Assistant消息数:', assistantMessages.length)
        console.log('📄 Assistant消息列表:', assistantMessages.map(m => ({ id: m.id, metadata: m.metadata })))

        // 使用 [...] 创建新数组副本，避免修改原数组
        const currentMessage = assistantMessages[assistantMessages.length - 1]
        if (currentMessage) {
          console.log('📄 找到assistant消息，直接更新:', currentMessage.id)
          console.log('📄 原metadata:', currentMessage.metadata)
          console.log('📄 新metadata:', message.data.metadata)

          updateMessage(currentMessage.id, {
            metadata: {
              ...(currentMessage.metadata || {}),
              ...message.data.metadata
            }
          })

          const generatedFiles = createSessionFilesFromMetadata(message.data.metadata, currentMessage.id)
          console.log('📄 创建了', generatedFiles.length, '个文件，准备添加到右侧面板')
          generatedFiles.forEach((file) => {
            console.log('📄 添加文件:', file.name, file.id)
            addToCurrentSessionFiles(file)
          })

          // 验证更新是否成功
          setTimeout(() => {
            const latest = useAppStore.getState()
            const updatedMsg = latest.messages.find(m => m.id === currentMessage.id)
            console.log('📄 更新后的消息metadata:', updatedMsg?.metadata)
            console.log('📄 当前会话文件数:', latest.currentSessionFiles.length)
          }, 100)

          // 提示用户
          const fileTypes = []
          if (message.data.metadata.csv_download_url) fileTypes.push('CSV')
          if (message.data.metadata.md_download_url) fileTypes.push('Markdown')
          if (message.data.metadata.kappa_results_csv_url) fileTypes.push('热导率结果')
          if (message.data.metadata.kappa_batch_csv_url) fileTypes.push('批量热导率结果')
          if (message.data.metadata.phonon_dispersion_csv_url) fileTypes.push('声子色散数据')
          if (message.data.metadata.phonon_dos_csv_url) fileTypes.push('声子态密度数据')
          if (fileTypes.length > 0) {
            console.log('📄 显示toast提示:', fileTypes)
            toast.success(`已生成${fileTypes.join('和')}文件，可在消息中查看和下载`, {
              duration: 4000,
              icon: '📄'
            })
          }
        } else {
          console.warn('⚠️ 未找到assistant消息，暂存文件元数据以便稍后应用')
          console.log('⚠️ 暂存的元数据:', message.data.metadata)
          pendingFileMetadataRef.current.push(message.data.metadata)
          console.log('⚠️ pending队列长度:', pendingFileMetadataRef.current.length)
        }
      } else if (message.type === 'phonon_data' && message.data?.phonon_data) {
        // 直接处理声子谱数据
        const phononData = message.data.phonon_data
        console.log('🎵 收到声子谱数据:', phononData)

        // 提取声子谱图片
        if (phononData.images && Array.isArray(phononData.images)) {
          setPhononImages(phononData.images)
          setCurrentSessionPhononImages(phononData.images)
          setShowPhononVisualization(true)
          toast.success(`已加载 ${phononData.images.length} 个声子谱图像`)
        } else {
          toast.success('已加载声子谱计算结果')
        }

        // 将声子谱数据添加到当前消息的metadata中
        const latestState = useAppStore.getState()
        const currentMessage = latestState.messages[latestState.messages.length - 1]
        if (currentMessage) {
          updateMessage(currentMessage.id, {
            metadata: {
              ...currentMessage.metadata,
              phononData: phononData
            }
          })

          const phononFiles = createSessionFilesFromPhononData(phononData, currentMessage.id)
          phononFiles.forEach((file) => addToCurrentSessionFiles(file))
        }
      } else if ((message.type as any) === 'conversation_stats' && message.data) {
        // 🆕 处理会话计费统计响应
        console.log('📊 [计费统计] 收到会话统计:', message.data)
        // 会话统计已经通过 billingData 更新，这里不需要额外处理
        // BillingStatsPanel 会监听 billingData 的变化
      } else if ((message.type as any) === 'user_stats' && message.data) {
        // 🆕 处理用户计费统计响应
        console.log('📊 [计费统计] 收到用户统计:', message.data)
        if (message.data.success && message.data.data) {
          setUserBillingStats(message.data.data)
        }
      } else if ((message.type as any) === 'global_stats' && message.data) {
        // 🆕 处理全局计费统计响应
        console.log('📊 [计费统计] 收到全局统计:', message.data)
        if (message.data.success && message.data.data) {
          setGlobalBillingStats(message.data.data)
        }
      } else if ((message.type as any) === 'analysis_complete' && message.data) {
        // 处理批量分析完成
        console.log('✅ [批量分析] 分析完成:', message.data)

        setIsLoading(false)
        setLoadingMessage('')
        toast.dismiss('agent-processing-toast')

        const storeState = useAppStore.getState()
        const pendingToolMessage = storeState.messages.find(
          (m) =>
            m.type === 'tool_execution' &&
            m.toolExecution?.toolName === 'batch_paper_analysis' &&
            m.toolExecution?.status === 'pending'
        )
        if (pendingToolMessage) {
          storeState.updateMessage(pendingToolMessage.id, {
            toolExecution: {
              ...pendingToolMessage.toolExecution,
              status: 'success',
              output: message.data
            },
            metadata: message.data || {}
          })
        }

        toast.success(message.data.message || '批量分析已完成！', {
          duration: 5000,
          icon: '✅'
        })
      } else if ((message.type as any) === 'analysis_error' && message.data) {
        // 处理批量分析错误
        console.error('❌ [批量分析] 分析失败:', message.data)

        setIsLoading(false)
        setLoadingMessage('')
        toast.dismiss('agent-processing-toast')

        const storeState = useAppStore.getState()
        const pendingToolMessage = storeState.messages.find(
          (m) =>
            m.type === 'tool_execution' &&
            m.toolExecution?.toolName === 'batch_paper_analysis' &&
            m.toolExecution?.status === 'pending'
        )
        if (pendingToolMessage) {
          storeState.updateMessage(pendingToolMessage.id, {
            toolExecution: {
              ...pendingToolMessage.toolExecution,
              status: 'error',
              error: message.data?.error || '??????'
            }
          })
        }

        toast.error(message.data.error || '批量分析失败', {
          duration: 6000,
          icon: '❌'
        })
      } else if ((message.type as any) === 'report_complete' && message.data) {
        // 处理报告生成完成
        console.log('✅ [报告生成] 生成完成:', message.data)

        setIsLoading(false)
        setLoadingMessage('')
        toast.dismiss('agent-processing-toast')

        toast.success(message.data.message || '研究报告生成完成！', {
          duration: 5000,
          icon: '📄'
        })
      } else if ((message.type as any) === 'report_error' && message.data) {
        // 处理报告生成错误
        console.error('❌ [报告生成] 生成失败:', message.data)

        setIsLoading(false)
        setLoadingMessage('')
        toast.dismiss('agent-processing-toast')

        toast.error(message.data.error || '报告生成失败', {
          duration: 6000,
          icon: '❌'
        })
      } else if ((message.type as any) === 'history' && message.data?.history) {
        const historyMessages = buildMessagesFromHistory(message.data.history)
        if (historyMessages.length > 0) {
          setMessages(historyMessages)
          console.log('📜 已恢复历史消息:', historyMessages.length)
        } else {
          console.log('📜 历史消息为空或无法解析')
        }
      } else if ((message.type as any) === 'session_recovered' && message.data) {
        // 🆕 处理会话恢复消息（WebSocket 重连后）
        console.log('🔄 [会话恢复] 收到恢复确认:', message.data)

        // 检查是否有活跃任务
        if (message.data.hasActiveTask && message.data.activeTask) {
          console.log('🔄 [会话恢复] 发现活跃任务:', message.data.activeTask)
          // 恢复加载状态
          setIsLoading(true)
          setLoadingMessage(`🔄 恢复中: ${message.data.activeTask.description || '正在处理...'}`)
        } else {
          // 没有活跃任务，确保清除加载状态
          console.log('🔄 [会话恢复] 无活跃任务，清除加载状态')
          setIsLoading(false)
          setLoadingMessage('')
          toast.dismiss('agent-processing-toast')
        }

        const recoveredSessionId = message.data.sessionId
        if (recoveredSessionId && historyRequestRef.current !== recoveredSessionId) {
          wsService.send({
            type: 'get_history',
            data: {
              sessionId: recoveredSessionId,
              agentId: currentAgent?.id,
            }
          })
          historyRequestRef.current = recoveredSessionId
        }

        toast.success('已恢复连接', { duration: 2000, icon: '🔄' })
      } else if ((message.type as any) === 'connected' && message.data?.isReconnection) {
        // 🆕 处理重连成功消息
        console.log('🔄 [重连] WebSocket 重连成功')
        toast.success('重新连接成功', { duration: 2000, icon: '🔄' })
      }
    })

    // 监听连接状态
    const unsubscribeConnection = wsService.onConnection((connected) => {
      setConnected(connected)
      if (connected) {
        toast.success('重新连接成功')
      } else {
        toast.error('连接已断开')
        historyRequestRef.current = null
        // 🆕 连接断开时，设置超时后自动清除加载状态，避免卡住
        setTimeout(() => {
          const currentLoading = useAppStore.getState()
          // 如果 5 秒后仍然断开且仍在加载中，清除加载状态
          if (!wsService.isConnected) {
            console.log('⚠️ [超时恢复] 连接断开超过 5 秒，清除加载状态')
            setIsLoading(false)
            setLoadingMessage('')
            toast.dismiss('agent-processing-toast')
          }
        }, 5000)
      }
    })

    return () => {
      console.log('🧹 ChatPage cleanup - 只清理事件监听，保持连接')
      unsubscribeMessage()
      unsubscribeConnection()
      // 不断开WebSocket连接，让其他组件继续使用
    }
  }, []) // 移除函数依赖项，这些函数引用会导致不断重连

  useEffect(() => {
    if (!connected || !currentSession?.id) return
    if (historyRequestRef.current === currentSession.id) return

    wsService.send({
      type: 'get_history',
      data: {
        sessionId: currentSession.id,
        agentId: currentAgent?.id,
      }
    })
    historyRequestRef.current = currentSession.id
  }, [connected, currentSession?.id, currentAgent?.id])

  // 自动创建会话 - 仅在发送消息时创建，避免刷新页面时自动创建
  // 移除自动创建逻辑，改为在发送消息时检查并创建

  return (
    <div className="h-full flex flex-col">
      {/* 智能体选择器 - 恢复显示，以确保用户明确当前使用的智能体 */}
      <div className="flex-none bg-white border-b border-gray-200 z-10 relative hidden md:block">
        <AgentSelector />
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 min-h-0">
        <ChatInterface />
      </div>

      {/* 声子谱可视化组件 (保留用于全屏显示) */}
      {showPhononVisualization && phononImages.length > 0 && (
        <PhononVisualization
          images={phononImages}
          onClose={() => setShowPhononVisualization(false)}
          dispersionCsvPath={phononImages[0]?.dispersionCsvPath}
          dosCsvPath={phononImages[0]?.dosCsvPath}
        />
      )}
    </div>
  )
}

export default ChatPage
