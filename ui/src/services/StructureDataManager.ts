/**
 * StructureDataManager - 结构数据管理和通信服务
 * 负责与后端API通信，管理结构数据缓存，处理WebSocket事件
 */

import { CrystalStructure } from '../types'
import { API_CONFIG } from '../constants'

export interface StructureResponse {
  success: boolean
  structures: CrystalStructure[]
  count: number
  simulation_count?: number
  database_count?: number
  cache_stats?: any
  timestamp: string
  error?: string
}

export interface PhononResponse {
  success: boolean
  phonon_results: any[]
  count: number
  timestamp: string
  error?: string
}

export interface CIFParseRequest {
  cif_content: string
  to_conventional?: boolean
}

export interface CIFParseResponse {
  success: boolean
  formula?: string
  spaceGroup?: string
  latticeParameters?: {
    a: number
    b: number
    c: number
    alpha: number
    beta: number
    gamma: number
    volume?: number
  }
  atoms?: Array<{
    element: string
    x: number
    y: number
    z: number
    fractional_coords?: [number, number, number]
  }>
  atomCount?: number
  properties?: any
  rendering_data?: any
  error?: string
  timestamp: string
}

export interface WebSocketEventData {
  type: string
  data: any
  timestamp?: string
}

class StructureDataManager {
  private baseUrl: string
  private cache: Map<string, any> = new Map()
  private cacheExpiry: Map<string, number> = new Map()
  private defaultCacheTime = 5 * 60 * 1000 // 5分钟缓存

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL || 'http://0.0.0.0:50002'
  }

  /**
   * 获取最新结构数据
   */
  async fetchLatestStructures(): Promise<StructureResponse> {
    const cacheKey = 'latest_structures'
    
    // 检查缓存
    if (this.isCacheValid(cacheKey)) {
      console.log('📦 使用缓存的结构数据')
      return this.cache.get(cacheKey)
    }

    try {
      console.log('🌐 获取最新结构数据...')
      const response = await fetch(`${this.baseUrl}/api/latest_structures`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: StructureResponse = await response.json()
      
      // 缓存结果
      this.setCache(cacheKey, data)
      
      console.log(`✅ 获取到 ${data.count} 个结构数据`)
      return data

    } catch (error) {
      console.error('❌ 获取结构数据失败:', error)
      return {
        success: false,
        structures: [],
        count: 0,
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 获取声子谱结果
   */
  async fetchPhononResults(): Promise<PhononResponse> {
    const cacheKey = 'phonon_results'

    // 检查缓存
    if (this.isCacheValid(cacheKey)) {
      console.log('📦 使用缓存的声子谱数据')
      return this.cache.get(cacheKey)
    }

    try {
      console.log('🌐 获取声子谱结果...')
      // 使用新的统一端点 /api/files?type=phonon_results
      const response = await fetch(`${this.baseUrl}/api/files?type=phonon_results`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: PhononResponse = await response.json()

      // 缓存结果
      this.setCache(cacheKey, data)

      console.log(`✅ 获取到 ${data.count} 个声子谱结果`)
      return data

    } catch (error) {
      console.error('❌ 获取声子谱结果失败:', error)
      return {
        success: false,
        phonon_results: [],
        count: 0,
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 解析CIF文件
   */
  async parseCIFForRendering(cifContent: string, toConventional: boolean = true): Promise<CIFParseResponse> {
    try {
      console.log('🔬 解析CIF文件...')
      const response = await fetch(`${this.baseUrl}/api/parse_cif`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cif_content: cifContent,
          to_conventional: toConventional
        } as CIFParseRequest)
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CIFParseResponse = await response.json()
      
      if (data.success) {
        console.log(`✅ CIF解析成功: ${data.formula} (${data.atomCount} 个原子)`)
      } else {
        console.error('❌ CIF解析失败:', data.error)
      }
      
      return data

    } catch (error) {
      console.error('❌ CIF解析请求失败:', error)
      return {
        success: false,
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 获取服务状态
   */
  async fetchServiceStatus(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/service_status`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()

    } catch (error) {
      console.error('❌ 获取服务状态失败:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 清空缓存
   */
  async clearCache(cacheType: string = 'all'): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/clear_cache`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ cache_type: cacheType })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      // 同时清空本地缓存
      this.clearLocalCache()
      
      return await response.json()

    } catch (error) {
      console.error('❌ 清空缓存失败:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 处理WebSocket事件
   */
  handleWebSocketEvent(eventData: WebSocketEventData): void {
    const { type, data } = eventData

    console.log(`📡 收到WebSocket事件: ${type}`)

    switch (type) {
      case 'unified_data':
        this.handleUnifiedDataEvent(data)
        break
      
      case 'structure_data':
        this.handleStructureDataEvent(data)
        break
      
      case 'image_data':
        this.handleImageDataEvent(data)
        break
      
      case 'phonon_response':
        this.handlePhononResponseEvent(data)
        break
      
      case 'structures_response':
        this.handleStructuresResponseEvent(data)
        break
      
      case 'cache_cleared':
        this.handleCacheClearedEvent(data)
        break
      
      case 'error_response':
        this.handleErrorResponseEvent(data)
        break
      
      default:
        console.log(`🔍 未处理的事件类型: ${type}`)
    }
  }

  /**
   * 处理统一数据事件
   */
  private handleUnifiedDataEvent(data: any): void {
    console.log(`🎯 收到统一数据事件: ${data.type} (来源: ${data.source})`)
    
    // 更新结构缓存
    if (data.structures && Array.isArray(data.structures)) {
      this.updateStructureCache(data.structures, data.source)
    }
    
    // 处理图片数据
    if (data.images && Array.isArray(data.images)) {
      this.updateImageCache(data.images, data.source, data.composition)
    }
    
    // 处理声子谱数据
    if (data.type === 'phonon_calculation' && data.images) {
      this.updatePhononCache(data)
    }
  }

  /**
   * 处理结构数据事件
   */
  private handleStructureDataEvent(data: any): void {
    if (data.structures && Array.isArray(data.structures)) {
      console.log(`📊 收到 ${data.structures.length} 个新结构`)
      this.updateStructureCache(data.structures, data.source)
    }
  }

  /**
   * 处理图片数据事件
   */
  private handleImageDataEvent(data: any): void {
    if (data.images && Array.isArray(data.images)) {
      console.log(`🖼️ 收到 ${data.images.length} 个图片`)
      this.updateImageCache(data.images, data.source, data.composition)
    }
  }

  /**
   * 更新结构缓存
   */
  private updateStructureCache(structures: any[], _source?: string): void {
    const cacheKey = 'latest_structures'
    const cachedData = this.cache.get(cacheKey)
    
    if (cachedData) {
      // 合并新数据，避免重复
      const existingIds = new Set(cachedData.structures.map((s: any) => s.id))
      const newStructures = structures.filter(s => !existingIds.has(s.id))
      
      const updatedData = {
        ...cachedData,
        structures: [...newStructures, ...cachedData.structures],
        count: newStructures.length + cachedData.count,
        timestamp: new Date().toISOString()
      }
      this.setCache(cacheKey, updatedData)
      
      if (newStructures.length > 0) {
        console.log(`📊 缓存更新: 新增 ${newStructures.length} 个结构`)
      }
    } else {
      // 创建新缓存
      this.setCache(cacheKey, {
        success: true,
        structures: structures,
        count: structures.length,
        timestamp: new Date().toISOString()
      })
      console.log(`📊 创建结构缓存: ${structures.length} 个结构`)
    }
  }

  /**
   * 更新图片缓存
   */
  private updateImageCache(images: any[], source?: string, composition?: string): void {
    const cacheKey = 'latest_images'
    const imageData = {
      images: images,
      source: source,
      composition: composition,
      timestamp: new Date().toISOString()
    }
    
    this.setCache(cacheKey, imageData)
    console.log(`🖼️ 图片缓存更新: ${images.length} 个图片`)
  }

  /**
   * 更新声子谱缓存
   */
  private updatePhononCache(data: any): void {
    const cacheKey = 'phonon_results'
    const cachedData = this.cache.get(cacheKey)
    
    const newPhononResult = {
      composition: data.composition,
      stability_status: data.properties?.stability_status || data.stability_status,
      has_imaginary_modes: data.properties?.has_imaginary_modes || data.has_imaginary_modes,
      images: data.images || [],
      timestamp: data.timestamp || new Date().toISOString()
    }
    
    // 合并新数据到现有缓存
    if (cachedData && cachedData.phonon_results) {
      const updatedResults = [newPhononResult, ...cachedData.phonon_results]
      this.setCache(cacheKey, {
        success: true,
        phonon_results: updatedResults,
        count: updatedResults.length,
        timestamp: new Date().toISOString()
      })
      console.log(`🎵 声子谱缓存更新: ${data.composition} (总计: ${updatedResults.length})`)
    } else {
      this.setCache(cacheKey, {
        success: true,
        phonon_results: [newPhononResult],
        count: 1,
        timestamp: new Date().toISOString()
      })
      console.log(`🎵 声子谱缓存创建: ${data.composition}`)
    }
  }

  /**
   * 处理声子谱响应事件
   */
  private handlePhononResponseEvent(data: any): void {
    console.log(`🎵 收到声子谱响应事件`, data)
    
    if (data.phonon_results) {
      // 更新缓存
      this.setCache('phonon_results', data)
    } else if (data.images) {
      // 如果直接包含images，转换为标准格式
      const phononData = {
        composition: data.composition || 'Unknown',
        stability_status: data.stability_status,
        has_imaginary_modes: data.has_imaginary_modes,
        images: data.images,
        timestamp: data.timestamp || new Date().toISOString()
      }
      this.updatePhononCache(phononData)
    }
  }

  /**
   * 处理结构响应事件
   */
  private handleStructuresResponseEvent(data: any): void {
    if (data.structures) {
      console.log(`🏗️ 收到结构响应: ${data.count} 个结构`)
      
      // 更新缓存
      this.setCache('latest_structures', data)
    }
  }

  /**
   * 处理缓存清空事件
   */
  private handleCacheClearedEvent(data: any): void {
    console.log(`🧹 服务器缓存已清空: ${data.cache_type}`)
    
    // 清空本地缓存
    this.clearLocalCache()
  }

  /**
   * 处理错误响应事件
   */
  private handleErrorResponseEvent(data: any): void {
    console.error(`❌ 服务器错误: ${data.error}`)
  }

  /**
   * 转换API数据为Three.js渲染格式
   */
  convertToRenderingFormat(apiData: any): CrystalStructure | null {
    try {
      if (!apiData || !apiData.atoms) {
        console.warn('⚠️ API数据缺少原子信息')
        return null
      }

      const structure: CrystalStructure = {
        id: apiData.id || `structure_${Date.now()}`,
        formula: apiData.formula || 'Unknown',
        spaceGroup: apiData.spaceGroup || 'Unknown',
        latticeParameters: {
          a: apiData.latticeParameters?.a || 1,
          b: apiData.latticeParameters?.b || 1,
          c: apiData.latticeParameters?.c || 1,
          alpha: apiData.latticeParameters?.alpha || 90,
          beta: apiData.latticeParameters?.beta || 90,
          gamma: apiData.latticeParameters?.gamma || 90
        },
        atoms: apiData.atoms.map((atom: any) => ({
          element: atom.element,
          position: [atom.x || 0, atom.y || 0, atom.z || 0] as [number, number, number],
          occupancy: atom.occupancy || 1.0
        })),
        properties: {
          ...apiData.properties,
          numAtoms: apiData.atomCount || apiData.atoms.length
        },
        source: {
          database: apiData.source || 'Unknown' as any,
          materialId: apiData.material_id,
          retrievedAt: new Date()
        }
      }

      return structure

    } catch (error) {
      console.error('❌ 数据格式转换失败:', error)
      return null
    }
  }

  // 缓存管理方法

  private isCacheValid(key: string): boolean {
    const expiry = this.cacheExpiry.get(key)
    if (!expiry || Date.now() > expiry) {
      this.cache.delete(key)
      this.cacheExpiry.delete(key)
      return false
    }
    return this.cache.has(key)
  }

  private setCache(key: string, data: any, ttl: number = this.defaultCacheTime): void {
    this.cache.set(key, data)
    this.cacheExpiry.set(key, Date.now() + ttl)
  }

  private clearLocalCache(): void {
    this.cache.clear()
    this.cacheExpiry.clear()
    console.log('🧹 本地缓存已清空')
  }

  /**
   * 获取最新图片数据
   */
  async fetchLatestImages(): Promise<any> {
    const cacheKey = 'latest_images'
    
    // 检查缓存
    if (this.isCacheValid(cacheKey)) {
      console.log('📦 使用缓存的图片数据')
      return this.cache.get(cacheKey)
    }

    try {
      console.log('🌐 获取最新图片数据...')
      const response = await fetch(`${this.baseUrl}/api/latest_images`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      
      // 缓存结果
      this.setCache(cacheKey, data)
      
      console.log(`✅ 获取到 ${data.images?.length || 0} 个图片`)
      return data

    } catch (error) {
      console.error('❌ 获取图片数据失败:', error)
      return {
        success: false,
        images: [],
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 获取统一格式的数据
   */
  async fetchUnifiedData(dataType: string = 'all'): Promise<any> {
    try {
      console.log(`🌐 获取统一格式数据: ${dataType}`)
      const response = await fetch(`${this.baseUrl}/api/unified_data?type=${dataType}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log(`✅ 获取统一数据成功`)
      return data

    } catch (error) {
      console.error('❌ 获取统一数据失败:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      }
    }
  }

  /**
   * 获取缓存统计
   */
  getCacheStats(): any {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
      memory_usage_estimate: JSON.stringify(Array.from(this.cache.values())).length
    }
  }
}

// 导出单例实例
export const structureDataManager = new StructureDataManager()
export default StructureDataManager