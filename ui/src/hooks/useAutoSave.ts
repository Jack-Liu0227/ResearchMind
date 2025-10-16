import { useEffect, useRef } from 'react'
import { useAppStore } from '../store/useAppStore'

/**
 * 自动保存 Hook
 * 定期保存应用状态到 localStorage，确保数据不丢失
 */
export const useAutoSave = (intervalMs: number = 30000) => { // 默认30秒保存一次
  const forceSave = useAppStore(state => state.forceSave)
  const sessions = useAppStore(state => state.sessions)
  const messages = useAppStore(state => state.messages)
  const currentSession = useAppStore(state => state.currentSession)
  
  const lastSaveRef = useRef<{
    sessionsCount: number
    messagesCount: number
    currentSessionId: string | null
  }>({
    sessionsCount: 0,
    messagesCount: 0,
    currentSessionId: null
  })

  useEffect(() => {
    // 检查数据是否有变化
    const hasChanges = 
      lastSaveRef.current.sessionsCount !== sessions.length ||
      lastSaveRef.current.messagesCount !== messages.length ||
      lastSaveRef.current.currentSessionId !== currentSession?.id

    if (hasChanges) {
      console.log('检测到数据变化，触发自动保存')
      forceSave()
      
      // 更新最后保存的状态
      lastSaveRef.current = {
        sessionsCount: sessions.length,
        messagesCount: messages.length,
        currentSessionId: currentSession?.id || null
      }
    }
  }, [sessions, messages, currentSession, forceSave])

  useEffect(() => {
    // 定期自动保存
    const interval = setInterval(() => {
      console.log('定期自动保存触发')
      forceSave()
    }, intervalMs)

    return () => clearInterval(interval)
  }, [forceSave, intervalMs])

  // 页面卸载前保存
  useEffect(() => {
    const handleBeforeUnload = () => {
      console.log('页面卸载前保存数据')
      forceSave()
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        console.log('页面隐藏时保存数据')
        forceSave()
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [forceSave])
}