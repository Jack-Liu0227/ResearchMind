import React, { useState } from 'react'
import { 
  Database, 
  Download, 
  Search, 
  Filter, 
  Eye, 
  Trash2, 

  ChevronDown,
  ChevronRight,
  Atom as AtomIcon,
  ExternalLink,
  Info
} from 'lucide-react'
import { CrystalStructure } from '../types'
import { useAppStore } from '../store/useAppStore'
import toast from 'react-hot-toast'

interface StructureManagerProps {
  className?: string
}

/**
 * 增强的结构管理组件
 * 支持多数据库来源的结构展示、筛选、管理
 */
const StructureManager: React.FC<StructureManagerProps> = ({ className = '' }) => {
  const {
    currentSessionStructures,
    currentStructure,
    setCurrentStructure,
    clearCurrentSessionStructures,
    structureList
  } = useAppStore()

  const [searchTerm, setSearchTerm] = useState('')
  const [selectedDatabase, setSelectedDatabase] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'formula' | 'database' | 'timestamp'>('timestamp')
  const [isExpanded, setIsExpanded] = useState(true)
  const [showDetails, setShowDetails] = useState<string | null>(null)

  // 合并当前会话结构和全局结构列表
  const allStructures = [
    ...currentSessionStructures,
    ...structureList.filter(s => !currentSessionStructures.find(cs => cs.id === s.id))
  ]

  // 筛选和排序结构
  const filteredStructures = allStructures
    .filter(structure => {
      const matchesSearch = structure.formula.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           structure.spaceGroup.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           structure.id.toLowerCase().includes(searchTerm.toLowerCase())
      
      const matchesDatabase = selectedDatabase === 'all' || 
                             structure.source?.database === selectedDatabase
      
      return matchesSearch && matchesDatabase
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'formula':
          return a.formula.localeCompare(b.formula)
        case 'database':
          return (a.source?.database || '').localeCompare(b.source?.database || '')
        case 'timestamp':
        default:
          return (b.metadata?.timestamp || 0) - (a.metadata?.timestamp || 0)
      }
    })

  // 按数据库分组
  const groupedStructures = filteredStructures.reduce((groups, structure) => {
    const database = structure.source?.database || 'Unknown'
    if (!groups[database]) {
      groups[database] = []
    }
    groups[database].push(structure)
    return groups
  }, {} as Record<string, CrystalStructure[]>)

  // 获取可用的数据库列表
  const availableDatabases = Array.from(
    new Set(allStructures.map(s => s.source?.database).filter(Boolean))
  )

  const handleStructureSelect = (structure: CrystalStructure) => {
    setCurrentStructure(structure)
    toast.success(`已切换到 ${structure.formula} (${structure.source?.database || 'Unknown'})`)
  }

  const handleDownloadCIF = (structure: CrystalStructure) => {
    // 统一使用 cifContent 字段
    const cifData = structure.cifContent
    
    if (cifData) {
      const blob = new Blob([cifData], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${structure.formula}_${structure.id}.cif`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('CIF 文件已下载')
    } else {
      toast.error('该结构没有可用的 CIF 数据')
    }
  }

  const handleClearAll = () => {
    clearCurrentSessionStructures()
    toast.success('已清空所有结构')
  }

  const getDatabaseIcon = (database?: string) => {
    switch (database) {
      case 'MP': return '🔬'
      case 'OQMD': return '⚛️'
      case 'COD': return '💎'
      case 'AFLOW': return '🌊'
      case 'Generated': return '🤖'
      case 'Upload': return '📤'
      default: return '📊'
    }
  }

  const getDatabaseColor = (database?: string) => {
    switch (database) {
      case 'MP': return 'bg-blue-100 text-blue-800'
      case 'OQMD': return 'bg-green-100 text-green-800'
      case 'COD': return 'bg-purple-100 text-purple-800'
      case 'AFLOW': return 'bg-orange-100 text-orange-800'
      case 'Generated': return 'bg-pink-100 text-pink-800'
      case 'Upload': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (allStructures.length === 0) {
    return null  // 没有结构时不显示组件
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
      {/* 紧凑的头部 */}
      <div className="px-3 py-2 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-white rounded transition-colors"
            >
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-gray-600" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
              )}
            </button>
            <Database className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-800">
              数据库结构
            </h3>
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
              {allStructures.length}
            </span>
          </div>

          <div className="flex items-center space-x-1">
            {/* 数据库状态指示器 */}
            <div className="flex items-center space-x-1">
              {availableDatabases.map(db => (
                <span key={db} className="w-2 h-2 rounded-full bg-green-400" title={`${db} 数据库可用`}></span>
              ))}
            </div>
            
            <button
              onClick={handleClearAll}
              className="p-1 hover:bg-white rounded transition-colors"
              title="清空所有结构"
            >
              <Trash2 className="w-3.5 h-3.5 text-gray-500 hover:text-red-600" />
            </button>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-2 space-y-2">
            {/* 数据库统计信息 */}
            <div className="flex flex-wrap gap-1">
              {Object.entries(groupedStructures).map(([database, structures]) => (
                <span key={database} className={`px-2 py-0.5 text-xs rounded-full ${getDatabaseColor(database)}`}>
                  {getDatabaseIcon(database)} {database} ({structures.length})
                </span>
              ))}
            </div>

            {/* 紧凑的搜索框 */}
            {allStructures.length > 3 && (
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索分子式、空间群或ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            )}

            {/* 紧凑的筛选器 */}
            {allStructures.length > 3 && (
              <div className="flex items-center space-x-2 text-xs">
                <Filter className="w-3 h-3 text-gray-500" />
                <select
                  value={selectedDatabase}
                  onChange={(e) => setSelectedDatabase(e.target.value)}
                  className="text-xs border border-gray-300 rounded px-1.5 py-1 flex-1"
                >
                  <option value="all">全部数据库</option>
                  {availableDatabases.map(db => (
                    <option key={db} value={db}>
                      {getDatabaseIcon(db)} {db}
                    </option>
                  ))}
                </select>

                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="text-xs border border-gray-300 rounded px-1.5 py-1"
                >
                  <option value="timestamp">最新</option>
                  <option value="formula">分子式</option>
                  <option value="database">数据库</option>
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 紧凑的结构列表 */}
      {isExpanded && (
        <div className="max-h-64 overflow-y-auto">
          {Object.entries(groupedStructures).map(([database, structures]) => (
            <div key={database} className="border-b border-gray-100 last:border-b-0">
              <div className="px-3 py-1.5 bg-gray-50 text-xs font-medium text-gray-600 flex items-center space-x-1.5">
                <span>{getDatabaseIcon(database)}</span>
                <span>{database}</span>
                <span className="text-gray-400">({structures.length})</span>
              </div>

              <div className="divide-y divide-gray-50">
                {structures.map((structure) => (
                  <StructureItem
                    key={structure.id}
                    structure={structure}
                    isSelected={currentStructure?.id === structure.id}
                    onSelect={() => handleStructureSelect(structure)}
                    onDownload={() => handleDownloadCIF(structure)}
                    onToggleDetails={() => setShowDetails(
                      showDetails === structure.id ? null : structure.id
                    )}
                    showDetails={showDetails === structure.id}
                    getDatabaseColor={getDatabaseColor}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

interface StructureItemProps {
  structure: CrystalStructure
  isSelected: boolean
  onSelect: () => void
  onDownload: () => void
  onToggleDetails: () => void
  showDetails: boolean
  getDatabaseColor: (database?: string) => string
}

const StructureItem: React.FC<StructureItemProps> = ({
  structure,
  isSelected,
  onSelect,
  onDownload,
  onToggleDetails,
  showDetails,
  getDatabaseColor
}) => {
  return (
    <div className={`px-3 py-2 hover:bg-blue-50 transition-colors cursor-pointer ${isSelected ? 'bg-blue-100 border-l-2 border-l-blue-600' : ''}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0" onClick={onSelect}>
          <div className="flex items-center space-x-1.5 mb-0.5">
            <span className="text-sm font-semibold text-gray-900 truncate">
              {structure.formula}
            </span>
            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${getDatabaseColor(structure.source?.database)}`}>
              {structure.source?.database || 'N/A'}
            </span>
          </div>

          <div className="text-xs text-gray-600 space-x-2">
            <span>{structure.spaceGroup}</span>
            <span>•</span>
            <span>{structure.atoms.length} 原子</span>
            {structure.properties?.density && (
              <>
                <span>•</span>
                <span>{structure.properties.density.toFixed(2)} g/cm³</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-0.5 ml-2">
          <button
            onClick={(e) => { e.stopPropagation(); onToggleDetails(); }}
            className="p-1 hover:bg-white rounded transition-colors"
            title="详情"
          >
            <Info className="w-3.5 h-3.5 text-gray-500" />
          </button>

          {structure.cifContent && (
            <button
              onClick={(e) => { e.stopPropagation(); onDownload(); }}
              className="p-1 hover:bg-white rounded transition-colors"
              title="下载"
            >
              <Download className="w-3.5 h-3.5 text-gray-500" />
            </button>
          )}

          {structure.source?.url && (
            <a
              href={structure.source.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-1 hover:bg-white rounded transition-colors"
              title="原始数据"
            >
              <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
            </a>
          )}

          <button
            onClick={(e) => { e.stopPropagation(); onSelect(); }}
            className="p-1 hover:bg-white rounded transition-colors"
            title="查看"
          >
            <Eye className="w-3.5 h-3.5 text-blue-600" />
          </button>
        </div>
      </div>

      {/* 紧凑的详细信息面板 */}
      {showDetails && (
        <div className="mt-2 pt-2 border-t border-gray-200 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <h4 className="font-semibold text-gray-700 mb-1">晶格参数</h4>
              <div className="space-y-0.5 text-gray-600">
                <div>a={structure.latticeParameters.a.toFixed(2)} b={structure.latticeParameters.b.toFixed(2)} c={structure.latticeParameters.c.toFixed(2)} Å</div>
                <div>α={structure.latticeParameters.alpha.toFixed(1)}° β={structure.latticeParameters.beta.toFixed(1)}° γ={structure.latticeParameters.gamma.toFixed(1)}°</div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold text-gray-700 mb-1">物理性质</h4>
              <div className="space-y-0.5 text-gray-600">
                {structure.properties?.volume && (
                  <div>体积: {structure.properties.volume.toFixed(1)} Å³</div>
                )}
                {structure.properties?.bandGap !== undefined && (
                  <div>带隙: {structure.properties.bandGap.toFixed(2)} eV</div>
                )}
                {structure.properties?.energyAboveHull !== undefined && (
                  <div>E: {structure.properties.energyAboveHull.toFixed(3)} eV/atom</div>
                )}
              </div>
            </div>
          </div>

          {structure.source?.materialId && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <span className="font-semibold text-gray-700">ID:</span>
              <span className="ml-1 text-gray-600">{structure.source.materialId}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default StructureManager
