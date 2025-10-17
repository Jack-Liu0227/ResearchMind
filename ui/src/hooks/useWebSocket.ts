import { useEffect, useRef, useCallback } from 'react'
import { useAppStore } from '../store/useAppStore'
import { WebSocketMessage } from '../types'

interface UseWebSocketOptions {
  url?: string
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectAttempts?: number
  reconnectInterval?: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = import.meta.env.VITE_WS_URL || 'ws://0.0.0.0:50003/ws',
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectAttempts = 5,
    reconnectInterval = 1000,
  } = options

  const { setConnected, addMessage } = useAppStore()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const clientIdRef = useRef(`client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsUrl = `${url}/${clientIdRef.current}`
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        reconnectCountRef.current = 0
        onConnect?.()
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          
          // 处理消息
          if (message.type === 'message' && message.data) {
            const newMessage = {
              id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
              content: message.data.content,
              role: 'assistant' as const,
              timestamp: new Date(message.data.timestamp || Date.now()),
              agentId: message.data.agentId,
              agentName: message.data.agentName,
              type: message.data.type || 'text',
              metadata: message.data.metadata,
            }
            addMessage(newMessage)
          }
          
          onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setConnected(false)
        onDisconnect?.()

        // 自动重连
        if (!event.wasClean && reconnectCountRef.current < reconnectAttempts) {
          const delay = reconnectInterval * Math.pow(2, reconnectCountRef.current)
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectCountRef.current + 1}/${reconnectAttempts})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current++
            connect()
          }, delay)
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [url, setConnected, addMessage, onConnect, onDisconnect, onMessage, onError, reconnectAttempts, reconnectInterval])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    
    setConnected(false)
  }, [setConnected])

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const sendChatMessage = useCallback((content: string, agentId?: string, sessionId?: string) => {
    sendMessage({
      type: 'message',
      data: {
        content,
        agentId,
        sessionId,
        timestamp: new Date(),
      },
    })
  }, [sendMessage])

  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    connect,
    disconnect,
    sendMessage,
    sendChatMessage,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    clientId: clientIdRef.current,
  }
}