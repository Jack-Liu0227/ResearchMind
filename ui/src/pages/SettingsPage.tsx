import React, { useState } from 'react'
import { Save, RefreshCw, Download, Upload, Trash2, ArrowLeft, Info } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { APP_CONFIG, API_CONFIG } from '../constants'

const SettingsPage: React.FC = () => {
  const navigate = useNavigate()
  const {
    settings,
    updateSettings,
    sessions,
    setSessions,
    clearCurrentSessionStructures,
    clearPhononImages,
    setCurrentStructure,
    setShowPhononVisualization,
    agents,
    setCurrentAgent,
    uiConfig,
    setShowFilesInChat
  } = useAppStore()
  const [localSettings, setLocalSettings] = useState(settings)
  const [isLoading, setIsLoading] = useState(false)

  // 当store中的settings变化时，更新localSettings
  React.useEffect(() => {
    setLocalSettings(settings)
  }, [settings])

  const handleSave = async () => {
    setIsLoading(true)
    try {
      console.log('Saving settings:', localSettings)
      updateSettings(localSettings)
      toast.success('设置已保存')
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast.error('保存设置失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setLocalSettings(settings)
    toast('设置已重置', { icon: 'ℹ️' })
  }

  const handleExportData = () => {
    try {
      const data = {
        sessions,
        settings,
        exportTime: new Date().toISOString(),
      }

      console.log('Exporting data:', data)

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `researchmind-data-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      toast.success('数据已导出')
    } catch (error) {
      console.error('Failed to export data:', error)
      toast.error('导出数据失败')
    }
  }

  const handleImportData = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string)
        console.log('Importing data:', data)

        if (data.sessions) {
          setSessions(data.sessions)
        }
        if (data.settings) {
          updateSettings(data.settings)
          setLocalSettings(data.settings)
        }
        toast.success('数据已导入')
      } catch (error) {
        console.error('Failed to import data:', error)
        toast.error('导入数据失败，文件格式不正确')
      }
    }
    reader.readAsText(file)
  }

  const handleClearData = () => {
    if (confirm('确定要清除所有数据吗？此操作不可恢复。\n\n将清除：\n- 所有会话和消息\n- 所有结构数据\n- 所有声子谱图片')) {
      try {
        console.log('Clearing all data...')
        setSessions([])
        clearCurrentSessionStructures()
        clearPhononImages()
        setCurrentStructure(null)
        setShowPhononVisualization(false)
        toast.success('所有数据已清除')
      } catch (error) {
        console.error('Failed to clear data:', error)
        toast.error('清除数据失败')
      }
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        {/* 返回按钮 */}
        <div className="mb-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>返回对话</span>
          </button>
        </div>

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">设置</h1>
          <p className="text-gray-600 mt-1">配置您的ResearchMind体验</p>
        </div>

        <div className="space-y-6">
          {/* 系统信息 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">系统信息</h2>
            </div>
            <div className="card-content space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">应用名称：</span>
                  <span className="font-medium ml-2">{APP_CONFIG.NAME}</span>
                </div>
                <div>
                  <span className="text-gray-500">版本号：</span>
                  <span className="font-medium ml-2">{APP_CONFIG.VERSION}</span>
                </div>
                <div>
                  <span className="text-gray-500">API 地址：</span>
                  <span className="font-medium ml-2 text-xs">{API_CONFIG.API_BASE_URL}</span>
                </div>
                <div>
                  <span className="text-gray-500">WebSocket：</span>
                  <span className="font-medium ml-2 text-xs">{API_CONFIG.WS_URL}</span>
                </div>
              </div>
            </div>
          </div>

          {/* 界面设置 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">界面设置</h2>
            </div>
            <div className="card-content space-y-4">
              {/* 主题设置 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  主题模式
                </label>
                <select
                  value={localSettings.theme}
                  onChange={(e) => {
                    const newTheme = e.target.value as any
                    setLocalSettings({
                      ...localSettings,
                      theme: newTheme
                    })
                    if (newTheme !== 'light') {
                      toast('深色模式和自动模式正在开发中，敬请期待！', { icon: '🚧' })
                    }
                  }}
                  className="input"
                  disabled={localSettings.theme !== 'light'}
                >
                  <option value="light">浅色模式（当前）</option>
                  <option value="dark">深色模式（开发中）</option>
                  <option value="auto">跟随系统（开发中）</option>
                </select>
                <p className="text-sm text-gray-500 mt-1">
                  当前仅支持浅色模式，深色模式正在开发中
                </p>
              </div>

              {/* 默认智能体 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
                  默认智能体
                  <Info className="w-4 h-4 ml-1 text-gray-400" />
                </label>
                <select
                  value={localSettings.defaultAgent}
                  onChange={(e) => {
                    const newAgentId = e.target.value
                    setLocalSettings({
                      ...localSettings,
                      defaultAgent: newAgentId
                    })

                    // 立即切换当前智能体
                    const selectedAgent = agents.find(a => a.id === newAgentId)
                    if (selectedAgent) {
                      setCurrentAgent(selectedAgent)
                      toast.success(`已切换到 ${selectedAgent.name}`)
                    } else {
                      toast.success('默认智能体已更新')
                    }
                  }}
                  className="input"
                >
                  <option value="research_coordinator">研究协调器 - 智能路由和任务分配</option>
                  <option value="deep_research_agent">文献研究智能体 - 论文搜索和分析</option>
                  <option value="database_agent">数据库智能体 - 材料数据查询</option>
                  <option value="simulation_agent">仿真智能体 - 结构弛豫和声子计算</option>
                </select>
                <p className="text-sm text-gray-500 mt-1">
                  选择后立即切换当前智能体，并在新建对话时使用
                </p>
              </div>
            </div>
          </div>

          {/* 功能设置 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">功能设置</h2>
            </div>
            <div className="card-content space-y-4">
              {/* 自动保存 */}
              <div className="flex items-center justify-between py-2">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700 flex items-center">
                    自动保存对话
                    <Info className="w-4 h-4 ml-1 text-gray-400" />
                  </label>
                  <p className="text-sm text-gray-500 mt-1">
                    自动保存对话记录、结构数据和声子谱到浏览器本地存储
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer ml-4">
                  <input
                    type="checkbox"
                    checked={localSettings.autoSave}
                    onChange={(e) => {
                      const newValue = e.target.checked
                      setLocalSettings({
                        ...localSettings,
                        autoSave: newValue
                      })
                      toast.success(newValue ? '已启用自动保存' : '已禁用自动保存')
                    }}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div className="border-t border-gray-200"></div>

              {/* 🆕 对话框文件展示设置 */}
              <div className="flex items-center justify-between py-2">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700 flex items-center">
                    对话框中显示文件
                    <Info className="w-4 h-4 ml-1 text-gray-400" />
                  </label>
                  <p className="text-sm text-gray-500 mt-1">
                    在对话框中显示 CSV、图片等文件（右侧边栏始终显示所有数据）
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer ml-4">
                  <input
                    type="checkbox"
                    checked={uiConfig.showFilesInChat}
                    onChange={(e) => {
                      const newValue = e.target.checked
                      setShowFilesInChat(newValue)
                      toast.success(newValue ? '已在对话框中显示文件' : '已隐藏对话框中的文件')
                    }}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div className="border-t border-gray-200"></div>

              {/* 通知设置 */}
              <div className="flex items-center justify-between py-2">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700 flex items-center">
                    桌面通知
                    <Info className="w-4 h-4 ml-1 text-gray-400" />
                  </label>
                  <p className="text-sm text-gray-500 mt-1">
                    智能体回复时显示浏览器桌面通知（需要授权）
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer ml-4">
                  <input
                    type="checkbox"
                    checked={localSettings.notifications}
                    onChange={(e) => {
                      const newValue = e.target.checked
                      setLocalSettings({
                        ...localSettings,
                        notifications: newValue
                      })
                      if (newValue && 'Notification' in window && Notification.permission === 'default') {
                        Notification.requestPermission().then(permission => {
                          if (permission === 'granted') {
                            toast.success('通知权限已授予')
                          } else {
                            toast.error('通知权限被拒绝')
                            setLocalSettings({
                              ...localSettings,
                              notifications: false
                            })
                          }
                        })
                      } else {
                        toast.success(newValue ? '已启用桌面通知' : '已禁用桌面通知')
                      }
                    }}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* 数据管理 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">数据管理</h2>
            </div>
            <div className="card-content space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start">
                  <Info className="w-5 h-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium mb-1">数据存储说明</p>
                    <p>所有数据存储在浏览器本地，包括：对话记录、结构数据、声子谱图片、用户设置等。清除浏览器缓存会导致数据丢失，建议定期导出备份。</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={handleExportData}
                  className="btn btn-secondary btn-md flex items-center justify-center"
                  title="导出所有数据到 JSON 文件"
                >
                  <Download className="w-4 h-4 mr-2" />
                  导出数据
                </button>

                <label className="btn btn-secondary btn-md flex items-center justify-center cursor-pointer" title="从 JSON 文件导入数据">
                  <Upload className="w-4 h-4 mr-2" />
                  导入数据
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleImportData}
                    className="hidden"
                  />
                </label>

                <button
                  onClick={handleClearData}
                  className="btn bg-red-100 text-red-700 hover:bg-red-200 btn-md flex items-center justify-center"
                  title="清除所有本地数据"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  清除数据
                </button>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600 space-y-2">
                <p className="font-medium text-gray-700">操作说明：</p>
                <ul className="space-y-1 ml-4">
                  <li className="flex items-start">
                    <span className="text-primary-600 mr-2">•</span>
                    <span><strong>导出数据</strong>：将所有对话记录、结构数据、声子谱和设置导出为 JSON 文件</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary-600 mr-2">•</span>
                    <span><strong>导入数据</strong>：从之前导出的 JSON 文件恢复数据（会覆盖当前数据）</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-600 mr-2">•</span>
                    <span><strong>清除数据</strong>：删除所有本地存储的数据，此操作不可恢复</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex justify-end space-x-3">
            <button
              onClick={handleReset}
              className="btn btn-secondary btn-md"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              重置
            </button>
            <button
              onClick={handleSave}
              disabled={isLoading}
              className="btn btn-primary btn-md"
            >
              <Save className="w-4 h-4 mr-2" />
              {isLoading ? '保存中...' : '保存设置'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage