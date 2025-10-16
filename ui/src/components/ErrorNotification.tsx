/**
 * ErrorNotification - 错误通知组件
 * 显示错误信息和恢复操作
 */

import React, { useState, useEffect } from 'react'
import { errorService, ErrorReport, ErrorRecoveryAction } from '../services/ErrorService'

interface ErrorNotificationProps {
  maxVisible?: number
  autoHide?: boolean
  hideDelay?: number
}

const ErrorNotification: React.FC<ErrorNotificationProps> = ({
  maxVisible = 3,
  autoHide = true,
  hideDelay = 5000
}) => {
  const [errors, setErrors] = useState<ErrorReport[]>([])
  const [hiddenErrors, setHiddenErrors] = useState<Set<string>>(new Set())

  useEffect(() => {
    // 监听错误事件
    const unsubscribe = errorService.onError((error) => {
      setErrors(prev => [error, ...prev.slice(0, maxVisible - 1)])
      
      // 自动隐藏
      if (autoHide) {
        setTimeout(() => {
          setHiddenErrors(prev => new Set([...prev, error.id]))
        }, hideDelay)
      }
    })

    return unsubscribe
  }, [maxVisible, autoHide, hideDelay])

  const handleDismiss = (errorId: string) => {
    setHiddenErrors(prev => new Set([...prev, errorId]))
  }

  const handleAction = async (action: ErrorRecoveryAction, errorId: string) => {
    try {
      await action.action()
      handleDismiss(errorId)
    } catch (e) {
      console.error('恢复操作失败:', e)
    }
  }

  const visibleErrors = errors.filter(error => !hiddenErrors.has(error.id))

  if (visibleErrors.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {visibleErrors.map((error) => (
        <ErrorCard
          key={error.id}
          error={error}
          onDismiss={() => handleDismiss(error.id)}
          onAction={(action) => handleAction(action, error.id)}
        />
      ))}
    </div>
  )
}

interface ErrorCardProps {
  error: ErrorReport
  onDismiss: () => void
  onAction: (action: ErrorRecoveryAction) => void
}

const ErrorCard: React.FC<ErrorCardProps> = ({ error, onDismiss, onAction }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const recoveryActions = errorService.createRecoveryActions(error)

  const getErrorIcon = (type: string) => {
    switch (type) {
      case 'network_error':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        )
      case 'websocket_error':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
          </svg>
        )
      case 'rendering_error':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
    }
  }

  const getErrorColor = (type: string) => {
    switch (type) {
      case 'network_error':
        return 'bg-orange-50 border-orange-200 text-orange-800'
      case 'websocket_error':
        return 'bg-blue-50 border-blue-200 text-blue-800'
      case 'rendering_error':
        return 'bg-purple-50 border-purple-200 text-purple-800'
      case 'validation_error':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      default:
        return 'bg-red-50 border-red-200 text-red-800'
    }
  }

  const getErrorTitle = (type: string) => {
    switch (type) {
      case 'network_error':
        return '网络错误'
      case 'websocket_error':
        return '连接错误'
      case 'rendering_error':
        return '渲染错误'
      case 'data_parsing_error':
        return '数据解析错误'
      case 'validation_error':
        return '验证错误'
      default:
        return '系统错误'
    }
  }

  return (
    <div className={`rounded-lg border p-4 shadow-lg ${getErrorColor(error.type)}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          {getErrorIcon(error.type)}
        </div>
        
        <div className="ml-3 flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              {getErrorTitle(error.type)}
            </h3>
            <button
              onClick={onDismiss}
              className="ml-2 flex-shrink-0 rounded-md p-1.5 hover:bg-black hover:bg-opacity-10 focus:outline-none focus:ring-2 focus:ring-offset-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="mt-1">
            <p className="text-sm opacity-90">
              {error.message}
            </p>
          </div>

          {/* 恢复操作 */}
          {recoveryActions.length > 0 && (
            <div className="mt-3 flex space-x-2">
              {recoveryActions.slice(0, 2).map((action, index) => (
                <button
                  key={index}
                  onClick={() => onAction(action)}
                  className={`text-xs px-3 py-1 rounded-md font-medium transition-colors ${
                    action.type === 'primary'
                      ? 'bg-white bg-opacity-20 hover:bg-opacity-30'
                      : 'bg-black bg-opacity-10 hover:bg-opacity-20'
                  }`}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {/* 详细信息 */}
          {(error.stack || error.context) && (
            <div className="mt-2">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs opacity-75 hover:opacity-100 transition-opacity"
              >
                {isExpanded ? '隐藏详情' : '查看详情'}
              </button>
              
              {isExpanded && (
                <div className="mt-2 p-2 bg-black bg-opacity-10 rounded text-xs font-mono">
                  {error.context && (
                    <div className="mb-2">
                      <div className="font-semibold mb-1">上下文:</div>
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(error.context, null, 2)}
                      </pre>
                    </div>
                  )}
                  
                  {error.stack && (
                    <div>
                      <div className="font-semibold mb-1">堆栈跟踪:</div>
                      <pre className="whitespace-pre-wrap text-xs">
                        {error.stack}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ErrorNotification