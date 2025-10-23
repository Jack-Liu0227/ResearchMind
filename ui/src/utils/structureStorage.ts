/**
 * Structure Storage Utilities
 * 用于保存和检索晶体结构数据
 */

import { API_CONFIG } from '../constants'

const API_ORIGIN = API_CONFIG.BASE_URL;
const API_PATH = API_CONFIG.API_PATH || '/api';
const API_BASE_URL = API_CONFIG.API_BASE_URL || `${API_ORIGIN}${API_PATH}`;

const ensureLeadingSlash = (value: string) => (value.startsWith('/') ? value : `/${value}`);
const buildApiUrl = (path: string) => `${API_BASE_URL}${ensureLeadingSlash(path)}`;

export interface StructureStorageResponse {
  success: boolean;
  structure_id: string;
  access_url: string;
}

/**
 * 保存结构数据到服务器
 * @param structureData 结构数据
 * @returns 保存结果，包含访问URL
 */
export async function saveStructure(structureData: any): Promise<StructureStorageResponse> {
  try {
    const response = await fetch(buildApiUrl('structures'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(structureData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '保存结构数据失败');
    }

    const data: StructureStorageResponse = await response.json();
    console.log('💾 结构数据已保存:', data.structure_id);
    return data;
  } catch (error) {
    console.error('❌ 保存结构数据失败:', error);
    throw error;
  }
}

/**
 * 根据ID获取结构数据
 * @param structureId 结构ID
 * @returns 结构数据
 */
export async function getStructure(structureId: string): Promise<any> {
  try {
    const response = await fetch(buildApiUrl(`structures/${structureId}`));

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('结构数据未找到');
      }
      const error = await response.json();
      throw new Error(error.detail || '获取结构数据失败');
    }

    const data = await response.json();
    console.log('🔍 获取结构数据:', structureId);
    return data;
  } catch (error) {
    console.error('❌ 获取结构数据失败:', error);
    throw error;
  }
}

/**
 * 列出所有保存的结构
 * @returns 结构列表
 */
export async function listStructures(): Promise<Array<{id: string, created_at: string}>> {
  try {
    const response = await fetch(buildApiUrl('structures'));

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '获取结构列表失败');
    }

    const data = await response.json();
    return data.structures;
  } catch (error) {
    console.error('❌ 获取结构列表失败:', error);
    throw error;
  }
}
