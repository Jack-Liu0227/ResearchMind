# 文献选择功能修复总结

## 修复的问题

### 问题1：Agent 提示未选择文献 ✅

**根本原因：**
- 前端直接调用 `/api/mcp/call_tool` 端点，将选择状态存储在 HTTP Server 的内存中
- MCP Server (`mcp_servers/paper_search/server.py`) 有自己独立的状态存储 `_paper_selections`
- 这两个状态是隔离的，所以 Agent 调用 MCP 工具时读取不到前端的选择

**解决方案：**
- 前端选择文献时通过 WebSocket 发送消息给 Agent
- Agent 调用 `select_papers` MCP 工具
- 状态存储在 MCP Server 的 `_paper_selections` 中
- 后续的 `batch_paper_analysis` 和 `generate_research_report` 可以正确读取选择状态

### 问题2：文献标题不可点击 ✅

**解决方案：**
- 当 `paper.url` 存在时，标题渲染为 `<a>` 标签
- 点击标题在新标签页打开论文原文链接
- 悬停时显示下划线和蓝色文字
- 如果 `paper.url` 不存在，标题显示为普通文本

### 问题3：文献数据没有持久化存储 ✅

**根本原因：**
- 文献数据（`currentPapersCsvPath`、`currentPapersCount`）存储在全局 store 中
- 但没有与 `ChatSession` 对象关联
- 刷新页面后，虽然 Zustand persist 会保存这些字段，但在恢复会话时没有恢复逻辑

**解决方案：**
- 在 `ChatSession` 接口中添加 `papersCsvPath` 和 `papersCount` 字段
- `setPapersData` 时同时保存到当前会话对象中
- 恢复会话时（`onRehydrateStorage`）自动恢复文献数据
- 切换会话时（`setCurrentSession`）自动恢复文献数据

## 修改的文件

### 1. `ui/src/types/index.ts`

#### 修改：在 ChatSession 接口中添加文献数据字段
```typescript
export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
  agentId: string
  tags?: string[]
  // 会话独立的数据
  structures?: CrystalStructure[]
  phononImages?: any[]
  files?: SessionFile[]
  // 🆕 文献数据（持久化）
  papersCsvPath?: string | null
  papersCount?: number
}
```

### 2. `ui/src/store/useAppStore.ts`

#### 修改1：setPapersData 同时保存到会话
```typescript
setPapersData: (csvPath, sessionId, count) => {
  set({
    currentPapersCsvPath: csvPath,
    currentPapersSessionId: sessionId,
    currentPapersCount: count,
  })

  // 🆕 同时保存到当前会话中（持久化）
  const { currentSession, sessions } = get()
  if (currentSession && currentSession.id === sessionId) {
    const updatedSession = {
      ...currentSession,
      papersCsvPath: csvPath,
      papersCount: count,
      updatedAt: new Date()
    }

    const updatedSessions = sessions.map(s =>
      s.id === sessionId ? updatedSession : s
    )

    set({
      currentSession: updatedSession,
      sessions: updatedSessions
    })

    console.log('💾 文献数据已保存到会话:', { sessionId, csvPath, count })
    setTimeout(() => forceSaveState(get()), 100)
  }
}
```

#### 修改2：onRehydrateStorage 恢复文献数据
```typescript
onRehydrateStorage: (state) => {
  return (state, error) => {
    // ... 恢复会话逻辑
    if (restored) {
      console.log('✅ 恢复当前会话:', restored.id)
      console.log('📚 文献数:', restored.papersCount || 0)

      state.currentSession = restored
      // ... 其他恢复逻辑

      // 🆕 恢复文献数据
      state.currentPapersCsvPath = restored.papersCsvPath || null
      state.currentPapersSessionId = restored.id
      state.currentPapersCount = restored.papersCount || 0
    }
  }
}
```

#### 修改3：setCurrentSession 切换会话时恢复文献数据
```typescript
setCurrentSession: (session) => {
  // ... 保存当前会话的文献数据
  if (currentSession) {
    const updated = {
      ...sessions[idx],
      structures: currentSessionStructures,
      phononImages: currentSessionPhononImages,
      files: currentSessionFiles,
      // 🆕 保存文献数据到会话
      papersCsvPath: currentPapersCsvPath,
      papersCount: currentPapersCount,
    }
  }

  // ... 恢复新会话的文献数据
  set({
    currentSession: latest,
    // ... 其他恢复逻辑
    // 🆕 恢复文献数据
    currentPapersCsvPath: latest.papersCsvPath || null,
    currentPapersSessionId: latest.id,
    currentPapersCount: latest.papersCount || 0,
  })

  console.log('🔄 切换会话，恢复文献数据:', {
    sessionId: latest.id,
    csvPath: latest.papersCsvPath,
    count: latest.papersCount
  })
}
```

### 3. `ui/src/components/RightPanel.tsx`

#### 修改1：导入 WebSocket 服务
```typescript
import { wsService } from '../services/websocket'
```

#### 修改2：文献选择通过 WebSocket 同步
```typescript
const handleToggleSelect = async (paperId: string) => {
  // 立即更新本地状态（乐观更新）
  setSelectedIds(newSelectedIds)

  // 通过 WebSocket 发送消息给 Agent
  const paperIdsJson = JSON.stringify(newSelectedIds)
  const message = `请调用 select_papers 工具更新文献选择状态，参数如下：
session_id="${sessionId}"
paper_ids=${paperIdsJson}
mode="replace"

只需执行工具，无需回复确认。`
  
  wsService.sendMessage(message, 'deep_research_agent', sessionId)
}
```

#### 修改3：标题可点击
```typescript
{paper.url ? (
  <a
    href={paper.url}
    target="_blank"
    rel="noopener noreferrer"
    className="flex-1 font-semibold text-sm text-gray-900 leading-snug line-clamp-2 hover:text-blue-600 hover:underline cursor-pointer transition-colors"
    title="点击打开原文链接"
  >
    {paper.title}
  </a>
) : (
  <h4 className="flex-1 font-semibold text-sm text-gray-900 leading-snug line-clamp-2">
    {paper.title}
  </h4>
)}
```

#### 修改4：批量分析和生成报告通过 WebSocket
```typescript
const handleBatchAnalysis = async () => {
  const message = `请对我选中的 ${selectedIds.length} 篇文献进行批量分析，使用 batch_paper_analysis 工具，参数：session_id="${sessionId}", use_selected_papers=true`
  wsService.sendMessage(message, 'deep_research_agent', sessionId)
  toast.success(`已发送批量分析请求（${selectedIds.length} 篇文献）`)
}

const handleGenerateReport = async () => {
  const topic = window.prompt('请输入研究主题：', '研究报告')
  if (!topic) return
  
  const message = `请基于我选中的 ${selectedIds.length} 篇文献生成研究报告，主题是"${topic}"，使用 generate_research_report 工具，参数：topic="${topic}", session_id="${sessionId}", use_selected_papers=true`
  wsService.sendMessage(message, 'deep_research_agent', sessionId)
  toast.success(`已发送报告生成请求（主题：${topic}）`)
}
```

## 完整工作流程

```
1. 用户搜索文献
   ↓
2. search_papers 工具执行，返回 CSV 路径
   ↓
3. ChatPage 自动调用 setPapersData()
   ↓
4. 用户切换到"文献"标签页
   ↓
5. 自动加载文献列表（调用 /api/mcp/call_tool - list_papers_from_csv）
   ↓
6. 显示美化的文献卡片
   ↓
7. 用户选择文献
   ↓
8. 前端通过 WebSocket 发送消息给 Agent
   ↓
9. Agent 调用 select_papers 工具
   ↓
10. 选择状态存储在 MCP Server 的 _paper_selections 中
   ↓
11. 用户点击"批量分析"或"生成报告"
   ↓
12. 前端通过 WebSocket 发送消息给 Agent
   ↓
13. Agent 调用 batch_paper_analysis 或 generate_research_report 工具
   ↓
14. 工具从 _paper_selections 读取选择状态（use_selected_papers=true）
   ↓
15. 只处理选中的文献
   ↓
16. 返回结果给用户
```

## 关键点

1. **状态同步**：所有文献选择操作都通过 WebSocket → Agent → MCP 工具的路径
2. **乐观更新**：前端立即更新 UI，不等待后端确认
3. **静默执行**：选择操作不需要 Agent 回复，避免打扰用户
4. **会话隔离**：所有操作都使用相同的 `session_id`
5. **可点击标题**：提升用户体验，快速访问原文

## 测试建议

1. **测试文献选择同步**：
   - 选择几篇文献
   - 检查浏览器控制台是否有"📤 已发送文献选择更新"日志
   - 点击"批量分析"，验证 Agent 是否能正确读取选择

2. **测试标题点击**：
   - 点击文献标题，验证是否在新标签页打开
   - 悬停时是否显示下划线和蓝色文字

3. **测试批量操作**：
   - 选择文献 → 批量分析 → 验证只分析选中的文献
   - 选择文献 → 生成报告 → 验证只使用选中的文献

## 注意事项

1. **不需要重启后端**：所有修改都在前端，不需要重启后端服务
2. **Agent 响应**：Agent 可能会回复"已执行 select_papers 工具"，这是正常的
3. **错误处理**：如果选择同步失败，不会显示错误提示，避免打扰用户

