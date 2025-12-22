/**
 * 定价页面弹窗组件
 * 
 * 在用户登录成功后自动弹出，展示收费标准
 * 支持"不再显示"选项
 */

import React, { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { toast } from 'react-hot-toast'

interface PricingConfig {
  version: string
  feature_pricing: Record<string, number>
  free_quota: Record<string, number>
  invitation_rewards: {
    inviter: {
      membership_days: number
      photons_per_membership: number
      photons_validity_days: number
      cloud_storage_gb: number
    }
    invitee: {
      photons: number
      photons_validity_days: number
    }
  }
  batch_discount: Record<string, number>
}

interface PricingModalProps {
  isOpen: boolean
  onClose: () => void
}

const PricingModal: React.FC<PricingModalProps> = ({ isOpen, onClose }) => {
  const [config, setConfig] = useState<PricingConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [dontShowAgain, setDontShowAgain] = useState(false)

  useEffect(() => {
    if (isOpen) {
      fetchPricingConfig()
    }
  }, [isOpen])

  const fetchPricingConfig = async () => {
    try {
      const response = await fetch('/api/billing/pricing/config')
      const data = await response.json()

      if (data.success) {
        setConfig(data)
      } else {
        toast.error('获取收费标准失败')
      }
    } catch (error) {
      console.error('获取收费标准失败:', error)
      toast.error('获取收费标准失败')
    } finally {
      setLoading(false)
    }
  }

  const getFeatureName = (key: string): string => {
    const names: Record<string, string> = {
      search: '文献搜索',
      database: '数据库查询',
      export: '文件导出',
      chat: 'Agent 对话',
      report: '文献调研报告',
      analysis: '文献分析报告',
      structure_gen: '结构生成',
      relaxation: '结构弛豫',
      phonon: '声子谱计算',
      kappa: '热导率计算',
      batch_kappa: '批量热导率计算',
    }
    return names[key] || key
  }

  const getFeatureUnit = (key: string): string => {
    const units: Record<string, string> = {
      search: '/次',
      database: '/次',
      chat: '/次',
      report: '/次',
      analysis: '/次',
      structure_gen: '/次',
      relaxation: '/次',
      phonon: '/次',
      batch_phonon: '/结构',
      kappa: '/次',
      batch_kappa: '/结构',
    }
    return units[key] || ''
  }

  const handleClose = () => {
    if (dontShowAgain) {
      // 保存用户偏好到 localStorage
      localStorage.setItem('researchmind_hide_pricing_modal', 'true')
      toast.success('已设置不再显示定价页面')
    }
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[300] overflow-y-auto bg-black bg-opacity-50">
      <div className="flex min-h-full items-center justify-center p-4">
        {/* 弹窗内容 */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-6xl w-full flex flex-col z-10 max-h-[85vh]">
          {/* 头部 */}
          <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">ResearchMind 收费标准</h2>
              <p className="text-sm text-gray-600 mt-1">透明、公平、按需付费</p>
            </div>
            <button
              onClick={handleClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              title="关闭"
            >
              <X className="w-6 h-6 text-gray-600" />
            </button>
          </div>

          {/* 内容区域 - 可滚动 */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-gray-600">加载中...</div>
              </div>
            ) : !config ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-red-600">加载失败</div>
              </div>
            ) : (
              <>
                {/* 功能定价表 */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">功能定价</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            功能
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            光子消耗
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            说明
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {Object.entries(config.feature_pricing).map(([key, photons]) => (
                          <tr key={key} className={photons === 0 ? 'bg-green-50' : ''}>
                            <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                              {getFeatureName(key)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                              {photons === 0 ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                  永久免费
                                </span>
                              ) : (
                                <span className="font-semibold">
                                  {photons} 光子{getFeatureUnit(key)}
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {key === 'batch_kappa' && config.batch_discount[key] && (
                                <span className="text-orange-600">
                                  享受 {(config.batch_discount[key] * 100).toFixed(0)}% 折扣
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 邀请奖励 */}
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">邀请奖励</h3>

                  {/* 平台说明 */}
                  <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-xs text-yellow-800">
                      <strong>说明：</strong>邀请奖励由 Bohrium 平台提供和管理（活动 ID: 1200000），ResearchMind 仅展示规则。
                    </p>
                  </div>

                  {/* 奖励卡片 */}
                  <div className="grid md:grid-cols-2 gap-4 mb-4">
                    {/* 邀请人奖励 */}
                    <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
                      <h4 className="text-base font-semibold text-blue-900 mb-3">🎁 邀请人奖励</h4>
                      <div className="space-y-2">
                        <div className="bg-white rounded p-2">
                          <p className="text-xs font-medium text-gray-900 mb-1">基础奖励（每邀请1人）</p>
                          <ul className="space-y-1 text-xs text-gray-700">
                            <li>✅ <strong>{config.invitation_rewards.inviter.membership_days} 天</strong>体验会员</li>
                            <li>✅ <strong>{config.invitation_rewards.inviter.photons_per_membership} 光子</strong>（有效期 {config.invitation_rewards.inviter.photons_validity_days} 天）</li>
                            <li>✅ <strong>{config.invitation_rewards.inviter.cloud_storage_gb}GB</strong> 玻尔云盘空间</li>
                          </ul>
                        </div>
                        <div className="bg-white rounded p-2">
                          <p className="text-xs font-medium text-gray-900 mb-1">累加规则</p>
                          <ul className="space-y-1 text-xs text-gray-700">
                            <li>✅ 会员时长向后延续累加</li>
                            <li>✅ 邀请 5 人 = 35 天 + 5000 光子</li>
                            <li>✅ 邀请 10 人 = 70 天 + 10000 光子</li>
                          </ul>
                        </div>
                      </div>
                    </div>

                    {/* 受邀请人奖励 */}
                    <div className="border border-green-200 rounded-lg p-4 bg-green-50">
                      <h4 className="text-base font-semibold text-green-900 mb-3">🎉 受邀请人奖励</h4>
                      <div className="space-y-2">
                        <div className="bg-white rounded p-2">
                          <p className="text-xs font-medium text-gray-900 mb-1">新用户奖励</p>
                          <ul className="space-y-1 text-xs text-gray-700">
                            <li>✅ 填写学术码后获得 <strong>{config.invitation_rewards.invitee.photons} 光子</strong></li>
                            <li>✅ 光子有效期 <strong>{config.invitation_rewards.invitee.photons_validity_days} 天</strong></li>
                          </ul>
                        </div>
                        <div className="bg-white rounded p-2">
                          <p className="text-xs font-medium text-gray-900 mb-1">重要提示</p>
                          <ul className="space-y-1 text-xs text-gray-700">
                            <li>⚠️ 需在注册后 <strong>72 小时内</strong>填写学术码</li>
                            <li>⚠️ 超时后将无法获得奖励</li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 可用功能示例 */}
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200 mb-4">
                    <h4 className="text-sm font-semibold text-purple-900 mb-3">💡 光子可用功能示例</h4>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-medium text-purple-900 mb-2">邀请人奖励（1000 光子）：</p>
                        <ul className="space-y-1 text-xs text-gray-700">
                          <li>• <strong>1000 次</strong> Agent 对话</li>
                          <li>• <strong>33 次</strong> 文献调研报告</li>
                          <li>• <strong>200 次</strong> 结构弛豫计算</li>
                          <li>• <strong>200 次</strong> 热导率计算</li>
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-purple-900 mb-2">受邀请人奖励（500 光子）：</p>
                        <ul className="space-y-1 text-xs text-gray-700">
                          <li>• <strong>500 次</strong> Agent 对话</li>
                          <li>• <strong>16 次</strong> 文献调研报告</li>
                          <li>• <strong>100 次</strong> 结构弛豫计算</li>
                          <li>• <strong>100 次</strong> 热导率计算</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* 如何参与 */}
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <h4 className="text-sm font-semibold text-blue-900 mb-3">📝 如何参与邀请活动</h4>
                    <div className="space-y-2 text-xs text-gray-700">
                      <div className="flex items-start space-x-2">
                        <span className="flex-shrink-0 w-5 h-5 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">1</span>
                        <div>
                          <p className="font-medium text-gray-900">登录 Bohrium 平台</p>
                          <p className="text-gray-600">访问 <a href="https://bohrium.dp.tech" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">bohrium.dp.tech</a></p>
                        </div>
                      </div>
                      <div className="flex items-start space-x-2">
                        <span className="flex-shrink-0 w-5 h-5 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">2</span>
                        <p className="font-medium text-gray-900">获取您的学术码（邀请码）</p>
                      </div>
                      <div className="flex items-start space-x-2">
                        <span className="flex-shrink-0 w-5 h-5 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">3</span>
                        <p className="font-medium text-gray-900">分享给好友</p>
                      </div>
                      <div className="flex items-start space-x-2">
                        <span className="flex-shrink-0 w-5 h-5 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">4</span>
                        <p className="font-medium text-gray-900">好友在 72 小时内填写学术码</p>
                      </div>
                      <div className="flex items-start space-x-2">
                        <span className="flex-shrink-0 w-5 h-5 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">5</span>
                        <p className="font-medium text-gray-900">双方自动获得奖励</p>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* 底部操作栏 */}
          <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={dontShowAgain}
                  onChange={(e) => setDontShowAgain(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">不再显示此页面</span>
              </label>
              <button
                onClick={handleClose}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PricingModal

