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
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
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
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
      this.isConnecting = false
      this.notifyConnectionHandlers(false)
    }
  }

  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  sendMessage(content: string, agentId?: string, sessionId?: string): void {
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
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  // 发送带附件的聊天消息（例如内联CIF内容）
  sendChatWithAttachments(params: { content?: string; agentId?: string; sessionId?: string; attachments: Array<{ filename: string; content: string }> }): void {
    const { content, agentId, sessionId, attachments } = params
    const message: any = {
      type: 'chat_with_attachments',
      content,
      agentId,
      sessionId,
      attachments,
      timestamp: new Date().toISOString(),
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
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
}

// 创建全局WebSocket实例
export const wsService = new WebSocketService()

// React Hook for WebSocket - 统一使用 wsService
export const useWebSocket = () => {
  console.log('🔧 Using wsService instead of separate hook')
  return wsService
}
