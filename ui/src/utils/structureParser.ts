/**
 * Structure Data Parser
 * 从后端返回的文本中解析晶体结构数据
 */

import { CrystalStructure, Atom } from '../types'
import { parseCIF, isValidCIF } from './cifParser'

/**
 * 从文本中提取晶体结构数据
 * 支持 Materials Project, OQMD, COD 等数据库的输出格式
 */
export function parseStructureFromText(text: string): CrystalStructure | null {
  try {
    // 尝试多种解析方法
    let structure = parseMaterialsProjectFormat(text)
    if (structure) return structure

    structure = parseOQMDFormat(text)
    if (structure) return structure

    structure = parseGenericFormat(text)
    if (structure) return structure

    return null
  } catch (error) {
    console.error('解析结构数据失败:', error)
    return null
  }
}

/**
 * 解析 Materials Project 格式
 * 示例：
 * 材料ID: mp-22862
 * 化学式: NaCl
 * 晶格参数: a=3.951, b=3.951, c=3.951, α=60.00, β=60.00, γ=60.00
 * 空间群: Fm-3m
 * 原子位置:
 *   Na (0.0, 0.0, 0.0)
 *   Cl (2.281, 1.613, 3.951)
 */
function parseMaterialsProjectFormat(text: string): CrystalStructure | null {
  const lines = text.split('\n')
  
  let materialId = ''
  let formula = ''
  let spaceGroup = ''
  let latticeParams = { a: 0, b: 0, c: 0, alpha: 0, beta: 0, gamma: 0 }
  const atoms: Atom[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()

    // 提取材料ID
    if (line.includes('材料ID') || line.includes('Material ID')) {
      const match = line.match(/mp-\d+/)
      if (match) materialId = match[0]
    }

    // 提取化学式
    if (line.includes('化学式') || line.includes('Formula')) {
      const match = line.match(/[:：]\s*([A-Za-z0-9]+)/)
      if (match) formula = match[1]
    }

    // 提取空间群
    if (line.includes('空间群') || line.includes('Space Group')) {
      const match = line.match(/[:：]\s*([A-Za-z0-9\-\/]+)/)
      if (match) spaceGroup = match[1]
    }

    // 提取晶格参数
    if (line.includes('晶格参数') || line.includes('Lattice Parameters')) {
      const aMatch = line.match(/a=([0-9.]+)/)
      const bMatch = line.match(/b=([0-9.]+)/)
      const cMatch = line.match(/c=([0-9.]+)/)
      const alphaMatch = line.match(/α=([0-9.]+)/)
      const betaMatch = line.match(/β=([0-9.]+)/)
      const gammaMatch = line.match(/γ=([0-9.]+)/)

      if (aMatch) latticeParams.a = parseFloat(aMatch[1])
      if (bMatch) latticeParams.b = parseFloat(bMatch[1])
      if (cMatch) latticeParams.c = parseFloat(cMatch[1])
      if (alphaMatch) latticeParams.alpha = parseFloat(alphaMatch[1])
      if (betaMatch) latticeParams.beta = parseFloat(betaMatch[1])
      if (gammaMatch) latticeParams.gamma = parseFloat(gammaMatch[1])
    }

    // 提取原子位置
    if (line.includes('原子位置') || line.includes('Sites') || line.includes('Atomic positions')) {
      // 读取后续的原子数据
      for (let j = i + 1; j < lines.length; j++) {
        const atomLine = lines[j].trim()
        if (!atomLine || atomLine.startsWith('**') || atomLine.startsWith('---')) break

        // 匹配格式: Na (0.0, 0.0, 0.0) 或 Na 0.0 0.0 0.0
        const match1 = atomLine.match(/([A-Z][a-z]?)\s*\(([0-9.\-]+),\s*([0-9.\-]+),\s*([0-9.\-]+)\)/)
        const match2 = atomLine.match(/([A-Z][a-z]?)\s+([0-9.\-]+)\s+([0-9.\-]+)\s+([0-9.\-]+)/)
        const match3 = atomLine.match(/([A-Z][a-z]?)\s*\[([0-9.\-]+),\s*([0-9.\-]+),\s*([0-9.\-]+)\]/)

        const match = match1 || match2 || match3
        if (match) {
          atoms.push({
            element: match[1],
            position: [parseFloat(match[2]), parseFloat(match[3]), parseFloat(match[4])],
            charge: 0
          })
        }
      }
      break
    }
  }

  // 验证数据完整性
  if (!formula || latticeParams.a === 0 || atoms.length === 0) {
    return null
  }

  return {
    id: materialId || `structure_${Date.now()}`,
    formula,
    spaceGroup: spaceGroup || 'P1',
    latticeParameters: latticeParams,
    atoms,
    properties: {}
  }
}

/**
 * 解析 OQMD 格式
 */
function parseOQMDFormat(text: string): CrystalStructure | null {
  // OQMD 格式类似，使用相同的解析逻辑
  return parseMaterialsProjectFormat(text)
}

/**
 * 解析通用格式
 * 尝试从任何包含结构信息的文本中提取数据
 */
function parseGenericFormat(text: string): CrystalStructure | null {
  const lines = text.split('\n')
  
  let formula = ''
  let spaceGroup = 'P1'
  let latticeParams = { a: 5.0, b: 5.0, c: 5.0, alpha: 90, beta: 90, gamma: 90 }
  const atoms: Atom[] = []

  // 尝试提取化学式
  const formulaMatch = text.match(/([A-Z][a-z]?[0-9]*)+/)
  if (formulaMatch) formula = formulaMatch[0]

  // 尝试提取晶格参数
  const latticeMatch = text.match(/a\s*=\s*([0-9.]+).*b\s*=\s*([0-9.]+).*c\s*=\s*([0-9.]+)/)
  if (latticeMatch) {
    latticeParams.a = parseFloat(latticeMatch[1])
    latticeParams.b = parseFloat(latticeMatch[2])
    latticeParams.c = parseFloat(latticeMatch[3])
  }

  // 尝试提取原子坐标
  for (const line of lines) {
    const atomMatch = line.match(/([A-Z][a-z]?)\s+([0-9.\-]+)\s+([0-9.\-]+)\s+([0-9.\-]+)/)
    if (atomMatch) {
      atoms.push({
        element: atomMatch[1],
        position: [parseFloat(atomMatch[2]), parseFloat(atomMatch[3]), parseFloat(atomMatch[4])],
        charge: 0
      })
    }
  }

  if (!formula || atoms.length === 0) {
    return null
  }

  return {
    id: `structure_${Date.now()}`,
    formula,
    spaceGroup,
    latticeParameters: latticeParams,
    atoms,
    properties: {}
  }
}

/**
 * 检测文本中是否包含结构数据
 */
export function hasStructureData(text: string): boolean {
  // 首先检查是否是 CIF 格式
  if (isValidCIF(text)) {
    return true
  }

  // 检查其他格式的关键词
  const keywords = [
    '晶格参数', 'Lattice Parameters', 'lattice',
    '原子位置', 'Atomic positions', 'Sites',
    '空间群', 'Space Group',
    '化学式', 'Formula',
    'mp-', 'oqmd-', 'cod-',
    '_cell_length_a', '_atom_site_fract_x'  // CIF 关键词
  ]

  return keywords.some(keyword => text.includes(keyword))
}

/**
 * 从 JSON 格式解析结构数据
 */
export function parseStructureFromJSON(json: any): CrystalStructure | null {
  try {
    if (!json.formula || !json.atoms || !Array.isArray(json.atoms)) {
      return null
    }

    return {
      id: json.id || json.material_id || `structure_${Date.now()}`,
      formula: json.formula || json.chemical_formula,
      spaceGroup: json.spaceGroup || json.space_group || 'P1',
      latticeParameters: {
        a: json.latticeParameters?.a || json.lattice?.a || 5.0,
        b: json.latticeParameters?.b || json.lattice?.b || 5.0,
        c: json.latticeParameters?.c || json.lattice?.c || 5.0,
        alpha: json.latticeParameters?.alpha || json.lattice?.alpha || 90,
        beta: json.latticeParameters?.beta || json.lattice?.beta || 90,
        gamma: json.latticeParameters?.gamma || json.lattice?.gamma || 90,
      },
      atoms: json.atoms.map((atom: any) => ({
        element: atom.element || atom.species || 'X',
        position: atom.position || atom.coords || [0, 0, 0],
        charge: atom.charge || 0
      })),
      properties: json.properties || {}
    }
  } catch (error) {
    console.error('解析 JSON 结构数据失败:', error)
    return null
  }
}

/**
 * 智能解析：尝试所有可能的格式
 */
export function smartParseStructure(content: string, source?: { database?: string, materialId?: string, url?: string }): CrystalStructure | null {
  // 1. 尝试 CIF 格式（优先，因为最常用）
  if (isValidCIF(content)) {
    const structure = parseCIF(content, true)  // 使用惯胞模式
    if (structure) {
      console.log('✅ 成功解析 CIF 格式结构')
      return enhanceStructureWithMetadata(structure, content, source)
    }
  }

  // 2. 尝试 JSON 格式
  try {
    const json = JSON.parse(content)
    const structure = parseStructureFromJSON(json)
    if (structure) {
      console.log('✅ 成功解析 JSON 格式结构')
      return enhanceStructureWithMetadata(structure, content, source)
    }
  } catch {
    // 不是 JSON 格式，继续尝试其他格式
  }

  // 3. 尝试文本格式
  const structure = parseStructureFromText(content)
  if (structure) {
    console.log('✅ 成功解析文本格式结构')
    return enhanceStructureWithMetadata(structure, content, source)
  }
  return structure
}

/**
 * 增强结构数据，添加元数据和来源信息
 */
function enhanceStructureWithMetadata(
  structure: CrystalStructure,
  originalContent: string,
  source?: { database?: string, materialId?: string, url?: string }
): CrystalStructure {
  const now = new Date()

  return {
    ...structure,
    source: {
      database: (source?.database as any) || detectDatabase(originalContent),
      materialId: source?.materialId || extractMaterialId(originalContent),
      url: source?.url,
      retrievedAt: now
    },
    metadata: {
      ...structure.metadata,
      timestamp: Date.now()
    },
    // 统一使用 cifContent 字段
    cifContent: isValidCIF(originalContent) ? originalContent : undefined
  }
}

/**
 * 从内容中检测数据库来源
 */
function detectDatabase(content: string): 'MP' | 'OQMD' | 'COD' | 'AFLOW' | 'Generated' | 'Custom' {
  const lowerContent = content.toLowerCase()

  if (lowerContent.includes('materials project') || lowerContent.includes('mp-')) {
    return 'MP'
  }
  if (lowerContent.includes('oqmd') || lowerContent.includes('open quantum')) {
    return 'OQMD'
  }
  if (lowerContent.includes('crystallography open database') || lowerContent.includes('cod')) {
    return 'COD'
  }
  if (lowerContent.includes('aflow') || lowerContent.includes('automatic flow')) {
    return 'AFLOW'
  }
  if (lowerContent.includes('generated') || lowerContent.includes('crystallm')) {
    return 'Generated'
  }

  return 'Custom'
}

/**
 * 从内容中提取材料ID
 */
function extractMaterialId(content: string): string | undefined {
  // Materials Project ID
  const mpMatch = content.match(/mp-\d+/i)
  if (mpMatch) return mpMatch[0]

  // OQMD ID
  const oqmdMatch = content.match(/oqmd-\d+/i)
  if (oqmdMatch) return oqmdMatch[0]

  // COD ID
  const codMatch = content.match(/cod-\d+/i)
  if (codMatch) return codMatch[0]

  // AFLOW ID
  const aflowMatch = content.match(/aflow:\w+/i)
  if (aflowMatch) return aflowMatch[0]

  return undefined
}

