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
  private maxReconnectAttempts = 5
  private reconnectInterval = 1000
  private messageHandlers: MessageHandler[] = []
  private connectionHandlers: ConnectionHandler[] = []
  private clientId: string
  private isConnecting = false // 防止重复连接的标志
  private heartbeatInterval: number | null = null // 心跳定时器
  private heartbeatTimeout: number | null = null // 心跳超时定时器
  private readonly HEARTBEAT_INTERVAL = 30000 // 30秒发送一次心跳
  private readonly HEARTBEAT_TIMEOUT = 10000 // 10秒内未收到响应则认为连接断开

  // 🔧 优化：请求去重 - 跟踪待处理的消息
  private pendingMessages = new Set<string>() // 存储消息内容的哈希

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
        
        console.log(`🔌 连接 WebSocket: ${wsUrl}`)
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('✅ WebSocket 已连接')
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.notifyConnectionHandlers(true)

          // 启动心跳检测
          this.startHeartbeat()

          // 🆕 发送 JWT Token 进行认证
          this.sendAuthToken()

          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)

            // 处理心跳响应
            if (message.type === 'pong') {
              this.resetHeartbeatTimeout()
              return
            }

            this.notifyMessageHandlers(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          console.log('🔧 Connection was clean:', event.wasClean)
          console.log('🔧 Reconnect attempts:', this.reconnectAttempts, '/', this.maxReconnectAttempts)
          this.isConnecting = false
          this.notifyConnectionHandlers(false)

          // 停止心跳检测
          this.stopHeartbeat()

          // 只有在非正常关闭且未达到最大重试次数时才重连
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            console.log('🔄 Schedule reconnect...')
            this.scheduleReconnect()
          } else {
            console.log('🚫 No reconnect scheduled')
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          reject(error)
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  disconnect(): void {
    if (this.ws) {
      console.log('🔌 正在断开WebSocket连接...')
      this.stopHeartbeat()
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
      this.isConnecting = false
      this.notifyConnectionHandlers(false)
    }
  }

  /**
   * 启动心跳检测
   */
  private startHeartbeat(): void {
    console.log('💓 启动心跳检测')
    this.stopHeartbeat() // 先清除旧的定时器

    this.heartbeatInterval = window.setInterval(() => {
      if (this.isConnected) {
        console.log('💓 发送心跳 ping')
        this.send({ type: 'ping', data: { timestamp: Date.now() } })

        // 设置心跳超时检测
        this.heartbeatTimeout = window.setTimeout(() => {
          console.warn('💔 心跳超时，连接可能已断开')
          // 主动关闭连接，触发重连
          this.ws?.close(1006, 'Heartbeat timeout')
        }, this.HEARTBEAT_TIMEOUT)
      }
    }, this.HEARTBEAT_INTERVAL)
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      console.log('💓 停止心跳检测')
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }

  /**
   * 重置心跳超时定时器
   */
  private resetHeartbeatTimeout(): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
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

  // sendUserBohriumConfig 已删除
  // 用户配置现在通过登录流程（/api/auth/login-from-cookie）保存到数据库
  // WebSocket 认证时只需发送 JWT Token 即可

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
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`🔄 Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      // 再次检查状态，避免重复连接
      if (this.isConnected || this.isConnecting) {
        console.log('🚫 Skipping delayed reconnect - already connected or connecting')
        return
      }
      
      this.connect().catch(error => {
        console.error('❌ Reconnection failed:', error)
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
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
}

// 创建全局WebSocket实例
export const wsService = new WebSocketService()

// React Hook for WebSocket - 统一使用 wsService
export const useWebSocket = () => {
  console.log('🔧 Using wsService instead of separate hook')
  return wsService
}
