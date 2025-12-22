/**
 * 计费统计面板组件
 *
 * ⚠️ Token 自动扣费已禁用 - 改为按次计费模式
 * 此组件显示的 Token 和光子统计仅供参考，不再用于实际扣费
 *
 * 🔧 重构：使用 WebSocket 实时推送代替 HTTP API 轮询
 *
 * 显示详细的计费统计信息，包括：
 * - 当前会话的 Token 使用统计（仅记录，不扣费）
 * - 用户总 Token 使用统计（仅记录，不扣费）
 * - 全局 Token 使用统计（仅记录，不扣费）
 *
 * 实际扣费请使用 /api/billing/charge 端点（按次计费）
 */

import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom'
import { BillingStats } from '../utils/apiClient'
import { useAppStore } from '../store/useAppStore'
import { wsService } from '../services/websocket'

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
  const {
    currentSession,
    billingData,
    userBillingStats,
    // 🔧 移除 globalBillingStats
    // user
  } = useAppStore()
  const [conversationStats, setConversationStats] = useState<BillingStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'conversation' | 'user'>('conversation')  // 🔧 移除 'global' 选项
  const [error, setError] = useState<string | null>(null)

  // 🔧 重构：通过 WebSocket 请求计费统计数据
  useEffect(() => {
    if (!isOpen) return

    console.log('📊 [BillingStatsPanel] 面板打开，通过 WebSocket 请求计费统计...')
    setLoading(true)
    setError(null)

    // 🔧 移除全局统计请求

    // 请求当前会话的计费统计
    if (currentSession?.id) {
      console.log(`📊 [BillingStatsPanel] 请求会话 ${currentSession.id} 的计费数据...`)
      wsService.requestConversationStats(currentSession.id)

      // 如果用户已登录，请求用户统计
      // if (user?.id) {
      //   console.log(`📊 [BillingStatsPanel] 请求用户 ${user.id} 的统计...`)
      //   wsService.requestUserStats(user.id.toString())
      // }
    } else {
      setError('请先创建或选择一个会话')
      setLoading(false)
    }

    // 设置超时，防止永久加载
    const timeout = setTimeout(() => {
      setLoading(false)
    }, 3000)

    return () => clearTimeout(timeout)
  }, [isOpen, currentSession?.id])

  // 🔧 监听 WebSocket 消息更新
  useEffect(() => {
    // 当 billingData 更新时，同步到 conversationStats
    if (billingData && currentSession?.id) {
      console.log('📊 [BillingStatsPanel] billingData 更新，同步到 conversationStats:', billingData)
      console.log('📊 [BillingStatsPanel] billingData.charged:', billingData.charged)
      console.log('📊 [BillingStatsPanel] billingData.billing_source:', billingData.billing_source)

      const newStats = {
        conversation_id: currentSession.id,
        user_id: 'unknown',
        total_tokens: billingData.session_total_tokens || 0,  // 🔧 添加默认值
        total_photons: billingData.session_total_photons || 0,  // 🔧 添加默认值
        request_count: billingData.requests_count || 0,  // 🔧 添加默认值
        charged: billingData.charged ?? false,  // 🔧 修复：使用后端返回的 charged 状态
        billing_source: billingData.billing_source,  // 🔧 添加：计费来源
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      console.log('📊 [BillingStatsPanel] 设置 conversationStats:', newStats)
      setConversationStats(newStats)
    }
  }, [billingData, currentSession?.id])

  if (!isOpen) return null

  return ReactDOM.createPortal(
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
          {/* 🔧 移除全局统计标签 */}
        </div>

        {/* 内容区域 */}
        <div className="billing-stats-body">
          {loading ? (
            <div className="billing-stats-loading">
              <div className="spinner" />
              <p>加载中...</p>
            </div>
          ) : error ? (
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
                      <span className="billing-stat-value highlight">{(conversationStats.total_tokens || 0).toLocaleString()}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总光子</span>
                      <span className="billing-stat-value highlight">{(conversationStats.total_photons || 0).toFixed(4)}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">请求次数</span>
                      <span className="billing-stat-value">{conversationStats.request_count || 0}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">平均每次</span>
                      <span className="billing-stat-value">
                        {(conversationStats.request_count || 0) > 0
                          ? ((conversationStats.total_tokens || 0) / conversationStats.request_count).toFixed(0)
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

                  {/* 🆕 功能扣费明细 */}
                  {billingData?.feature_charges && billingData.feature_charges.length > 0 && (
                    <div className="billing-charges-section" style={{ marginTop: '20px' }}>
                      <h4 style={{ marginBottom: '10px', fontSize: '14px', fontWeight: 600 }}>功能扣费明细</h4>
                      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                        {billingData.feature_charges.map((charge, index) => (
                          <div
                            key={index}
                            style={{
                              padding: '8px 12px',
                              marginBottom: '8px',
                              borderRadius: '6px',
                              backgroundColor: charge.success ? '#f0f9ff' : '#fef2f2',
                              border: `1px solid ${charge.success ? '#bfdbfe' : '#fecaca'}`,
                              fontSize: '12px'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontWeight: 500 }}>
                                {charge.success ? '✅' : '❌'} {charge.feature_type}
                              </span>
                              <span style={{
                                color: charge.success ? '#059669' : '#dc2626',
                                fontWeight: 600
                              }}>
                                {charge.photons} 光子
                              </span>
                            </div>
                            {!charge.success && charge.error_message && (
                              <div style={{
                                marginTop: '4px',
                                color: '#dc2626',
                                fontSize: '11px'
                              }}>
                                失败原因: {charge.error_message}
                              </div>
                            )}
                            <div style={{
                              marginTop: '4px',
                              color: '#6b7280',
                              fontSize: '11px'
                            }}>
                              {new Date(charge.timestamp).toLocaleString()}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* 扣费统计摘要 */}
                      <div style={{
                        marginTop: '12px',
                        padding: '10px',
                        backgroundColor: '#f9fafb',
                        borderRadius: '6px',
                        fontSize: '12px'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span>成功扣费:</span>
                          <span style={{ color: '#059669', fontWeight: 600 }}>
                            {billingData.feature_charges.filter(c => c.success).reduce((sum, c) => sum + c.photons, 0)} 光子
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span>失败扣费:</span>
                          <span style={{ color: '#dc2626', fontWeight: 600 }}>
                            {billingData.feature_charges.filter(c => !c.success).reduce((sum, c) => sum + c.photons, 0)} 光子
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '4px', borderTop: '1px solid #e5e7eb' }}>
                          <span style={{ fontWeight: 600 }}>应扣累计:</span>
                          <span style={{ fontWeight: 600 }}>
                            {billingData.feature_charges.filter(c => !c.success).reduce((sum, c) => sum + c.photons, 0)} 光子
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 用户统计 */}
              {activeTab === 'user' && userBillingStats && (
                <div className="billing-stats-section">
                  <h3>用户总统计</h3>
                  <div className="billing-stats-grid">
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">用户 ID</span>
                      <span className="billing-stat-value">{userBillingStats.user_id.slice(0, 8)}...</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总对话数</span>
                      <span className="billing-stat-value">{userBillingStats.total_conversations}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总 Tokens</span>
                      <span className="billing-stat-value highlight">{userBillingStats.total_tokens.toLocaleString()}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总光子</span>
                      <span className="billing-stat-value highlight">{(userBillingStats.total_photons_charged || 0).toFixed(4)}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总请求数</span>
                      <span className="billing-stat-value">{userBillingStats.total_requests}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">平均每次</span>
                      <span className="billing-stat-value">
                        {userBillingStats.total_requests > 0
                          ? (userBillingStats.total_tokens / userBillingStats.total_requests).toFixed(0)
                          : 0} tokens
                      </span>
                    </div>
                  </div>

                  {/* 🆕 功能扣费汇总 */}
                  <h3 className="mt-6">功能扣费汇总</h3>
                  <div className="billing-stats-grid">
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">总扣费次数</span>
                      <span className="billing-stat-value">{userBillingStats.total_feature_charges || 0}</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">成功扣费</span>
                      <span className="billing-stat-value success">{userBillingStats.success_photons || 0} 光子</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">失败扣费</span>
                      <span className="billing-stat-value error">{userBillingStats.failed_photons || 0} 光子</span>
                    </div>
                    <div className="billing-stat-item">
                      <span className="billing-stat-label">应扣累计</span>
                      <span className="billing-stat-value highlight">{userBillingStats.failed_photons || 0} 光子</span>
                    </div>
                  </div>

                  {/* 🆕 功能扣费明细（最近 10 条） */}
                  {userBillingStats.recent_feature_charges && userBillingStats.recent_feature_charges.length > 0 && (
                    <>
                      <h3 className="mt-6">功能扣费明细</h3>
                      <div className="billing-feature-charges">
                        {userBillingStats.recent_feature_charges.map((charge, index) => (
                          <div
                            key={index}
                            className={`billing-feature-charge-item ${charge.success ? '' : 'failed'}`}
                          >
                            <div className="charge-header">
                              <span className={`charge-status ${charge.success ? 'success' : 'error'}`}>
                                {charge.success ? '✓' : '✗'}
                              </span>
                              <span className="charge-feature">{charge.feature_type}</span>
                              <span className="charge-photons">{charge.photons} 光子</span>
                            </div>
                            <div className="charge-details">
                              <span className="charge-time">
                                {new Date(charge.timestamp).toLocaleString('zh-CN', {
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </span>
                              {charge.conversation_id && (
                                <span className="charge-session">
                                  会话: {charge.conversation_id.slice(0, 8)}...
                                </span>
                              )}
                              {!charge.success && charge.error_message && (
                                <span className="charge-error">{charge.error_message}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      {(userBillingStats.total_feature_charges || 0) > 10 && (
                        <p className="billing-stats-note">
                          💡 仅显示最近 10 条扣费记录，共 {userBillingStats.total_feature_charges} 条
                        </p>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* 🔧 移除全局统计 */}
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

        /* 🆕 功能扣费明细样式 */
        .billing-feature-charges {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-top: 12px;
        }

        .billing-feature-charge-item {
          padding: 12px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          transition: all 0.2s ease;
        }

        .billing-feature-charge-item:hover {
          background: #f3f4f6;
          border-color: #d1d5db;
        }

        .billing-feature-charge-item.failed {
          background: #fef2f2;
          border-color: #fecaca;
        }

        .charge-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
        }

        .charge-status {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 700;
        }

        .charge-status.success {
          background: #d1fae5;
          color: #065f46;
        }

        .charge-status.error {
          background: #fee2e2;
          color: #991b1b;
        }

        .charge-feature {
          flex: 1;
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
        }

        .charge-photons {
          font-size: 14px;
          font-weight: 600;
          color: #667eea;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .charge-details {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          font-size: 12px;
          color: #6b7280;
          padding-left: 28px;
        }

        .charge-time {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .charge-session {
          color: #9ca3af;
        }

        .charge-error {
          color: #dc2626;
          font-weight: 500;
        }

        .billing-stats-note {
          margin-top: 12px;
          padding: 10px;
          background: #fffbeb;
          border: 1px solid #fde68a;
          border-radius: 6px;
          font-size: 13px;
          color: #92400e;
          text-align: center;
        }

        .mt-6 {
          margin-top: 24px;
        }

        .billing-stat-value.success {
          color: #059669;
        }

        .billing-stat-value.error {
          color: #dc2626;
        }
      `}</style>
    </div>,
    document.body
  )
}

export default BillingStatsPanel
