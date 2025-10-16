import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Agent, ChatSession, Message, UserSettings, CrystalStructure } from '../types'
import { forceSaveState, validateSessionData } from '../utils/storage'

// 声子谱图片接口
export interface PhononImage {
  name: string
  path?: string
  url?: string
  filename?: string
  type: 'phonon_dispersion' | 'phonon_dos' | 'phonon' | 'band' | 'dos' | string
  description?: string
  base64?: string
}

interface AppState {
  // 智能体相关
  agents: Agent[]
  currentAgent: Agent | null

  // 聊天相关
  sessions: ChatSession[]
  currentSession: ChatSession | null
  messages: Message[]

  // UI状态
  sidebarOpen: boolean

  // 结构数据
  currentStructure: CrystalStructure | null
  structureList: CrystalStructure[]  // 数据库查询返回的结构列表
  currentSessionStructures: CrystalStructure[]  // 当前会话的结构列表

  // 声子谱数据
  phononImages: PhononImage[]  // 全局声子谱图片（已废弃，保留用于兼容）
  currentSessionPhononImages: PhononImage[]  // 当前会话的声子谱图片
  showPhononVisualization: boolean
  phononDisplayMode: 'fullscreen' | 'bottom' | 'panel'

  // 用户设置
  settings: UserSettings

  // WebSocket连接状态
  connected: boolean

  // 加载状态
  isLoading: boolean
  loadingMessage: string

  // Actions
  setAgents: (agents: Agent[]) => void
  setCurrentAgent: (agent: Agent | null) => void

  setSessions: (sessions: ChatSession[]) => void
  setCurrentSession: (session: ChatSession | null) => void
  addMessage: (message: Message) => void
  updateMessage: (messageId: string, updates: Partial<Message>) => void

  setSidebarOpen: (open: boolean) => void

  setCurrentStructure: (structure: CrystalStructure | null) => void
  setStructureList: (structures: CrystalStructure[]) => void
  addToStructureList: (structure: CrystalStructure) => void
  clearStructureList: () => void
  setCurrentSessionStructures: (structures: CrystalStructure[]) => void
  addToCurrentSessionStructures: (structure: CrystalStructure) => void
  clearCurrentSessionStructures: () => void

  // 声子谱管理
  setPhononImages: (images: PhononImage[]) => void
  addPhononImage: (image: PhononImage) => void
  clearPhononImages: () => void
  setCurrentSessionPhononImages: (images: PhononImage[]) => void
  addToCurrentSessionPhononImages: (image: PhononImage) => void
  clearCurrentSessionPhononImages: () => void
  setShowPhononVisualization: (show: boolean) => void
  setPhononDisplayMode: (mode: 'fullscreen' | 'bottom' | 'panel') => void

  updateSettings: (settings: Partial<UserSettings>) => void

  setConnected: (connected: boolean) => void

  // 加载状态管理
  setIsLoading: (loading: boolean) => void
  setLoadingMessage: (message: string) => void

  // 会话管理
  createSession: (title: string, agentId: string) => ChatSession
  deleteSession: (sessionId: string) => void
  deleteAllSessions: () => void
  clearSession: (sessionId: string) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void

  // 存储管理
  forceSave: () => void
}

const defaultSettings: UserSettings = {
  theme: 'light',
  language: 'zh',
  defaultAgent: 'deep_research_agent',
  autoSave: true,
  notifications: true,
  apiEndpoint: import.meta.env.VITE_API_URL || 'http://localhost:8000',
}

const defaultAgents: Agent[] = [
  {
    id: 'deep_research_agent',
    name: '文献研究助手',
    description: '专门用于文献搜索、分析和研究的AI助手，可以帮您查找相关论文、分析研究趋势。',
    type: 'literature',
    capabilities: ['literature_search', 'paper_analysis', 'trend_analysis'],
    status: 'active',
  },
  {
    id: 'database_agent',
    name: '数据库查询助手',
    description: '专门用于材料数据库查询和数据检索的AI助手，可以帮您查找材料属性和实验数据。',
    type: 'database',
    capabilities: ['database_query', 'data_retrieval', 'property_search'],
    status: 'active',
  },
  {
    id: 'simulation_agent',
    name: '仿真计算助手',
    description: '专门用于分子建模和计算仿真的AI助手，可以帮您进行分子动力学模拟和量子化学计算。',
    type: 'simulation',
    capabilities: ['molecular_modeling', 'simulation', 'quantum_calculation'],
    status: 'active',
  },
]

// 修复从 localStorage 恢复的会话数据
const fixRestoredSessions = (sessions: ChatSession[]): ChatSession[] => {
  return sessions.map(session => ({
    ...session,
    messages: session.messages || [],  // 确保有 messages 数组
    createdAt: session.createdAt ? new Date(session.createdAt) : new Date(),
    updatedAt: session.updatedAt ? new Date(session.updatedAt) : new Date(),
  }))
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 初始状态
      agents: defaultAgents,
      currentAgent: defaultAgents[0],
      
      sessions: [],
      currentSession: null,
      messages: [],

      sidebarOpen: true,

      currentStructure: null,
      structureList: [],
      currentSessionStructures: [],

      phononImages: [],
      currentSessionPhononImages: [],
      showPhononVisualization: false,
      phononDisplayMode: 'fullscreen',

      settings: defaultSettings,

      connected: false,

      isLoading: false,
      loadingMessage: '智能体正在思考...',

      // Actions
      setAgents: (agents) => set({ agents }),
      setCurrentAgent: (agent) => set({ currentAgent: agent }),
      
      setSessions: (sessions) => set({ sessions }),
      setCurrentSession: (session) => {
        console.log('切换会话:', session?.id, '消息数:', session?.messages?.length || 0)

        const { sessions, currentSession, currentSessionStructures, currentSessionPhononImages } = get()

        // 保存当前会话的数据到会话对象中
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].structures = currentSessionStructures
            sessions[sessionIndex].phononImages = currentSessionPhononImages
            console.log('💾 保存当前会话数据:', currentSession.id, '结构数:', currentSessionStructures.length, '图片数:', currentSessionPhononImages.length)
          }
        }

        if (session) {
          // 确保 session 有 messages 属性
          if (!session.messages) {
            session.messages = []
          }

          // 从会话列表中获取最新的会话数据，确保消息是最新的
          const latestSession = sessions.find(s => s.id === session.id)
          const sessionToUse = latestSession || session

          console.log('使用会话数据:', sessionToUse.id, '消息数:', sessionToUse.messages?.length || 0)

          // 恢复新会话的数据
          const newStructures = sessionToUse.structures || []
          const newPhononImages = sessionToUse.phononImages || []
          const newCurrentStructure = newStructures.length > 0 ? newStructures[newStructures.length - 1] : null

          console.log('🔄 恢复会话数据:', sessionToUse.id, '结构数:', newStructures.length, '图片数:', newPhononImages.length)

          set({
            sessions: sessions,  // 更新会话列表（包含保存的数据）
            currentSession: sessionToUse,
            messages: sessionToUse.messages || [],
            currentSessionStructures: newStructures,
            currentStructure: newCurrentStructure,
            currentSessionPhononImages: newPhononImages
          })
        } else {
          // 清空当前会话
          set({
            currentSession: null,
            messages: [],
            currentSessionStructures: [],
            currentStructure: null,
            currentSessionPhononImages: []
          })
        }
      },
      
      addMessage: (message) => {
        const { currentSession, sessions } = get()
        const newMessages = [...get().messages, message]

        // 更新当前会话
        if (currentSession) {
          const updatedSession = {
            ...currentSession,
            messages: newMessages,
            updatedAt: new Date(),
          }

          const updatedSessions = sessions.map(s =>
            s.id === currentSession.id ? updatedSession : s
          )

          console.log('添加消息到会话:', currentSession.id, '新消息数:', newMessages.length)

          // 一次性更新所有相关状态，确保数据一致性
          set({
            messages: newMessages,
            currentSession: updatedSession,
            sessions: updatedSessions
          })
          
          // 强制触发持久化存储
          setTimeout(() => {
            const currentState = get()
            forceSaveState(currentState)
          }, 100)
        } else {
          console.warn('添加消息时没有当前会话')
          set({ messages: newMessages })
        }
      },
      
      updateMessage: (messageId, updates) => {
        const { currentSession, sessions } = get()
        const newMessages = get().messages.map(msg =>
          msg.id === messageId ? { ...msg, ...updates } : msg
        )
        
        // 更新当前会话
        if (currentSession) {
          const updatedSession = {
            ...currentSession,
            messages: newMessages,
            updatedAt: new Date(),
          }
          
          const updatedSessions = sessions.map(s => 
            s.id === currentSession.id ? updatedSession : s
          )
          
          // 一次性更新所有相关状态，确保数据一致性
          set({ 
            messages: newMessages,
            currentSession: updatedSession,
            sessions: updatedSessions
          })
          
          // 强制触发持久化存储
          setTimeout(() => {
            const currentState = get()
            forceSaveState(currentState)
          }, 100)
        } else {
          set({ messages: newMessages })
        }
      },
      
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      setCurrentStructure: (structure) => set({ currentStructure: structure }),
      setStructureList: (structures) => set({ structureList: structures }),
      addToStructureList: (structure) => {
        const { structureList } = get()
        set({ structureList: [...structureList, structure] })
      },
      clearStructureList: () => set({ structureList: [] }),

      setCurrentSessionStructures: (structures) => {
        set({ currentSessionStructures: structures })

        // 同时更新当前会话对象
        const { currentSession, sessions } = get()
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].structures = structures
            set({ sessions: sessions })
          }
        }
      },
      addToCurrentSessionStructures: (structure) => {
        const { currentSessionStructures, currentSession, sessions } = get()
        const newStructures = [...currentSessionStructures, structure]
        console.log('➕ 添加结构到当前会话:', structure.formula || 'unknown', '总数:', newStructures.length)
        set({ currentSessionStructures: newStructures })

        // 同时更新当前会话对象
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].structures = newStructures
            set({ sessions: sessions })
          }
        }

        // 强制触发持久化
        setTimeout(() => {
          const currentState = get()
          forceSaveState(currentState)
          console.log('💾 保存结构数据 - 结构数:', currentState.currentSessionStructures.length)
        }, 100)
      },
      clearCurrentSessionStructures: () => {
        set({ currentSessionStructures: [] })

        // 同时更新当前会话对象
        const { currentSession, sessions } = get()
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].structures = []
            set({ sessions: sessions })
          }
        }
      },

      // 声子谱管理
      setPhononImages: (images) => set({ phononImages: images }),
      addPhononImage: (image) => {
        const { phononImages } = get()
        set({ phononImages: [...phononImages, image] })
      },
      clearPhononImages: () => set({ phononImages: [] }),

      // 当前会话声子谱管理
      setCurrentSessionPhononImages: (images) => {
        // 限制最多10个图片（用户要求）
        const limitedImages = images.slice(-10)
        set({ currentSessionPhononImages: limitedImages })

        // 同时更新当前会话对象
        const { currentSession, sessions } = get()
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].phononImages = limitedImages
            set({ sessions: sessions })
          }
        }
      },
      addToCurrentSessionPhononImages: (image) => {
        const { currentSessionPhononImages, currentSession, sessions } = get()
        const newImages = [...currentSessionPhononImages, image]
        // 限制最多10个图片（用户要求）
        const limitedImages = newImages.slice(-10)
        set({ currentSessionPhononImages: limitedImages })

        // 同时更新当前会话对象
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].phononImages = limitedImages
            set({ sessions: sessions })
          }
        }
      },
      clearCurrentSessionPhononImages: () => {
        set({ currentSessionPhononImages: [] })

        // 同时更新当前会话对象
        const { currentSession, sessions } = get()
        if (currentSession) {
          const sessionIndex = sessions.findIndex(s => s.id === currentSession.id)
          if (sessionIndex !== -1) {
            sessions[sessionIndex].phononImages = []
            set({ sessions: sessions })
          }
        }
      },

      setShowPhononVisualization: (show) => set({ showPhononVisualization: show }),
      setPhononDisplayMode: (mode) => set({ phononDisplayMode: mode }),

      updateSettings: (newSettings) =>
        set({ settings: { ...get().settings, ...newSettings } }),
      
      setConnected: (connected) => set({ connected }),
      
      // 加载状态管理
      setIsLoading: (loading) => set({ isLoading: loading }),
      setLoadingMessage: (message) => set({ loadingMessage: message }),
      
      // 会话管理
      createSession: (title, agentId) => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          title,
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          agentId,
        }
        
        const sessions = [...get().sessions, newSession]
        console.log('创建新会话:', newSession.id, '总会话数:', sessions.length)
        
        set({
          sessions,
          currentSession: newSession,
          messages: [],
          currentSessionStructures: [],  // 清空当前会话结构
          currentStructure: null,  // 清空当前结构
          currentSessionPhononImages: []  // 清空当前会话声子谱图片
        })
        
        // 强制触发持久化存储
        setTimeout(() => {
          const currentState = get()
          forceSaveState(currentState)
        }, 100)
        
        return newSession
      },
      
      deleteSession: (sessionId) => {
        const { sessions, currentSession } = get()
        const updatedSessions = sessions.filter(s => s.id !== sessionId)

        console.log('删除会话:', sessionId, '剩余会话数:', updatedSessions.length)

        // 如果删除的是当前会话，清空当前会话和消息
        const isCurrentSession = currentSession?.id === sessionId

        set({
          sessions: updatedSessions,
          currentSession: isCurrentSession ? null : currentSession,
          messages: isCurrentSession ? [] : get().messages
        })
      },

      deleteAllSessions: () => {
        console.log('清除所有会话')
        set({
          sessions: [],
          currentSession: null,
          messages: [],
          currentSessionStructures: [],
          currentStructure: null
        })
      },

      clearSession: (sessionId) => {
        const { sessions, currentSession } = get()
        const updatedSessions = sessions.map(s => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: [],
              updatedAt: new Date()
            }
          }
          return s
        })

        console.log('清除会话内容:', sessionId)

        // 如果清除的是当前会话,也清空当前消息和结构
        const isCurrentSession = currentSession?.id === sessionId

        set({
          sessions: updatedSessions,
          currentSession: isCurrentSession ? { ...currentSession, messages: [] } : currentSession,
          messages: isCurrentSession ? [] : get().messages,
          currentSessionStructures: isCurrentSession ? [] : get().currentSessionStructures,
          currentStructure: isCurrentSession ? null : get().currentStructure
        })
      },
      
      updateSession: (sessionId, updates) => {
        const sessions = get().sessions.map(s =>
          s.id === sessionId ? { ...s, ...updates, updatedAt: new Date() } : s
        )
        
        set({ sessions })
        
        // 如果更新的是当前会话，也更新currentSession
        const { currentSession } = get()
        if (currentSession?.id === sessionId) {
          set({ currentSession: { ...currentSession, ...updates, updatedAt: new Date() } })
        }
      },
      
      // 强制保存当前状态
      forceSave: () => {
        const currentState = get()
        forceSaveState(currentState)
        console.log('手动触发保存 - 会话数:', currentState.sessions.length, '消息数:', currentState.messages.length)
      },
    }),
    {
      name: 'researchmind-app-store',
      partialize: (state) => ({
        sessions: state.sessions,
        currentSession: state.currentSession,
        messages: state.messages,
        settings: state.settings,
        // 持久化结构数据
        currentStructure: state.currentStructure,
        currentSessionStructures: state.currentSessionStructures,
        // 持久化声子谱数据
        phononImages: state.phononImages,
        currentSessionPhononImages: state.currentSessionPhononImages,
        showPhononVisualization: state.showPhononVisualization,
        phononDisplayMode: state.phononDisplayMode,
        // 不持久化侧边栏状态，每次都使用默认值（true）
        // 这样可以避免用户关闭侧边栏后下次打开时看到空白界面
      }),
      // 恢复数据时修复会话结构
      onRehydrateStorage: () => (state) => {
        if (!state) return

        if (state.sessions) {
          // 验证会话数据完整性
          if (!validateSessionData(state.sessions)) {
            console.warn('⚠️ 检测到损坏的会话数据，重置为空')
            state.sessions = []
            state.currentSession = null
            state.messages = []
            return
          }

          state.sessions = fixRestoredSessions(state.sessions)
          console.log('✅ 恢复会话数据:', state.sessions.length, '个会话')

          // 如果有当前会话，确保消息正确恢复
          if (state.currentSession) {
            const currentSession = state.sessions.find(s => s.id === state.currentSession?.id)
            if (currentSession) {
              state.currentSession = currentSession
              state.messages = currentSession.messages || []
              console.log('✅ 恢复当前会话消息:', state.messages.length, '条消息')
            } else {
              // 如果当前会话不存在于会话列表中，清空当前会话
              console.log('⚠️ 当前会话不存在于会话列表中，清空当前会话')
              state.currentSession = null
              state.messages = []
            }
          } else if (state.messages && state.messages.length > 0) {
            // 如果没有当前会话但有消息，清空消息
            console.log('⚠️ 没有当前会话但有消息，清空消息')
            state.messages = []
          }
        } else {
          // 初始化空状态
          state.sessions = []
          state.currentSession = null
          state.messages = []
        }

        // 恢复结构数据
        if (state.currentSessionStructures && Array.isArray(state.currentSessionStructures)) {
          console.log('✅ 恢复结构数据:', state.currentSessionStructures.length, '个结构')
        } else {
          console.log('⚠️ 初始化空结构列表')
          state.currentSessionStructures = []
        }

        // 恢复当前结构
        if (state.currentStructure) {
          console.log('✅ 恢复当前结构:', state.currentStructure.formula || 'unknown')
        } else {
          state.currentStructure = null
        }

        // 恢复声子谱数据
        if (state.phononImages && state.phononImages.length > 0) {
          console.log('✅ 恢复声子谱图片:', state.phononImages.length, '张图片')
        }

        // 恢复当前会话声子谱数据
        if (state.currentSessionPhononImages && Array.isArray(state.currentSessionPhononImages)) {
          console.log('✅ 恢复当前会话声子谱图片:', state.currentSessionPhononImages.length, '张图片')
        } else {
          console.log('⚠️ 初始化空声子谱列表')
          state.currentSessionPhononImages = []
        }
      },
    }
  )
)