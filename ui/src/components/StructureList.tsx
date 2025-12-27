import React, { useState, useMemo } from 'react'
import { Atom, ChevronDown, ChevronUp, X, Download, Trash2, CheckSquare, Square, Zap, Activity, Flame, Filter, Battery } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { CrystalStructure } from '../types'
import { wsService } from '../services/websocket'
import toast from 'react-hot-toast'

/**
 * 结构列表组件
 * 显示数据库查询返回的所有结构，可以点击查看
 * 🔧 修复：显示所有结构，不再限制显示数量
 */

// 来源类型定义
type SourceFilter = 'all' | 'Upload' | 'Relaxed' | 'Generated' | 'MP' | 'OQMD' | 'COD' | 'AFLOW'

const StructureList: React.FC = () => {
  const {
    currentSessionStructures,
    currentStructure,
    setCurrentStructure,
    removeFromCurrentSessionStructures,
    clearCurrentSessionStructures,
    selectedStructureIds,
    toggleStructureSelection,
    selectAllStructures,
    clearSelectedStructures,
    setSelectedStructureIds, // 🆕 Add this
    setCurrentSessionStructures, // 🆕 Add this
    currentSession
  } = useAppStore()
  const [isExpanded, setIsExpanded] = useState(true)
  const [showActions, setShowActions] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')
  const [showFilterMenu, setShowFilterMenu] = useState(false)

  // 获取所有可用的来源类型
  const availableSources = useMemo(() => {
    const sources = new Set<string>()
    currentSessionStructures.forEach(s => {
      if (s.source?.database) {
        sources.add(s.source.database)
      }
    })
    return Array.from(sources)
  }, [currentSessionStructures])

  // 根据筛选条件过滤结构
  const filteredStructures = useMemo(() => {
    if (sourceFilter === 'all') {
      return currentSessionStructures
    }
    return currentSessionStructures.filter(s => s.source?.database === sourceFilter)
  }, [currentSessionStructures, sourceFilter])

  // 🔧 修复：显示所有结构，按时间倒序排列（最新的在上方）
  const displayStructures = [...filteredStructures].reverse()
  const totalCount = currentSessionStructures.length
  const filteredCount = filteredStructures.length
  const selectedCount = selectedStructureIds.length
  // 🔧 修复：使用当前会话 ID，不使用 'default' fallback
  const sessionId = currentSession?.id || ''

  const handleStructureClick = (structure: CrystalStructure, index: number) => {
    setCurrentStructure(structure)
    toast.success(`已切换到第 ${index + 1} 个结构: ${structure.formula}`)
  }

  const handleClearList = () => {
    clearCurrentSessionStructures()
    clearSelectedStructures()
    toast.success('已清空当前会话的结构列表')
  }

  // 🆕 批量删除操作
  const handleBatchDelete = () => {
    if (selectedCount === 0) return

    if (window.confirm(`确定要删除选中的 ${selectedCount} 个结构吗？`)) {
      const remainingStructures = currentSessionStructures.filter(s => !selectedStructureIds.includes(s.id))
      setCurrentSessionStructures(remainingStructures)
      clearSelectedStructures()
      toast.success(`已删除 ${selectedCount} 个结构`)
      setShowActions(false)
    }
  }

  // 🆕 全选/取消全选 (支持基于当前筛选视图)
  const handleSelectAll = () => {
    const visibleIds = displayStructures.map(s => s.id)
    const allVisibleSelected = visibleIds.length > 0 && visibleIds.every(id => selectedStructureIds.includes(id))

    if (allVisibleSelected) {
      // 取消全选当前视图的结构 (保留其他不在视图中的选中项)
      const newSelection = selectedStructureIds.filter(id => !visibleIds.includes(id))
      setSelectedStructureIds(newSelection)
    } else {
      // 全选当前视图的结构 (合并到现有选中项)
      const newSelection = Array.from(new Set([...selectedStructureIds, ...visibleIds]))
      setSelectedStructureIds(newSelection)
    }
  }

  // 🆕 仿真计算操作
  const handleRelaxation = () => {
    if (selectedCount === 0) {
      toast.error('请先选择要弛豫的结构')
      return
    }

    // 🆕 过滤掉已弛豫的结构
    const selectedStructs = currentSessionStructures.filter(s => selectedStructureIds.includes(s.id))
    const nonRelaxedStructs = selectedStructs.filter(s => s.source?.database !== 'Relaxed')
    const alreadyRelaxedCount = selectedStructs.length - nonRelaxedStructs.length

    if (alreadyRelaxedCount > 0) {
      toast(`⚠️ 已自动跳过 ${alreadyRelaxedCount} 个已弛豫的结构`, {
        icon: 'ℹ️',
        duration: 3000
      })
    }

    if (nonRelaxedStructs.length === 0) {
      toast.error('所有选中的结构都已弛豫，无需再次弛豫')
      return
    }

    // 🔧 只传递 file_path 和 source
    const structures = nonRelaxedStructs.map(s => ({
      file_path: (s as any).cif_file_path,
      source: s.source?.database === 'Upload' ? 'upload' :
        s.source?.database === 'Relaxed' ? 'relax' :
          s.source?.database === 'Generated' ? 'generate' :
            ['MP', 'OQMD', 'COD', 'AFLOW'].includes(s.source?.database || '') ? 'database' : 'upload'
    }))

    const structuresJson = JSON.stringify(structures)
    const message = `请对选中的 ${nonRelaxedStructs.length} 个结构进行弛豫计算。
⚠️ 重要指令：
1.所有结构均已包含绝对文件路径（file_path字段）。
2.请【直接】调用 relax_structure 工具处理这 ${nonRelaxedStructs.length} 个文件。
3.【绝对不要】调用 extract_and_validate_cif，也不要试图重新提取文件。
4.必须一次性处理所有文件，不要遗漏数据库来源的文件。

参数：
session_id="${sessionId}"
structures=${structuresJson}
device="cuda"`

    wsService.sendMessage(message, 'simulation_agent', sessionId)
    toast.success(`已发送弛豫请求（${nonRelaxedStructs.length} 个结构）`)
    setShowActions(false)
  }

  const handlePhononCalculation = () => {
    if (selectedCount === 0) {
      toast.error('请先选择要计算声子的结构')
      return
    }

    // 检查是否有未弛豫的结构
    const selectedStructs = currentSessionStructures.filter(s => selectedStructureIds.includes(s.id))
    const nonRelaxedCount = selectedStructs.filter(s => s.source?.database !== 'Relaxed').length

    if (nonRelaxedCount > 0) {
      toast(`⚠️ ${nonRelaxedCount} 个结构未弛豫，建议先进行弛豫计算`, {
        icon: '⚠️',
        duration: 4000
      })
    }

    // 🔧 只传递 file_path 和 source
    const structures = selectedStructs.map(s => ({
      file_path: (s as any).cif_file_path,
      source: s.source?.database === 'Upload' ? 'upload' :
        s.source?.database === 'Relaxed' ? 'relax' :
          s.source?.database === 'Generated' ? 'generate' :
            ['MP', 'OQMD', 'COD', 'AFLOW'].includes(s.source?.database || '') ? 'database' : 'upload'
    }))

    const structuresJson = JSON.stringify(structures)
    // 🔧 修改：声子计算不再内置弛豫，用户需要先单独弛豫
    const message = `请对选中的 ${selectedCount} 个结构进行声子计算。
⚠️ 重要指令：
1.所有结构均已包含绝对文件路径（file_path字段）。
2.请【直接】调用 calculate_phonon 工具处理这 ${selectedCount} 个结构。
3.【绝对不要】调用 extract_and_validate_cif。
4.必须一次性处理所有结构。

参数：
session_id="${sessionId}"
structures=${structuresJson}
perform_relaxation=false
device="cuda"`

    wsService.sendMessage(message, 'simulation_agent', sessionId)
    toast.success(`已发送声子计算请求（${selectedCount} 个结构）`)
    setShowActions(false)
  }

  // 🆕 能量计算操作
  const handleEnergyCalculation = () => {
    if (selectedCount === 0) {
      toast.error('请先选择要计算能量的结构')
      return
    }

    // 🔧 只传递 file_path 和 source
    const structures = currentSessionStructures
      .filter(s => selectedStructureIds.includes(s.id))
      .map(s => ({
        file_path: (s as any).cif_file_path,
        source: s.source?.database === 'Upload' ? 'upload' :
          s.source?.database === 'Relaxed' ? 'relax' :
            s.source?.database === 'Generated' ? 'generate' :
              ['MP', 'OQMD', 'COD', 'AFLOW'].includes(s.source?.database || '') ? 'database' : 'upload'
      }))

    const structuresJson = JSON.stringify(structures)
    const message = `请对选中的 ${selectedCount} 个结构进行静态能量计算。
⚠️ 重要指令：
1.所有结构均已包含绝对文件路径（file_path字段）。
2.请【直接】调用 calculate_energy 工具处理这 ${selectedCount} 个结构。
3.【绝对不要】调用 extract_and_validate_cif。
4.必须一次性处理所有结构。

参数：
session_id="${sessionId}"
structures=${structuresJson}
device="cuda"`

    wsService.sendMessage(message, 'simulation_agent', sessionId)
    toast.success(`已发送能量计算请求（${selectedCount} 个结构）`)
    setShowActions(false)
  }

  const handleKappaCalculation = () => {
    if (selectedCount === 0) {
      toast.error('请先选择要计算热导率的结构')
      return
    }

    // 🔧 只传递 file_path 和 source
    const structures = currentSessionStructures
      .filter(s => selectedStructureIds.includes(s.id))
      .map(s => ({
        file_path: (s as any).cif_file_path,
        source: s.source?.database === 'Upload' ? 'upload' :
          s.source?.database === 'Relaxed' ? 'relax' :
            s.source?.database === 'Generated' ? 'generate' :
              ['MP', 'OQMD', 'COD', 'AFLOW'].includes(s.source?.database || '') ? 'database' : 'upload'
      }))

    const structuresJson = JSON.stringify(structures)
    const message = `请对选中的 ${selectedCount} 个结构进行热导率计算。
⚠️ 重要指令：
1.所有结构均已包含绝对文件路径（file_path字段）。
2.请【直接】调用 calculate_kappa 工具处理这 ${selectedCount} 个结构。
3.【绝对不要】调用 extract_and_validate_cif。
4.必须一次性处理所有结构。

参数：
session_id="${sessionId}"
structures=${structuresJson}
method="kappa_p"
temperature=300.0`

    wsService.sendMessage(message, 'simulation_agent', sessionId)
    toast.success(`已发送热导率计算请求（${selectedCount} 个结构）`)
    setShowActions(false)
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
            晶体结构 ({filteredCount}/{totalCount})
          </span>
        </div>
        <div className="flex items-center space-x-1">
          {/* 🆕 来源筛选按钮 */}
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className={`p-1.5 rounded transition-colors ${sourceFilter !== 'all' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-200 text-gray-600'}`}
              title="按来源筛选"
            >
              <Filter className="w-4 h-4" />
            </button>
            {/* 筛选下拉菜单 */}
            {showFilterMenu && (
              <div className="absolute right-0 top-full mt-1 w-36 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                <button
                  onClick={() => { setSourceFilter('all'); setShowFilterMenu(false); }}
                  className={`w-full px-3 py-1.5 text-left text-xs hover:bg-gray-100 ${sourceFilter === 'all' ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'}`}
                >
                  全部来源
                </button>
                {availableSources.map(source => (
                  <button
                    key={source}
                    onClick={() => { setSourceFilter(source as SourceFilter); setShowFilterMenu(false); }}
                    className={`w-full px-3 py-1.5 text-left text-xs hover:bg-gray-100 flex items-center space-x-2 ${sourceFilter === source ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'}`}
                  >
                    <span className={`w-2 h-2 rounded-full ${source === 'Upload' ? 'bg-blue-500' :
                      source === 'Relaxed' ? 'bg-green-500' :
                        source === 'Generated' ? 'bg-purple-500' :
                          source === 'MP' ? 'bg-orange-500' :
                            source === 'OQMD' ? 'bg-pink-500' :
                              source === 'COD' ? 'bg-indigo-500' :
                                source === 'AFLOW' ? 'bg-teal-500' :
                                  'bg-gray-500'
                      }`}></span>
                    <span>{source}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* 🆕 全选按钮 */}
          <button
            onClick={handleSelectAll}
            className={`p-1.5 rounded transition-colors ${selectedCount === totalCount && totalCount > 0 ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-200 text-gray-600'}`}
            title={selectedCount === totalCount ? "取消全选" : "全选"}
          >
            {selectedCount === totalCount && totalCount > 0 ? (
              <CheckSquare className="w-4 h-4" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>
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

      {/* 🆕 当前筛选状态提示 */}
      {sourceFilter !== 'all' && (
        <div className="px-4 py-1.5 bg-blue-50 border-b border-blue-200 flex items-center justify-between">
          <span className="text-xs text-blue-700">
            筛选: <span className="font-medium">{sourceFilter}</span> ({filteredCount} 个)
          </span>
          <button
            onClick={() => setSourceFilter('all')}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            清除筛选
          </button>
        </div>
      )}

      {/* 🆕 选中状态和操作按钮 */}
      {selectedCount > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-200 flex items-center justify-between">
          <span className="text-sm text-blue-700 font-medium">
            已选择 {selectedCount} 个结构
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowActions(!showActions)}
              className="px-3 py-1 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors whitespace-nowrap"
            >
              {showActions ? '收起' : '批量计算'}
            </button>
            <button
              onClick={handleBatchDelete}
              className="px-3 py-1 text-xs font-medium bg-red-100 text-red-600 rounded hover:bg-red-200 transition-colors flex items-center space-x-1"
              title="批量删除选中的结构"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>删除</span>
            </button>
            <button
              onClick={clearSelectedStructures}
              className="px-2 py-1 text-xs text-blue-600 hover:text-blue-800"
            >
              取消选择
            </button>
          </div>
        </div>
      )}

      {/* 🆕 计算操作面板 - 手机端固定在底部，PC端正常显示 */}
      {showActions && selectedCount > 0 && (
        <>
          {/* 移动端遮罩层 */}
          <div
            className="md:hidden fixed inset-0 bg-black/20 z-40"
            onClick={() => setShowActions(false)}
          />
          <div className="md:static fixed bottom-0 left-0 right-0 z-[100] bg-white md:bg-gradient-to-r md:from-blue-50 md:to-indigo-50 border-t md:border-b md:border-t-0 border-blue-200 px-4 pt-4 pb-32 md:py-3 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] md:shadow-none space-y-3 md:space-y-2 animate-in slide-in-from-bottom duration-200">
            <div className="flex items-center justify-between md:block">
              <p className="text-sm font-medium text-gray-700 md:text-gray-600 md:text-xs md:font-normal">
                对选中的 {selectedCount} 个结构执行计算：
              </p>
              <button
                onClick={() => setShowActions(false)}
                className="md:hidden text-gray-500 hover:text-gray-700 whitespace-nowrap"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 md:flex md:flex-wrap md:gap-2">
              <button
                onClick={handleRelaxation}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 md:py-2 bg-green-600 text-white text-sm md:text-xs font-medium rounded-lg hover:bg-green-700 transition-colors shadow-sm active:scale-95 whitespace-nowrap"
              >
                <Zap className="w-4 h-4 md:w-3.5 md:h-3.5" />
                <span>结构弛豫</span>
              </button>
              <button
                onClick={handleEnergyCalculation}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 md:py-2 bg-teal-600 text-white text-sm md:text-xs font-medium rounded-lg hover:bg-teal-700 transition-colors shadow-sm active:scale-95"
              >
                <Battery className="w-4 h-4 md:w-3.5 md:h-3.5" />
                <span>静态能量</span>
              </button>
              <button
                onClick={handlePhononCalculation}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 md:py-2 bg-purple-600 text-white text-sm md:text-xs font-medium rounded-lg hover:bg-purple-700 transition-colors shadow-sm active:scale-95"
              >
                <Activity className="w-4 h-4 md:w-3.5 md:h-3.5" />
                <span>声子计算</span>
              </button>
              <button
                onClick={handleKappaCalculation}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 md:py-2 bg-orange-600 text-white text-sm md:text-xs font-medium rounded-lg hover:bg-orange-700 transition-colors shadow-sm active:scale-95"
              >
                <Flame className="w-4 h-4 md:w-3.5 md:h-3.5" />
                <span>热导率</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* 结构列表 */}
      {isExpanded && (
        <div className={`flex-1 overflow-y-auto ${showActions ? 'pb-48 md:pb-0' : ''}`}>
          <div className="divide-y divide-gray-100">
            {displayStructures.map((structure, index) => (
              <StructureListItem
                key={structure.id || `${structure.formula}-${structure.metadata?.timestamp || index}`}
                structure={structure}
                index={index}
                isSelected={currentStructure?.id === structure.id}
                isChecked={selectedStructureIds.includes(structure.id)}
                onToggleCheck={() => toggleStructureSelection(structure.id)}
                onClick={() => handleStructureClick(structure, index)}
                onDelete={() => {
                  removeFromCurrentSessionStructures(structure.id)
                  toast.success(`已删除结构: ${structure.formula}`)
                }}
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
  isChecked: boolean
  onToggleCheck: () => void
  onClick: () => void
  onDelete: () => void
}

const StructureListItem: React.FC<StructureListItemProps> = ({
  structure,
  index,
  isSelected,
  isChecked,
  onToggleCheck,
  onClick,
  onDelete
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
      className={`w-full px-4 py-3 hover:bg-blue-50 transition-all duration-200 relative group cursor-pointer ${isSelected ? 'bg-blue-50 border-l-4 border-blue-500 shadow-sm' : isChecked ? 'bg-green-50 border-l-4 border-green-400' : 'border-l-4 border-transparent'
        }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* 🆕 复选框 + 序号和化学式 */}
          <div className="flex items-center space-x-2.5 mb-2">
            {/* 复选框 */}
            <button
              onClick={(e) => {
                e.stopPropagation()
                onToggleCheck()
              }}
              className={`flex-shrink-0 w-5 h-5 flex items-center justify-center rounded transition-colors ${isChecked
                ? 'text-green-600 hover:text-green-700'
                : 'text-gray-400 hover:text-gray-600'
                }`}
              title={isChecked ? "取消选择" : "选择此结构"}
            >
              {isChecked ? (
                <CheckSquare className="w-4 h-4" />
              ) : (
                <Square className="w-4 h-4" />
              )}
            </button>
            <span className={`flex-shrink-0 w-6 h-6 flex items-center justify-center text-xs font-semibold rounded-full transition-colors ${isSelected
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 text-gray-700 group-hover:bg-blue-200 group-hover:text-blue-700'
              }`}>
              {index + 1}
            </span>
            <span className={`font-semibold text-base truncate transition-colors ${isSelected ? 'text-blue-700' : 'text-gray-900'
              }`}>
              {structure.formula}
            </span>
          </div>

          {/* 结构信息 */}
          <div className="text-xs text-gray-600 space-y-1 ml-12">
            {/* 数据库来源 */}
            {structure.source?.database && (
              <div className="flex items-center space-x-1.5">
                <span className="font-medium text-gray-500">来源:</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold shadow-sm ${structure.source.database === 'Upload' ? 'bg-blue-100 text-blue-700' :
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

        {/* 操作按钮和选中指示器 */}
        <div className="flex-shrink-0 ml-3 flex items-center space-x-1">
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

          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-2 hover:bg-red-100 rounded-lg text-red-600 hover:shadow-sm"
            title="删除此结构"
          >
            <Trash2 className="w-4 h-4" />
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

