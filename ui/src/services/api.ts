import axios from 'axios'
import { ApiResponse } from '../types'
import { API_CONFIG } from '../constants'

const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// ============================================
// 后端实际存在的端点 (services/http_server.py)
// ============================================

// 健康检查
export const healthCheck = async (): Promise<ApiResponse> => {
  return api.get('/api/health')
}

// 服务状态
export const getServiceStatus = async (): Promise<ApiResponse> => {
  return api.get('/api/service_status')
}

// 获取文件列表 (统一端点)
export const getFiles = async (type: string = 'phonon_results'): Promise<ApiResponse> => {
  return api.get(`/api/files?type=${type}`)
}

// 声子谱结果列表 (兼容性，使用新端点)
export const getPhononResults = async (): Promise<ApiResponse> => {
  return getFiles('phonon_results')
}

// 生成结构列表 (兼容性，使用新端点)
export const getGeneratedStructures = async (): Promise<ApiResponse> => {
  return getFiles('generated_structures')
}

// 获取声子谱示例 (新端点)
export const getPhononExamples = async (): Promise<ApiResponse> => {
  return getFiles('phonon_examples')
}

// 文件上传 (统一端点)
export const uploadFile = async (files: File | File[], type: string = 'structure'): Promise<ApiResponse> => {
  const formData = new FormData()

  // 支持单个文件或多个文件
  if (Array.isArray(files)) {
    files.forEach(file => formData.append('files', file))
  } else {
    formData.append('files', files)
  }

  formData.append('type', type)

  return api.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export default api