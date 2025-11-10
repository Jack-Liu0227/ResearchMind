/**
 * API Client for ResearchMind HTTP API
 * 用于调用后端 API 进行晶体结构处理
 */

import { CrystalStructure } from '../types';
import { API_CONFIG } from '../constants';

const API_ORIGIN = API_CONFIG.BASE_URL;
const API_PATH = API_CONFIG.API_PATH || '/api';
const API_BASE_URL = API_CONFIG.API_BASE_URL || `${API_ORIGIN}${API_PATH}`;

const ensureLeadingSlash = (value: string) => (value.startsWith('/') ? value : `/${value}`);

const buildApiUrl = (path: string) => `${API_BASE_URL}${ensureLeadingSlash(path)}`;

/**
 * 统一的 API 调用包装器
 * 🔧 优化：减少重复的错误处理代码
 */
async function apiCall<T>(
  fetcher: () => Promise<Response>,
  errorMessage: string
): Promise<T> {
  try {
    const response = await fetcher();

    if (!response.ok) {
      let errorDetail = errorMessage;
      try {
        const error = await response.json();
        errorDetail = error.detail || error.message || errorMessage;
      } catch {
        // 如果响应不是 JSON，使用默认错误消息
        errorDetail = `${errorMessage}: ${response.statusText}`;
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (error) {
    console.error(`❌ ${errorMessage}:`, error);
    throw error;
  }
}

/**
 * 安全的 API 调用包装器（返回 null 而不是抛出错误）
 * 🔧 优化：用于可选的 API 调用，失败时返回 null
 */
async function safeApiCall<T>(
  fetcher: () => Promise<Response>,
  errorMessage: string
): Promise<T | null> {
  try {
    return await apiCall<T>(fetcher, errorMessage);
  } catch (error) {
    // 错误已经被 apiCall 记录，这里只返回 null
    return null;
  }
}

const resolveEffectiveOrigin = () => {
  if (API_ORIGIN.startsWith('http://') || API_ORIGIN.startsWith('https://')) {
    return API_ORIGIN;
  }

  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    return port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;
  }

  return API_ORIGIN;
};

/**
 * 处理 URL 转换：如果是相对路径，转换为完整 URL
 * 用于处理后端返回的相对路径 URL（如 /api/download/...）
 *
 * 支持两种部署方式：
 * 1. 直接访问：http://localhost:50002/api/download/...
 * 2. 反向代理：http://dyum1393797.bohrium.tech:50001/api/download/...
 */
export function resolveFileUrl(url: string): string {
  console.log('🔗 resolveFileUrl - input:', url);
  console.log('🔗 resolveFileUrl - API_ORIGIN:', API_ORIGIN);
  console.log('🔗 resolveFileUrl - API_PATH:', API_PATH);

  if (url.startsWith('http://') || url.startsWith('https://')) {
    try {
      const parsed = new URL(url)
      // If absolute URL path starts with /download/, rewrite to /api/download/ to match backend mount
      if (parsed.pathname.startsWith('/download/')) {
        const newPath = `${API_PATH}${parsed.pathname.startsWith('/api/') ? parsed.pathname.slice(4) : parsed.pathname}`
        const result = `${parsed.origin}${newPath}${parsed.search}${parsed.hash}`
        console.log('🔗 resolveFileUrl - rewrote absolute /download to:', result)
        return result
      }
    } catch (e) {
      console.warn('🔗 resolveFileUrl - failed to parse absolute URL, returning as is')
    }
    console.log('🔗 resolveFileUrl - already full URL, returning:', url);
    return url;
  }

  const effectiveOrigin = resolveEffectiveOrigin();
  console.log('🔗 resolveFileUrl - effective origin:', effectiveOrigin);

  const ensureApiPath = (value: string) => {
    const normalized = ensureLeadingSlash(value);
    if (API_PATH === '/' || normalized.startsWith(API_PATH)) {
      return normalized;
    }
    if (normalized.startsWith('/download/')) {
      return `${API_PATH}${normalized}`;
    }
    return `${API_PATH}${normalized}`;
  };

  if (url.startsWith('/')) {
    const pathWithApi = ensureApiPath(url);
    const result = `${effectiveOrigin}${pathWithApi}`;
    console.log('🔗 resolveFileUrl - resolved absolute path:', result);
    return result;
  }

  const pathWithApi = ensureApiPath(url);
  const result = `${effectiveOrigin}${pathWithApi}`;
  console.log('🔗 resolveFileUrl - resolved relative path:', result);
  return result;
}

export interface APIStructureResponse {
  formula: string;
  spaceGroup: string;
  latticeParameters: {
    a: number;
    b: number;
    c: number;
    alpha: number;
    beta: number;
    gamma: number;
  };
  atoms: Array<{
    element: string;
    position: [number, number, number];
    charge: number;
  }>;
  properties?: {
    volume?: number;
    density?: number;
    isConventionalCell?: boolean;
  };
}

/**
 * 将 CIF 文件转换为惯胞
 */
export async function convertToConventionalCell(
  cifContent: string
): Promise<CrystalStructure> {
  const data = await apiCall<APIStructureResponse>(
    () => fetch(buildApiUrl('cif'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        cif_content: cifContent,
        to_conventional: true,
      }),
    }),
    '惯胞转换失败'
  );

  // 转换为 CrystalStructure 格式
  return {
    id: `api_${Date.now()}`,
    formula: data.formula,
    spaceGroup: data.spaceGroup,
    latticeParameters: data.latticeParameters,
    atoms: data.atoms.map(atom => ({
      element: atom.element,
      position: atom.position,
      charge: atom.charge,
    })),
    properties: data.properties,
  };
}

/**
 * 解析 CIF 文件
 * @param cifContent CIF 文件内容
 * @param toConventional 是否转换为惯胞 (默认 false,返回原胞)
 */
export async function parseCIF(
  cifContent: string,
  toConventional: boolean = false
): Promise<CrystalStructure> {
  const data = await apiCall<APIStructureResponse>(
    () => fetch(buildApiUrl('cif'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        cif_content: cifContent,
        to_conventional: toConventional,
      }),
    }),
    'CIF 解析失败'
  );

  // 转换为 CrystalStructure 格式
  return {
    id: `api_${Date.now()}`,
    formula: data.formula,
    spaceGroup: data.spaceGroup,
    latticeParameters: data.latticeParameters,
    atoms: data.atoms.map(atom => ({
      element: atom.element,
      position: atom.position,
      charge: atom.charge,
    })),
    properties: data.properties,
  };
}

/**
 * 检查 API 服务器健康状态
 */
export async function checkAPIHealth(): Promise<boolean> {
  try {
    const response = await fetch(buildApiUrl('health'));
    if (!response.ok) return false;

    const data = await response.json();
    return data.status === 'healthy' && data.pymatgen_available;
  } catch (error) {
    console.error('❌ API 健康检查失败:', error);
    return false;
  }
}

/**
 * 获取声子谱图片
 * @param imageType 图片类型 (phonon 或 generated_structures)
 * @param filename 文件名
 */
export async function getPhononImage(
  imageType: 'phonon' | 'generated_structures',
  filename: string
): Promise<string> {
  try {
    // 统一使用 resolveFileUrl 处理相对路径（不包含 /api 前缀）
    const url = resolveFileUrl(`/images/${imageType}/${filename}`);
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.statusText}`);
    }

    // 返回图片 URL (可以直接用于 <img src={url} />)
    return url;
  } catch (error) {
    console.error('❌ 获取声子谱图片失败:', error);
    throw error;
  }
}

/**
 * 获取声子谱结果列表
 */
export async function getPhononResults(): Promise<string[]> {
  const data = await apiCall<{ files: string[] }>(
    () => fetch(buildApiUrl('files?type=phonon_results')),
    '获取声子谱结果列表失败'
  );
  return data.files || [];
}

/**
 * 获取生成结构列表
 */
export async function getGeneratedStructures(): Promise<string[]> {
  const data = await apiCall<{ files: string[] }>(
    () => fetch(buildApiUrl('files?type=generated_structures')),
    '获取生成结构列表失败'
  );
  return data.files || [];
}

/**
 * 声子谱图片接口
 */
export interface PhononImage {
  name: string;
  url: string;
  path: string;
  type: 'phonon_dispersion' | 'phonon_dos';
  description?: string;
}

/**
 * 获取声子谱示例图片列表
 */
export async function getPhononExamples(): Promise<PhononImage[]> {
  const data = await apiCall<{ files: PhononImage[] }>(
    () => fetch(buildApiUrl('files?type=phonon_examples')),
    '获取声子谱示例失败'
  );
  return data.files || [];
}

// Safer health check that tolerates non-JSON responses
export async function checkAPIHealthSafe(): Promise<boolean> {
  const apiHealthUrl = buildApiUrl('health');

  try {
    const res = await fetch(apiHealthUrl);
    if (res.ok) {
      try {
        const data = await res.json();
        return data.status === 'healthy' && (typeof data.pymatgen_available === 'boolean' ? true : true);
      } catch {
        const txt = await res.text();
        return /healthy/i.test(txt);
      }
    }
  } catch (e) {
    console.error('API health check failed:', e);
    return false;
  }
}

/**
 * 计费统计相关接口
 */

export interface BillingStats {
  conversation_id?: string
  user_id?: string
  total_tokens: number
  total_photons: number
  request_count: number
  charged?: boolean
  has_user_config?: boolean
  billing_source?: string
  created_at?: string
  updated_at?: string
}

export interface UserBillingStats {
  user_id: string
  total_conversations: number
  total_tokens: number
  total_photons: number
  total_requests: number
  conversations: BillingStats[]
}

export interface GlobalBillingStats {
  total_tokens: number
  total_photons: number
  total_requests: number
  total_sessions: number
  start_time: string
  current_time: string
  billing_config: {
    tokens_per_photon: number
    billing_enabled: boolean
    precision: number
  }
}

/**
 * 获取指定对话的计费统计
 * 🔧 优化：正确处理 success=false 的情况
 */
export async function getConversationBillingStats(conversationId: string): Promise<BillingStats | null> {
  const result = await safeApiCall<{ success: boolean; message?: string; data: BillingStats | null }>(
    () => fetch(buildApiUrl(`billing/stats/conversation/${conversationId}`)),
    '获取对话计费统计失败'
  );

  // 如果 API 调用失败（网络错误等），返回 null
  if (!result) {
    console.warn('⚠️ [getConversationBillingStats] API 调用失败，返回 null');
    return null;
  }

  // 如果后端返回 success=false（对话不存在），也返回 null
  if (!result.success) {
    console.log(`ℹ️ [getConversationBillingStats] 对话 ${conversationId} 不存在或无数据: ${result.message}`);
    return null;
  }

  // 返回实际数据
  return result.data;
}

/**
 * 获取指定用户的总计费统计
 */
export async function getUserBillingStats(userId: string): Promise<UserBillingStats | null> {
  const result = await safeApiCall<{ success: boolean; data: UserBillingStats }>(
    () => fetch(buildApiUrl(`billing/stats/user/${userId}`)),
    '获取用户计费统计失败'
  );
  return result?.success && result.data ? result.data : null;
}

/**
 * 获取全局计费统计
 */
export async function getGlobalBillingStats(): Promise<GlobalBillingStats | null> {
  const result = await safeApiCall<{ success: boolean; data: GlobalBillingStats }>(
    () => fetch(buildApiUrl('billing/stats/global')),
    '获取全局计费统计失败'
  );
  return result?.success && result.data ? result.data : null;
}

/**
 * 列出指定用户的所有对话及其计费信息
 */
export async function listUserConversations(userId: string): Promise<BillingStats[]> {
  const result = await safeApiCall<{ success: boolean; conversations: BillingStats[] }>(
    () => fetch(buildApiUrl(`billing/conversations/user/${userId}`)),
    '列出用户对话失败'
  );
  return result?.success && result.conversations ? result.conversations : [];
}
