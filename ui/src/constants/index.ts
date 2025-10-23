const trimEnv = (value: string | undefined | null) => {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : undefined
}

const DEFAULT_API_PATH = trimEnv(import.meta.env.VITE_API_PATH) || '/api'

const isWindowsAbsolutePath = (value: string) =>
  /^[a-zA-Z]:[\\/]/.test(value) || value.startsWith('\\\\')

const sanitizeWindowsPath = (value: string | undefined, fallback?: string) => {
  if (typeof value !== 'string') return value
  const trimmed = value.trim()
  if (trimmed.length === 0) return undefined
  if (isWindowsAbsolutePath(trimmed)) {
    return fallback
  }
  return trimmed
}

const resolveRuntimeLocation = () => {
  if (typeof window === 'undefined') {
    return {
      protocol: 'http:' as const,
      hostname: '127.0.0.1',
      isHttps: false,
    }
  }

  // 处理本地开发时的 file:// 协议
  let protocol: string
  let hostname: string

  if (window.location.protocol === 'file:') {
    // 本地开发（file:// 协议）
    protocol = 'http:'
    hostname = 'localhost'
  } else {
    // 正常部署
    protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
    hostname = window.location.hostname || '127.0.0.1'
  }

  return {
    protocol,
    hostname,
    isHttps: protocol === 'https:',
  }
}

const buildOrigin = (protocol: string, hostname: string, port?: string) => {
  const normalizedPort = trimEnv(port)

  if (!normalizedPort) {
    return `${protocol}//${hostname}`
  }

  const isDefaultHttp = protocol === 'http:' && normalizedPort === '80'
  const isDefaultHttps = protocol === 'https:' && normalizedPort === '443'

  if (isDefaultHttp || isDefaultHttps) {
    return `${protocol}//${hostname}`
  }

  return `${protocol}//${hostname}:${normalizedPort}`
}

const buildDefaultApiOrigin = () => {
  const { protocol, hostname } = resolveRuntimeLocation()
  const fallbackPort =
    trimEnv(import.meta.env.VITE_API_PORT) ||
    (typeof window !== 'undefined' ? trimEnv(window.location.port) : undefined) ||
    '50002'
  return buildOrigin(protocol, hostname, fallbackPort)
}

const buildDefaultWsUrl = () => {
  const { hostname, isHttps } = resolveRuntimeLocation()
  const protocol = isHttps ? 'wss:' : 'ws:'
  const port = trimEnv(import.meta.env.VITE_WS_PORT) || '50003'
  const path = trimEnv(import.meta.env.VITE_WS_PATH) || '/ws'
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${protocol}//${hostname}:${port}${normalizedPath}`
}

const RAW_API_URL = sanitizeWindowsPath(import.meta.env.VITE_API_URL, DEFAULT_API_PATH)
const RAW_WS_URL = sanitizeWindowsPath(import.meta.env.VITE_WS_URL, '/ws')

const ENV_API_URL = trimEnv(RAW_API_URL)
const ENV_WS_URL = trimEnv(RAW_WS_URL)

// 处理相对路径 API URL
const normalizeApiPath = (path?: string): string => {
  if (!path) return DEFAULT_API_PATH
  const trimmed = path.trim()
  if (trimmed.length === 0) return DEFAULT_API_PATH
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  if (withLeadingSlash === '/') return DEFAULT_API_PATH
  return withLeadingSlash.endsWith('/') ? withLeadingSlash.slice(0, -1) : withLeadingSlash
}

const resolveApiOrigin = (envUrl?: string): string => {
  if (!envUrl) {
    return buildDefaultApiOrigin()
  }

  if (envUrl.startsWith('/')) {
    const { protocol, hostname } = resolveRuntimeLocation()
    const configuredPort = trimEnv(import.meta.env.VITE_API_PORT)

    if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
      const port = configuredPort || '50002'
      return buildOrigin(protocol, 'localhost', port)
    }

    const runtimePort =
      configuredPort ||
      (typeof window !== 'undefined' ? trimEnv(window.location.port) : undefined)

    return buildOrigin(protocol, hostname, runtimePort)
  }

  try {
    return new URL(envUrl).origin
  } catch {
    try {
      const { protocol } = resolveRuntimeLocation()
      return new URL(`${protocol}//${envUrl}`).origin
    } catch (error) {
      console.warn('⚠️ Failed to parse VITE_API_URL, falling back to default origin:', error)
      return buildDefaultApiOrigin()
    }
  }
}

const resolveApiPath = (envUrl?: string): string => {
  if (!envUrl) {
    return DEFAULT_API_PATH
  }

  if (envUrl.startsWith('/')) {
    return normalizeApiPath(envUrl)
  }

  try {
    const parsed = new URL(envUrl)
    return normalizeApiPath(parsed.pathname)
  } catch {
    return DEFAULT_API_PATH
  }
}

const resolveWsUrl = (envUrl?: string): string => {
  console.log('🔧 resolveWsUrl called with:', envUrl)
  
  if (!envUrl) {
    const defaultUrl = buildDefaultWsUrl()
    console.log('🔧 Using default WS URL:', defaultUrl)
    return defaultUrl
  }

  // 如果是相对路径（以 / 开头），转换为完整 URL
  if (envUrl.startsWith('/')) {
    const { hostname, isHttps } = resolveRuntimeLocation()
    const protocol = isHttps ? 'wss:' : 'ws:'
    console.log('🔧 Runtime location:', { hostname, isHttps, protocol })

    // 对于本地开发（file:// 协议），需要指定完整的主机和端口
    if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
      console.log('🔧 Detected file:// protocol, using local development settings')
      // 本地开发：强制使用ws协议和nginx代理端口
      const proxyPort = trimEnv(import.meta.env.VITE_PROXY_PORT) || '50001'
      const directPort = trimEnv(import.meta.env.VITE_WS_PORT) || '50003'
      
      // 优先使用代理端口（nginx），如果没有则使用直连端口
      const port = proxyPort !== '50001' ? proxyPort : (directPort !== '50003' ? directPort : '50001')
      const result = `ws://localhost:${port}${envUrl}`
      console.log('🔧 File protocol WS URL:', result)
      return result
    }

    // 对于正常部署，检查是否有指定的 WebSocket 端口
    const wsPort = trimEnv(import.meta.env.VITE_WS_PORT)
    if (wsPort) {
      // 如果指定了端口，使用指定的端口
      return `${protocol}//${hostname}:${wsPort}${envUrl}`
    }

    // 如果没有指定端口，使用当前访问的端口（通过 Nginx 反向代理）
    // 这样可以支持任意端口的 Nginx 反向代理配置
    return `${protocol}//${hostname}${envUrl}`
  }

  // 如果是完整 URL，直接返回
  return envUrl
}

// API 配置
const API_ORIGIN = resolveApiOrigin(ENV_API_URL)
const API_PATH = resolveApiPath(ENV_API_URL)

export const API_CONFIG = {
  BASE_URL: API_ORIGIN,
  API_PATH,
  API_BASE_URL: `${API_ORIGIN}${API_PATH}`,
  WS_URL: resolveWsUrl(ENV_WS_URL),
  TIMEOUT: 30000,
} as const

// 调试输出最终的配置
console.log('🔧 Final API_CONFIG:', API_CONFIG)

// 调试输出环境变量
console.log('🔧 Environment Variables:', {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  VITE_WS_URL: import.meta.env.VITE_WS_URL,
  VITE_API_PORT: import.meta.env.VITE_API_PORT,
  VITE_WS_PORT: import.meta.env.VITE_WS_PORT,
  window_location_protocol: typeof window !== 'undefined' ? window.location.protocol : 'N/A',
  window_location_hostname: typeof window !== 'undefined' ? window.location.hostname : 'N/A',
  API_CONFIG_BASE_URL: API_CONFIG.BASE_URL,
  API_CONFIG_API_PATH: API_CONFIG.API_PATH,
  API_CONFIG_API_BASE_URL: API_CONFIG.API_BASE_URL,
  API_CONFIG_WS_URL: API_CONFIG.WS_URL
})

// 应用配置
export const APP_CONFIG = {
  NAME: 'ResearchMind',
  VERSION: '2.0.0',
  DESCRIPTION: 'AI 研究助手',
  MAX_MESSAGE_LENGTH: 10000,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  SUPPORTED_FILE_TYPES: ['.txt', '.pdf', '.doc', '.docx', '.cif', '.xyz', '.pdb'],
} as const

// 智能体类型
export const AGENT_TYPES = {
  COORDINATOR: 'coordinator',
  LITERATURE: 'literature',
  DATABASE: 'database',
  SIMULATION: 'simulation',
} as const

// 消息类型
export const MESSAGE_TYPES = {
  TEXT: 'text',
  STRUCTURE: 'structure',
  FILE: 'file',
  ERROR: 'error',
} as const

// WebSocket 消息类型
export const WS_MESSAGE_TYPES = {
  MESSAGE: 'message',
  STATUS: 'status',
  ERROR: 'error',
  PING: 'ping',
  PONG: 'pong',
} as const

// 本地存储键名
export const STORAGE_KEYS = {
  SESSIONS: 'researchmind_sessions',
  SETTINGS: 'researchmind_settings',
  CURRENT_SESSION: 'researchmind_current_session',
  CURRENT_AGENT: 'researchmind_current_agent',
} as const

// 主题配置
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  AUTO: 'auto',
} as const

// 语言配置
export const LANGUAGES = {
  ZH: 'zh',
  EN: 'en',
} as const

// 默认设置
export const DEFAULT_SETTINGS = {
  theme: THEMES.LIGHT,
  language: LANGUAGES.ZH,
  defaultAgent: 'research_coordinator',
  autoSave: true,
  notifications: true,
  apiEndpoint: API_CONFIG.BASE_URL,
} as const

// 错误消息
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  SERVER_ERROR: '服务器错误，请稍后重试',
  INVALID_INPUT: '输入内容无效',
  FILE_TOO_LARGE: '文件大小超过限制',
  UNSUPPORTED_FILE_TYPE: '不支持的文件类型',
  WEBSOCKET_ERROR: 'WebSocket 连接失败',
  AGENT_NOT_AVAILABLE: '智能体暂不可用',
} as const

// 成功消息
export const SUCCESS_MESSAGES = {
  MESSAGE_SENT: '消息发送成功',
  FILE_UPLOADED: '文件上传成功',
  SETTINGS_SAVED: '设置保存成功',
  SESSION_CREATED: '会���创建成功',
  SESSION_DELETED: '会话删除成功',
} as const

// 路由路径
export const ROUTES = {
  HOME: '/',
  CHAT: '/chat',
  SETTINGS: '/settings',
} as const

// 动画配置
export const ANIMATION_CONFIG = {
  DURATION: {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
  },
  EASING: {
    EASE_IN: 'ease-in',
    EASE_OUT: 'ease-out',
    EASE_IN_OUT: 'ease-in-out',
  },
} as const

// 分页配置
export const PAGINATION_CONFIG = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const

// 正则表达式
export const REGEX_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  URL: /^https?:\/\/.+/,
  CHEMICAL_FORMULA: /^[A-Z][a-z]?(\d+)?([A-Z][a-z]?(\d+)?)*$/,
} as const
