/**
 * 批量分析面板组件
 *
 * 功能：
 * - 显示批量分析和报告生成选项
 * - 通过 WebSocket 消息自动重置状态
 * - 显示分析结果
 */

import React from 'react'
import { FileText, Download } from 'lucide-react'
import { wsService } from '../services/websocket'
import { useAppStore } from '../store/useAppStore'
import toast from 'react-hot-toast'

interface BatchAnalysisPanelProps {
  csvFilePath: string
  sessionId: string
  selectedPaperIds: string[]
  totalPapers: number
}

const BatchAnalysisPanel: React.FC<BatchAnalysisPanelProps> = ({
  csvFilePath,
  sessionId,
  selectedPaperIds,
  totalPapers
}) => {
  const currentAgent = useAppStore((state) => state.currentAgent)
  const targetAgentId = currentAgent?.id === 'deep_research_agent' ? currentAgent.id : 'deep_research_agent'

  const ensureWsConnected = async () => {
    if (wsService.isConnected) {
      return true
    }

    try {
      await wsService.connect()
      return wsService.isConnected
    } catch (error) {
      toast.error('WebSocket 未连接，请刷新页面或检查后端服务 (50003)')
      return false
    }
  }

  // 批量分析
  const handleBatchAnalysis = async () => {
    if (!(await ensureWsConnected())) {
      return
    }

    // 构造消息
    const paperIdsJson = JSON.stringify(selectedPaperIds)
    const message = selectedPaperIds.length === 0
      ? `请对 CSV 文件中的所有文献进行批量分析，使用 batch_paper_analysis 工具，参数：
csv_file_path="${csvFilePath}"
paper_ids=[]
session_id="${sessionId}"`
      : `请对我选中的 ${selectedPaperIds.length} 篇文献进行批量分析，使用 batch_paper_analysis 工具，参数：
csv_file_path="${csvFilePath}"
paper_ids=${paperIdsJson}
session_id="${sessionId}"`

    wsService.sendMessage(message, targetAgentId, sessionId)
    
    toast.success(
      selectedPaperIds.length === 0
        ? `已发送批量分析请求（所有 ${totalPapers} 篇文献）`
        : `已发送批量分析请求（${selectedPaperIds.length} 篇文献）`
    )
  }

  // 生成研究报告
  const handleGenerateReport = async () => {
    if (!(await ensureWsConnected())) {
      return
    }

    // 构造消息
    const paperIdsJson = JSON.stringify(selectedPaperIds)
    const message = selectedPaperIds.length === 0
      ? `请基于 CSV 文件中的所有文献生成研究报告，使用 generate_research_report 工具，参数：
csv_file_path="${csvFilePath}"
paper_ids=[]
session_id="${sessionId}"
topic="综合研究报告"`
      : `请基于我选中的 ${selectedPaperIds.length} 篇文献生成研究报告，使用 generate_research_report 工具，参数：
csv_file_path="${csvFilePath}"
paper_ids=${paperIdsJson}
session_id="${sessionId}"
topic="综合研究报告"`

    wsService.sendMessage(message, targetAgentId, sessionId)
    
    toast.success(
      selectedPaperIds.length === 0
        ? `已发送报告生成请求（所有 ${totalPapers} 篇文献）`
        : `已发送报告生成请求（${selectedPaperIds.length} 篇文献）`
    )
  }

  // 🔧 取消和关闭进度追踪器的函数已移除，因为：
  // 1. 进度追踪器已被禁用（使用 Toast 通知替代）
  // 2. 状态重置现在由 ChatPage.tsx 中的 WebSocket 消息处理器负责
  // 3. 避免 analysisProgress 闭包问题

  const selectedCount = selectedPaperIds.length
  const targetCount = selectedCount || totalPapers

  return (
    <div className="space-y-4">
      {/* 操作按钮 */}
      <div className="flex space-x-3">
        <button
          onClick={handleBatchAnalysis}
          className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
        >
          <FileText className="w-5 h-5" />
          <span>批量分析 ({targetCount}篇)</span>
        </button>

        <button
          onClick={handleGenerateReport}
          className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors font-medium"
        >
          <Download className="w-5 h-5" />
          <span>生成报告 ({targetCount}篇)</span>
        </button>
      </div>
    </div>
  )
}

export default BatchAnalysisPanel
