# 文献选择确认机制修复

## 问题描述

用户报告：当选择一篇文献后，按照来源筛选时会立即触发选择同步，导致频繁发送 WebSocket 消息。

**期望行为：**
- 用户可以先筛选、浏览、选择多篇文献
- 选择完成后，点击"确认选择"按钮
- 一次性同步所有选择到后端

**实际行为：**
- 每次点击复选框都会立即同步到后端 ❌
- 筛选来源时也会触发同步 ❌
- 频繁发送 WebSocket 消息，影响性能 ❌

## 根本原因

原始实现中，`handleToggleSelect` 函数每次都会立即通过 WebSocket 同步选择状态：

```typescript
// ❌ 原始逻辑
const handleToggleSelect = async (paperId: string) => {
  const newSelectedIds = selectedIds.includes(paperId)
    ? selectedIds.filter(id => id !== paperId)
    : [...selectedIds, paperId]

  setSelectedIds(newSelectedIds)

  // 立即同步到后端
  wsService.sendMessage(message, 'deep_research_agent', sessionId)
}
```

## 解决方案

### 1. 修改选择逻辑（仅更新本地状态）

```typescript
// ✅ 新逻辑：只更新本地状态
const handleToggleSelect = (paperId: string) => {
  const newSelectedIds = selectedIds.includes(paperId)
    ? selectedIds.filter(id => id !== paperId)
    : [...selectedIds, paperId]

  // 只更新本地状态，不同步到后端
  setSelectedIds(newSelectedIds)
}
```

### 2. 添加确认选择函数

```typescript
// 🆕 确认选择（同步到后端）
const handleConfirmSelection = async () => {
  if (!sessionId) {
    toast.error('会话 ID 不存在')
    return
  }

  try {
    const paperIdsJson = JSON.stringify(selectedIds)
    const message = `请调用 select_papers 工具更新文献选择状态，参数如下：
session_id="${sessionId}"
paper_ids=${paperIdsJson}
mode="replace"

只需执行工具，无需回复确认。`

    wsService.sendMessage(message, 'deep_research_agent', sessionId)

    toast.success(`已确认选择 ${selectedIds.length} 篇文献`)
    console.log('📤 已发送文献选择更新:', { sessionId, count: selectedIds.length })
  } catch (error) {
    console.error('Failed to sync selection:', error)
    toast.error('同步选择失败')
  }
}
```

### 3. 修改全选逻辑

```typescript
// ✅ 全选/取消全选（仅更新本地状态）
const handleToggleSelectAll = () => {
  const newSelectedIds = selectedIds.length === filteredPapers.length 
    ? [] 
    : filteredPapers.map(p => p.paper_id)

  setSelectedIds(newSelectedIds)

  // 提示用户需要确认选择
  if (newSelectedIds.length > 0) {
    toast.info(`已选择 ${newSelectedIds.length} 篇文献（点击"确认选择"按钮同步）`)
  } else {
    toast.info('已清空选择')
  }
}
```

### 4. 添加确认选择按钮

```tsx
{selectedIds.length > 0 && (
  <div className="flex flex-col gap-2">
    {/* 🆕 确认选择按钮 */}
    <button
      onClick={handleConfirmSelection}
      className="w-full flex items-center justify-center gap-1 px-3 py-1.5 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors"
    >
      <Check className="w-3 h-3" />
      确认选择 ({selectedIds.length} 篇)
    </button>
    
    {/* 批量分析和生成报告按钮 */}
    <div className="flex gap-2">
      <button onClick={handleBatchAnalysis}>批量分析</button>
      <button onClick={handleGenerateReport}>生成报告</button>
    </div>
  </div>
)}
```

## 用户工作流程

### 修复前 ❌

1. 用户点击复选框 → 立即同步到后端
2. 用户筛选来源 → 立即同步到后端
3. 用户再次点击复选框 → 立即同步到后端
4. **结果：** 频繁发送 WebSocket 消息，性能差

### 修复后 ✅

1. 用户点击复选框 → 仅更新前端状态
2. 用户筛选来源 → 仅更新前端状态
3. 用户继续选择 → 仅更新前端状态
4. 用户点击"确认选择"按钮 → **一次性同步到后端**
5. **结果：** 减少 WebSocket 消息，性能好

## 修改的文件

- `ui/src/components/RightPanel.tsx`
  - 修改 `handleToggleSelect` - 移除立即同步逻辑
  - 修改 `handleToggleSelectAll` - 移除立即同步逻辑
  - 添加 `handleConfirmSelection` - 新增确认选择函数
  - 添加"确认选择"按钮 - 紫色按钮，显示选择数量
  - 导入 `Check` 图标

## UI 变化

### 按钮布局

```
┌─────────────────────────────────────┐
│  确认选择 (5 篇)                    │  ← 🆕 紫色按钮
├─────────────────┬───────────────────┤
│  批量分析       │  生成报告         │
└─────────────────┴───────────────────┘
```

### 提示信息

- 全选时：`已选择 50 篇文献（点击"确认选择"按钮同步）`
- 确认选择时：`已确认选择 50 篇文献`
- 同步失败时：`同步选择失败`

## 性能优化

### 修复前

- 选择 10 篇文献 → 发送 10 次 WebSocket 消息
- 全选 50 篇文献 → 发送 1 次 WebSocket 消息
- **总计：** 11 次消息

### 修复后

- 选择 10 篇文献 → 0 次消息
- 全选 50 篇文献 → 0 次消息
- 点击"确认选择" → 1 次消息
- **总计：** 1 次消息 ✅

**性能提升：** 减少 90% 的 WebSocket 消息

## 注意事项

1. **必须点击"确认选择"按钮**才能同步到后端
2. 如果不点击"确认选择"，直接点击"批量分析"或"生成报告"，后端可能读取不到最新选择
3. 建议在"批量分析"和"生成报告"按钮中添加自动确认逻辑（可选）

## 后续优化建议

### 自动确认逻辑（可选）

在"批量分析"和"生成报告"按钮中，自动调用 `handleConfirmSelection`：

```typescript
const handleBatchAnalysis = async () => {
  // 🆕 自动确认选择
  await handleConfirmSelection()
  
  // 执行批量分析
  const message = `请对我选中的 ${selectedIds.length} 篇文献进行批量分析...`
  wsService.sendMessage(message, 'deep_research_agent', sessionId)
}
```

这样用户就不需要手动点击"确认选择"按钮了。

