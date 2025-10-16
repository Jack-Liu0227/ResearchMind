import React, { useState } from 'react'
import { ChevronDown, Bot, Zap, Database, BookOpen, Cpu } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { Agent } from '../types'

const agentIcons = {
  coordinator: Zap,
  literature: BookOpen,
  database: Database,
  simulation: Cpu,
}

const AgentSelector: React.FC = () => {
  const { agents, currentAgent, setCurrentAgent } = useAppStore()
  const [isOpen, setIsOpen] = useState(false)

  const handleSelectAgent = (agent: Agent) => {
    setCurrentAgent(agent)
    setIsOpen(false)
  }

  const getAgentIcon = (type: Agent['type']) => {
    const IconComponent = agentIcons[type] || Bot
    return IconComponent
  }

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'active':
        return 'text-green-500'
      case 'busy':
        return 'text-yellow-500'
      case 'inactive':
        return 'text-gray-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusText = (status: Agent['status']) => {
    switch (status) {
      case 'active':
        return '可用'
      case 'busy':
        return '忙碌'
      case 'inactive':
        return '离线'
      default:
        return '未知'
    }
  }

  return (
    <div className="p-4">
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center space-x-3">
            {currentAgent ? (
              <>
                {React.createElement(getAgentIcon(currentAgent.type), {
                  className: "w-5 h-5 text-primary-600"
                })}
                <div className="text-left">
                  <div className="font-medium text-gray-900">
                    {currentAgent.name}
                  </div>
                  <div className="text-sm text-gray-500">
                    {currentAgent.description}
                  </div>
                </div>
              </>
            ) : (
              <>
                <Bot className="w-5 h-5 text-gray-400" />
                <div className="text-left">
                  <div className="font-medium text-gray-500">
                    选择智能体
                  </div>
                  <div className="text-sm text-gray-400">
                    请选择一个智能体开始对话
                  </div>
                </div>
              </>
            )}
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* 下拉菜单 */}
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
            <div className="p-2">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide px-3 py-2">
                可用智能体
              </div>
              {agents.map((agent) => {
                const IconComponent = getAgentIcon(agent.type)
                return (
                  <button
                    key={agent.id}
                    onClick={() => handleSelectAgent(agent)}
                    className={`w-full flex items-center space-x-3 p-3 rounded-lg text-left hover:bg-gray-50 transition-colors ${
                      currentAgent?.id === agent.id ? 'bg-primary-50 border border-primary-200' : ''
                    }`}
                  >
                    <IconComponent className="w-5 h-5 text-primary-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-gray-900 truncate">
                          {agent.name}
                        </div>
                        <div className={`text-xs ${getStatusColor(agent.status)}`}>
                          {getStatusText(agent.status)}
                        </div>
                      </div>
                      <div className="text-sm text-gray-500 truncate">
                        {agent.description}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {agent.capabilities?.slice(0, 3).map((capability, index) => (
                          <span
                            key={index}
                            className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                          >
                            {capability}
                          </span>
                        ))}
                        {agent.capabilities && agent.capabilities.length > 3 && (
                          <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                            +{agent.capabilities.length - 3}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* 当前智能体能力展示 */}
      {currentAgent && currentAgent.capabilities && currentAgent.capabilities.length > 0 && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 mb-2">
            智能体能力
          </div>
          <div className="flex flex-wrap gap-2">
            {currentAgent.capabilities.map((capability, index) => (
              <span
                key={index}
                className="inline-block px-2 py-1 text-xs bg-primary-100 text-primary-700 rounded-full"
              >
                {capability}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AgentSelector