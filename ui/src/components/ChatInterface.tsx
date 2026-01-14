import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic, Square, X, Copy, Bot, MessageSquarePlus } from 'lucide-react'
import toast from 'react-hot-toast'

import MessageList from './MessageList'
import { useAppStore } from '../store/useAppStore'
import { wsService } from '../services/websocket'
import { APP_CONFIG, API_CONFIG } from '../constants'
import { parseCIF as apiParseCIF, checkAPIHealthSafe as checkAPIHealth, resolveFileUrl } from '../utils/apiClient'
import { uploadFile } from '../services/api'
import { copyToClipboard } from '../utils'

const ChatInterface: React.FC = () => {
  const {
    messages,
    currentAgent,
    currentSession,
    currentStructure,
    sessions,
    addMessage,
    connected,
    createSession,
    setCurrentSession,
    setCurrentStructure,
    addToCurrentSessionStructures,
    addToCurrentSessionFiles,
    isLoading,
    setIsLoading,
    loadingMessage,
    setLoadingMessage,
    agents,
    setCurrentAgent
  } = useAppStore()

  const [inputValue, setInputValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isAgentMenuOpen, setIsAgentMenuOpen] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[] | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [inputValue])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentAgent || !connected) {
      if (!connected) {
        toast.error('Not connected to the server. Please check the backend.')
      } else if (!currentAgent) {
        toast.error('Please select an agent first.')
      }
      return
    }

    const messageContent = inputValue.trim()
    setInputValue('')

    let sessionToUse = currentSession
    if (!sessionToUse && currentAgent) {
      sessionToUse = createSession('New chat', currentAgent.id)
      setCurrentSession(sessionToUse)
      console.log('Created session for message send:', sessionToUse.id)
    }

    const userMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content: messageContent,
      role: 'user' as const,
      timestamp: new Date(),
    }
    addMessage(userMessage)

    setIsLoading(true)
    setLoadingMessage(`${currentAgent?.name || 'Agent'} is processing your request...`)

    toast.loading(`Sending message to ${currentAgent?.name || 'agent'}...`, {
      id: 'send-message-toast',
    })

    try {
      const isPhononIntent = /phonon/i.test(messageContent)
      const cif = (currentStructure as any)?.cifContent
      if (isPhononIntent && cif) {
        wsService.sendChatWithAttachments({
          content: messageContent,
          agentId: currentAgent.id,
          sessionId: sessionToUse?.id,
          attachments: [
            { filename: `${(currentStructure as any)?.formula || 'structure'}.cif`, content: cif }
          ],
        })
      } else {
        wsService.sendMessage(
          messageContent,
          currentAgent.id,
          sessionToUse?.id
        )
      }

      toast.success('Message sent. Waiting for response...', {
        id: 'send-message-toast',
      })
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('Failed to send message. Please try again.', {
        id: 'send-message-toast',
      })
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (uploadedFiles && uploadedFiles.length > 0) {
        handleSendWithFile()
      } else {
        handleSendMessage()
      }
    }
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const handleCopyInput = async () => {
    if (!inputValue.trim()) {
      toast.error('Nothing to copy.')
      return
    }

    const success = await copyToClipboard(inputValue)
    if (success) {
      toast.success('Copied input text.')
    } else {
      toast.error('Copy failed. Please select the text manually.')
    }
  }

  const hasFiles = (uploadedFiles?.length || 0) > 0

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    const selected: File[] = []
    const skipped: string[] = []

    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i]
      if (f.size > APP_CONFIG.MAX_FILE_SIZE) {
        const sizeMB = (f.size / (1024 * 1024)).toFixed(1)
        const maxSizeMB = (APP_CONFIG.MAX_FILE_SIZE / (1024 * 1024)).toFixed(0)
        skipped.push(`${f.name} (${sizeMB}MB > ${maxSizeMB}MB)`)
        continue
      }
      selected.push(f)
    }

    if (skipped.length > 0) {
      toast.error(`Skipped oversized files: ${skipped.join(', ')}`)
    }

    if (selected.length === 0) return
    setUploadedFiles(selected)
    toast.success(selected.length === 1 ? `Selected file: ${selected[0].name}` : `Selected ${selected.length} files`)
  }

  const handleRemoveFile = () => {
    setUploadedFiles(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSendWithFile = async () => {
    if (!uploadedFiles || uploadedFiles.length === 0) {
      handleSendMessage()
      return
    }

    if (currentAgent) {
      setIsLoading(true)
      setLoadingMessage(`${currentAgent.name} is processing the data...`)
    }

    let sessionToUse = currentSession
    if (!sessionToUse && currentAgent) {
      const lastForAgent = [...(sessions || [])].reverse().find(s => s.agentId === currentAgent.id)
      if (lastForAgent) {
        sessionToUse = lastForAgent
        setCurrentSession(lastForAgent)
        console.log('Reusing existing session:', lastForAgent.id)
      } else {
        sessionToUse = createSession('New chat', currentAgent.id)
        setCurrentSession(sessionToUse)
        console.log('Created session for attachments:', sessionToUse.id)
      }
    }

    const pendingUserText = (inputValue || '').trim()
    if (pendingUserText) {
      addMessage({
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        content: pendingUserText,
        role: 'user' as const,
        timestamp: new Date(),
      })
    }
    setInputValue('')

    const hasNonCif = uploadedFiles.some(f => !f.name.toLowerCase().endsWith('.cif'))
    if (hasNonCif) {
      const nonCifFiles = uploadedFiles.filter(f => !f.name.toLowerCase().endsWith('.cif'))

      if (currentAgent?.id === 'deep_research_agent') {
        try {
          const fileAttachments: Array<{ filename: string; content: string; encoding: string; mime_type: string }> = []

          for (const file of nonCifFiles) {
            const arrayBuffer = await file.arrayBuffer()
            const base64 = btoa(
              new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
            )
            fileAttachments.push({
              filename: file.name,
              content: base64,
              encoding: 'base64',
              mime_type: file.type || 'application/octet-stream'
            })
          }

          wsService.sendChatWithAttachments({
            content: (pendingUserText || '').trim() || 'Please analyze the uploaded documents.',
            agentId: currentAgent.id,
            sessionId: (sessionToUse || currentSession)?.id,
            attachments: fileAttachments,
          })

          toast.success(`Uploaded ${nonCifFiles.length} file(s). Processing...`)
        } catch (err) {
          console.error('Failed to read files:', err)
          toast.error('Failed to read files. Please retry.')
        } finally {
          setUploadedFiles(null)
          if (fileInputRef.current) fileInputRef.current.value = ''
          setIsLoading(false)
          setLoadingMessage('')
        }
        return
      }

      try {
        const form = new FormData()
        nonCifFiles.forEach(f => form.append('files', f))

        const sessionId = (sessionToUse || currentSession)?.id
        const clientId = wsService.getClientId()

        let uploadUrl = resolveFileUrl('/upload?type=documents')
        if (sessionId) {
          uploadUrl += `&session_id=${encodeURIComponent(sessionId)}`
        }
        if (clientId) {
          uploadUrl += `&client_id=${encodeURIComponent(clientId)}`
        }

        console.log('Uploading documents:', {
          fileCount: nonCifFiles.length,
          sessionId,
          clientId,
          uploadUrl
        })

        const resp = await fetch(uploadUrl, { method: 'POST', body: form })
        if (!resp.ok) {
          const text = await resp.text()
          throw new Error(text || `HTTP ${resp.status}`)
        }

        const data = await resp.json()
        console.log('Upload response:', data)

        const uploaded = Array.isArray(data.uploaded_files) ? data.uploaded_files : []

        uploaded.forEach((it: any) => {
          const lower = (it.filename || '').toLowerCase()
          if (lower.endsWith('.pdf')) return
          const type = lower.endsWith('.md') ? 'md' : lower.endsWith('.csv') ? 'csv' : 'data'
          addToCurrentSessionFiles({
            id: `doc:${it.paper_id || it.filename}`,
            type,
            name: it.filename || 'document',
            downloadUrl: it.download_url,
            filePath: it.file_path,
            createdAt: Date.now(),
            sourceMessageId: undefined,
          })
        })

        if (data.csv_download_url) {
          console.log('Adding CSV summary file:', data.csv_download_url)
          addToCurrentSessionFiles({
            id: `csv:${Date.now()}`,
            type: 'csv',
            name: data.csv_file_path ? (data.csv_file_path.split('/').pop() || 'uploaded_papers.csv') : 'uploaded_papers.csv',
            downloadUrl: data.csv_download_url,
            filePath: data.csv_file_path,
            createdAt: Date.now(),
            sourceMessageId: undefined,
          })
        }

        addMessage({
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content: `Processed ${uploadedFiles.length} document(s). Download links are ready.`,
          role: 'assistant' as const,
          timestamp: new Date(),
        })
        toast.success(`Processed ${uploadedFiles.length} document(s). Download links are ready.`)
      } catch (err) {
        console.error('Document upload failed:', err)
        toast.error('Document processing failed. Please retry.')
      } finally {
        setUploadedFiles(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
        setIsLoading(false)
        setLoadingMessage('')
      }
      return
    }

    try {
      const cifFiles = uploadedFiles.filter(f => f.name.toLowerCase().endsWith('.cif'))

      const attachments: Array<{ filename: string; content: string }> = []

      for (const file of cifFiles) {
        const fileContent = await file.text()
        attachments.push({ filename: file.name, content: fileContent })

        try {
          const response = await uploadFile(file, 'structure')

          if (response.data?.success && response.data?.structures?.length > 0) {
            const structure = response.data.structures[0]
            setCurrentStructure(structure)
            addToCurrentSessionStructures(structure)
            toast.success(`Loaded structure: ${structure.formula}`)
            console.log('Uploaded structure with cif_file_path:', structure.cif_file_path)
          } else {
            console.warn('Backend upload failed, falling back to local parsing')
            const apiAvailable = await checkAPIHealth()
            if (apiAvailable) {
              const structure = await apiParseCIF(fileContent)
              const conventionalStructure = await apiParseCIF(fileContent, true)
              if (structure && conventionalStructure) {
                structure.source = {
                  database: 'Upload',
                  materialId: structure.id,
                  retrievedAt: new Date(),
                }
                structure.cifContent = fileContent
                structure.cifFilename = file.name
                structure.metadata = {
                  ...structure.metadata,
                  originalFilename: file.name,
                  conventionalStructure,
                }
                setCurrentStructure(structure)
                addToCurrentSessionStructures(structure)
                toast.success(`Loaded structure: ${structure.formula} (local parse)`)
              }
            }
          }
        } catch (error) {
          console.error('CIF upload/parse failed:', error)
          toast.error(`CIF processing failed: ${file.name}`)
        }
      }

      if (attachments.length > 0 && currentAgent) {
        wsService.sendChatWithAttachments({
          content: (pendingUserText || '').trim() || 'Please analyze the attached CIF file(s).',
          agentId: currentAgent.id,
          sessionId: (sessionToUse || currentSession)?.id,
          attachments,
        })
      }
    } finally {
      setUploadedFiles(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const handleNewTopic = () => {
    if (!currentAgent) return

    const newSession = createSession('New chat', currentAgent.id)
    setCurrentSession(newSession)
    toast.success('Started a new chat. Context reset.')
  }

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false)
      toast.success('Recording stopped.')
    } else {
      setIsRecording(true)
      toast.success('Recording started...')
    }
  }

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage.role === 'assistant') {
        setIsLoading(false)
      }
    }
  }, [messages, setIsLoading])

  const handleStopResponse = () => {
    if (!currentAgent || !currentSession) {
      return
    }

    wsService.sendStopRequest(currentAgent.id, currentSession.id)

    setIsLoading(false)
    setLoadingMessage('')

    toast.success('Response stopped.')
  }

  const handleRegenerate = async (messageId: string) => {
    if (!currentAgent || !connected || !currentSession) {
      toast.error('Cannot regenerate: not connected or no session selected.')
      return
    }

    const messageIndex = messages.findIndex(msg => msg.id === messageId)
    if (messageIndex === -1 || messages[messageIndex].role !== 'assistant') {
      toast.error('Cannot regenerate this message.')
      return
    }

    let userMessageContent = ''
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        userMessageContent = messages[i].content
        break
      }
    }

    if (!userMessageContent) {
      toast.error('No previous user message found.')
      return
    }

    setIsLoading(true)
    toast('Regenerating...', { icon: 'i' })

    try {
      wsService.sendMessage(
        userMessageContent,
        currentAgent.id,
        currentSession.id
      )
    } catch (error) {
      console.error('Failed to regenerate message:', error)
      toast.error('Regeneration failed.')
      setIsLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages} onRegenerate={handleRegenerate} />
      </div>

      <div className="flex-shrink-0 bg-transparent z-10 transition-all duration-300 ease-in-out p-2 sm:p-5 pb-24 sm:pb-5">
        <div className="max-w-4xl mx-auto relative group">
          <div className="glass-panel border-t border-white/40 bg-white/60 shadow-2xl backdrop-blur-xl sm:rounded-2xl sm:border p-1.5 sm:p-3 transition-all hover:bg-white/70 hover:shadow-primary-500/10">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileChange}
              accept=".txt,.pdf,.doc,.docx,.cif,.xyz,.pdb"
              multiple
            />

            {uploadedFiles && uploadedFiles.length > 0 && (
              <div className="mb-2 flex items-center justify-between bg-primary-50/50 border border-primary-100/50 rounded-xl px-2 py-1.5 animate-fade-in">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 bg-primary-100 text-primary-600 rounded-lg">
                    <Paperclip className="w-4 h-4" />
                  </div>
                  {uploadedFiles.length === 1 ? (
                    <>
                      <span className="text-sm font-medium text-primary-900 truncate max-w-[150px] sm:max-w-xs">{uploadedFiles[0].name}</span>
                      <span className="text-xs text-primary-500">({(uploadedFiles[0].size / 1024).toFixed(1)} KB)</span>
                    </>
                  ) : (
                    <span className="text-sm font-medium text-primary-900">{uploadedFiles.length} files</span>
                  )}
                </div>
                <button
                  onClick={handleRemoveFile}
                  className="p-1.5 text-primary-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  title="Remove files"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            <div className="relative flex items-end gap-2">
              <div className="flex items-center gap-1">
                <div className="relative">
                  <button
                    onClick={() => setIsAgentMenuOpen(!isAgentMenuOpen)}
                    className="flex-shrink-0 p-2 text-gray-400 hover:text-primary-600 hover:bg-white/50 rounded-xl transition-all active:scale-95 group/agent-btn"
                    title={currentAgent?.name || 'Switch agent'}
                  >
                    <Bot className={`w-5 h-5 ${currentAgent ? 'text-primary-600' : ''}`} />
                  </button>

                  {isAgentMenuOpen && (
                    <>
                      <div className="fixed inset-0 z-30" onClick={() => setIsAgentMenuOpen(false)} />
                      <div className="absolute bottom-full left-0 mb-3 w-64 bg-white/90 backdrop-blur-xl border border-white/40 rounded-xl shadow-2xl z-40 overflow-hidden animate-slide-up origin-bottom-left ring-1 ring-black/5">
                        <div className="p-1 max-h-[50vh] overflow-y-auto custom-scrollbar">
                          <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Switch assistant</div>
                          {agents.map((agent) => (
                            <button
                              key={agent.id}
                              onClick={() => {
                                setCurrentAgent(agent)
                                setIsAgentMenuOpen(false)
                                if (!currentSession || currentSession.agentId !== agent.id) {
                                  // Switching context only.
                                }
                              }}
                              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left ${currentAgent?.id === agent.id
                                ? 'bg-primary-50 text-primary-900 border border-primary-100'
                                : 'hover:bg-black/5 text-gray-700 border border-transparent'
                                }`}
                            >
                              <Bot className={`w-4 h-4 ${currentAgent?.id === agent.id ? 'text-primary-600' : 'text-gray-400'}`} />
                              <span className="font-medium text-sm truncate">{agent.name}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                </div>

                <div className="w-px h-6 bg-gray-200/50 mx-1"></div>

                <button
                  onClick={handleFileUpload}
                  className="flex-shrink-0 p-2 text-gray-400 hover:text-primary-600 hover:bg-white/50 rounded-xl transition-all active:scale-95"
                  title="Upload files"
                >
                  <Paperclip className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    currentAgent
                      ? `Message ${currentAgent.name}...`
                      : 'Select an agent to start...'
                  }
                  className="w-full resize-none bg-transparent border-0 rounded-lg px-2 py-2 focus:outline-none focus:ring-0 text-gray-800 placeholder-gray-400 max-h-32 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent text-sm sm:text-base leading-relaxed"
                  rows={1}
                  disabled={!currentAgent || !connected}
                  style={{ minHeight: '44px' }}
                />
              </div>

              <div className="flex items-center gap-1">
                {!inputValue && (
                  <button
                    onClick={handleNewTopic}
                    className="p-2.5 rounded-xl transition-all active:scale-95 text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                    title="Start a new chat (reset context)"
                  >
                    <MessageSquarePlus className="w-5 h-5" />
                  </button>
                )}

                {!inputValue && (
                  <button
                    onClick={toggleRecording}
                    className={`p-2.5 rounded-xl transition-all active:scale-95 ${isRecording
                      ? 'bg-red-100 text-red-600 animate-pulse'
                      : 'text-gray-400 hover:text-gray-600 hover:bg-white/50'
                      }`}
                    title={isRecording ? 'Stop recording' : 'Voice input'}
                  >
                    {isRecording ? <Square className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                  </button>
                )}

                {isLoading ? (
                  <button
                    onClick={handleStopResponse}
                    className="p-2.5 bg-red-500 text-white rounded-xl shadow-lg shadow-red-500/30 hover:bg-red-600 transition-all active:scale-95"
                    title="Stop response"
                  >
                    <Square className="w-5 h-5" />
                  </button>
                ) : (
                  <button
                    onClick={hasFiles ? handleSendWithFile : handleSendMessage}
                    disabled={(!inputValue.trim() && !hasFiles) || !currentAgent || !connected}
                    className={`p-2.5 rounded-xl shadow-lg transition-all active:scale-95 flex items-center justify-center ${(!inputValue.trim() && !hasFiles) || !currentAgent || !connected
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed hidden sm:flex'
                      : 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-primary-500/30 hover:shadow-primary-500/40 hover:-translate-y-0.5'
                      }`}
                    title="Send"
                  >
                    <Send className="w-5 h-5 ml-0.5" />
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between mt-2 px-2 text-xs text-gray-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <div className="flex items-center space-x-2">
              <span>ResearchMind AI</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>v2.0</span>
            </div>
            <div>
              {!connected && (
                <span className="text-red-500 flex items-center gap-1">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                  Offline
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
