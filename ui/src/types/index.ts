// 智能体类型定义
export interface Agent {
  id: string
  name: string
  description: string
  type: 'coordinator' | 'literature' | 'database' | 'simulation'
  capabilities: string[]
  status: 'active' | 'inactive' | 'busy'
  avatar?: string
}

// 消息类型定义
export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  agentId?: string
  agentName?: string
  type?: 'text' | 'structure' | 'analysis' | 'error'
  metadata?: {
    structureData?: CrystalStructure
    analysisData?: AnalysisResult
    citations?: Citation[]
    // Paper search MCP tool返回的文件链接
    csv_download_url?: string
    md_download_url?: string
    csv_file_path?: string
    summary_file_path?: string
    report_file_path?: string
    images?: any[]
    phononData?: any
    [key: string]: any  // 允许其他动态属性
  }
}

// 对话会话类型
export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
  agentId: string
  tags?: string[]
  // 会话独立的数据
  structures?: CrystalStructure[]  // 晶体结构列表
  phononImages?: any[]             // 声子谱图片列表
}

// 晶胞类型数据
export interface CellTypeData {
  latticeParameters: {
    a: number
    b: number
    c: number
    alpha: number
    beta: number
    gamma: number
  }
  atoms: Atom[]
  volume: number
  numAtoms: number
}

// 晶体结构数据类型
export interface CrystalStructure {
  id: string
  formula: string
  spaceGroup: string
  latticeParameters: {
    a: number
    b: number
    c: number
    alpha: number
    beta: number
    gamma: number
  }
  atoms: Atom[]
  cifContent?: string  // CIF 文件内容（统一字段）
  properties?: {
    bandGap?: number
    density?: number
    volume?: number
    energyAboveHull?: number
    magneticMoment?: number
    totalEnergy?: number
    numAtoms?: number  // Pymatgen 统计的原子数
    numSites?: number  // 位点数
    isConventionalCell?: boolean  // 是否为惯胞
    spaceGroupNumber?: number  // 空间群编号
    crystalSystem?: string  // 晶系
  }
  source?: {
    database: 'MP' | 'OQMD' | 'COD' | 'AFLOW' | 'Generated' | 'Upload' | 'Relaxed'
    materialId?: string
    url?: string
    retrievedAt?: Date
  }
  metadata?: {
    messageId?: string
    sessionId?: string
    timestamp?: number
    notes?: string
    conventionalStructure?: CrystalStructure  // 惯胞数据
    generation_id?: string  // CrystaLLM 生成ID
    composition?: string  // 化学组成
    filename?: string  // 文件名
  }
  // 晶胞类型切换数据
  cellTypes?: {
    primitive: CellTypeData
    conventional: CellTypeData
  }
  currentCellType?: 'primitive' | 'conventional'
}

export interface Atom {
  element: string
  position: [number, number, number]
  occupancy?: number
  charge?: number
}

// 分析结果类型
export interface AnalysisResult {
  type: 'literature' | 'database' | 'simulation'
  title: string
  summary: string
  data: any
  confidence: number
  timestamp: Date
}

// 引用类型
export interface Citation {
  title: string
  authors: string[]
  journal?: string
  year: number
  doi?: string
  url?: string
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: 'message' | 'status' | 'error' | 'structure' | 'structure_data' | 'image_data' | 'phonon_data' | 'analysis' | 'connection' | 'agents_list' | 'agent_selected' | 'pong' | 'session_cleared' | 'agent_selected' | 'feedback_request'
  data: any
  sessionId?: string
  agentId?: string
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// 任务类型
export interface Task {
  id: string
  type: string
  query: string
  agentId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: any
  error?: string
  createdAt: Date
  completedAt?: Date
}

// 用户设置类型
export interface UserSettings {
  theme: 'light' | 'dark' | 'auto'
  language: 'zh' | 'en'
  defaultAgent: string
  autoSave: boolean
  notifications: boolean
  apiEndpoint: string
}

// 搜索结果类型
export interface SearchResult {
  id: string
  title: string
  abstract: string
  authors: string[]
  source: string
  url?: string
  relevanceScore: number
  publishedDate?: Date
}

// 声子谱图片类型
export interface PhononImage {
  id: string
  sessionId: string
  messageId?: string
  base64: string
  name: string
  timestamp: number
  metadata?: {
    formula?: string
    description?: string
  }
}

// 文件附件类型
export interface FileAttachment {
  path: string
  base64: string
  name: string
  url?: string
}