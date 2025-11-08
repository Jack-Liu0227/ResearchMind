/**
 * LocalStorage 管理工具
 */

const STORAGE_KEY = 'researchmind-app-store'
const VERSION_KEY = 'researchmind-version'
const CURRENT_VERSION = '2.0.0'

/**
 * 检查并清除旧版本的存储数据
 */
export function checkAndClearOldStorage(): void {
  try {
    const storedVersion = localStorage.getItem(VERSION_KEY)
    
    // 如果版本不匹配或不存在，清除旧数据
    if (storedVersion !== CURRENT_VERSION) {
      console.log('🔄 检测到版本更新，清除旧数据...')
      localStorage.removeItem(STORAGE_KEY)
      localStorage.setItem(VERSION_KEY, CURRENT_VERSION)
      console.log('✅ 旧数据已清除，使用新版本默认设置')
    }
  } catch (error) {
    console.error('清除存储时出错:', error)
  }
}

/**
 * 清除所有应用数据
 */
export function clearAllStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(VERSION_KEY)
    console.log('✅ 所有存储数据已清除')
  } catch (error) {
    console.error('清除存储时出错:', error)
  }
}

/**
 * 日期反序列化函数
 */
function reviveDates(key: string, value: any): any {
  // 检查是否是日期字符串格式
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) {
    const date = new Date(value)
    return isNaN(date.getTime()) ? value : date
  }
  // 检查特定的日期字段
  if ((key === 'timestamp' || key === 'createdAt' || key === 'updatedAt') && value) {
    const date = new Date(value)
    return isNaN(date.getTime()) ? new Date() : date
  }
  return value
}

/**
 * 获取存储数据
 */
export function getStorageData(): any {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data, reviveDates) : null
  } catch (error) {
    console.error('读取存储数据时出错:', error)
    return null
  }
}

/**
 * 检查存储数据是否有效
 */
export function isStorageValid(): boolean {
  try {
    const data = getStorageData()
    if (!data || !data.state) {
      return false
    }
    
    // 检查必要的字段
    const state = data.state
    if (typeof state.sidebarOpen !== 'boolean') {
      return false
    }
    
    return true
  } catch (error) {
    return false
  }
}

/**
 * 修复损坏的存储数据
 */
export function repairStorage(): void {
  try {
    const data = getStorageData()
    if (!data || !data.state) {
      console.log('⚠️ 存储数据损坏，重置为默认值')
      clearAllStorage()
      return
    }
    
    if (typeof data.state.sidebarOpen !== 'boolean') {
      data.state.sidebarOpen = false
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
      console.log('🔧 初始化侧边栏状态为默认值 (关闭)')
    }
  } catch (error) {
    console.error('修复存储时出错:', error)
    clearAllStorage()
  }
}

/**
 * 强制保存应用状态到 localStorage
 */
export function forceSaveState(state: any): void {
  try {
    // 在保存前，确保当前会话的数据已同步到 sessions 数组中
    let sessionsToSave = [...(state.sessions || [])]
    let updatedCurrentSession = state.currentSession

    if (state.currentSession) {
      const currentSessionIndex = sessionsToSave.findIndex(
        (s: any) => s.id === state.currentSession.id
      )

      if (currentSessionIndex !== -1) {
        // 更新当前会话的数据 - 使用最新的 currentSession* 数据
        const updatedSession = {
          ...sessionsToSave[currentSessionIndex],
          messages: state.messages || [],
          structures: state.currentSessionStructures || [],
          phononImages: state.currentSessionPhononImages || [],
          files: state.currentSessionFiles || [],
          updatedAt: new Date().toISOString(),
        }

        sessionsToSave[currentSessionIndex] = updatedSession
        updatedCurrentSession = updatedSession  // 使用更新后的会话对象

        console.log('💾 更新会话数据:', {
          sessionId: updatedSession.id,
          messagesCount: updatedSession.messages.length,
          structuresCount: updatedSession.structures.length,
          phononImagesCount: updatedSession.phononImages.length,
          filesCount: updatedSession.files.length,
        })
      } else {
        console.warn('⚠️ 当前会话不在 sessions 数组中:', state.currentSession.id)
      }
    }

    const dataToSave = {
      state: {
        sessions: sessionsToSave,
        currentSession: updatedCurrentSession || null,
        messages: state.messages || [],
        settings: state.settings || {},
        // 持久化结构数据
        currentStructure: state.currentStructure || null,
        currentSessionStructures: state.currentSessionStructures || [],
        currentSessionFiles: state.currentSessionFiles || [],
        // 持久化声子谱数据
        phononImages: state.phononImages || [],
        currentSessionPhononImages: state.currentSessionPhononImages || [],
        showPhononVisualization: state.showPhononVisualization || false,
        phononDisplayMode: state.phononDisplayMode || 'fullscreen',
      },
      version: 0
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave))
    console.log(
      '💾 强制保存状态完成 - 会话数:',
      sessionsToSave.length,
      '消息数:',
      state.messages?.length || 0,
      '结构数:',
      state.currentSessionStructures?.length || 0,
      '文件数:',
      state.currentSessionFiles?.length || 0,
      '声子谱图片数:',
      state.currentSessionPhononImages?.length || 0
    )
  } catch (error) {
    console.error('强制保存状态时出错:', error)
  }
}

/**
 * 验证会话数据完整性
 */
export function validateSessionData(sessions: any[]): boolean {
  if (!Array.isArray(sessions)) {
    return false
  }
  
  return sessions.every(session => {
    return session && 
           typeof session.id === 'string' &&
           typeof session.title === 'string' &&
           Array.isArray(session.messages) &&
           session.createdAt &&
           session.updatedAt
  })
}

/**
 * 获取 localStorage 使用情况
 */
export function getStorageUsage(): { used: number; total: number; percentage: number } {
  let used = 0
  let total = 5 * 1024 * 1024 // 默认 5MB

  try {
    // 计算当前使用量
    for (const key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        used += localStorage[key].length + key.length
      }
    }

    // 尝试估算总容量（通过二分查找）
    try {
      const testKey = '__storage_test__'
      let low = 0
      let high = 10 * 1024 * 1024 // 10MB

      while (low < high) {
        const mid = Math.floor((low + high) / 2)
        try {
          localStorage.setItem(testKey, 'x'.repeat(mid))
          localStorage.removeItem(testKey)
          low = mid + 1
        } catch {
          high = mid
        }
      }

      total = low + used
    } catch {
      // 如果测试失败，使用默认值
    }
  } catch (error) {
    console.error('计算存储使用量时出错:', error)
  }

  return {
    used,
    total,
    percentage: (used / total) * 100
  }
}

/**
 * 清理旧会话数据（保留最近的 N 个会话）
 */
export function cleanupOldSessions(keepCount: number = 10): void {
  try {
    const data = getStorageData()
    if (!data || !data.state || !Array.isArray(data.state.sessions)) {
      return
    }

    const sessions = data.state.sessions
    if (sessions.length <= keepCount) {
      return
    }

    // 按更新时间排序，保留最新的 N 个
    const sortedSessions = [...sessions].sort((a, b) => {
      const dateA = new Date(a.updatedAt || a.createdAt).getTime()
      const dateB = new Date(b.updatedAt || b.createdAt).getTime()
      return dateB - dateA
    })

    const sessionsToKeep = sortedSessions.slice(0, keepCount)
    const removedCount = sessions.length - keepCount

    data.state.sessions = sessionsToKeep

    // 如果当前会话被删除，清除它
    if (data.state.currentSession &&
        !sessionsToKeep.find(s => s.id === data.state.currentSession.id)) {
      data.state.currentSession = null
      data.state.messages = []
      data.state.currentSessionStructures = []
      data.state.currentSessionFiles = []
      data.state.currentSessionPhononImages = []
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    console.log(`🧹 清理了 ${removedCount} 个旧会话，保留最新的 ${keepCount} 个`)
  } catch (error) {
    console.error('清理旧会话时出错:', error)
  }
}

/**
 * 智能存储管理：当接近配额时自动清理
 */
export function smartStorageManagement(): void {
  try {
    const usage = getStorageUsage()
    console.log(`📊 存储使用情况: ${(usage.used / 1024).toFixed(2)} KB / ${(usage.total / 1024).toFixed(2)} KB (${usage.percentage.toFixed(1)}%)`)

    // 如果使用超过 80%，开始清理
    if (usage.percentage > 80) {
      console.warn('⚠️ 存储使用超过 80%，开始清理...')

      // 先清理旧会话
      cleanupOldSessions(5)

      const newUsage = getStorageUsage()
      console.log(`📊 清理后使用情况: ${(newUsage.used / 1024).toFixed(2)} KB / ${(newUsage.total / 1024).toFixed(2)} KB (${newUsage.percentage.toFixed(1)}%)`)

      // 如果还是超过 90%，清除所有数据
      if (newUsage.percentage > 90) {
        console.error('❌ 存储空间严重不足，清除所有数据')
        clearAllStorage()
      }
    }
  } catch (error) {
    console.error('智能存储管理时出错:', error)
  }
}

/**
 * 初始化存储
 * 在应用启动时调用
 */
export function initStorage(): void {
  console.log('🚀 初始化存储系统...')

  try {
    // 检查存储使用情况
    smartStorageManagement()

    // 只修复侧边栏状态，不清除其他数据
    const data = getStorageData()
    if (data && data.state && typeof data.state.sidebarOpen !== 'boolean') {
      data.state.sidebarOpen = false
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    }
    console.log('✅ 存储系统初始化完成')
  } catch (error) {
    console.error('初始化存储时出错:', error)
    // 如果是配额错误，清除所有数据
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.error('❌ 存储配额超限，清除所有数据')
      clearAllStorage()
    }
  }
}

