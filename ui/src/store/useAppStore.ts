
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

  // Settings and connectivity
  settings: UserSettings
  connected: boolean

  // Loading indicator
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

  updateSettings: (settings: Partial<UserSettings>) => void

  setConnected: (connected: boolean) => void

  setIsLoading: (loading: boolean) => void
  setLoadingMessage: (message: string) => void

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

      sidebarOpen: false,

      currentStructure: null,
      structureList: [],
      currentSessionStructures: [],
      currentSessionFiles: [],

      phononImages: [],
      currentSessionPhononImages: [],
      showPhononVisualization: false,
      phononDisplayMode: 'fullscreen',

      settings: defaultSettings,

      connected: false,

      isLoading: false,
      loadingMessage: '智能体正在思考...',

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
      },

      clearCurrentSessionFiles: () => {
        get().setCurrentSessionFiles([])
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
      },

      clearCurrentSessionPhononImages: () => {
        get().setCurrentSessionPhononImages([])
      },

      setShowPhononVisualization: (show) => set({ showPhononVisualization: show }),
      setPhononDisplayMode: (mode) => set({ phononDisplayMode: mode }),

      updateSettings: (settings) => set({ settings: { ...get().settings, ...settings } }),

      setConnected: (connected) => set({ connected }),

      setIsLoading: (loading) => set({ isLoading: loading }),
      setLoadingMessage: (message) => set({ loadingMessage: message }),

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
      partialize: (state) => ({
        sessions: state.sessions,
        currentSession: state.currentSession,
        messages: state.messages,
        settings: state.settings,
        currentStructure: state.currentStructure,
        currentSessionStructures: state.currentSessionStructures,
        currentSessionFiles: state.currentSessionFiles,
        phononImages: state.phononImages,
        currentSessionPhononImages: state.currentSessionPhononImages,
        showPhononVisualization: state.showPhononVisualization,
        phononDisplayMode: state.phononDisplayMode,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return

        if (state.sessions) {
          if (!validateSessionData(state.sessions)) {
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
            const restored = state.sessions.find((s) => s.id === state.currentSession?.id)
            if (restored) {
              state.currentSession = restored
              state.messages = restored.messages || []
              state.currentStructure = restored.structures?.slice(-1)[0] ?? null
              state.currentSessionStructures = restored.structures || []
              state.currentSessionFiles = restored.files || []
              state.currentSessionPhononImages = restored.phononImages || []
            } else {
              state.currentSession = null
              state.messages = []
              state.currentStructure = null
              state.currentSessionStructures = []
              state.currentSessionFiles = []
              state.currentSessionPhononImages = []
            }
          } else {
            state.messages = []
            state.currentStructure = null
            state.currentSessionStructures = []
            state.currentSessionFiles = []
            state.currentSessionPhononImages = []
          }
        } else {
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
    },
  ),
)
