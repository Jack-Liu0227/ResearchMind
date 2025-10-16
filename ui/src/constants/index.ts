// API 配置
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:50001',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:50002/ws',
  TIMEOUT: 30000,
} as const

// 调试输出环境变量
console.log('🔧 Environment Variables:', {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  VITE_WS_URL: import.meta.env.VITE_WS_URL,
  API_CONFIG_BASE_URL: API_CONFIG.BASE_URL,
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