/**
 * CIF (Crystallographic Information File) Parser
 * 解析 CIF 文件并转换为 3D 可视化所需的晶体结构格式
 */

import { CrystalStructure, Atom } from '../types'

interface CIFData {
  cellLengthA?: number
  cellLengthB?: number
  cellLengthC?: number
  cellAngleAlpha?: number
  cellAngleBeta?: number
  cellAngleGamma?: number
  spaceGroup?: string
  chemicalFormula?: string
  atoms: Array<{
    label: string
    element: string
    x: number
    y: number
    z: number
    occupancy?: number
  }>
}

/**
 * 从 CIF 文件内容中提取数据
 * @param cifContent CIF 文件内容
 * @param useConventionalCell 是否转换为惯胞（默认为 true）
 */
export function parseCIF(cifContent: string, useConventionalCell: boolean = true): CrystalStructure | null {
  try {
    const lines = cifContent.split('\n').map(line => line.trim())
    const data: CIFData = {
      atoms: []
    }

    // 解析晶胞参数
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]

      // 晶胞长度
      if (line.startsWith('_cell_length_a')) {
        data.cellLengthA = parseFloat(line.split(/\s+/)[1])
      } else if (line.startsWith('_cell_length_b')) {
        data.cellLengthB = parseFloat(line.split(/\s+/)[1])
      } else if (line.startsWith('_cell_length_c')) {
        data.cellLengthC = parseFloat(line.split(/\s+/)[1])
      }

      // 晶胞角度
      else if (line.startsWith('_cell_angle_alpha')) {
        data.cellAngleAlpha = parseFloat(line.split(/\s+/)[1])
      } else if (line.startsWith('_cell_angle_beta')) {
        data.cellAngleBeta = parseFloat(line.split(/\s+/)[1])
      } else if (line.startsWith('_cell_angle_gamma')) {
        data.cellAngleGamma = parseFloat(line.split(/\s+/)[1])
      }

      // 空间群
      else if (line.startsWith('_symmetry_space_group_name_H-M') || 
               line.startsWith('_space_group_name_H-M_alt')) {
        data.spaceGroup = line.split(/\s+/).slice(1).join(' ').replace(/['"]/g, '')
      }

      // 化学式
      else if (line.startsWith('_chemical_formula_sum')) {
        data.chemicalFormula = line.split(/\s+/).slice(1).join(' ').replace(/['"]/g, '')
      }

      // 原子坐标循环
      else if (line.startsWith('loop_')) {
        const loopData = parseLoop(lines, i)
        if (loopData.atoms.length > 0) {
          data.atoms = loopData.atoms
        }
        i = loopData.endIndex
      }
    }

    // 验证必需的数据
    if (!data.cellLengthA || !data.cellLengthB || !data.cellLengthC ||
        !data.cellAngleAlpha || !data.cellAngleBeta || !data.cellAngleGamma ||
        data.atoms.length === 0) {
      console.error('CIF 文件缺少必需的数据')
      return null
    }

    // 转换为 CrystalStructure 格式
    let structure: CrystalStructure = {
      id: `cif_${Date.now()}`,
      formula: data.chemicalFormula || 'Unknown',
      spaceGroup: data.spaceGroup || 'P1',
      latticeParameters: {
        a: data.cellLengthA,
        b: data.cellLengthB,
        c: data.cellLengthC,
        alpha: data.cellAngleAlpha,
        beta: data.cellAngleBeta,
        gamma: data.cellAngleGamma,
      },
      atoms: convertFractionalToCartesian(
        data.atoms,
        data.cellLengthA,
        data.cellLengthB,
        data.cellLengthC,
        data.cellAngleAlpha,
        data.cellAngleBeta,
        data.cellAngleGamma
      ),
      properties: {
        volume: calculateCellVolume(
          data.cellLengthA,
          data.cellLengthB,
          data.cellLengthC,
          data.cellAngleAlpha,
          data.cellAngleBeta,
          data.cellAngleGamma
        )
      }
    }

    // 如果需要，转换为惯胞
    if (useConventionalCell) {
      structure = convertToConventionalCell(structure)
    }

    return structure
  } catch (error) {
    console.error('解析 CIF 文件失败:', error)
    return null
  }
}

/**
 * 解析 CIF 文件中的 loop_ 块
 */
function parseLoop(lines: string[], startIndex: number): { atoms: CIFData['atoms'], endIndex: number } {
  const atoms: CIFData['atoms'] = []
  let i = startIndex + 1

  // 读取列标题
  const columns: string[] = []
  while (i < lines.length && lines[i].startsWith('_')) {
    columns.push(lines[i])
    i++
  }

  // 查找原子坐标相关的列
  const labelIndex = columns.findIndex(col => col.includes('_atom_site_label') || col.includes('_atom_site_type_symbol'))
  const elementIndex = columns.findIndex(col => col.includes('_atom_site_type_symbol'))
  const xIndex = columns.findIndex(col => col.includes('_atom_site_fract_x'))
  const yIndex = columns.findIndex(col => col.includes('_atom_site_fract_y'))
  const zIndex = columns.findIndex(col => col.includes('_atom_site_fract_z'))
  const occupancyIndex = columns.findIndex(col => col.includes('_atom_site_occupancy'))

  if (xIndex === -1 || yIndex === -1 || zIndex === -1) {
    return { atoms: [], endIndex: i }
  }

  // 读取数据行
  while (i < lines.length && lines[i] && !lines[i].startsWith('_') && !lines[i].startsWith('loop_') && !lines[i].startsWith('#')) {
    const parts = lines[i].split(/\s+/)
    if (parts.length >= columns.length) {
      const label = parts[labelIndex] || parts[elementIndex] || 'X'
      const element = extractElement(parts[elementIndex] || parts[labelIndex] || 'X')
      const x = parseFloat(parts[xIndex])
      const y = parseFloat(parts[yIndex])
      const z = parseFloat(parts[zIndex])
      const occupancy = occupancyIndex !== -1 ? parseFloat(parts[occupancyIndex]) : 1.0

      if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
        atoms.push({ label, element, x, y, z, occupancy })
      }
    }
    i++
  }

  return { atoms, endIndex: i - 1 }
}

/**
 * 从原子标签中提取元素符号
 */
function extractElement(label: string): string {
  // 移除数字和特殊字符，只保留字母
  const match = label.match(/[A-Z][a-z]?/)
  return match ? match[0] : label.substring(0, 2)
}

/**
 * 将分数坐标转换为笛卡尔坐标
 */
function convertFractionalToCartesian(
  atoms: CIFData['atoms'],
  a: number,
  b: number,
  c: number,
  alpha: number,
  beta: number,
  gamma: number
): Atom[] {
  // 转换角度为弧度
  const alphaRad = (alpha * Math.PI) / 180
  const betaRad = (beta * Math.PI) / 180
  const gammaRad = (gamma * Math.PI) / 180

  // 计算转换矩阵
  const cosAlpha = Math.cos(alphaRad)
  const cosBeta = Math.cos(betaRad)
  const cosGamma = Math.cos(gammaRad)
  const sinGamma = Math.sin(gammaRad)

  const volume = a * b * c * Math.sqrt(
    1 - cosAlpha * cosAlpha - cosBeta * cosBeta - cosGamma * cosGamma +
    2 * cosAlpha * cosBeta * cosGamma
  )

  // 转换矩阵
  const m11 = a
  const m12 = b * cosGamma
  const m13 = c * cosBeta
  const m22 = b * sinGamma
  const m23 = c * (cosAlpha - cosBeta * cosGamma) / sinGamma
  const m33 = volume / (a * b * sinGamma)

  return atoms.map(atom => {
    const x = m11 * atom.x + m12 * atom.y + m13 * atom.z
    const y = m22 * atom.y + m23 * atom.z
    const z = m33 * atom.z

    return {
      element: atom.element,
      position: [x, y, z] as [number, number, number],
      charge: 0
    }
  })
}

/**
 * 计算晶胞体积
 */
function calculateCellVolume(
  a: number,
  b: number,
  c: number,
  alpha: number,
  beta: number,
  gamma: number
): number {
  const alphaRad = (alpha * Math.PI) / 180
  const betaRad = (beta * Math.PI) / 180
  const gammaRad = (gamma * Math.PI) / 180

  const cosAlpha = Math.cos(alphaRad)
  const cosBeta = Math.cos(betaRad)
  const cosGamma = Math.cos(gammaRad)

  return a * b * c * Math.sqrt(
    1 - cosAlpha * cosAlpha - cosBeta * cosBeta - cosGamma * cosGamma +
    2 * cosAlpha * cosBeta * cosGamma
  )
}

/**
 * 验证 CIF 文件格式
 */
export function isValidCIF(content: string): boolean {
  return content.includes('_cell_length_a') &&
         content.includes('_cell_length_b') &&
         content.includes('_cell_length_c') &&
         (content.includes('_atom_site_fract_x') || content.includes('_atom_site_Cartn_x'))
}

/**
 * 将晶体结构转换为惯胞（conventional cell）
 * 惯胞是晶体学中的标准晶胞表示，通常比原胞更大但更对称
 *
 * 注意：这是一个简化的实现，真正的惯胞转换需要空间群信息
 * 这里我们根据晶格参数判断晶系，然后生成对应的惯胞
 */
export function convertToConventionalCell(structure: CrystalStructure): CrystalStructure {
  const { latticeParameters, atoms } = structure
  const { a, b, c, alpha, beta, gamma } = latticeParameters

  // 判断晶系
  const tolerance = 0.01
  const angleTolerance = 1.0 // 度

  // 立方晶系: a = b = c, α = β = γ = 90°
  const isCubic =
    Math.abs(a - b) < tolerance &&
    Math.abs(b - c) < tolerance &&
    Math.abs(alpha - 90) < angleTolerance &&
    Math.abs(beta - 90) < angleTolerance &&
    Math.abs(gamma - 90) < angleTolerance

  // 四方晶系: a = b ≠ c, α = β = γ = 90°
  const isTetragonal =
    Math.abs(a - b) < tolerance &&
    Math.abs(a - c) > tolerance &&
    Math.abs(alpha - 90) < angleTolerance &&
    Math.abs(beta - 90) < angleTolerance &&
    Math.abs(gamma - 90) < angleTolerance

  // 正交晶系: a ≠ b ≠ c, α = β = γ = 90°
  const isOrthorhombic =
    Math.abs(alpha - 90) < angleTolerance &&
    Math.abs(beta - 90) < angleTolerance &&
    Math.abs(gamma - 90) < angleTolerance

  // 六方晶系: a = b ≠ c, α = β = 90°, γ = 120°
  const isHexagonal =
    Math.abs(a - b) < tolerance &&
    Math.abs(alpha - 90) < angleTolerance &&
    Math.abs(beta - 90) < angleTolerance &&
    Math.abs(gamma - 120) < angleTolerance

  // 三方晶系: a = b = c, α = β = γ ≠ 90°
  const isTrigonal =
    Math.abs(a - b) < tolerance &&
    Math.abs(b - c) < tolerance &&
    Math.abs(alpha - beta) < angleTolerance &&
    Math.abs(beta - gamma) < angleTolerance &&
    Math.abs(alpha - 90) > angleTolerance

  // 单斜晶系: a ≠ b ≠ c, α = γ = 90° ≠ β
  const isMonoclinic =
    Math.abs(alpha - 90) < angleTolerance &&
    Math.abs(gamma - 90) < angleTolerance &&
    Math.abs(beta - 90) > angleTolerance

  // 对于大多数情况，如果已经是正交、四方或立方晶系，
  // 原胞和惯胞是相同的或非常接近的
  // 这里我们主要确保原子坐标在 [0, 1) 范围内，并复制周期性边界的原子

  // 生成惯胞：使用改进的对称操作确保所有原子都显示，特别是顶点和边缘原子
  const conventionalAtoms: Atom[] = []
  const atomSet = new Set<string>() // 用于去重

  // 对于每个原子，生成所有对称等价位置
  atoms.forEach(atom => {
    const [x, y, z] = atom.position

    // 将笛卡尔坐标转换回分数坐标
    const fractional = cartesianToFractional(
      [x, y, z],
      a, b, c, alpha, beta, gamma
    )

    // 归一化到 [0, 1) 范围
    const normFrac = fractional.map(coord => {
      let normalized = coord % 1
      if (normalized < 0) normalized += 1
      return normalized
    }) as [number, number, number]

    // 使用更精确的阈值和更大的扩展范围来确保顶点原子显示
    const threshold = 0.001  // 更精确的阈值
    const positions: [number, number, number][] = []

    // 生成更大的扩展晶胞 3x3x3，确保所有边界和顶点原子都被包含
    for (let i = -1; i <= 1; i++) {
      for (let j = -1; j <= 1; j++) {
        for (let k = -1; k <= 1; k++) {
          const newFrac: [number, number, number] = [
            normFrac[0] + i,
            normFrac[1] + j,
            normFrac[2] + k
          ]
          
          // 更宽松的边界检查，确保包含所有可能的对称位置
          if (newFrac[0] >= -0.1 && newFrac[0] <= 1.1 &&
              newFrac[1] >= -0.1 && newFrac[1] <= 1.1 &&
              newFrac[2] >= -0.1 && newFrac[2] <= 1.1) {
            positions.push(newFrac)
          }
        }
      }
    }

    // 对于接近边界的原子，额外生成镜像位置
    const edgeThreshold = 0.05
    if (normFrac[0] < edgeThreshold || normFrac[0] > 1 - edgeThreshold ||
        normFrac[1] < edgeThreshold || normFrac[1] > 1 - edgeThreshold ||
        normFrac[2] < edgeThreshold || normFrac[2] > 1 - edgeThreshold) {
      
      // 为边界原子生成额外的对称位置
      const extraPositions: [number, number, number][] = []
      
      // X边界
      if (normFrac[0] < edgeThreshold) extraPositions.push([normFrac[0] + 1, normFrac[1], normFrac[2]])
      if (normFrac[0] > 1 - edgeThreshold) extraPositions.push([normFrac[0] - 1, normFrac[1], normFrac[2]])
      
      // Y边界
      if (normFrac[1] < edgeThreshold) extraPositions.push([normFrac[0], normFrac[1] + 1, normFrac[2]])
      if (normFrac[1] > 1 - edgeThreshold) extraPositions.push([normFrac[0], normFrac[1] - 1, normFrac[2]])
      
      // Z边界
      if (normFrac[2] < edgeThreshold) extraPositions.push([normFrac[0], normFrac[1], normFrac[2] + 1])
      if (normFrac[2] > 1 - edgeThreshold) extraPositions.push([normFrac[0], normFrac[1], normFrac[2] - 1])
      
      positions.push(...extraPositions)
    }

    // 转换所有位置并添加到结果中
    positions.forEach(pos => {
      const cartesian = fractionalToCartesian(pos, a, b, c, alpha, beta, gamma)
      
      // 使用更精确的唯一键以避免重复原子
      const key = `${atom.element}_${cartesian[0].toFixed(4)}_${cartesian[1].toFixed(4)}_${cartesian[2].toFixed(4)}`
      
      if (!atomSet.has(key)) {
        atomSet.add(key)
        conventionalAtoms.push({
          ...atom,
          position: cartesian
        })
      }
    })
  })

  return {
    ...structure,
    atoms: conventionalAtoms,
    properties: {
      ...structure.properties,
      isConventionalCell: true
    }
  }
}

/**
 * 将笛卡尔坐标转换为分数坐标
 */
export function cartesianToFractional(
  position: [number, number, number],
  a: number,
  b: number,
  c: number,
  alpha: number,
  beta: number,
  gamma: number
): [number, number, number] {
  const [x, y, z] = position

  // 转换角度为弧度
  const alphaRad = (alpha * Math.PI) / 180
  const betaRad = (beta * Math.PI) / 180
  const gammaRad = (gamma * Math.PI) / 180

  const cosAlpha = Math.cos(alphaRad)
  const cosBeta = Math.cos(betaRad)
  const cosGamma = Math.cos(gammaRad)
  const sinGamma = Math.sin(gammaRad)

  const volume = a * b * c * Math.sqrt(
    1 - cosAlpha * cosAlpha - cosBeta * cosBeta - cosGamma * cosGamma +
    2 * cosAlpha * cosBeta * cosGamma
  )

  // 逆转换矩阵
  const v = volume / (a * b * c)
  const fracX = x / a - (y * cosGamma) / (a * sinGamma) +
                (z * (cosAlpha * cosGamma - cosBeta)) / (a * sinGamma * v * c)
  const fracY = y / (b * sinGamma) -
                (z * (cosAlpha - cosBeta * cosGamma)) / (b * sinGamma * sinGamma * v * c)
  const fracZ = z * a * b * sinGamma / volume

  return [fracX, fracY, fracZ]
}

/**
 * 将分数坐标转换为笛卡尔坐标（辅助函数）
 */
export function fractionalToCartesian(
  fractional: [number, number, number],
  a: number,
  b: number,
  c: number,
  alpha: number,
  beta: number,
  gamma: number
): [number, number, number] {
  const [fx, fy, fz] = fractional

  // 转换角度为弧度
  const alphaRad = (alpha * Math.PI) / 180
  const betaRad = (beta * Math.PI) / 180
  const gammaRad = (gamma * Math.PI) / 180

  const cosAlpha = Math.cos(alphaRad)
  const cosBeta = Math.cos(betaRad)
  const cosGamma = Math.cos(gammaRad)
  const sinGamma = Math.sin(gammaRad)

  const volume = a * b * c * Math.sqrt(
    1 - cosAlpha * cosAlpha - cosBeta * cosBeta - cosGamma * cosGamma +
    2 * cosAlpha * cosBeta * cosGamma
  )

  // 转换矩阵
  const m11 = a
  const m12 = b * cosGamma
  const m13 = c * cosBeta
  const m22 = b * sinGamma
  const m23 = c * (cosAlpha - cosBeta * cosGamma) / sinGamma
  const m33 = volume / (a * b * sinGamma)

  const x = m11 * fx + m12 * fy + m13 * fz
  const y = m22 * fy + m23 * fz
  const z = m33 * fz

  return [x, y, z]
}

