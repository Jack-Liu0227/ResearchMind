import React, { useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { wsService } from '../services/websocket'
import ChatInterface from '../components/ChatInterface'
import AgentSelector from '../components/AgentSelector'
import PhononVisualization from '../components/PhononVisualization'
import toast from 'react-hot-toast'
import { smartParseStructure, hasStructureData } from '../utils/structureParser'

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
    agents,
    setIsLoading,
    setLoadingMessage,
    phononImages,
    showPhononVisualization,
    setPhononImages,
    setCurrentSessionPhononImages,
    addToCurrentSessionPhononImages,
    setShowPhononVisualization,
    messages,
    sessions
  } = useAppStore()

  useEffect(() => {
    // 初始化WebSocket连接
    const initWebSocket = async () => {
      try {
        console.log('🔌 正在连接 WebSocket...')
        await wsService.connect()
        console.log('✅ WebSocket 连接成功')
        setConnected(true)
        toast.success('已连接到服务器')
      } catch (error) {
        console.error('❌ WebSocket 连接失败:', error)
        setConnected(false)
        toast.error('连接服务器失败，请确保后端服务器正在运行 (端口 8002)')
      }
    }

    initWebSocket()

    // 监听WebSocket消息
    const unsubscribeMessage = wsService.onMessage((message) => {
      console.log('📥 [WebSocket接收]', message.type, '数据大小:', JSON.stringify(message).length, '字符')
      console.log('📥 [WebSocket接收] 完整消息:', message)

      if (message.type === 'message' && message.data) {
        // 收到agent消息时，立即显示"智能体正在思考"提示
        if (message.data.agentName && !message.data.content) {
          // 如果只有agentName没有content，说明agent刚开始处理
          setIsLoading(true)
          setLoadingMessage(`${message.data.agentName} 正在思考...`)
        }

        // 如果消息有内容，添加到消息列表
        if (message.data.content && message.data.content.trim()) {
          const newMessage = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            content: message.data.content,
            role: 'assistant' as const,
            timestamp: new Date(message.data.timestamp || Date.now()),
            agentId: message.data.agentId,
            agentName: message.data.agentName,
            type: (message.data.type || 'text') as 'text' | 'structure' | 'analysis' | 'error',
            metadata: message.data.metadata,
          }
          addMessage(newMessage)

          // 收到内容后，保持loading状态，等待complete状态
          // 不在这里关闭loading，因为可能还有后续消息

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

        const errorMessage = message.data.message || '发生错误'

        // 添加错误消息到聊天记录
        const errorMsg = {
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content: `❌ ${errorMessage}`,
          role: 'assistant' as const,
          timestamp: new Date(),
          agentId: currentAgent?.id,
          agentName: currentAgent?.name,
          type: 'error' as const,
        }
        addMessage(errorMsg)

        // 显示toast提示
        toast.error(errorMessage, {
          duration: 5000,
          icon: '❌',
        })
      } else if (message.type === 'status' && message.data) {
        // 处理状态消息
        if (message.data.status === 'complete') {
          setIsLoading(false)
          setLoadingMessage('')
        } else if (message.data.status === 'processing') {
          setIsLoading(true)
          setLoadingMessage(message.data.message || '正在处理您的请求...')
        } else if (message.data.status === 'thinking') {
          setIsLoading(true)
          setLoadingMessage(message.data.message || '智能体正在思考...')
        } else if (message.data.status === 'working') {
          setIsLoading(true)
          // 显示工具调用状态，提取工具名称
          const toolMessage = message.data.message || '智能体正在工作...'
          setLoadingMessage(toolMessage)
        }
      } else if ((message.type as any) === 'agent_thinking' && message.data) {
        // 处理agent_thinking消息（工具调用详情）
        setIsLoading(true)
        const thinking = message.data.thinking || '正在处理...'
        // 如果thinking包含工具名称，显示更友好的提示
        if (thinking.includes('Using tool:')) {
          const toolName = thinking.replace('Using tool:', '').trim()
          setLoadingMessage(`🔧 正在使用工具: ${toolName}`)
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

        toast.success(`已加载 ${images.length} 个声子谱图片`)

        // 不自动显示全屏，让用户在右侧面板查看
        // setShowPhononVisualization(true)

        // 将图片数据添加到当前消息的metadata中，并触发重新渲染
        const currentMessage = messages[messages.length - 1]
        if (currentMessage) {
          // 使用updateMessage方法确保触发重新渲染
          updateMessage(currentMessage.id, {
            metadata: {
              ...currentMessage.metadata,
              images: images as any
            }
          })
        }
        toast.success(`已加载 ${images.length} 个声子谱图片，请在右侧面板查看`)
      } else if ((message.type as any) === 'file_metadata' && message.data?.metadata) {
        // 处理文件元数据（CSV和MD文件链接）
        console.log('📄 收到文件元数据:', message.data.metadata)

        // 将文件元数据添加到最后一条消息的metadata中
        const currentMessage = messages[messages.length - 1]
        if (currentMessage && currentMessage.role === 'assistant') {
          updateMessage(currentMessage.id, {
            metadata: {
              ...currentMessage.metadata,
              ...message.data.metadata
            }
          })

          // 提示用户（不显示toast，避免干扰）
          // const fileTypes = []
          // if (message.data.metadata.csv_download_url) fileTypes.push('CSV')
          // if (message.data.metadata.md_download_url) fileTypes.push('Markdown')
          // if (fileTypes.length > 0) {
          //   toast.success(`已生成${fileTypes.join('和')}文件，可在消息中查看和下载`)
          // }
        }
      } else if (message.type === 'phonon_data' && message.data?.phonon_data) {
        // 直接处理声子谱数据
        const phononData = message.data.phonon_data
        console.log('🎵 收到声子谱数据:', phononData)

        // 提取声子谱图片
        if (phononData.images && Array.isArray(phononData.images)) {
          setPhononImages(phononData.images)
          setShowPhononVisualization(true)
          toast.success(`已加载 ${phononData.images.length} 个声子谱图像`)
        } else {
          toast.success('已加载声子谱计算结果')
        }

        // 将声子谱数据添加到当前消息的metadata中
        const currentMessage = messages[messages.length - 1]
        if (currentMessage) {
          updateMessage(currentMessage.id, {
            metadata: {
              ...currentMessage.metadata,
              phononData: phononData
            }
          })
        }
      }
    })

    // 监听连接状态
    const unsubscribeConnection = wsService.onConnection((connected) => {
      setConnected(connected)
      if (connected) {
        toast.success('重新连接成功')
      } else {
        toast.error('连接已断开')
      }
    })

    return () => {
      unsubscribeMessage()
      unsubscribeConnection()
      wsService.disconnect()
    }
  }, [setConnected, addMessage, setAgents])

  // 自动创建会话 - 仅在发送消息时创建，避免刷新页面时自动创建
  // 移除自动创建逻辑，改为在发送消息时检查并创建

  return (
    <div className="h-full flex flex-col">
      {/* 智能体选择器 */}
      <div className="border-b border-gray-200 bg-white">
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
        />
      )}
    </div>
  )
}

export default ChatPage