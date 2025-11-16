import React, { useEffect, useState } from 'react'
import { toast } from 'react-hot-toast'

interface InvitationStats {
  invitation_code: string
  invitation_count: number
  total_rewards: number
  pending_invitations: number
  successful_invitations: number
}

interface InvitationPanelProps {
  userId: number
}

const InvitationPanel: React.FC<InvitationPanelProps> = ({ userId }) => {
  const [stats, setStats] = useState<InvitationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAcceptModal, setShowAcceptModal] = useState(false)
  const [invitationCode, setInvitationCode] = useState('')
  const [accepting, setAccepting] = useState(false)

  useEffect(() => {
    fetchStats()
  }, [userId])

  const fetchStats = async () => {
    try {
      const response = await fetch(`/api/billing/invitation/stats/${userId}`)
      const data = await response.json()

      if (data.success) {
        setStats(data.stats)
      } else {
        toast.error('获取邀请统计失败')
      }
    } catch (error) {
      console.error('获取邀请统计失败:', error)
      toast.error('获取邀请统计失败')
    } finally {
      setLoading(false)
    }
  }

  const copyInvitationCode = () => {
    if (stats?.invitation_code) {
      navigator.clipboard.writeText(stats.invitation_code)
      toast.success('邀请码已复制到剪贴板')
    }
  }

  const shareInvitation = () => {
    if (stats?.invitation_code) {
      const shareText = `加入 ResearchMind，使用我的邀请码 ${stats.invitation_code} 获得 500 光子奖励！`
      const shareUrl = `${window.location.origin}?invite=${stats.invitation_code}`

      if (navigator.share) {
        navigator.share({
          title: 'ResearchMind 邀请',
          text: shareText,
          url: shareUrl,
        }).catch(() => {
          // 分享失败，复制到剪贴板
          navigator.clipboard.writeText(`${shareText}\n${shareUrl}`)
          toast.success('邀请链接已复制到剪贴板')
        })
      } else {
        navigator.clipboard.writeText(`${shareText}\n${shareUrl}`)
        toast.success('邀请链接已复制到剪贴板')
      }
    }
  }

  const handleAcceptInvitation = async () => {
    if (!invitationCode.trim()) {
      toast.error('请输入邀请码')
      return
    }

    setAccepting(true)
    try {
      // 获取用户的 AccessKey（从 Cookie）
      const accessKey = document.cookie
        .split('; ')
        .find(row => row.startsWith('appAccessKey='))
        ?.split('=')[1]

      if (!accessKey) {
        toast.error('未找到 AccessKey，请先登录')
        return
      }

      const response = await fetch('/api/billing/invitation/accept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          invitation_code: invitationCode.trim(),
          access_key: accessKey,
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast.success(data.message)
        if (data.invitee_reward) {
          toast.success(`您获得了 ${data.invitee_reward.photons} 光子奖励！`)
        }
        setShowAcceptModal(false)
        setInvitationCode('')
        fetchStats() // 刷新统计
      } else {
        toast.error(data.message)
      }
    } catch (error) {
      console.error('接受邀请失败:', error)
      toast.error('接受邀请失败')
    } finally {
      setAccepting(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-gray-600">加载中...</div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">加载失败</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">邀请好友</h2>

      {/* 邀请码展示 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          您的邀请码
        </label>
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={stats.invitation_code}
            readOnly
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 font-mono text-lg"
          />
          <button
            onClick={copyInvitationCode}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            复制
          </button>
          <button
            onClick={shareInvitation}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
          >
            分享
          </button>
        </div>
      </div>

      {/* 统计信息 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">成功邀请</div>
          <div className="text-2xl font-bold text-blue-600">{stats.successful_invitations}</div>
        </div>
        <div className="bg-green-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">总奖励</div>
          <div className="text-2xl font-bold text-green-600">{stats.total_rewards}</div>
        </div>
        <div className="bg-yellow-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">待接受</div>
          <div className="text-2xl font-bold text-yellow-600">{stats.pending_invitations}</div>
        </div>
        <div className="bg-purple-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">邀请总数</div>
          <div className="text-2xl font-bold text-purple-600">{stats.invitation_count}</div>
        </div>
      </div>

      {/* 接受邀请按钮 */}
      <button
        onClick={() => setShowAcceptModal(true)}
        className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
      >
        我有邀请码
      </button>

      {/* 接受邀请模态框 */}
      {showAcceptModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">填写邀请码</h3>
            <input
              type="text"
              value={invitationCode}
              onChange={(e) => setInvitationCode(e.target.value)}
              placeholder="请输入邀请码"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4"
            />
            <div className="flex space-x-2">
              <button
                onClick={handleAcceptInvitation}
                disabled={accepting}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
              >
                {accepting ? '提交中...' : '提交'}
              </button>
              <button
                onClick={() => {
                  setShowAcceptModal(false)
                  setInvitationCode('')
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default InvitationPanel

