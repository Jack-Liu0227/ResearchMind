import React, { useState } from 'react'
import { Plus, Search, MessageSquare, Trash2, Edit3, Calendar, Save, Eraser } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import toast from 'react-hot-toast'

const Sidebar: React.FC = () => {
  const {
    sessions,
    currentSession,
    setCurrentSession,
    createSession,
    deleteSession,
    deleteAllSessions,
    clearSession,
    updateSession,
    currentAgent,
    settings,
    forceSave
  } = useAppStore()

  const [searchTerm, setSearchTerm] = useState('')
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  // 过滤并按创建时间倒序排列（最新的在最前面）
  const filteredSessions = sessions
    .filter(session =>
      session.title.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      const timeA = new Date(b.createdAt).getTime()
      const timeB = new Date(a.createdAt).getTime()
      return timeA - timeB
    })

  const handleSaveData = () => {
    forceSave()
    toast.success('数据已保存')
  }

  const handleCreateSession = () => {
    // 使用设置中的默认智能体，如果没有则使用当前智能体
    const agentId = settings.defaultAgent || currentAgent?.id
    if (agentId) {
      // 创建新会话时，当前会话的消息已经通过 addMessage 保存了
      // 所以直接创建新会话即可
      const newSession = createSession('新对话', agentId)
      setCurrentSession(newSession)
      console.log('创建新会话:', newSession.id, '使用智能体:', agentId, '当前会话数:', sessions.length + 1)
    }
  }

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    console.log('尝试删除会话:', sessionId)
    if (confirm('确定要删除这个对话吗？')) {
      try {
        deleteSession(sessionId)
        console.log('会话删除成功:', sessionId)
      } catch (error) {
        console.error('删除会话失败:', error)
      }
    }
  }

  const handleDeleteAllSessions = () => {
    if (confirm('确定要清除所有会话吗？此操作不可恢复！')) {
      try {
        deleteAllSessions()
        console.log('所有会话已清除')
        toast.success('所有会话已清除')
      } catch (error) {
        console.error('清除会话失败:', error)
        toast.error('清除会话失败')
      }
    }
  }

  const handleClearSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    console.log('尝试清除会话内容:', sessionId)
    if (confirm('确定要清除这个会话的所有消息吗？')) {
      try {
        clearSession(sessionId)
        console.log('会话内容已清除:', sessionId)
        toast.success('会话内容已清除')
      } catch (error) {
        console.error('清除会话内容失败:', error)
        toast.error('清除会话内容失败')
      }
    }
  }

  const handleEditSession = (session: any, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSessionId(session.id)
    setEditTitle(session.title)
  }

  const handleSaveEdit = (sessionId: string) => {
    if (editTitle.trim()) {
      updateSession(sessionId, { title: editTitle.trim() })
    }
    setEditingSessionId(null)
    setEditTitle('')
  }

  const handleCancelEdit = () => {
    setEditingSessionId(null)
    setEditTitle('')
  }

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">对话历史</h2>
          <button
            onClick={handleSaveData}
            className="p-1.5 bg-white/50 hover:bg-white text-gray-600 rounded-lg transition-colors shadow-sm"
            title="手动保存数据"
          >
            <Save className="w-4 h-4" />
          </button>
        </div>

        {/* 搜索框 */}
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 group-hover:text-primary-500 transition-colors" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/40 border border-white/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:bg-white/60 transition-all text-sm placeholder-gray-400"
          />
        </div>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {filteredSessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">暂无对话记录</p>
            <p className="text-xs text-gray-400 mt-1">
              点击"新对话"开始聊天
            </p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {/* 新建对话按钮 - 放在列表最前面 */}
            <button
              onClick={handleCreateSession}
              className="w-full p-3 rounded-lg border-2 border-dashed border-primary-300 hover:border-primary-500 hover:bg-primary-50 transition-colors flex items-center justify-center gap-2 text-primary-600 font-medium"
              disabled={!currentAgent}
            >
              <Plus className="w-5 h-5" />
              新建对话
            </button>

            {/* 清除所有会话按钮 */}
            {sessions.length > 0 && (
              <button
                onClick={handleDeleteAllSessions}
                className="w-full p-2 rounded-lg border border-red-300 hover:border-red-500 hover:bg-red-50 transition-colors flex items-center justify-center gap-2 text-red-600 text-sm"
              >
                <Trash2 className="w-4 h-4" />
                清除所有会话
              </button>
            )}

            {filteredSessions.map((session) => (
              <div
                key={session.id}
                onClick={() => setCurrentSession(session)}
                className={`group relative p-3 rounded-xl cursor-pointer transition-all duration-200 border ${currentSession?.id === session.id
                    ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-md border-primary-400/50'
                    : 'hover:bg-white/60 border-transparent hover:border-white/40 hover:shadow-sm text-gray-700'
                  }`}
              >
                {editingSessionId === session.id ? (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="input w-full text-sm"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleSaveEdit(session.id)
                        } else if (e.key === 'Escape') {
                          handleCancelEdit()
                        }
                      }}
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleSaveEdit(session.id)}
                        className="btn btn-primary btn-sm text-xs"
                      >
                        保存
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="btn btn-secondary btn-sm text-xs"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className={`text-sm font-medium truncate ${currentSession?.id === session.id ? 'text-white' : 'text-gray-900 group-hover:text-primary-700'}`}>
                          {session.title}
                        </h3>
                        <div className={`flex items-center mt-1 text-xs ${currentSession?.id === session.id ? 'text-blue-100' : 'text-gray-500'}`}>
                          <Calendar className="w-3 h-3 mr-1" />
                          {session.updatedAt && !isNaN(new Date(session.updatedAt).getTime())
                            ? formatDistanceToNow(new Date(session.updatedAt), {
                              addSuffix: true,
                              locale: zhCN
                            })
                            : '刚刚'
                          }
                        </div>
                        <p className={`text-xs mt-1 ${currentSession?.id === session.id ? 'text-blue-200' : 'text-gray-400'}`}>
                          {session.messages.length} 条消息
                        </p>
                      </div>

                      {/* 操作按钮 */}
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex space-x-1">
                        <button
                          onClick={(e) => handleEditSession(session, e)}
                          className={`p-1.5 rounded-lg transition-colors ${currentSession?.id === session.id
                              ? 'hover:bg-white/20 text-white'
                              : 'hover:bg-gray-200 text-gray-500'
                            }`}
                          title="重命名"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => handleClearSession(session.id, e)}
                          className={`p-1.5 rounded-lg transition-colors ${currentSession?.id === session.id
                              ? 'hover:bg-white/20 text-white'
                              : 'hover:bg-yellow-100 text-yellow-600'
                            }`}
                          title="清除内容"
                        >
                          <Eraser className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteSession(session.id, e)}
                          className={`p-1.5 rounded-lg transition-colors ${currentSession?.id === session.id
                              ? 'hover:bg-white/20 text-white'
                              : 'hover:bg-red-100 text-red-600'
                            }`}
                          title="删除会话"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Sidebar