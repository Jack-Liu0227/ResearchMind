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
  return api.get('/health')
}

// 服务状态
export const getServiceStatus = async (): Promise<ApiResponse> => {
  return api.get('/api/service_status')
}

// 声子谱结果列表
export const getPhononResults = async (): Promise<ApiResponse> => {
  return api.get('/api/phonon_results')
}

// 生成结构列表
export const getGeneratedStructures = async (): Promise<ApiResponse> => {
  return api.get('/api/generated_structures')
}

// 文件上传
export const uploadFile = async (file: File, type?: string): Promise<ApiResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  if (type) formData.append('type', type)

  return api.post('/api/upload/structure', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export default api