import React, { useEffect, useState } from 'react'
import { toast } from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

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

const PricingPage: React.FC = () => {
  const navigate = useNavigate()
  const [config, setConfig] = useState<PricingConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPricingConfig()
  }, [])

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

  // 获取功能的计费单位
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">加载中...</div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600">加载失败</div>
      </div>
    )
  }

  return (
    <div className="bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto pb-12">
        {/* 返回按钮 */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>返回主界面</span>
          </button>
        </div>

        {/* 标题 */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">ResearchMind 收费标准</h1>
          <p className="text-lg text-gray-600">透明、公平、按需付费</p>
          <p className="text-sm text-gray-500 mt-2">版本：{config.version}</p>
        </div>

        {/* 功能定价表 */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">功能定价</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    功能
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    光子消耗
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    说明
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(config.feature_pricing).map(([key, photons]) => (
                  <tr key={key} className={photons === 0 ? 'bg-green-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {getFeatureName(key)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
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
                    <td className="px-6 py-4 text-sm text-gray-500">
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
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">邀请奖励</h2>

          {/* 平台说明 */}
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              <strong>说明：</strong>邀请奖励由 Bohrium 平台提供和管理（活动 ID: 1200000），ResearchMind 仅展示规则。
            </p>
          </div>

          {/* 奖励卡片 */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {/* 邀请人奖励 */}
            <div className="border border-blue-200 rounded-lg p-6 bg-blue-50">
              <h3 className="text-lg font-semibold text-blue-900 mb-4">🎁 邀请人奖励</h3>
              <div className="space-y-3">
                <div className="bg-white rounded-lg p-3">
                  <p className="text-sm font-medium text-gray-900 mb-2">基础奖励（每邀请1人）</p>
                  <ul className="space-y-1 text-sm text-gray-700">
                    <li>✅ <strong>{config.invitation_rewards.inviter.membership_days} 天</strong>体验会员</li>
                    <li>✅ <strong>{config.invitation_rewards.inviter.photons_per_membership} 光子</strong>（有效期 {config.invitation_rewards.inviter.photons_validity_days} 天）</li>
                    <li>✅ <strong>{config.invitation_rewards.inviter.cloud_storage_gb}GB</strong> 玻尔云盘空间</li>
                  </ul>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <p className="text-sm font-medium text-gray-900 mb-2">累加规则</p>
                  <ul className="space-y-1 text-sm text-gray-700">
                    <li>✅ 会员时长向后延续累加</li>
                    <li>✅ 邀请 5 人 = 35 天会员 + 5000 光子</li>
                    <li>✅ 邀请 10 人 = 70 天会员 + 10000 光子</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* 受邀请人奖励 */}
            <div className="border border-green-200 rounded-lg p-6 bg-green-50">
              <h3 className="text-lg font-semibold text-green-900 mb-4">🎉 受邀请人奖励</h3>
              <div className="space-y-3">
                <div className="bg-white rounded-lg p-3">
                  <p className="text-sm font-medium text-gray-900 mb-2">新用户奖励</p>
                  <ul className="space-y-1 text-sm text-gray-700">
                    <li>✅ 填写学术码后获得 <strong>{config.invitation_rewards.invitee.photons} 光子</strong></li>
                    <li>✅ 光子有效期 <strong>{config.invitation_rewards.invitee.photons_validity_days} 天</strong></li>
                  </ul>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <p className="text-sm font-medium text-gray-900 mb-2">重要提示</p>
                  <ul className="space-y-1 text-sm text-gray-700">
                    <li>⚠️ 需在注册后 <strong>72 小时内</strong>填写学术码</li>
                    <li>⚠️ 超时后将无法获得奖励</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* 可用功能示例 */}
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6 border border-purple-200">
            <h3 className="text-lg font-semibold text-purple-900 mb-4">💡 光子可用功能示例</h3>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm font-medium text-purple-900 mb-3">邀请人奖励（1000 光子）可用于：</p>
                <ul className="space-y-2 text-sm text-gray-700">
                  <li>• <strong>1000 次</strong> Agent 对话</li>
                  <li>• <strong>33 次</strong> 文献调研报告（全文分析）</li>
                  <li>• <strong>66 次</strong> 文献分析报告（摘要分析）</li>
                  <li>• <strong>200 次</strong> 结构弛豫计算</li>
                  <li>• <strong>200 次</strong> 声子谱计算</li>
                  <li>• <strong>200 次</strong> 热导率计算</li>
                </ul>
              </div>
              <div>
                <p className="text-sm font-medium text-purple-900 mb-3">受邀请人奖励（500 光子）可用于：</p>
                <ul className="space-y-2 text-sm text-gray-700">
                  <li>• <strong>500 次</strong> Agent 对话</li>
                  <li>• <strong>16 次</strong> 文献调研报告（全文分析）</li>
                  <li>• <strong>33 次</strong> 文献分析报告（摘要分析）</li>
                  <li>• <strong>100 次</strong> 结构弛豫计算</li>
                  <li>• <strong>100 次</strong> 声子谱计算</li>
                  <li>• <strong>100 次</strong> 热导率计算</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 如何参与 */}
          <div className="mt-6 bg-blue-50 rounded-lg p-6 border border-blue-200">
            <h3 className="text-lg font-semibold text-blue-900 mb-4">📝 如何参与邀请活动</h3>
            <div className="space-y-3 text-sm text-gray-700">
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">1</span>
                <div>
                  <p className="font-medium text-gray-900">登录 Bohrium 平台</p>
                  <p className="text-gray-600">访问 <a href="https://bohrium.dp.tech" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://bohrium.dp.tech</a> 并登录您的账号</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">2</span>
                <div>
                  <p className="font-medium text-gray-900">获取您的学术码</p>
                  <p className="text-gray-600">在个人中心找到您的专属学术码（邀请码）</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">3</span>
                <div>
                  <p className="font-medium text-gray-900">分享给好友</p>
                  <p className="text-gray-600">将学术码分享给您的同学、同事或研究伙伴</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">4</span>
                <div>
                  <p className="font-medium text-gray-900">好友填写学术码</p>
                  <p className="text-gray-600">好友在注册后 72 小时内填写您的学术码</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">5</span>
                <div>
                  <p className="font-medium text-gray-900">自动获得奖励</p>
                  <p className="text-gray-600">双方自动获得相应的光子和会员奖励</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PricingPage

