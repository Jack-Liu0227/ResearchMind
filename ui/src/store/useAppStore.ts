
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Agent, ChatSession, Message, UserSettings, CrystalStructure, SessionFile } from '../types'
import { forceSaveState, validateSessionData } from '../utils/storage'
import { API_CONFIG } from '../constants'

export interface PhononImage {
  name: string
  path?: string
  url?: string
  filename?: string
  type: 'phonon_dispersion' | 'phonon_dos' | 'phonon' | 'band' | 'dos' | string
  description?: string
  base64?: string
  timestamp?: string | number
  // 🆕 原始数据 CSV 文件路径
  dispersionCsvPath?: string  // 声子色散数据 CSV 路径
  dosCsvPath?: string         // 声子 DOS 数据 CSV 路径
}

// 🆕 功能扣费记录
export interface FeatureCharge {
  feature_type: string  // 功能类型（如 'relaxation', 'phonon', 'kappa'）
  photons: number  // 扣费光子数
  success: boolean  // 扣费是否成功
  error_message?: string  // 扣费失败原因（可选）
  timestamp: string  // 扣费时间
  conversation_id?: string  // 🆕 所属会话 ID（用于用户统计）
}

export interface BillingData {
  session_total_tokens: number
  session_total_photons: number
  requests_count: number
  current_tokens?: number  // 本次对话的 tokens
  current_photons?: number  // 本次对话的光子
  model_name?: string  // 使用的模型
  charged?: boolean  // 🔧 新增：是否已扣费
  billing_source?: string  // 🔧 新增：计费来源（Cookie/用户配置/开发者默认）
  feature_charges?: FeatureCharge[]  // 🆕 功能扣费明细
}

// 🆕 用户计费统计
export interface UserBillingStats {
  user_id: string
  total_tokens: number
  total_photons_charged: number  // 🔧 修复：匹配后端字段名
  total_requests: number  // 🔧 修复：匹配后端字段名
  total_conversations: number  // 🔧 修复：匹配后端字段名
  has_user_config?: boolean
  billing_source?: string
  total_feature_charges?: number  // 🆕 总扣费次数
  success_charges_count?: number  // 🆕 成功扣费次数
  failed_charges_count?: number  // 🆕 失败扣费次数
  success_photons?: number  // 🆕 成功扣费的光子数
  failed_photons?: number  // 🆕 失败扣费的光子数（应扣累计）
  recent_feature_charges?: FeatureCharge[]  // 🆕 最近 10 条扣费明细
}

// 🆕 全局计费统计
export interface GlobalBillingStats {
  total_tokens: number
  total_photons: number
  request_count: number
  user_count: number
  conversation_count: number
}

interface AppState {
  // Agents
  agents: Agent[]
  currentAgent: Agent | null

  // Chat state
  sessions: ChatSession[]
  currentSession: ChatSession | null
  messages: Message[]

  // UI flags
  sidebarOpen: boolean

  // Session scoped artefacts
  currentStructure: CrystalStructure | null
  structureList: CrystalStructure[]
  currentSessionStructures: CrystalStructure[]
  currentSessionFiles: SessionFile[]

  // Phonon assets
  phononImages: PhononImage[]
  currentSessionPhononImages: PhononImage[]
  showPhononVisualization: boolean
  phononDisplayMode: 'fullscreen' | 'bottom' | 'panel'

  // 🆕 UI 配置：控制对话框中的文件展示
  uiConfig: {
    showFilesInChat: boolean  // 是否在对话框中显示 CSV/图片等文件（右侧边栏始终显示）
  }

  // Settings and connectivity
  settings: UserSettings
  connected: boolean

  // Loading indicator
  isLoading: boolean
  loadingMessage: string

  // Billing data
  billingData: BillingData | null
  // 🆕 用户和全局计费统计
  userBillingStats: UserBillingStats | null
  globalBillingStats: GlobalBillingStats | null

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
  removeFromCurrentSessionStructures: (structureId: string) => void
  clearCurrentSessionStructures: () => void
  setCurrentSessionFiles: (files: SessionFile[]) => void
  addToCurrentSessionFiles: (file: SessionFile) => void
  clearCurrentSessionFiles: () => void

  setPhononImages: (images: PhononImage[]) => void
  addPhononImage: (image: PhononImage) => void
  clearPhononImages: () => void
  setCurrentSessionPhononImages: (images: PhononImage[]) => void
  addToCurrentSessionPhononImages: (image: PhononImage) => void
  clearCurrentSessionPhononImages: () => void
  setShowPhononVisualization: (show: boolean) => void
  setPhononDisplayMode: (mode: 'fullscreen' | 'bottom' | 'panel') => void

  setShowFilesInChat: (show: boolean) => void

  updateSettings: (settings: Partial<UserSettings>) => void

  setConnected: (connected: boolean) => void

  setIsLoading: (loading: boolean) => void
  setLoadingMessage: (message: string) => void

  setBillingData: (data: BillingData | null) => void
  updateBillingData: (data: Partial<BillingData>) => void
  // 🆕 用户和全局计费统计的 setter
  setUserBillingStats: (data: UserBillingStats | null) => void
  setGlobalBillingStats: (data: GlobalBillingStats | null) => void

  createSession: (title: string, agentId: string) => ChatSession
  deleteSession: (sessionId: string) => void
  deleteAllSessions: () => void
  clearSession: (sessionId: string) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void

  forceSave: () => void
}

const MAX_SESSION_FILES = 20
const MAX_SESSION_PHONON_IMAGES = 10

const defaultSettings: UserSettings = {
  theme: 'light',
  language: 'zh',
  defaultAgent: 'deep_research_agent',
  autoSave: true,
  notifications: true,
  apiEndpoint: API_CONFIG.BASE_URL,
  // 🆕 UI 配置默认值
  leftSidebarOpen: true,     // 左侧边栏默认展开
  rightSidebarOpen: true,    // 右侧边栏默认展开
  showPricingModal: true,    // 登录时默认显示定价页面
}

const defaultAgents: Agent[] = [
  {
    id: 'deep_research_agent',
    name: '文献研究助手',
    description: '专门用于文献搜索、分析和研究的 AI 助手，可以帮您查找相关论文、分析研究趋势。',
    type: 'literature',
    capabilities: ['literature_search', 'paper_analysis', 'trend_analysis'],
    status: 'active',
  },
  {
    id: 'database_agent',
    name: '数据库查询助手',
    description: '专门用于材料数据库查询和数据检索的 AI 助手，可以帮您查找材料属性和实验数据。',
    type: 'database',
    capabilities: ['database_query', 'data_retrieval', 'property_search'],
    status: 'active',
  },
  {
    id: 'simulation_agent',
    name: '仿真计算助手',
    description: '专门用于分子建模和计算仿真的 AI 助手，可以帮您进行分子动力学模拟和量子化学计算。',
    type: 'simulation',
    capabilities: ['molecular_modeling', 'simulation', 'quantum_calculation'],
    status: 'active',
  },
]

const fixRestoredSessions = (sessions: ChatSession[]): ChatSession[] =>
  sessions.map((session) => ({
    ...session,
    messages: session.messages || [],
    structures: session.structures || [],
    phononImages: session.phononImages || [],
    files: session.files || [],
    createdAt: session.createdAt ? new Date(session.createdAt) : new Date(),
    updatedAt: session.updatedAt ? new Date(session.updatedAt) : new Date(),
  }))

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      agents: defaultAgents,
      currentAgent: defaultAgents[0],

      sessions: [],
      currentSession: null,
      messages: [],

      sidebarOpen: true,  // 🆕 默认展开左侧边栏

      currentStructure: null,
      structureList: [],
      currentSessionStructures: [],
      currentSessionFiles: [],

      phononImages: [],
      currentSessionPhononImages: [],
      showPhononVisualization: false,
      phononDisplayMode: 'fullscreen',

      uiConfig: {
        showFilesInChat: false,  // 默认显示文件
      },

      settings: defaultSettings,

      connected: false,

      isLoading: false,
      loadingMessage: '智能体正在思考...',

      billingData: null,
      userBillingStats: null,
      globalBillingStats: null,

      setAgents: (agents) => set({ agents }),
      setCurrentAgent: (agent) => set({ currentAgent: agent }),

      setSessions: (sessions) => set({ sessions }),

      setCurrentSession: (session) => {
        const state = get()
        const { sessions, currentSession, currentSessionStructures, currentSessionPhononImages, currentSessionFiles } = state

        if (currentSession) {
          const idx = sessions.findIndex((s) => s.id === currentSession.id)
          if (idx !== -1) {
            const updated = {
              ...sessions[idx],
              structures: currentSessionStructures,
              phononImages: currentSessionPhononImages,
              files: currentSessionFiles,
            }
            const nextSessions = [...sessions]
            nextSessions[idx] = updated
            set({ sessions: nextSessions })
          }
        }

        if (!session) {
          set({
            currentSession: null,
            messages: [],
            currentStructure: null,
            currentSessionStructures: [],
            currentSessionFiles: [],
            currentSessionPhononImages: [],
          })
          return
        }

        const latest = sessions.find((s) => s.id === session.id) || session
        const restoredStructures = latest.structures || []
        const restoredFiles = latest.files || []
        const restoredPhonon = latest.phononImages || []

        set({
          currentSession: latest,
          messages: latest.messages || [],
          currentStructure: restoredStructures.slice(-1)[0] ?? null,
          currentSessionStructures: restoredStructures,
          currentSessionFiles: restoredFiles,
          currentSessionPhononImages: restoredPhonon,
        })
      },

      addMessage: (message) => {
        const state = get()
        const { currentSession, sessions, messages } = state
        const updatedMessages = [...messages, message]

        if (!currentSession) {
          set({ messages: updatedMessages })
          return
        }

        const updatedSession: ChatSession = {
          ...currentSession,
          messages: updatedMessages,
          updatedAt: new Date(),
        }

        const nextSessions = sessions.map((s) => (s.id === currentSession.id ? updatedSession : s))

        set({
          messages: updatedMessages,
          currentSession: updatedSession,
          sessions: nextSessions,
        })

        setTimeout(() => forceSaveState(get()), 100)
      },

      updateMessage: (messageId, updates) => {
        const state = get()
        const { currentSession, sessions, messages } = state
        const updatedMessages = messages.map((msg) => (msg.id === messageId ? { ...msg, ...updates } : msg))

        if (!currentSession) {
          set({ messages: updatedMessages })
          return
        }

        const updatedSession: ChatSession = {
          ...currentSession,
          messages: updatedMessages,
          updatedAt: new Date(),
        }

        const nextSessions = sessions.map((s) => (s.id === currentSession.id ? updatedSession : s))

        set({
          messages: updatedMessages,
          currentSession: updatedSession,
          sessions: nextSessions,
        })
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
        const { currentStructure } = get()
        set({ currentSessionStructures: structures })

        // 如果当前没有选中的结构，自动选中第一个
        if (!currentStructure && structures.length > 0) {
          set({ currentStructure: structures[0] })
        }

        const { currentSession, sessions } = get()
        if (currentSession) {
          const nextSessions = sessions.map((s) =>
            s.id === currentSession.id ? { ...s, structures } : s
          )
          set({ sessions: nextSessions })
        }
      },

      addToCurrentSessionStructures: (structure) => {
        const { currentSessionStructures, currentStructure } = get()
        const updatedStructures = [...currentSessionStructures, structure]
        set({ currentSessionStructures: updatedStructures })

        // 如果当前没有选中的结构，自动选中第一个
        if (!currentStructure && updatedStructures.length > 0) {
          set({ currentStructure: updatedStructures[0] })
        }

        get().setCurrentSessionStructures(updatedStructures)
        setTimeout(() => forceSaveState(get()), 100)
      },

      removeFromCurrentSessionStructures: (structureId) => {
        const { currentSessionStructures, currentStructure } = get()
        const updatedStructures = currentSessionStructures.filter(s => s.id !== structureId)

        // If the removed structure was the current one, set current to the last remaining structure
        let newCurrentStructure = currentStructure
        if (currentStructure?.id === structureId) {
          newCurrentStructure = updatedStructures.length > 0 ? updatedStructures[updatedStructures.length - 1] : null
        }

        set({
          currentSessionStructures: updatedStructures,
          currentStructure: newCurrentStructure
        })
        get().setCurrentSessionStructures(updatedStructures)
        setTimeout(() => forceSaveState(get()), 100)
      },

      clearCurrentSessionStructures: () => {
        set({ currentSessionStructures: [] })
        get().setCurrentSessionStructures([])
      },

      setCurrentSessionFiles: (files) => {
        set({ currentSessionFiles: files })

        const { currentSession, sessions } = get()
        if (currentSession) {
          const nextSessions = sessions.map((s) =>
            s.id === currentSession.id ? { ...s, files } : s
          )
          set({
            sessions: nextSessions,
            currentSession: { ...currentSession, files },
          })
        }
      },

      addToCurrentSessionFiles: (file) => {
        const { currentSessionFiles } = get()
        const filtered = currentSessionFiles.filter((item) => item.id !== file.id)
        const updated = [...filtered, file].slice(-MAX_SESSION_FILES)
        get().setCurrentSessionFiles(updated)
        setTimeout(() => forceSaveState(get()), 100)
      },

      clearCurrentSessionFiles: () => {
        get().setCurrentSessionFiles([])
        setTimeout(() => forceSaveState(get()), 100)
      },

      setPhononImages: (images) => set({ phononImages: images }),
      addPhononImage: (image) => {
        const { phononImages } = get()
        set({ phononImages: [...phononImages, image] })
      },
      clearPhononImages: () => set({ phononImages: [] }),

      setCurrentSessionPhononImages: (images) => {
        const limited = images.slice(-MAX_SESSION_PHONON_IMAGES)
        set({ currentSessionPhononImages: limited })

        const { currentSession, sessions } = get()
        if (currentSession) {
          const nextSessions = sessions.map((s) =>
            s.id === currentSession.id ? { ...s, phononImages: limited } : s
          )
          set({ sessions: nextSessions })
        }
      },

      addToCurrentSessionPhononImages: (image) => {
        const { currentSessionPhononImages } = get()
        const updated = [...currentSessionPhononImages, image]
        get().setCurrentSessionPhononImages(updated)
        setTimeout(() => forceSaveState(get()), 100)
      },

      clearCurrentSessionPhononImages: () => {
        get().setCurrentSessionPhononImages([])
        setTimeout(() => forceSaveState(get()), 100)
      },

      setShowPhononVisualization: (show) => set({ showPhononVisualization: show }),
      setPhononDisplayMode: (mode) => set({ phononDisplayMode: mode }),

      setShowFilesInChat: (show) => {
        set((state) => ({
          uiConfig: {
            ...state.uiConfig,
            showFilesInChat: show,
          },
        }))
      },

      updateSettings: (settings) => set({ settings: { ...get().settings, ...settings } }),

      setConnected: (connected) => set({ connected }),

      setIsLoading: (loading) => set({ isLoading: loading }),
      setLoadingMessage: (message) => set({ loadingMessage: message }),

      setBillingData: (data) => set({ billingData: data }),
      updateBillingData: (data) => {
        const current = get().billingData
        set({
          billingData: current
            ? { ...current, ...data }
            : {
                session_total_tokens: data.session_total_tokens || 0,
                session_total_photons: data.session_total_photons || 0,
                requests_count: data.requests_count || 0,
                charged: data.charged ?? false,  // 🔧 修复：添加 charged 字段
                billing_source: data.billing_source,  // 🔧 修复：添加 billing_source 字段
                feature_charges: data.feature_charges || [],  // 🆕 添加 feature_charges 字段
                current_tokens: data.current_tokens,
                current_photons: data.current_photons,
                model_name: data.model_name,
              },
        })
      },

      // 🆕 用户和全局计费统计的实现
      setUserBillingStats: (data) => set({ userBillingStats: data }),
      setGlobalBillingStats: (data) => set({ globalBillingStats: data }),

      createSession: (title, agentId) => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`,
          title,
          messages: [],
          structures: [],
          phononImages: [],
          files: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          agentId,
        }

        const sessions = [...get().sessions, newSession]

        set({
          sessions,
          currentSession: newSession,
          messages: [],
          currentStructure: null,
          currentSessionStructures: [],
          currentSessionFiles: [],
          currentSessionPhononImages: [],
        })

        // 🔧 修复：更新 localStorage 中的 session_id，确保计费配置查找正确
        // 这样前端和后端使用的 session_id 就一致了
        localStorage.setItem('researchmind_session_id', newSession.id)
        console.log('🔧 [计费修复] 更新 localStorage session_id:', newSession.id)

        setTimeout(() => forceSaveState(get()), 100)
        return newSession
      },

      deleteSession: (sessionId) => {
        const { sessions, currentSession } = get()
        const filtered = sessions.filter((s) => s.id !== sessionId)
        const deletingCurrent = currentSession?.id === sessionId

        set({
          sessions: filtered,
          currentSession: deletingCurrent ? null : currentSession,
          messages: deletingCurrent ? [] : get().messages,
          currentStructure: deletingCurrent ? null : get().currentStructure,
          currentSessionStructures: deletingCurrent ? [] : get().currentSessionStructures,
          currentSessionFiles: deletingCurrent ? [] : get().currentSessionFiles,
          currentSessionPhononImages: deletingCurrent ? [] : get().currentSessionPhononImages,
        })
      },

      deleteAllSessions: () => {
        set({
          sessions: [],
          currentSession: null,
          messages: [],
          currentStructure: null,
          currentSessionStructures: [],
          currentSessionFiles: [],
          currentSessionPhononImages: [],
        })
      },

      clearSession: (sessionId) => {
        const { sessions, currentSession } = get()
        const nextSessions = sessions.map((session) =>
          session.id === sessionId
            ? {
                ...session,
                messages: [],
                structures: [],
                phononImages: [],
                files: [],
                updatedAt: new Date(),
              }
            : session
        )

        const clearingCurrent = currentSession?.id === sessionId

        set({
          sessions: nextSessions,
          currentSession: clearingCurrent
            ? { ...currentSession!, messages: [], structures: [], phononImages: [], files: [], updatedAt: new Date() }
            : currentSession,
          messages: clearingCurrent ? [] : get().messages,
          currentSessionStructures: clearingCurrent ? [] : get().currentSessionStructures,
          currentSessionFiles: clearingCurrent ? [] : get().currentSessionFiles,
          currentSessionPhononImages: clearingCurrent ? [] : get().currentSessionPhononImages,
          currentStructure: clearingCurrent ? null : get().currentStructure,
        })
      },

      updateSession: (sessionId, updates) => {
        const nextSessions = get().sessions.map((session) =>
          session.id === sessionId ? { ...session, ...updates, updatedAt: new Date() } : session
        )

        set({ sessions: nextSessions })

        const { currentSession } = get()
        if (currentSession?.id === sessionId) {
          set({ currentSession: { ...currentSession, ...updates, updatedAt: new Date() } })
        }
      },

      forceSave: () => {
        forceSaveState(get())
      },
    }),
    {
      name: 'researchmind-app-store',
      partialize: (state) => {
        // 🔧 优化存储：只保存必要数据，移除大型对象（base64 图片等）
        const optimizedSessions = state.sessions.map(session => ({
          ...session,
          messages: session.messages.map(msg => ({
            ...msg,
            // 移除消息中的 base64 图片数据
            metadata: msg.metadata ? {
              ...msg.metadata,
              images: msg.metadata.images?.map(img => ({
                ...img,
                base64: undefined, // 不保存 base64 数据
              })),
            } : undefined,
          })),
          // 移除会话级别的大型数据
          phononImages: session.phononImages?.map(img => ({
            ...img,
            base64: undefined, // 不保存 base64 数据
          })),
          structures: session.structures?.map(struct => ({
            ...struct,
            // 保留结构元数据，但移除大型 CIF 内容
            cifContent: undefined,
          })),
        }))

        return {
          sessions: optimizedSessions,
          currentSession: state.currentSession ? {
            ...state.currentSession,
            messages: state.currentSession.messages.map(msg => ({
              ...msg,
              metadata: msg.metadata ? {
                ...msg.metadata,
                images: msg.metadata.images?.map(img => ({
                  ...img,
                  base64: undefined,
                })),
              } : undefined,
            })),
            phononImages: state.currentSession.phononImages?.map(img => ({
              ...img,
              base64: undefined,
            })),
            structures: state.currentSession.structures?.map(struct => ({
              ...struct,
              cifContent: undefined,
            })),
          } : null,
          messages: state.messages.map(msg => ({
            ...msg,
            metadata: msg.metadata ? {
              ...msg.metadata,
              images: msg.metadata.images?.map(img => ({
                ...img,
                base64: undefined,
              })),
            } : undefined,
          })),
          settings: state.settings,
          // 不保存当前结构和图片的详细数据（这些可以从服务器重新获取）
          currentStructure: state.currentStructure ? {
            id: state.currentStructure.id,
            formula: state.currentStructure.formula,
          } : null,
          currentSessionStructures: state.currentSessionStructures.map(struct => ({
            id: struct.id,
            formula: struct.formula,
          })),
          currentSessionFiles: state.currentSessionFiles.map(file => ({
            name: file.name,
            path: file.path,
            type: file.type,
          })),
          phononImages: [], // 不保存全局图片列表
          currentSessionPhononImages: state.currentSessionPhononImages.map(img => ({
            name: img.name,
            url: img.url,
            type: img.type,
          })),
          showPhononVisualization: state.showPhononVisualization,
          phononDisplayMode: state.phononDisplayMode,
        }
      },
      onRehydrateStorage: () => (state) => {
        if (!state) return

        console.log('🔄 恢复存储数据...')
        console.log('📊 会话数:', state.sessions?.length || 0)
        console.log('📊 当前会话:', state.currentSession?.id || 'null')

        try {
          if (state.sessions) {
            if (!validateSessionData(state.sessions)) {
              console.warn('⚠️ 会话数据验证失败，清空数据')
              state.sessions = []
              state.currentSession = null
              state.messages = []
              state.currentStructure = null
              state.currentSessionStructures = []
              state.currentSessionFiles = []
              state.currentSessionPhononImages = []
              return
            }

            state.sessions = fixRestoredSessions(state.sessions)

            if (state.currentSession) {
              // 有当前会话，尝试恢复
              const restored = state.sessions.find((s) => s.id === state.currentSession?.id)
              if (restored) {
                console.log('✅ 恢复当前会话:', restored.id)
                console.log('📊 结构数:', restored.structures?.length || 0)
                console.log('📊 文件数:', restored.files?.length || 0)
                console.log('📊 图片数:', restored.phononImages?.length || 0)

                state.currentSession = restored
                state.messages = restored.messages || []
                state.currentStructure = restored.structures?.slice(-1)[0] ?? null
                state.currentSessionStructures = restored.structures || []
                state.currentSessionFiles = restored.files || []
                state.currentSessionPhononImages = restored.phononImages || []
              } else {
                console.warn('⚠️ 当前会话不存在，清空当前会话数据')
                state.currentSession = null
                state.messages = []
                state.currentStructure = null
                state.currentSessionStructures = []
                state.currentSessionFiles = []
                state.currentSessionPhononImages = []
              }
            } else if (state.sessions.length > 0) {
              // 没有当前会话，但有会话列表，恢复最后一个会话
              const lastSession = state.sessions[state.sessions.length - 1]
              console.log('🔄 没有当前会话，恢复最后一个会话:', lastSession.id)
              console.log('📊 结构数:', lastSession.structures?.length || 0)
              console.log('📊 文件数:', lastSession.files?.length || 0)
              console.log('📊 图片数:', lastSession.phononImages?.length || 0)

              state.currentSession = lastSession
              state.messages = lastSession.messages || []
              state.currentStructure = lastSession.structures?.slice(-1)[0] ?? null
              state.currentSessionStructures = lastSession.structures || []
              state.currentSessionFiles = lastSession.files || []
              state.currentSessionPhononImages = lastSession.phononImages || []
            } else {
              // 没有任何会话
              console.log('ℹ️ 没有任何会话')
              state.messages = []
              state.currentStructure = null
              state.currentSessionStructures = []
              state.currentSessionFiles = []
              state.currentSessionPhononImages = []
            }
          } else {
            console.log('ℹ️ 没有存储的会话数据')
            state.sessions = []
            state.currentSession = null
            state.messages = []
            state.currentStructure = null
            state.currentSessionStructures = []
            state.currentSessionFiles = []
            state.currentSessionPhononImages = []
          }
        } catch (error) {
          console.error('❌ 恢复存储数据时出错:', error)
          // 清空数据以防止错误传播
          state.sessions = []
          state.currentSession = null
          state.messages = []
          state.currentStructure = null
          state.currentSessionStructures = []
          state.currentSessionFiles = []
          state.currentSessionPhononImages = []
        }

        if (!Array.isArray(state.currentSessionStructures)) {
          state.currentSessionStructures = []
        }

        if (!Array.isArray(state.currentSessionFiles)) {
          state.currentSessionFiles = []
        }

        if (!Array.isArray(state.currentSessionPhononImages)) {
          state.currentSessionPhononImages = []
        }

        if (!Array.isArray(state.phononImages)) {
          state.phononImages = []
        }
      },
      // 🔧 添加存储错误处理
      storage: {
        getItem: (name) => {
          try {
            const str = localStorage.getItem(name)
            return str ? JSON.parse(str) : null
          } catch (error) {
            console.error('❌ 读取存储时出错:', error)
            return null
          }
        },
        setItem: (name, value) => {
          try {
            localStorage.setItem(name, JSON.stringify(value))
          } catch (error) {
            console.error('❌ 保存存储时出错:', error)

            // 如果是配额错误，尝试清理
            if (error instanceof DOMException && error.name === 'QuotaExceededError') {
              console.warn('⚠️ 存储配额超限，尝试清理旧数据...')

              // 导入清理函数
              import('../utils/storage').then(({ cleanupOldSessions, clearAllStorage }) => {
                try {
                  // 先尝试清理旧会话
                  cleanupOldSessions(3)

                  // 再次尝试保存
                  try {
                    localStorage.setItem(name, JSON.stringify(value))
                    console.log('✅ 清理后保存成功')
                  } catch (retryError) {
                    // 如果还是失败，清除所有数据
                    console.error('❌ 清理后仍然失败，清除所有数据')
                    clearAllStorage()
                  }
                } catch (cleanupError) {
                  console.error('❌ 清理失败:', cleanupError)
                  clearAllStorage()
                }
              })
            }
          }
        },
        removeItem: (name) => {
          try {
            localStorage.removeItem(name)
          } catch (error) {
            console.error('❌ 删除存储时出错:', error)
          }
        },
      },
    },
  ),
)
