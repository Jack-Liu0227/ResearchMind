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
    toast.success('Data saved.')
  }

  const handleCreateSession = () => {
    const agentId = settings.defaultAgent || currentAgent?.id
    if (agentId) {
      const newSession = createSession('New chat', agentId)
      setCurrentSession(newSession)
      console.log('Created new session:', newSession.id)
    }
  }

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    console.log('Deleting session:', sessionId)
    if (confirm('Delete this conversation?')) {
      try {
        deleteSession(sessionId)
        console.log('Session deleted:', sessionId)
      } catch (error) {
        console.error('Failed to delete session:', error)
      }
    }
  }

  const handleDeleteAllSessions = () => {
    if (confirm('Clear all conversations? This cannot be undone.')) {
      try {
        deleteAllSessions()
        console.log('All conversations cleared')
        toast.success('All conversations cleared.')
      } catch (error) {
        console.error('Failed to clear conversations:', error)
        toast.error('Failed to clear conversations.')
      }
    }
  }

  const handleClearSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    console.log('Clearing messages in session:', sessionId)
    if (confirm('Clear all messages in this conversation?')) {
      try {
        clearSession(sessionId)
        console.log('Session cleared:', sessionId)
        toast.success('Conversation cleared.')
      } catch (error) {
        console.error('Failed to clear session:', error)
        toast.error('Failed to clear conversation.')
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
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">Conversations</h2>
          <button
            onClick={handleSaveData}
            className="p-1.5 bg-white/50 hover:bg-white text-gray-600 rounded-lg transition-colors shadow-sm"
            title="Save data"
          >
            <Save className="w-4 h-4" />
          </button>
        </div>

        <div className="relative group">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 group-hover:text-primary-500 transition-colors" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/40 border border-white/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:bg-white/60 transition-all text-sm placeholder-gray-400"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {filteredSessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs text-gray-400 mt-1">Click "New chat" to start.</p>
            <button
              onClick={handleCreateSession}
              className="mt-3 w-full p-3 rounded-lg border-2 border-dashed border-primary-300 hover:border-primary-500 hover:bg-primary-50 transition-colors flex items-center justify-center gap-2 text-primary-600 font-medium"
              disabled={!currentAgent}
            >
              <Plus className="w-5 h-5" />
              New chat
            </button>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            <button
              onClick={handleCreateSession}
              className="w-full p-3 rounded-lg border-2 border-dashed border-primary-300 hover:border-primary-500 hover:bg-primary-50 transition-colors flex items-center justify-center gap-2 text-primary-600 font-medium"
              disabled={!currentAgent}
            >
              <Plus className="w-5 h-5" />
              New chat
            </button>

            {sessions.length > 0 && (
              <button
                onClick={handleDeleteAllSessions}
                className="w-full p-2 rounded-lg border border-red-300 hover:border-red-500 hover:bg-red-50 transition-colors flex items-center justify-center gap-2 text-red-600 text-sm"
              >
                <Trash2 className="w-4 h-4" />
                Clear all conversations
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
                        Save
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="btn btn-secondary btn-sm text-xs"
                      >
                        Cancel
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
                            : 'just now'
                          }
                        </div>
                        <p className={`text-xs mt-1 ${currentSession?.id === session.id ? 'text-blue-200' : 'text-gray-400'}`}>
                          {session.messages.length} messages
                        </p>
                      </div>

                      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex space-x-1">
                        <button
                          onClick={(e) => handleEditSession(session, e)}
                          className={`p-1.5 rounded-lg transition-colors ${currentSession?.id === session.id
                              ? 'hover:bg-white/20 text-white'
                              : 'hover:bg-gray-200 text-gray-500'
                            }`}
                          title="Rename"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => handleClearSession(session.id, e)}
                          className={`p-1.5 rounded-lg transition-colors ${currentSession?.id === session.id
                              ? 'hover:bg-white/20 text-white'
                              : 'hover:bg-yellow-100 text-yellow-600'
                            }`}
                          title="Clear messages"
                        >
                          <Eraser className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteSession(session.id, e)}
                          className={`p-1.5 rounded-lg transition-colors ${currentSession?.id === session.id
                              ? 'hover:bg-white/20 text-white'
                              : 'hover:bg-red-100 text-red-600'
                            }`}
                          title="Delete"
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
