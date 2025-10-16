import React, { useState } from 'react'
import { Save, RefreshCw, Download, Upload, Trash2, ArrowLeft } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

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
    setShowPhononVisualization
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
          {/* 基本设置 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">基本设置</h2>
            </div>
            <div className="card-content space-y-4">
              {/* 主题设置 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  主题
                </label>
                <select
                  value={localSettings.theme}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    theme: e.target.value as any
                  })}
                  className="input"
                >
                  <option value="light">浅色</option>
                  <option value="dark">深色</option>
                  <option value="auto">跟随系统</option>
                </select>
              </div>

              {/* 语言设置 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  语言
                </label>
                <select
                  value={localSettings.language}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    language: e.target.value as any
                  })}
                  className="input"
                >
                  <option value="zh">中文</option>
                  <option value="en">English</option>
                </select>
              </div>

              {/* 默认智能体 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  默认智能体
                </label>
                <select
                  value={localSettings.defaultAgent}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    defaultAgent: e.target.value
                  })}
                  className="input"
                >
                  <option value="research_coordinator">研究协调器</option>
                  <option value="deep_research_agent">文献研究智能体</option>
                  <option value="database_agent">数据库智能体</option>
                  <option value="simulation_agent">仿真智能体</option>
                </select>
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
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    自动保存对话
                  </label>
                  <p className="text-sm text-gray-500">
                    自动保存对话记录到本地存储
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localSettings.autoSave}
                    onChange={(e) => setLocalSettings({
                      ...localSettings,
                      autoSave: e.target.checked
                    })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              {/* 通知设置 */}
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    桌面通知
                  </label>
                  <p className="text-sm text-gray-500">
                    接收智能体回复的桌面通知
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localSettings.notifications}
                    onChange={(e) => setLocalSettings({
                      ...localSettings,
                      notifications: e.target.checked
                    })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* 连接设置 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">连接设置</h2>
            </div>
            <div className="card-content space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API 端点
                </label>
                <input
                  type="url"
                  value={localSettings.apiEndpoint}
                  onChange={(e) => setLocalSettings({
                    ...localSettings,
                    apiEndpoint: e.target.value
                  })}
                  className="input"
                  placeholder="http://localhost:8000"
                />
                <p className="text-sm text-gray-500 mt-1">
                  ResearchMind 后端服务的地址
                </p>
              </div>
            </div>
          </div>

          {/* 数据管理 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold">数据管理</h2>
            </div>
            <div className="card-content space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={handleExportData}
                  className="btn btn-secondary btn-md flex items-center justify-center"
                >
                  <Download className="w-4 h-4 mr-2" />
                  导出数据
                </button>
                
                <label className="btn btn-secondary btn-md flex items-center justify-center cursor-pointer">
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
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  清除数据
                </button>
              </div>
              
              <div className="text-sm text-gray-500">
                <p>• 导出数据包含所有对话记录和设置</p>
                <p>• 导入数据将覆盖当前的对话记录和设置</p>
                <p>• 清除数据将删除所有本地存储的对话记录</p>
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