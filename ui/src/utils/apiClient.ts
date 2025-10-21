/**
 * API Client for ResearchMind HTTP API
 * 用于调用后端 API 进行晶体结构处理
 */

import { CrystalStructure } from '../types';
import { API_CONFIG } from '../constants';

const API_BASE_URL = API_CONFIG.BASE_URL;

/**
 * 处理 URL 转换：如果是相对路径，转换为完整 URL
 * 用于处理后端返回的相对路径 URL（如 /api/download/...）
 *
 * 支持两种部署方式：
 * 1. 直接访问：http://localhost:50002/api/download/...
 * 2. 反向代理：http://dyum1393797.bohrium.tech:50001/api/download/...
 */
export function resolveFileUrl(url: string): string {
  console.log('🔗 resolveFileUrl - input:', url)
  console.log('🔗 resolveFileUrl - API_BASE_URL:', API_BASE_URL)

  // 如果已经是完整 URL，直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    console.log('🔗 resolveFileUrl - already full URL, returning:', url)
    return url;
  }

  // 如果是相对路径，使用 API_BASE_URL 作为基础
  if (url.startsWith('/')) {
    // 关键修复：检查 API_BASE_URL 是否已经包含 /api
    let finalUrl = url;

    // 如果 API_BASE_URL 已经以 /api 结尾，就不要再添加 /api 前缀
    if (API_BASE_URL.endsWith('/api') || API_BASE_URL === '/api') {
      // API_BASE_URL 已经是 /api 或以 /api 结尾，直接使用 url
      finalUrl = url;
    } else if (!url.startsWith('/api/')) {
      // API_BASE_URL 不包含 /api，需要添加
      finalUrl = `/api${url}`;
    }

    // 如果 API_BASE_URL 是完整 URL
    if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
      const result = `${API_BASE_URL}${finalUrl}`;
      console.log('🔗 resolveFileUrl - using API_BASE_URL:', result)
      return result;
    }

    // 如果 API_BASE_URL 是相对路径（如 /api），则需要使用当前域名
    // 这种情况通常发生在通过反向代理访问时
    const { protocol, hostname, port } = window.location;

    // 构建基础 URL
    // 注意：不使用 import.meta.env.VITE_API_PORT，因为在反向代理环境中应该使用当前访问的端口
    const baseUrl = port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;

    const result = `${baseUrl}${finalUrl}`;
    console.log('🔗 resolveFileUrl - using window.location:', result)
    console.log('🔗 resolveFileUrl - window.location:', { protocol, hostname, port })
    return result;
  }

  // 其他情况：相对路径（不以 / 开头）
  // 例如：api/api/download/papers/...
  console.log('🔗 resolveFileUrl - relative path case:', url)

  // 转换为以 / 开头的路径
  const pathWithSlash = `/${url}`;

  // 如果 API_BASE_URL 是完整 URL
  if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
    const result = `${API_BASE_URL}${pathWithSlash}`;
    console.log('🔗 resolveFileUrl - relative path with API_BASE_URL:', result)
    return result;
  }

  // 如果 API_BASE_URL 是相对路径，使用当前域名
  const { protocol, hostname, port } = window.location;
  const baseUrl = port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;
  const result = `${baseUrl}${pathWithSlash}`;
  console.log('🔗 resolveFileUrl - relative path with window.location:', result)
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
    const response = await fetch(`${API_BASE_URL}/api/convert_to_conventional`, {
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
    const response = await fetch(`${API_BASE_URL}/api/parse_cif`, {
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
    const response = await fetch(`${API_BASE_URL}/health`);
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
    const response = await fetch(`${API_BASE_URL}/api/phonon_results`);

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
    const response = await fetch(`${API_BASE_URL}/api/generated_structures`);

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
    const response = await fetch(`${API_BASE_URL}/api/phonon_examples`);

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

