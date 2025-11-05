/**
 * 计费统计面板组件
 * 
 * 显示详细的计费统计信息，包括：
 * - 当前会话的计费统计
 * - 用户总计费统计
 * - 全局计费统计
 */

import React, { useState, useEffect } from 'react'
import { 
  getConversationBillingStats, 
  getUserBillingStats, 
  getGlobalBillingStats,
  BillingStats,
  UserBillingStats,
  GlobalBillingStats
} from '../utils/apiClient'
import { useAppStore } from '../store/useAppStore'

interface BillingStatsPanelProps {
  /** 是否显示面板 */
  isOpen: boolean
  /** 关闭面板的回调 */
  onClose: () => void
  /** 自定义样式类名 */
  className?: string
}

export const BillingStatsPanel: React.FC<BillingStatsPanelProps> = ({
  isOpen,
  onClose,
  className = ''
}) => {
  const { currentSession, billingData } = useAppStore()
  const [conversationStats, setConversationStats] = useState<BillingStats | null>(null)
  const [userStats, setUserStats] = useState<UserBillingStats | null>(null)
  const [globalStats, setGlobalStats] = useState<GlobalBillingStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'conversation' | 'user' | 'global'>('conversation')
  const [error, setError] = useState<string | null>(null)

  // 加载计费统计数据
  useEffect(() => {
    if (!isOpen) return

    const loadStats = async () => {
      setLoading(true)
      setError(null)
      try {
        console.log('🔍 [BillingStatsPanel] 开始加载计费统计...')
        console.log('🔍 [BillingStatsPanel] currentSession:', currentSession)
        console.log('🔍 [BillingStatsPanel] billingData:', billingData)

        // 加载全局统计（总是可用）
        const gStats = await getGlobalBillingStats()
        console.log('✅ [BillingStatsPanel] 全局统计:', gStats)
        setGlobalStats(gStats)

        // 尝试加载当前会话的计费统计
        if (currentSession?.id) {
          console.log(`🔍 [BillingStatsPanel] 尝试获取会话 ${currentSession.id} 的计费数据...`)
          try {
            const convStats = await getConversationBillingStats(currentSession.id)
            console.log('📊 [BillingStatsPanel] 会话计费数据:', convStats)

            if (convStats) {
              setConversationStats(convStats)

              // 如果有用户ID，加载用户统计
              if (convStats.user_id) {
                console.log(`🔍 [BillingStatsPanel] 获取用户 ${convStats.user_id} 的统计...`)
                const uStats = await getUserBillingStats(convStats.user_id)
                console.log('📊 [BillingStatsPanel] 用户统计:', uStats)
                setUserStats(uStats)
              }
            } else {
              console.warn('⚠️ 当前会话没有计费数据，可能还未发送消息')
              setError('当前会话暂无计费数据，请先发送消息')
            }
          } catch (err) {
            console.warn('⚠️ 获取会话计费数据失败:', err)
            setError('当前会话暂无计费数据，请先发送消息后再查看')
          }
        } else {
          setError('请先创建或选择一个会话')
        }
      } catch (error) {
        console.error('❌ 加载计费统计失败:', error)
        setError('加载计费统计失败，请稍后重试')
      } finally {
        setLoading(false)
      }
    }

    loadStats()
  }, [isOpen, currentSession?.id, billingData])

  if (!isOpen) return null

  return (
    <div className={`billing-stats-panel ${className}`}>
      {/* 遮罩层 */}
      <div className="billing-stats-overlay" onClick={onClose} />

      {/* 面板内容 */}
      <div className="billing-stats-content">
        {/* 头部 */}
        <div className="billing-stats-header">
          <h2>💎 计费统计</h2>
          <button className="billing-stats-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* 标签页 */}
        <div className="billing-stats-tabs">
          <button
            className={`billing-stats-tab ${activeTab === 'conversation' ? 'active' : ''}`}
            onClick={() => setActiveTab('conversation')}
          >
            当前会话
          </button>
          <button
            className={`billing-stats-tab ${activeTab === 'user' ? 'active' : ''}`}
            onClick={() => setActiveTab('user')}
          >
            用户统计
          </button>
          <button
            className={`billing-stats-tab ${activeTab === 'global' ? 'active' : ''}`}
            onClick={() => setActiveTab('global')}
          >
            全局统计
          </button>
        </div>

        {/* 内容区域 */}
        <div className="billing-stats-body">
          {loading ? (
            <div className="billing-stats-loading">
              <div className="spinner" />
              <p>加载中...</p>
            </div>
          ) : error && activeTab !== 'global' ? (
            <div className="billing-stats-error">
              <div className="error-icon">⚠️</div>
              <p>{error}</p>
              <p className="error-hint">提示：计费数据在发送第一条消息后才会生成</p>
            </div>
          ) : (
            <>
              {/* 当前会话统计 */}
              {activeTab === 'conversation' && conversationStats && (
                <div className="billing-stats-section">
                  <h3>当前会话统计</h3>
                  <div className="billing-stats-grid">
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">会话 ID</span>
                      <span className="billing-stat-value">{conversationStats.conversation_id?.slice(0, 8)}...</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总 Tokens</span>
                      <span className="billing-stat-value highlight">{conversationStats.total_tokens.toLocaleString()}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总光子</span>
                      <span className="billing-stat-value highlight">{conversationStats.total_photons.toFixed(4)}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">请求次数</span>
                      <span className="billing-stat-value">{conversationStats.request_count}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">平均每次</span>
                      <span className="billing-stat-value">
                        {conversationStats.request_count > 0 
                          ? (conversationStats.total_tokens / conversationStats.request_count).toFixed(0)
                          : 0} tokens
                      </span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">计费来源</span>
                      <span className="billing-stat-value">{conversationStats.billing_source || '未知'}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">是否已扣费</span>
                      <span className={`billing-stat-value ${conversationStats.charged ? 'charged' : 'not-charged'}`}>
                        {conversationStats.charged ? '已扣费' : '未扣费'}
                      </span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">创建时间</span>
                      <span className="billing-stat-value">
                        {conversationStats.created_at ? new Date(conversationStats.created_at).toLocaleString() : '-'}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* 用户统计 */}
              {activeTab === 'user' && userStats && (
                <div className="billing-stats-section">
                  <h3>用户总统计</h3>
                  <div className="billing-stats-grid">
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">用户 ID</span>
                      <span className="billing-stat-value">{userStats.user_id.slice(0, 8)}...</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总对话数</span>
                      <span className="billing-stat-value">{userStats.total_conversations}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总 Tokens</span>
                      <span className="billing-stat-value highlight">{userStats.total_tokens.toLocaleString()}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总光子</span>
                      <span className="billing-stat-value highlight">{userStats.total_photons.toFixed(4)}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总请求数</span>
                      <span className="billing-stat-value">{userStats.total_requests}</span>
                    </div>
                  </div>

                  {/* 对话列表 */}
                  {userStats.conversations.length > 0 && (
                    <div className="billing-conversations-list">
                      <h4>对话列表</h4>
                      <div className="billing-conversations-table">
                        <table>
                          <thead>
                            <tr>
                              <th>会话 ID</th>
                              <th>Tokens</th>
                              <th>光子</th>
                              <th>请求数</th>
                              <th>状态</th>
                            </tr>
                          </thead>
                          <tbody>
                            {userStats.conversations.map((conv) => (
                              <tr key={conv.conversation_id}>
                                <td>{conv.conversation_id?.slice(0, 8)}...</td>
                                <td>{conv.total_tokens.toLocaleString()}</td>
                                <td>{conv.total_photons.toFixed(4)}</td>
                                <td>{conv.request_count}</td>
                                <td>
                                  <span className={`status-badge ${conv.charged ? 'charged' : 'not-charged'}`}>
                                    {conv.charged ? '已扣费' : '未扣费'}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 全局统计 */}
              {activeTab === 'global' && globalStats && (
                <div className="billing-stats-section">
                  <h3>全局统计</h3>
                  <div className="billing-stats-grid">
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总 Tokens</span>
                      <span className="billing-stat-value highlight">{globalStats.total_tokens.toLocaleString()}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总光子</span>
                      <span className="billing-stat-value highlight">{globalStats.total_photons.toFixed(4)}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总请求数</span>
                      <span className="billing-stat-value">{globalStats.total_requests}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总会话数</span>
                      <span className="billing-stat-value">{globalStats.total_sessions}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">开始时间</span>
                      <span className="billing-stat-value">
                        {new Date(globalStats.start_time).toLocaleString()}
                      </span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">当前时间</span>
                      <span className="billing-stat-value">
                        {new Date(globalStats.current_time).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* 计费配置 */}
                  <div className="billing-config-section">
                    <h4>计费配置</h4>
                    <div className="billing-stats-grid">
                      <div className="billing-stat-item">
                        <span className="billing-stat-label">Tokens/光子</span>
                        <span className="billing-stat-value">
                          {globalStats.billing_config.tokens_per_photon.toLocaleString()}
                        </span>
                      </div>
                      <div className="billing-stat-item">
                        <span className="billing-stat-label">计费状态</span>
                        <span className={`billing-stat-value ${globalStats.billing_config.billing_enabled ? 'enabled' : 'disabled'}`}>
                          {globalStats.billing_config.billing_enabled ? '已启用' : '已禁用'}
                        </span>
                      </div>
                      <div className="billing-stat-item">
                        <span className="billing-stat-label">精度</span>
                        <span className="billing-stat-value">
                          {globalStats.billing_config.precision} 位小数
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <style>{`
        .billing-stats-panel {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .billing-stats-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(4px);
        }

        .billing-stats-content {
          position: relative;
          width: 90%;
          max-width: 900px;
          max-height: 90vh;
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .billing-stats-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 24px;
          border-bottom: 1px solid #e5e7eb;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .billing-stats-header h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: white;
        }

        .billing-stats-close {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          font-size: 24px;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }

        .billing-stats-close:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: scale(1.1);
        }

        .billing-stats-tabs {
          display: flex;
          border-bottom: 1px solid #e5e7eb;
          background: #f9fafb;
        }

        .billing-stats-tab {
          flex: 1;
          padding: 12px 16px;
          background: none;
          border: none;
          font-size: 14px;
          font-weight: 500;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s ease;
          border-bottom: 2px solid transparent;
        }

        .billing-stats-tab:hover {
          color: #667eea;
          background: rgba(102, 126, 234, 0.05);
        }

        .billing-stats-tab.active {
          color: #667eea;
          border-bottom-color: #667eea;
          background: white;
        }

        .billing-stats-body {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
        }

        .billing-stats-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px 20px;
          color: #6b7280;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid #e5e7eb;
          border-top-color: #667eea;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin-bottom: 16px;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .billing-stats-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px 20px;
          color: #6b7280;
          text-align: center;
        }

        .error-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }

        .billing-stats-error p {
          margin: 8px 0;
          font-size: 16px;
          color: #374151;
        }

        .error-hint {
          font-size: 14px !important;
          color: #9ca3af !important;
          margin-top: 16px !important;
        }

        .billing-stats-section {
          margin-bottom: 32px;
        }

        .billing-stats-section h3 {
          margin: 0 0 16px 0;
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
        }

        .billing-stats-section h4 {
          margin: 24px 0 12px 0;
          font-size: 16px;
          font-weight: 600;
          color: #374151;
        }

        .billing-stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
        }

        .billing-stat-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 16px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .billing-stat-label {
          font-size: 12px;
          font-weight: 500;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .billing-stat-value {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-stat-value.highlight {
          color: #667eea;
          font-size: 20px;
        }

        .billing-stat-value.charged {
          color: #10b981;
        }

        .billing-stat-value.not-charged {
          color: #f59e0b;
        }

        .billing-stat-value.enabled {
          color: #10b981;
        }

        .billing-stat-value.disabled {
          color: #ef4444;
        }

        .billing-conversations-list {
          margin-top: 24px;
        }

        .billing-conversations-table {
          overflow-x: auto;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .billing-conversations-table table {
          width: 100%;
          border-collapse: collapse;
          background: white;
        }

        .billing-conversations-table th {
          padding: 12px 16px;
          text-align: left;
          font-size: 12px;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          background: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
        }

        .billing-conversations-table td {
          padding: 12px 16px;
          font-size: 14px;
          color: #1f2937;
          border-bottom: 1px solid #f3f4f6;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-conversations-table tr:last-child td {
          border-bottom: none;
        }

        .billing-conversations-table tr:hover {
          background: #f9fafb;
        }

        .status-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .status-badge.charged {
          background: #d1fae5;
          color: #065f46;
        }

        .status-badge.not-charged {
          background: #fef3c7;
          color: #92400e;
        }

        .billing-config-section {
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #e5e7eb;
        }
      `}</style>
    </div>
  )
}

export default BillingStatsPanel

