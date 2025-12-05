/**
 * 进度追踪组件
 * 
 * 用于显示批量论文分析和报告生成的实时进度
 * 支持：
 * - 进度条显示
 * - 当前任务描述
 * - 已完成/总数统计
 * - 预估剩余时间
 * - 可取消操作
 */

import React, { useEffect, useState } from 'react'
import { X, Loader2, CheckCircle, AlertCircle } from 'lucide-react'

export interface ProgressData {
  current: number
  total: number
  progress: number  // 0-1
  message: string
  status?: 'running' | 'success' | 'error' | 'cancelled'
  error?: string
  startTime?: number
}

interface ProgressTrackerProps {
  data: ProgressData | null
  onCancel?: () => void
  onClose?: () => void
  title?: string
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  data,
  onCancel,
  onClose,
  title = '批量处理进度'
}) => {
  const [estimatedTime, setEstimatedTime] = useState<string>('')

  useEffect(() => {
    if (!data || !data.startTime || data.current === 0) {
      setEstimatedTime('')
      return
    }

    const elapsed = Date.now() - data.startTime
    const avgTimePerItem = elapsed / data.current
    const remaining = (data.total - data.current) * avgTimePerItem
    
    const minutes = Math.floor(remaining / 60000)
    const seconds = Math.floor((remaining % 60000) / 1000)
    
    if (minutes > 0) {
      setEstimatedTime(`预计剩余 ${minutes} 分 ${seconds} 秒`)
    } else {
      setEstimatedTime(`预计剩余 ${seconds} 秒`)
    }
  }, [data])

  if (!data) return null

  const progressPercent = Math.round(data.progress * 100)
  const isComplete = data.status === 'success' || data.current >= data.total
  const hasError = data.status === 'error'
  const isCancelled = data.status === 'cancelled'

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-white rounded-lg shadow-2xl border border-gray-200 z-50">
      {/* 标题栏 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          {!isComplete && !hasError && !isCancelled && (
            <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
          )}
          {isComplete && (
            <CheckCircle className="w-5 h-5 text-green-600" />
          )}
          {hasError && (
            <AlertCircle className="w-5 h-5 text-red-600" />
          )}
          <h3 className="font-semibold text-gray-900">{title}</h3>
        </div>
        
        {(isComplete || hasError || isCancelled) && onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        )}
      </div>

      {/* 进度内容 */}
      <div className="p-4 space-y-3">
        {/* 进度条 */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">
              {data.current} / {data.total}
            </span>
            <span className="font-medium text-gray-900">
              {progressPercent}%
            </span>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                hasError ? 'bg-red-500' :
                isComplete ? 'bg-green-500' :
                'bg-blue-600'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* 当前任务描述 */}
        <p className="text-sm text-gray-700 line-clamp-2">
          {data.message}
        </p>

        {/* 预估时间 */}
        {estimatedTime && !isComplete && !hasError && (
          <p className="text-xs text-gray-500">
            {estimatedTime}
          </p>
        )}

        {/* 错误信息 */}
        {hasError && data.error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {data.error}
          </div>
        )}

        {/* 操作按钮 */}
        {!isComplete && !hasError && !isCancelled && onCancel && (
          <button
            onClick={onCancel}
            className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors text-sm font-medium"
          >
            取消
          </button>
        )}
      </div>
    </div>
  )
}

export default ProgressTracker

