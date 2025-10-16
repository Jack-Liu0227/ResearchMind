/**
 * 前端错误处理服务
 * 提供统一的错误处理、报告和恢复机制
 */

export enum ErrorType {
  NETWORK_ERROR = 'network_error',
  WEBSOCKET_ERROR = 'websocket_error',
  DATA_PARSING_ERROR = 'data_parsing_error',
  RENDERING_ERROR = 'rendering_error',
  VALIDATION_ERROR = 'validation_error',
  UNKNOWN_ERROR = 'unknown_error'
}

export interface ErrorReport {
  id: string
  type: ErrorType
  message: string
  stack?: string
  context?: any
  timestamp: string
  userAgent: string
  url: string
  userId?: string
}

export interface ErrorRecoveryAction {
  label: string
  action: () => void | Promise<void>
  type: 'primary' | 'secondary' | 'danger'
}

class ErrorService {
  private errorReports: ErrorReport[] = []
  private maxReports = 50
  private errorListeners: ((error: ErrorReport) => void)[] = []

  constructor() {
    // 监听全局错误
    this.setupGlobalErrorHandlers()
  }

  /**
   * 设置全局错误处理器
   */
  private setupGlobalErrorHandlers(): void {
    // 监听JavaScript错误
    window.addEventListener('error', (event) => {
      this.handleError(new Error(event.message), {
        type: ErrorType.UNKNOWN_ERROR,
        context: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        }
      })
    })

    // 监听Promise拒绝
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError(event.reason, {
        type: ErrorType.UNKNOWN_ERROR,
        context: {
          promise: 'unhandled_rejection'
        }
      })
    })

    // 监听网络错误
    window.addEventListener('offline', () => {
      this.handleError(new Error('网络连接已断开'), {
        type: ErrorType.NETWORK_ERROR,
        context: { online: false }
      })
    })

    window.addEventListener('online', () => {
      console.log('✅ 网络连接已恢复')
    })
  }

  /**
   * 处理错误
   */
  handleError(
    error: Error | string, 
    options: {
      type?: ErrorType
      context?: any
      silent?: boolean
      recoveryActions?: ErrorRecoveryAction[]
    } = {}
  ): ErrorReport {
    const errorMessage = typeof error === 'string' ? error : error.message
    const errorStack = typeof error === 'string' ? undefined : error.stack

    const report: ErrorReport = {
      id: this.generateErrorId(),
      type: options.type || this.classifyError(error),
      message: errorMessage,
      stack: errorStack,
      context: options.context,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    // 存储错误报告
    this.storeErrorReport(report)

    // 通知监听器
    if (!options.silent) {
      this.notifyErrorListeners(report)
    }

    // 控制台输出
    console.error('🚨 错误报告:', report)

    return report
  }

  /**
   * 错误分类
   */
  private classifyError(error: Error | string): ErrorType {
    const errorStr = typeof error === 'string' ? error : error.message
    const lowerError = errorStr.toLowerCase()

    if (lowerError.includes('network') || lowerError.includes('fetch')) {
      return ErrorType.NETWORK_ERROR
    }

    if (lowerError.includes('websocket') || lowerError.includes('socket')) {
      return ErrorType.WEBSOCKET_ERROR
    }

    if (lowerError.includes('json') || lowerError.includes('parse')) {
      return ErrorType.DATA_PARSING_ERROR
    }

    if (lowerError.includes('render') || lowerError.includes('three')) {
      return ErrorType.RENDERING_ERROR
    }

    if (lowerError.includes('validation') || lowerError.includes('invalid')) {
      return ErrorType.VALIDATION_ERROR
    }

    return ErrorType.UNKNOWN_ERROR
  }

  /**
   * 生成错误ID
   */
  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 存储错误报告
   */
  private storeErrorReport(report: ErrorReport): void {
    this.errorReports.unshift(report)

    // 限制存储数量
    if (this.errorReports.length > this.maxReports) {
      this.errorReports = this.errorReports.slice(0, this.maxReports)
    }

    // 存储到localStorage（可选）
    try {
      const storedErrors = JSON.parse(localStorage.getItem('error_reports') || '[]')
      storedErrors.unshift(report)
      localStorage.setItem('error_reports', JSON.stringify(storedErrors.slice(0, 20)))
    } catch (e) {
      console.warn('无法存储错误报告到localStorage:', e)
    }
  }

  /**
   * 通知错误监听器
   */
  private notifyErrorListeners(report: ErrorReport): void {
    this.errorListeners.forEach(listener => {
      try {
        listener(report)
      } catch (e) {
        console.error('错误监听器执行失败:', e)
      }
    })
  }

  /**
   * 添加错误监听器
   */
  onError(listener: (error: ErrorReport) => void): () => void {
    this.errorListeners.push(listener)
    
    return () => {
      const index = this.errorListeners.indexOf(listener)
      if (index > -1) {
        this.errorListeners.splice(index, 1)
      }
    }
  }

  /**
   * 获取错误报告
   */
  getErrorReports(): ErrorReport[] {
    return [...this.errorReports]
  }

  /**
   * 清空错误报告
   */
  clearErrorReports(): void {
    this.errorReports = []
    localStorage.removeItem('error_reports')
  }

  /**
   * 获取错误统计
   */
  getErrorStats(): {
    total: number
    byType: Record<ErrorType, number>
    recent: ErrorReport[]
  } {
    const byType = this.errorReports.reduce((acc, report) => {
      acc[report.type] = (acc[report.type] || 0) + 1
      return acc
    }, {} as Record<ErrorType, number>)

    return {
      total: this.errorReports.length,
      byType,
      recent: this.errorReports.slice(0, 5)
    }
  }

  /**
   * 网络错误恢复
   */
  async retryNetworkRequest<T>(
    requestFn: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: Error

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await requestFn()
      } catch (error) {
        lastError = error as Error
        
        if (attempt < maxRetries) {
          console.warn(`🔄 网络请求失败，第 ${attempt} 次重试 (${delay}ms 后)`)
          await new Promise(resolve => setTimeout(resolve, delay * attempt))
        }
      }
    }

    // 所有重试都失败
    this.handleError(lastError!, {
      type: ErrorType.NETWORK_ERROR,
      context: { retries: maxRetries, failed: true }
    })

    throw lastError!
  }

  /**
   * 数据验证错误处理
   */
  validateAndHandle<T>(
    data: any,
    validator: (data: any) => T,
    errorMessage: string = '数据验证失败'
  ): T {
    try {
      return validator(data)
    } catch (error) {
      this.handleError(new Error(`${errorMessage}: ${error}`), {
        type: ErrorType.VALIDATION_ERROR,
        context: { data, validator: validator.name }
      })
      throw error
    }
  }

  /**
   * 安全执行函数
   */
  async safeExecute<T>(
    fn: () => Promise<T> | T,
    fallback?: T,
    errorType?: ErrorType
  ): Promise<T | undefined> {
    try {
      const result = await fn()
      return result
    } catch (error) {
      this.handleError(error as Error, {
        type: errorType || ErrorType.UNKNOWN_ERROR,
        context: { function: fn.name }
      })

      return fallback
    }
  }

  /**
   * 创建错误恢复操作
   */
  createRecoveryActions(error: ErrorReport): ErrorRecoveryAction[] {
    const actions: ErrorRecoveryAction[] = []

    // 通用操作
    actions.push({
      label: '刷新页面',
      action: () => window.location.reload(),
      type: 'primary'
    })

    // 根据错误类型添加特定操作
    switch (error.type) {
      case ErrorType.NETWORK_ERROR:
        actions.unshift({
          label: '重试请求',
          action: () => {
            // 这里可以触发重新请求
            console.log('🔄 重试网络请求')
          },
          type: 'primary'
        })
        break

      case ErrorType.WEBSOCKET_ERROR:
        actions.unshift({
          label: '重新连接',
          action: () => {
            // 这里可以触发WebSocket重连
            console.log('🔄 重新连接WebSocket')
          },
          type: 'primary'
        })
        break

      case ErrorType.RENDERING_ERROR:
        actions.unshift({
          label: '重置视图',
          action: () => {
            // 这里可以重置Three.js场景
            console.log('🔄 重置3D视图')
          },
          type: 'primary'
        })
        break
    }

    return actions
  }

  /**
   * 发送错误报告到服务器（可选）
   */
  async reportToServer(report: ErrorReport): Promise<void> {
    try {
      await fetch('/api/error_reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(report)
      })
    } catch (e) {
      console.warn('无法发送错误报告到服务器:', e)
    }
  }
}

// 导出单例实例
export const errorService = new ErrorService()
export default ErrorService