/**
 * 消息级别的计费徽章组件
 * 
 * 显示在每条 AI 消息下方，展示本次对话的 token 使用和光子消耗
 */

import React from 'react'

interface MessageBillingBadgeProps {
  /** 本次对话的 tokens */
  tokens?: number
  /** 本次对话的光子 */
  photons?: number
  /** 模型名称 */
  modelName?: string
  /** 是否紧凑模式 */
  compact?: boolean
}

export const MessageBillingBadge: React.FC<MessageBillingBadgeProps> = ({
  tokens,
  photons,
  modelName,
  compact = true
}) => {
  // 如果没有计费数据，不显示
  if (!tokens || tokens === 0) {
    return null
  }

  return (
    <div className={`message-billing-badge ${compact ? 'compact' : ''}`}>
      <div className="billing-badge-content">
        <span className="billing-badge-icon">💎</span>
        <span className="billing-badge-photons">{photons?.toFixed(4) || '0.0000'}</span>
        <span className="billing-badge-separator">·</span>
        <span className="billing-badge-tokens">{tokens.toLocaleString()} tokens</span>
        {modelName && (
          <>
            <span className="billing-badge-separator">·</span>
            <span className="billing-badge-model">{modelName}</span>
          </>
        )}
      </div>

      <style>{`
        .message-billing-badge {
          display: inline-flex;
          align-items: center;
          margin-top: 8px;
          padding: 4px 10px;
          background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
          border: 1px solid rgba(102, 126, 234, 0.2);
          border-radius: 12px;
          font-size: 11px;
          transition: all 0.2s ease;
        }

        .message-billing-badge:hover {
          background: linear-gradient(135deg, rgba(102, 126, 234, 0.12) 0%, rgba(118, 75, 162, 0.12) 100%);
          border-color: rgba(102, 126, 234, 0.3);
          transform: translateY(-1px);
        }

        .message-billing-badge.compact {
          padding: 3px 8px;
          font-size: 10px;
        }

        .billing-badge-content {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .billing-badge-icon {
          font-size: 12px;
          line-height: 1;
        }

        .message-billing-badge.compact .billing-badge-icon {
          font-size: 10px;
        }

        .billing-badge-photons {
          font-weight: 700;
          color: #667eea;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-badge-separator {
          color: #9ca3af;
          font-weight: 400;
        }

        .billing-badge-tokens {
          color: #6b7280;
          font-weight: 600;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-badge-model {
          color: #6366f1;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.3px;
          font-size: 9px;
        }

        .message-billing-badge.compact .billing-badge-model {
          font-size: 8px;
        }
      `}</style>
    </div>
  )
}

export default MessageBillingBadge

