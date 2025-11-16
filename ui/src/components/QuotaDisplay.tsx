import React, { useEffect, useState } from 'react'
import { toast } from 'react-hot-toast'

interface UserQuota {
  free_chat_quota: number
  free_chat_used: number
  free_chat_remaining: number
  total_photons_used: number
  invitation_count: number
  invitation_rewards_total: number
}

interface QuotaDisplayProps {
  userId: number
  compact?: boolean
}

const QuotaDisplay: React.FC<QuotaDisplayProps> = ({ userId, compact = false }) => {
  const [quota, setQuota] = useState<UserQuota | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchQuota()
  }, [userId])

  const fetchQuota = async () => {
    try {
      const response = await fetch(`/api/billing/quota/${userId}`)
      const data = await response.json()

      if (data.success) {
        setQuota(data.quota)
      } else {
        toast.error('获取配额信息失败')
      }
    } catch (error) {
      console.error('获取配额信息失败:', error)
      toast.error('获取配额信息失败')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-gray-600 text-sm">加载中...</div>
    )
  }

  if (!quota) {
    return (
      <div className="text-red-600 text-sm">加载失败</div>
    )
  }

  // 紧凑模式（用于顶部导航栏）
  if (compact) {
    return (
      <div className="flex items-center space-x-4 text-sm">
        <div className="flex items-center space-x-1">
          <span className="text-gray-600">免费对话:</span>
          <span className="font-semibold text-blue-600">
            {quota.free_chat_remaining}/{quota.free_chat_quota}
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <span className="text-gray-600">已用光子:</span>
          <span className="font-semibold text-orange-600">
            {quota.total_photons_used}
          </span>
        </div>
      </div>
    )
  }

  // 完整模式（用于设置页面）
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">我的配额</h2>

      <div className="space-y-4">
        {/* 免费对话额度 */}
        <div className="border-b border-gray-200 pb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-700">免费对话额度</span>
            <span className="text-lg font-semibold text-blue-600">
              {quota.free_chat_remaining} / {quota.free_chat_quota}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{
                width: `${(quota.free_chat_remaining / quota.free_chat_quota) * 100}%`
              }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            已使用 {quota.free_chat_used} 次
          </p>
        </div>

        {/* 光子消耗统计 */}
        <div className="border-b border-gray-200 pb-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">累计光子消耗</span>
            <span className="text-lg font-semibold text-orange-600">
              {quota.total_photons_used}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            所有功能的光子消耗总和
          </p>
        </div>

        {/* 邀请奖励统计 */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-700">邀请奖励</span>
            <span className="text-lg font-semibold text-green-600">
              {quota.invitation_rewards_total}
            </span>
          </div>
          <p className="text-xs text-gray-500">
            已成功邀请 {quota.invitation_count} 人
          </p>
        </div>
      </div>

      {/* 提示信息 */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <p className="text-sm text-gray-700">
          💡 <strong>提示：</strong>邀请好友可获得更多光子奖励！
        </p>
      </div>
    </div>
  )
}

export default QuotaDisplay

