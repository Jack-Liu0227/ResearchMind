/**
 * API Client for ResearchMind HTTP API
 * 用于调用后端 API 进行晶体结构处理
 */

import { CrystalStructure } from '../types';
import { API_CONFIG } from '../constants';

const API_BASE_URL = API_CONFIG.BASE_URL;

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
    const url = `${API_BASE_URL}/api/images/${imageType}/${filename}`;
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

