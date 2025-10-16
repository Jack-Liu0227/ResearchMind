import React, { useState } from 'react'
import { Atom, ChevronDown, ChevronUp, X, Download } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { CrystalStructure } from '../types'
import toast from 'react-hot-toast'

/**
 * 结构列表组件
 * 显示数据库查询返回的所有结构，可以点击查看
 * 最多显示5个最新的结构
 */
const MAX_DISPLAY_STRUCTURES = 5

const StructureList: React.FC = () => {
  const {
    currentSessionStructures,
    currentStructure,
    setCurrentStructure,
    clearCurrentSessionStructures
  } = useAppStore()
  const [isExpanded, setIsExpanded] = useState(true)

  // 只显示最新的5个结构
  const displayStructures = currentSessionStructures.slice(-MAX_DISPLAY_STRUCTURES)
  const totalCount = currentSessionStructures.length
  const hiddenCount = Math.max(0, totalCount - MAX_DISPLAY_STRUCTURES)

  const handleStructureClick = (structure: CrystalStructure, index: number) => {
    setCurrentStructure(structure)
    toast.success(`已切换到第 ${index + 1} 个结构: ${structure.formula}`)
  }

  const handleClearList = () => {
    clearCurrentSessionStructures()
    toast.success('已清空当前会话的结构列表')
  }

  if (currentSessionStructures.length === 0) {
    return null
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center space-x-2">
          <Atom className="w-4 h-4 text-primary-600" />
          <span className="text-sm font-semibold text-gray-800">
            晶体结构列表 ({totalCount} 个{hiddenCount > 0 ? `, 显示最新 ${MAX_DISPLAY_STRUCTURES} 个` : ''})
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 hover:bg-gray-200 rounded transition-colors"
            title={isExpanded ? "收起" : "展开"}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-600" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-600" />
            )}
          </button>
          <button
            onClick={handleClearList}
            className="p-1.5 hover:bg-red-100 rounded transition-colors"
            title="清空列表"
          >
            <X className="w-4 h-4 text-red-600" />
          </button>
        </div>
      </div>

      {/* 结构列表 */}
      {isExpanded && (
        <div className="flex-1 overflow-y-auto">
          {hiddenCount > 0 && (
            <div className="px-4 py-2 bg-yellow-50 border-b border-yellow-200">
              <p className="text-xs text-yellow-800 font-medium">
                ⚠️ 已隐藏 {hiddenCount} 个较早的结构，仅显示最新 {MAX_DISPLAY_STRUCTURES} 个
              </p>
            </div>
          )}
          <div className="divide-y divide-gray-100">
            {displayStructures.map((structure, index) => (
              <StructureListItem
                key={structure.id || index}
                structure={structure}
                index={index}
                isSelected={currentStructure?.id === structure.id}
                onClick={() => handleStructureClick(structure, index)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface StructureListItemProps {
  structure: CrystalStructure
  index: number
  isSelected: boolean
  onClick: () => void
}

const StructureListItem: React.FC<StructureListItemProps> = ({
  structure,
  index,
  isSelected,
  onClick
}) => {
  // 下载 CIF 文件
  const downloadCIF = (e: React.MouseEvent) => {
    e.stopPropagation() // 阻止触发 onClick

    // 统一使用 cifContent 字段
    const cifData = (structure as any).cifContent

    if (!cifData) {
      toast.error('无 CIF 数据可下载')
      console.error('结构数据:', structure)
      return
    }

    try {
      const blob = new Blob([cifData], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${structure.formula || 'structure'}.cif`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success(`已下载: ${structure.formula || 'structure'}.cif`)
    } catch (error) {
      console.error('下载 CIF 失败:', error)
      toast.error('下载 CIF 失败，请重试')
    }
  }

  return (
    <div
      className={`w-full px-4 py-3 hover:bg-blue-50 transition-all duration-200 relative group cursor-pointer ${
        isSelected ? 'bg-blue-50 border-l-4 border-blue-500 shadow-sm' : 'border-l-4 border-transparent'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* 序号和化学式 */}
          <div className="flex items-center space-x-2.5 mb-2">
            <span className={`flex-shrink-0 w-7 h-7 flex items-center justify-center text-xs font-semibold rounded-full transition-colors ${
              isSelected
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 group-hover:bg-blue-200 group-hover:text-blue-700'
            }`}>
              {index + 1}
            </span>
            <span className={`font-semibold text-base truncate transition-colors ${
              isSelected ? 'text-blue-700' : 'text-gray-900'
            }`}>
              {structure.formula}
            </span>
          </div>

          {/* 结构信息 */}
          <div className="text-xs text-gray-600 space-y-1 ml-9">
            {/* 数据库来源 */}
            {structure.source?.database && (
              <div className="flex items-center space-x-1.5">
                <span className="font-medium text-gray-500">来源:</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold shadow-sm ${
                  structure.source.database === 'Upload' ? 'bg-blue-100 text-blue-700' :
                  structure.source.database === 'Relaxed' ? 'bg-green-100 text-green-700' :
                  structure.source.database === 'Generated' ? 'bg-purple-100 text-purple-700' :
                  structure.source.database === 'MP' ? 'bg-orange-100 text-orange-700' :
                  structure.source.database === 'OQMD' ? 'bg-pink-100 text-pink-700' :
                  structure.source.database === 'COD' ? 'bg-indigo-100 text-indigo-700' :
                  structure.source.database === 'AFLOW' ? 'bg-teal-100 text-teal-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {structure.source.database}
                </span>
              </div>
            )}
            {structure.spaceGroup && (
              <div className="flex items-center space-x-1">
                <span className="font-medium text-gray-500">空间群:</span>
                <span className="text-gray-700">{structure.spaceGroup}</span>
              </div>
            )}
            {structure.latticeParameters && (
              <div className="flex items-center space-x-1">
                <span className="font-medium text-gray-500">晶格:</span>
                <span className="text-gray-700 font-mono text-xs">
                  a={structure.latticeParameters.a.toFixed(2)}Å,
                  b={structure.latticeParameters.b.toFixed(2)}Å,
                  c={structure.latticeParameters.c.toFixed(2)}Å
                </span>
              </div>
            )}
            {structure.atoms && (
              <div className="flex items-center space-x-1">
                <span className="font-medium text-gray-500">原子数:</span>
                <span className="text-gray-700">{structure.atoms.length}</span>
              </div>
            )}
            {structure.properties?.volume && (
              <div className="flex items-center space-x-1">
                <span className="font-medium text-gray-500">体积:</span>
                <span className="text-gray-700">{structure.properties.volume.toFixed(2)} Å³</span>
              </div>
            )}
          </div>
        </div>

        {/* 下载按钮和选中指示器 */}
        <div className="flex-shrink-0 ml-3 flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              downloadCIF(e)
            }}
            className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-2 hover:bg-blue-100 rounded-lg text-blue-600 hover:shadow-sm"
            title="下载 CIF 文件"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* 选中指示器 */}
          {isSelected && (
            <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse"></div>
          )}
        </div>
      </div>
    </div>
  )
}

export default StructureList

