import React, { useEffect, useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { getStorageData, isStorageValid, repairStorage, clearAllStorage } from '../utils/storage'
import toast from 'react-hot-toast'

interface StorageValidatorProps {
  children: React.ReactNode
}

/**
 * 存储验证组件
 * 在应用启动时验证和修复存储数据
 */
const StorageValidator: React.FC<StorageValidatorProps> = ({ children }) => {
  const [isValidating, setIsValidating] = useState(true)
  const [validationComplete, setValidationComplete] = useState(false)
  const { sessions, currentSession, messages, forceSave } = useAppStore()

  useEffect(() => {
    const validateAndRepairStorage = async () => {
      try {
        console.log('🔍 开始验证存储数据...')
        
        // 检查存储数据是否有效
        if (!isStorageValid()) {
          console.log('⚠️ 检测到无效的存储数据，尝试修复...')
          repairStorage()
        }

        // 获取存储数据
        const storageData = getStorageData()
        if (storageData && storageData.state) {
          const { sessions: storedSessions, currentSession: storedCurrentSession } = storageData.state
          
          // 验证会话数据完整性
          if (storedSessions && Array.isArray(storedSessions)) {
            let hasCorruptedData = false
            
            // 检查每个会话的完整性
            for (const session of storedSessions) {
              if (!session.id || !session.title || !Array.isArray(session.messages)) {
                hasCorruptedData = true
                break
              }
              
              // 检查消息的完整性
              for (const message of session.messages) {
                if (!message.id || !message.content || !message.role || !message.timestamp) {
                  hasCorruptedData = true
                  break
                }
              }
              
              if (hasCorruptedData) break
            }
            
            if (hasCorruptedData) {
              console.log('❌ 检测到损坏的会话数据，清除所有数据')
              clearAllStorage()
              toast.error('检测到损坏的数据，已重置为初始状态')
            } else {
              console.log('✅ 存储数据验证通过')
              
              // 验证当前会话是否存在于会话列表中
              if (storedCurrentSession && !storedSessions.find(s => s.id === storedCurrentSession.id)) {
                console.log('⚠️ 当前会话不存在于会话列表中，将被清除')
                // 这个问题会在 store 的 onRehydrateStorage 中处理
              }
            }
          }
        }

        // 延迟一点时间确保 Zustand 完成数据恢复
        await new Promise(resolve => setTimeout(resolve, 100))
        
        console.log('✅ 存储验证完成')
        console.log('当前状态 - 会话数:', sessions.length, '消息数:', messages.length, '当前会话:', currentSession?.id)
        
        setValidationComplete(true)
        setIsValidating(false)
        
      } catch (error) {
        console.error('存储验证过程中出错:', error)
        clearAllStorage()
        toast.error('存储验证失败，已重置为初始状态')
        setValidationComplete(true)
        setIsValidating(false)
      }
    }

    validateAndRepairStorage()
  }, [sessions.length, messages.length, currentSession?.id, forceSave])

  // 如果正在验证，显示加载状态
  if (isValidating) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在验证数据完整性...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default StorageValidator