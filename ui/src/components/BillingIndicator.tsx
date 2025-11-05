/**
 * 光子计费指示器组件
 *
 * 实时显示当前会话的 token 消耗和光子数
 */

import React, { useState, useEffect, useRef } from 'react'

interface BillingData {
  session_total_tokens: number
  session_total_photons: number
  requests_count: number
  current_tokens?: number  // 本次对话的 tokens
  current_photons?: number  // 本次对话的光子
  model_name?: string  // 使用的模型
}

interface BillingIndicatorProps {
  /** 计费数据 */
  billingData?: BillingData
  /** 是否显示详细信息 */
  showDetails?: boolean
  /** 自定义样式类名 */
  className?: string
}

export const BillingIndicator: React.FC<BillingIndicatorProps> = ({
  billingData,
  showDetails = false,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [animateUpdate, setAnimateUpdate] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<{tokens: number, photons: number} | null>(null)
  const prevDataRef = useRef<BillingData | null>(null)

  // 当计费数据更新时触发动画并计算增量
  useEffect(() => {
    console.log('💎 [BillingIndicator] 收到计费数据:', billingData)
    if (billingData && billingData.session_total_tokens > 0) {
      // 计算本次增量
      if (prevDataRef.current) {
        const deltaTokens = billingData.session_total_tokens - prevDataRef.current.session_total_tokens
        const deltaPhotons = billingData.session_total_photons - prevDataRef.current.session_total_photons

        if (deltaTokens > 0) {
          console.log('💎 [BillingIndicator] 增量更新:', { deltaTokens, deltaPhotons })
          setLastUpdate({ tokens: deltaTokens, photons: deltaPhotons })
          setAnimateUpdate(true)
          const timer = setTimeout(() => setAnimateUpdate(false), 500)
          return () => clearTimeout(timer)
        }
      }

      prevDataRef.current = billingData
    }
  }, [billingData?.session_total_tokens, billingData?.session_total_photons])

  if (!billingData || billingData.session_total_tokens === 0) {
    console.log('💎 [BillingIndicator] 不显示 - billingData:', billingData)
    return null
  }

  const { session_total_tokens, session_total_photons, requests_count, model_name } = billingData
  const tokensPerPhoton = 3000  // 从环境变量读取，默认 3000

  console.log('💎 [BillingIndicator] 渲染计费指示器:', { session_total_tokens, session_total_photons })

  return (
    <div className={`billing-indicator ${className}`}>
      {/* 紧凑模式 - 显示在顶部栏 */}
      <div
        className={`billing-compact ${animateUpdate ? 'billing-update' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
        title="点击查看详细计费信息"
      >
        <div className="billing-icon">💎</div>
        <div className="billing-summary">
          <span className="billing-photons">{session_total_photons.toFixed(4)}</span>
          <span className="billing-label">光子</span>
        </div>
        <div className="billing-tokens">
          <span className="billing-tokens-value">{session_total_tokens.toLocaleString()}</span>
          <span className="billing-tokens-label">tokens</span>
        </div>
        <svg
          className={`billing-expand-icon ${isExpanded ? 'expanded' : ''}`}
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
        >
          <path
            d="M3 4.5L6 7.5L9 4.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* 展开模式 - 显示详细信息 */}
      {isExpanded && (
        <div className="billing-details">
          <div className="billing-details-header">
            <h4>💎 光子计费详情</h4>
          </div>
          <div className="billing-details-content">
            {/* 本次对话 */}
            {lastUpdate && lastUpdate.tokens > 0 && (
              <>
                <div className="billing-section-title">本次对话</div>
                <div className="billing-detail-row">
                  <span className="billing-detail-label">Tokens:</span>
                  <span className="billing-detail-value current">
                    +{lastUpdate.tokens.toLocaleString()}
                  </span>
                </div>
                <div className="billing-detail-row">
                  <span className="billing-detail-label">光子:</span>
                  <span className="billing-detail-value current">
                    +{lastUpdate.photons.toFixed(4)}
                  </span>
                </div>
                <div className="billing-divider" />
              </>
            )}

            {/* 会话累计 */}
            <div className="billing-section-title">会话累计</div>
            <div className="billing-detail-row">
              <span className="billing-detail-label">累计 Tokens:</span>
              <span className="billing-detail-value">{session_total_tokens.toLocaleString()}</span>
            </div>
            <div className="billing-detail-row">
              <span className="billing-detail-label">累计光子:</span>
              <span className="billing-detail-value highlight">{session_total_photons.toFixed(4)}</span>
            </div>
            <div className="billing-detail-row">
              <span className="billing-detail-label">请求次数:</span>
              <span className="billing-detail-value">{requests_count}</span>
            </div>
            <div className="billing-detail-row">
              <span className="billing-detail-label">平均每次:</span>
              <span className="billing-detail-value">
                {requests_count > 0 ? (session_total_tokens / requests_count).toFixed(0) : 0} tokens
              </span>
            </div>

            {/* 模型信息 */}
            {model_name && (
              <>
                <div className="billing-divider" />
                <div className="billing-detail-row">
                  <span className="billing-detail-label">使用模型:</span>
                  <span className="billing-detail-value model">{model_name}</span>
                </div>
              </>
            )}

            <div className="billing-detail-info">
              <small>💡 收费标准: {tokensPerPhoton.toLocaleString()} tokens = 1 光子</small>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .billing-indicator {
          position: relative;
          user-select: none;
        }

        .billing-compact {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 12px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 20px;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }

        .billing-compact:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .billing-update {
          animation: billing-pulse 0.5s ease;
        }

        @keyframes billing-pulse {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
          }
        }

        .billing-icon {
          font-size: 16px;
          line-height: 1;
        }

        .billing-summary {
          display: flex;
          align-items: baseline;
          gap: 4px;
        }

        .billing-photons {
          font-size: 16px;
          font-weight: 700;
          color: #fff;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.9);
          font-weight: 500;
        }

        .billing-tokens {
          display: flex;
          align-items: baseline;
          gap: 3px;
          padding-left: 8px;
          border-left: 1px solid rgba(255, 255, 255, 0.3);
        }

        .billing-tokens-value {
          font-size: 13px;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.95);
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-tokens-label {
          font-size: 10px;
          color: rgba(255, 255, 255, 0.8);
        }

        .billing-expand-icon {
          margin-left: 4px;
          transition: transform 0.3s ease;
          color: rgba(255, 255, 255, 0.9);
        }

        .billing-expand-icon.expanded {
          transform: rotate(180deg);
        }

        .billing-details {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          min-width: 280px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
          z-index: 1000;
          animation: billing-slide-down 0.2s ease;
        }

        @keyframes billing-slide-down {
          from {
            opacity: 0;
            transform: translateY(-8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .billing-details-header {
          padding: 16px;
          border-bottom: 1px solid #e5e7eb;
        }

        .billing-details-header h4 {
          margin: 0;
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
        }

        .billing-details-content {
          padding: 16px;
        }

        .billing-detail-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid #f3f4f6;
        }

        .billing-detail-row:last-of-type {
          border-bottom: none;
        }

        .billing-detail-label {
          font-size: 13px;
          color: #6b7280;
          font-weight: 500;
        }

        .billing-detail-value {
          font-size: 14px;
          color: #1f2937;
          font-weight: 600;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .billing-detail-value.highlight {
          color: #667eea;
          font-size: 16px;
        }

        .billing-detail-value.current {
          color: #10b981;
          font-weight: 700;
        }

        .billing-detail-value.model {
          color: #6366f1;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .billing-section-title {
          font-size: 11px;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-top: 8px;
          margin-bottom: 8px;
        }

        .billing-section-title:first-child {
          margin-top: 0;
        }

        .billing-divider {
          height: 1px;
          background: linear-gradient(to right, transparent, #e5e7eb, transparent);
          margin: 12px 0;
        }

        .billing-detail-info {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #f3f4f6;
        }

        .billing-detail-info small {
          font-size: 12px;
          color: #9ca3af;
          display: block;
          text-align: center;
        }
      `}</style>
    </div>
  )
}

export default BillingIndicator

