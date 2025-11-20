# 文献数据持久化修复

## 问题描述

**现象：** 刷新页面后，右侧边栏的"文献"标签页显示的文献数据丢失

**原因：** 文献数据（`currentPapersCsvPath`、`currentPapersCount`）存储在全局 store 中，但没有与 `ChatSession` 对象关联，导致恢复会话时无法恢复文献数据

## 解决方案

### 1. 数据模型修改

在 `ChatSession` 接口中添加文献数据字段：

```typescript
// ui/src/types/index.ts
export interface ChatSession {
  // ... 其他字段
  papersCsvPath?: string | null    // 文献 CSV 文件路径
  papersCount?: number              // 文献总数
}
```

### 2. 保存逻辑修改

**修改 `setPapersData`：** 同时保存到全局 store 和当前会话对象

```typescript
// ui/src/store/useAppStore.ts
setPapersData: (csvPath, sessionId, count) => {
  // 1. 更新全局状态
  set({
    currentPapersCsvPath: csvPath,
    currentPapersSessionId: sessionId,
    currentPapersCount: count,
  })

  // 2. 保存到当前会话对象（持久化）
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
    
    // 3. 强制保存到 localStorage
    setTimeout(() => forceSaveState(get()), 100)
  }
}
```

### 3. 恢复逻辑修改

**修改 `onRehydrateStorage`：** 恢复会话时同时恢复文献数据

```typescript
onRehydrateStorage: (state) => {
  return (state, error) => {
    // ... 恢复会话逻辑
    if (restored) {
      // 恢复文献数据
      state.currentPapersCsvPath = restored.papersCsvPath || null
      state.currentPapersSessionId = restored.id
      state.currentPapersCount = restored.papersCount || 0
    }
  }
}
```

**修改 `setCurrentSession`：** 切换会话时恢复文献数据

```typescript
setCurrentSession: (session) => {
  // 1. 保存当前会话的文献数据
  if (currentSession) {
    const updated = {
      ...sessions[idx],
      papersCsvPath: currentPapersCsvPath,
      papersCount: currentPapersCount,
    }
  }
  
  // 2. 恢复新会话的文献数据
  set({
    currentSession: latest,
    currentPapersCsvPath: latest.papersCsvPath || null,
    currentPapersSessionId: latest.id,
    currentPapersCount: latest.papersCount || 0,
  })
}
```

## 数据流

```
1. 用户搜索文献 → search_papers 工具执行
2. ChatPage 调用 setPapersData(csvPath, sessionId, count)
3. 数据保存到：
   - 全局 store（currentPapersCsvPath, currentPapersCount）
   - 当前会话对象（session.papersCsvPath, session.papersCount）
   - localStorage（通过 Zustand persist）
4. 刷新页面 → onRehydrateStorage 触发
5. 恢复会话 → 同时恢复文献数据
6. 切换会话 → 自动恢复对应会话的文献数据
```

## 修改的文件

1. ✅ `ui/src/types/index.ts` - 添加 `papersCsvPath` 和 `papersCount` 字段
2. ✅ `ui/src/store/useAppStore.ts` - 修改保存和恢复逻辑

## 测试步骤

1. **测试保存：**
   - 搜索文献
   - 切换到"文献"标签页，验证文献列表显示
   - 刷新页面
   - 验证文献列表仍然显示（数据已持久化）

2. **测试切换会话：**
   - 在会话 A 中搜索文献
   - 创建新会话 B
   - 切换回会话 A
   - 验证文献列表仍然显示

3. **测试多会话隔离：**
   - 在会话 A 中搜索文献（主题：材料科学）
   - 在会话 B 中搜索文献（主题：量子计算）
   - 切换会话，验证文献列表正确对应

## 关键点

1. **双重存储**：全局 store + 会话对象
2. **自动保存**：`setPapersData` 时自动保存到会话
3. **自动恢复**：恢复/切换会话时自动恢复文献数据
4. **会话隔离**：每个会话有独立的文献数据
5. **持久化**：通过 Zustand persist 自动保存到 localStorage

## 与其他数据的一致性

文献数据的持久化逻辑与其他会话数据（结构、文件、图片）保持一致：

- ✅ `structures` - 晶体结构列表
- ✅ `phononImages` - 声子谱图片列表
- ✅ `files` - 会话文件列表
- ✅ `papersCsvPath` + `papersCount` - 文献数据（新增）

