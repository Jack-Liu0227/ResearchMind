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
  try {
    const response = await fetch(buildApiUrl('cif'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        cif_content: cifContent,
        to_conventional: true,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '惯胞转换失败');
    }

    const data: APIStructureResponse = await response.json();

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
  } catch (error) {
    console.error('❌ 惯胞转换失败:', error);
    throw error;
  }
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
  try {
    const response = await fetch(buildApiUrl('cif'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        cif_content: cifContent,
        to_conventional: toConventional,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'CIF 解析失败');
    }

    const data: APIStructureResponse = await response.json();

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
  } catch (error) {
    console.error('❌ CIF 解析失败:', error);
    throw error;
  }
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
 * @param imageType 图片类型 (phonon_results 或 generated_structures)
 * @param filename 文件名
 */
export async function getPhononImage(
  imageType: 'phonon_results' | 'generated_structures',
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
  try {
    const response = await fetch(buildApiUrl('files?type=phonon_results'));

    if (!response.ok) {
      throw new Error(`Failed to fetch phonon results: ${response.statusText}`);
    }

    const data = await response.json();
    return data.files || [];
  } catch (error) {
    console.error('❌ 获取声子谱结果列表失败:', error);
    throw error;
  }
}

/**
 * 获取生成结构列表
 */
export async function getGeneratedStructures(): Promise<string[]> {
  try {
    const response = await fetch(buildApiUrl('files?type=generated_structures'));

    if (!response.ok) {
      throw new Error(`Failed to fetch generated structures: ${response.statusText}`);
    }

    const data = await response.json();
    return data.files || [];
  } catch (error) {
    console.error('❌ 获取生成结构列表失败:', error);
    throw error;
  }
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
  try {
    const response = await fetch(buildApiUrl('files?type=phonon_examples'));

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data.files || [];
  } catch (error) {
    console.error('❌ 获取声子谱示例失败:', error);
    throw error;
  }
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

