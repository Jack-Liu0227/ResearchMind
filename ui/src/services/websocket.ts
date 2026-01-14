import { WebSocketMessage, Message } from '../types'
import { API_CONFIG } from '../constants'

type MessageHandler = (message: WebSocketMessage) => void
type ConnectionHandler = (connected: boolean) => void

const isWindowsAbsolutePath = (value: string) =>
  /^[a-zA-Z]:[\\/]/.test(value) || value.startsWith('\\\\')

const normalizeWebSocketUrl = (rawUrl: string): string => {
  const value = (rawUrl || '').trim()

  if (!value) {
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host || '127.0.0.1'
      return `${protocol}//${host}/ws`
    }
    return 'ws://127.0.0.1:50001/ws'
  }

  if (value.startsWith('ws://') || value.startsWith('wss://')) {
    return value
  }

  if (value.startsWith('http://') || value.startsWith('https://')) {
    return value.replace(/^http/i, 'ws')
  }

  if (isWindowsAbsolutePath(value)) {
    const normalized = value.replace(/\\/g, '/')
    const segments = normalized.split('/').filter(Boolean)
    const lastSegment = segments[segments.length - 1] || 'ws'
    return normalizeWebSocketUrl(`/${lastSegment}`)
  }

  const path = value.startsWith('/') ? value : `/${value}`

  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host || '127.0.0.1'
    return `${protocol}//${host}${path}`
  }

  return `ws://127.0.0.1:50001${path}`
}

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  // 基础重连配置
  private maxReconnectAttempts = -1 // -1 代表无限重连
  private reconnectInterval = 3000 // 基础重连间隔3秒

  // 状态和处理器
  private messageHandlers: MessageHandler[] = []
  private connectionHandlers: ConnectionHandler[] = []
  private clientId: string
  private isConnecting = false

  // 心跳配置 (仅用于保活，不用于断开检测)
  private heartbeatInterval: number | null = null
  private readonly HEARTBEAT_INTERVAL = 20000 // 20秒发送一次Ping保活 (配合后端的25s间隔)
  private readonly WATCHDOG_CLOSE_ON_TIMEOUT = false

  // 🔧 优化：请求去重 - 跟踪待处理的消息
  private pendingMessages = new Set<string>() // 存储消息内容的哈希

  // 🔧 优化：上次收到消息的时间戳 (用于看门狗检测僵尸连接)
  private lastMessageTime: number = Date.now()
  private readonly WATCHDOG_TIMEOUT = 1200000 // 1200秒 (20分钟) 无消息才视为僵尸连接

  constructor(url?: string) {
    this.url = url || API_CONFIG.WS_URL
    console.log('🔧 WebSocketService constructor - url param:', url)
    console.log('🔧 WebSocketService constructor - API_CONFIG.WS_URL:', API_CONFIG.WS_URL)
    console.log('🔧 WebSocketService constructor - final this.url:', this.url)

    // 从localStorage恢复client_id，如果不存在则创建新的
    const storedClientId = localStorage.getItem('researchmind_client_id')
    if (storedClientId) {
      this.clientId = storedClientId
      console.log('📦 恢复客户端ID:', this.clientId)
    } else {
      this.clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('researchmind_client_id', this.clientId)
      console.log('🆕 创建新客户端ID:', this.clientId)
    }
  }

  connect(): Promise<void> {
    // 如果已经连接或正在连接，直接返回
    if (this.isConnected) {
      console.log('🔌 WebSocket 已连接，跳过重复连接')
      return Promise.resolve()
    }

    if (this.isConnecting) {
      console.log('🔌 WebSocket 正在连接中，跳过重复连接')
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      try {
        this.isConnecting = true

        // 构建WebSocket URL，确保格式正确
        let wsUrl = normalizeWebSocketUrl(this.url)
        if (!wsUrl.endsWith('/ws')) {
          wsUrl = wsUrl.endsWith('/') ? `${wsUrl}ws` : `${wsUrl}/ws`
        }
        wsUrl = `${wsUrl}/${this.clientId}`

        console.log(`🔌 连接 WebSocket (无限重连模式): ${wsUrl}`)
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('✅ WebSocket 已连接')
          const wasReconnect = this.reconnectAttempts > 0
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.pendingMessages.clear()
          this.lastMessageTime = Date.now() // 重置心跳计时
          this.notifyConnectionHandlers(true)

          // 启动保活心跳 & 看门狗
          this.startHeartbeat()

          // 🆕 发送 JWT Token 进行认证
          this.sendAuthToken()

          // 🆕 如果是重连，请求恢复任务状态
          if (wasReconnect) {
            console.log('🔄 重连成功，请求恢复会话状态...')
            this.requestSessionRecovery()
          }

          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            // 收到任何消息都更新活跃时间
            this.lastMessageTime = Date.now()

            const message: WebSocketMessage = JSON.parse(event.data)

            // 处理心跳响应 (仅记录日志，不作超时处理)
            if (message.type === 'pong') {
              // console.debug('💓 Received pong') 
              return
            }

            this.notifyMessageHandlers(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          this.isConnecting = false
          this.pendingMessages.clear()
          this.notifyConnectionHandlers(false)

          // 停止心跳
          this.stopHeartbeat()

          //只要不是手动关闭，永远尝试重连
          if (this.ws) {
            console.log('🔄 Connection lost. Scheduling infinite reconnect...')
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          // 不reject，让重连逻辑处理
        }
      } catch (error) {
        this.isConnecting = false
        // 尝试重连
        this.scheduleReconnect()
      }
    })
  }

  disconnect(): void {
    if (this.ws) {
      console.log('🔌 用户主动断开WebSocket连接...')
      this.stopHeartbeat()
      const ws = this.ws
      this.ws = null // 先清空引用，标记为主动断开，阻止重连
      ws.close(1000, 'Client disconnect')
      this.isConnecting = false
      this.notifyConnectionHandlers(false)
    }
  }

  // 🔧 优化：使用 Web Worker 进行心跳保活，防止后台页面的定时器被浏览器冻结
  private heartbeatWorker: Worker | null = null

  /**
   * 启动保活心跳 & 看门狗机制
   * 1. 发送Ping保持链路活跃
   * 2. 检查 lastMessageTime，如果超时未收到消息（僵尸连接），主动断开重连
   */
  private startHeartbeat(): void {
    this.stopHeartbeat() // 先清除旧的定时器/Worker

    // 初始化 Worker (如果尚未初始化)
    if (!this.heartbeatWorker) {
      try {
        // 使用 Vite 的 worker 导入方式
        this.heartbeatWorker = new Worker(new URL('./heartbeat.worker.ts', import.meta.url), { type: 'module' });

        this.heartbeatWorker.onmessage = (e) => {
          if (e.data.type === 'tick') {
            if (this.isConnected) {
              const now = Date.now()
              // 🐕 看门狗检查
              if (now - this.lastMessageTime > this.WATCHDOG_TIMEOUT) {
                console.warn(`?? Watchdog: Connection idle for ${now - this.lastMessageTime}ms.`)
                if (this.WATCHDOG_CLOSE_ON_TIMEOUT && this.ws) {
                  this.ws.close(4000, 'Watchdog timeout')
                  return
                }
              }
              // 发送 Ping
              this.send({ type: 'ping', data: { timestamp: now } });
            }
          }
        };
      } catch (e) {
        console.error('❌ Failed to create heartbeat worker:', e);
        // Fallback to setInterval if Worker fails
        this.heartbeatInterval = window.setInterval(() => {
          // ... interval fallback logic ...
          if (this.isConnected) {
            const now = Date.now();
            if (now - this.lastMessageTime > this.WATCHDOG_TIMEOUT) {
              if (this.WATCHDOG_CLOSE_ON_TIMEOUT && this.ws) {
                this.ws.close(4000, 'Watchdog timeout')
                return
              }
            }
            this.send({ type: 'ping', data: { timestamp: now } });
          }
        }, this.HEARTBEAT_INTERVAL);
        return;
      }
    }

    // 启动 Worker 计时
    this.heartbeatWorker.postMessage({ type: 'start', interval: this.HEARTBEAT_INTERVAL });
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat(): void {
    if (this.heartbeatWorker) {
      this.heartbeatWorker.postMessage({ type: 'stop' });
      // Don't terminate, reuse the worker instance
    }

    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * 重置心跳超时定时器 - 已废弃，但保留空方法防止调用报错
   */
  private resetHeartbeatTimeout(): void {
    // Legacy support
  }

  /**
   * 🔧 优化：生成消息的唯一标识符用于去重
   */
  private getMessageHash(type: string, content: string, agentId?: string, sessionId?: string): string {
    return `${type}:${content}:${agentId || ''}:${sessionId || ''}`
  }

  /**
   * 🔧 优化：标记消息处理完成，从待处理集合中移除
   */
  private markMessageComplete(hash: string): void {
    this.pendingMessages.delete(hash)
  }

  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  sendMessage(content: string, agentId?: string, sessionId?: string): void {
    // 🔧 优化：请求去重 - 检查是否有相同的消息正在处理
    const messageHash = this.getMessageHash('message', content, agentId, sessionId)

    if (this.pendingMessages.has(messageHash)) {
      console.warn('⚠️ 重复消息被拦截:', content.substring(0, 50))
      return
    }

    // 后端期望的格式: { type, content, agentId, sessionId }
    // 不需要 data 包装层
    const message: any = {
      type: 'message',
      content,
      agentId,
      sessionId,
      timestamp: new Date().toISOString(),
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      // 添加到待处理集合
      this.pendingMessages.add(messageHash)

      this.ws.send(JSON.stringify(message))

      // 🔧 优化：设置超时自动清理（30秒后自动移除，防止永久阻塞）
      setTimeout(() => {
        this.markMessageComplete(messageHash)
      }, 30000)
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  // 发送带附件的聊天消息（例如内联CIF内容）
  sendChatWithAttachments(params: { content?: string; agentId?: string; sessionId?: string; attachments: Array<{ filename: string; content: string }> }): void {
    const { content, agentId, sessionId, attachments } = params

    // 🔧 优化：请求去重 - 使用附件文件名作为哈希的一部分
    const attachmentHash = attachments.map(a => a.filename).join(',')
    const messageHash = this.getMessageHash('chat_with_attachments', `${content || ''}:${attachmentHash}`, agentId, sessionId)

    if (this.pendingMessages.has(messageHash)) {
      console.warn('⚠️ 重复的附件消息被拦截:', attachments.map(a => a.filename).join(', '))
      return
    }

    const message: any = {
      type: 'chat_with_attachments',
      content,
      agentId,
      sessionId,
      attachments,
      timestamp: new Date().toISOString(),
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      // 添加到待处理集合
      this.pendingMessages.add(messageHash)

      this.ws.send(JSON.stringify(message))

      // 🔧 优化：设置超时自动清理（30秒后自动移除）
      setTimeout(() => {
        this.markMessageComplete(messageHash)
      }, 30000)
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  /**
   * 🆕 发送停止请求
   */
  sendStopRequest(agentId?: string, sessionId?: string): void {
    const message: any = {
      type: 'stop_response',
      agentId,
      sessionId,
      timestamp: new Date().toISOString(),
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      console.log('🛑 发送停止请求:', { agentId, sessionId })
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  /**
   * 🆕 发送认证信息（基于 Cookie）
   * 在 WebSocket 连接成功后立即调用
   *
   * ✅ 完全基于 Cookie 认证（不使用 JWT Token）
   */
  private sendAuthToken(): void {
    try {
      // 获取 sessionId（确保与计费系统一致）
      const sessionId = localStorage.getItem('researchmind_session_id') || this.clientId

      // ✅ 从 Cookie 读取 Bohrium 凭证（唯一认证来源）
      const appAccessKey = this.getCookie('appAccessKey')
      const clientName = this.getCookie('clientName')

      console.log('🍪 Cookie 凭证:', {
        appAccessKey: appAccessKey ? `${appAccessKey.substring(0, 8)}...` : 'null',
        clientName: clientName || 'null'
      })

      // 发送认证消息（仅包含 Cookie 凭证）
      this.send({
        type: 'auth',
        data: {
          timestamp: Date.now(),
          // ✅ Cookie 凭证（如果存在）
          appAccessKey: appAccessKey || undefined,
          clientName: clientName || undefined
        },
        sessionId
      })

      if (appAccessKey) {
        console.log('✅ 已发送 Cookie 凭证进行认证 (sessionId:', sessionId, ')')
      } else {
        console.warn('⚠️ 未检测到 Cookie 凭证，计费功能将不可用')
      }
    } catch (error) {
      console.error('❌ 发送认证信息失败:', error)
    }
  }

  /**
   * 获取 Cookie 值
   */
  private getCookie(name: string): string | null {
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) {
      return parts.pop()?.split(';').shift() || null
    }
    return null
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler)
    return () => {
      const index = this.messageHandlers.indexOf(handler)
      if (index > -1) {
        this.messageHandlers.splice(index, 1)
      }
    }
  }

  onConnection(handler: ConnectionHandler): () => void {
    this.connectionHandlers.push(handler)
    return () => {
      const index = this.connectionHandlers.indexOf(handler)
      if (index > -1) {
        this.connectionHandlers.splice(index, 1)
      }
    }
  }

  private notifyMessageHandlers(message: WebSocketMessage): void {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message)
      } catch (error) {
        console.error('Error in message handler:', error)
      }
    })
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected)
      } catch (error) {
        console.error('Error in connection handler:', error)
      }
    })
  }

  private scheduleReconnect(): void {
    // 防止在已经连接或正在连接时重连
    if (this.isConnected || this.isConnecting) {
      console.log('🚫 Skipping reconnect - already connected or connecting')
      return
    }

    this.reconnectAttempts++
    // 限制最大重连延迟为30秒，并在几次尝试后保持恒定，防止等待时间过长
    const maxDelay = 30000
    // ⚡ 优化：首次重连只需1秒，加快网络抖动恢复
    const baseDelay = this.reconnectAttempts === 1 ? 1000 : this.reconnectInterval
    const calculatedDelay = baseDelay * Math.pow(1.5, this.reconnectAttempts - 1)
    const delay = Math.min(calculatedDelay, maxDelay)

    const maxAttemptsLog = this.maxReconnectAttempts === -1 ? '∞' : this.maxReconnectAttempts
    console.log(`🔄 Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${maxAttemptsLog})`)

    setTimeout(() => {
      // 再次检查状态，避免重复连接
      if (this.isConnected || this.isConnecting) {
        console.log('🚫 Skipping delayed reconnect - already connected or connecting')
        return
      }

      this.connect().catch(error => {
        console.error('❌ Reconnection failed:', error)
        // Check if we should continue reconnecting:
        // 1. If maxReconnectAttempts is -1 (infinite)
        // 2. Or if current attempts < max allowed
        if (this.maxReconnectAttempts === -1 || this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        } else {
          console.log('🚫 Max reconnect attempts reached')
        }
      })
    }, delay)
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getClientId(): string {
    return this.clientId
  }

  /**
   * 🆕 请求会话计费统计（通过 WebSocket）
   */
  requestConversationStats(conversationId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'get_conversation_stats',
        conversationId,
        timestamp: new Date().toISOString(),
      }
      console.log('📊 [WebSocket] 请求会话计费统计:', conversationId)
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('⚠️ WebSocket 未连接，无法请求会话统计')
    }
  }

  /**
   * 🆕 请求用户计费统计（通过 WebSocket）
   */
  requestUserStats(userId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'get_user_stats',
        userId,
        timestamp: new Date().toISOString(),
      }
      console.log('📊 [WebSocket] 请求用户计费统计:', userId)
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('⚠️ WebSocket 未连接，无法请求用户统计')
    }
  }

  /**
   * 🆕 请求全局计费统计（通过 WebSocket）
   */
  requestGlobalStats(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'get_global_stats',
        timestamp: new Date().toISOString(),
      }
      console.log('📊 [WebSocket] 请求全局计费统计')
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('⚠️ WebSocket 未连接，无法请求全局统计')
    }
  }

  /**
   * 🆕 请求恢复会话状态（重连后使用）
   * 通知服务器重新发送当前会话的任务状态
   */
  requestSessionRecovery(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const sessionId = localStorage.getItem('researchmind_session_id')
      const message = {
        type: 'recover_session',
        sessionId: sessionId || undefined,
        clientId: this.clientId,
        timestamp: new Date().toISOString(),
      }
      console.log('🔄 [WebSocket] 请求恢复会话状态:', { sessionId, clientId: this.clientId })
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('⚠️ WebSocket 未连接，无法请求会话恢复')
    }
  }
}

// 创建全局WebSocket实例
export const wsService = new WebSocketService()

// React Hook for WebSocket - 统一使用 wsService
export const useWebSocket = () => {
  console.log('🔧 Using wsService instead of separate hook')
  return wsService
}
