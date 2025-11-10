# 计费数据获取机制重构 - WebSocket 实时推送

## 📋 重构概述

将所有基于 HTTP API 的计费查询改为通过 WebSocket 实时推送，实现统一数据源、提高一致性、减少冲突。

## ✅ 已完成的工作

### 1. 后端修改

#### `services/message_handler.py`
- ✅ 添加了 3 个新的 WebSocket 消息处理器：
  - `handle_get_conversation_stats` - 获取会话计费统计
  - `handle_get_user_stats` - 获取用户计费统计
  - `handle_get_global_stats` - 获取全局计费统计

**关键代码**：
```python
async def handle_get_conversation_stats(self, client_id, websocket, data, agent_coordinator):
    """通过 WebSocket 获取会话计费统计"""
    conversation_id = data.get("conversationId") or data.get("sessionId")
    context = context_manager.get_context(conversation_id)
    
    if not context:
        await self.send_message(websocket, "conversation_stats", {
            "success": False,
            "message": f"对话 {conversation_id} 不存在",
            "data": None
        })
        return
    
    snapshot = context.get_snapshot()
    await self.send_message(websocket, "conversation_stats", {
        "success": True,
        "message": "获取成功",
        "data": snapshot
    })
```

### 2. 前端 WebSocket 服务扩展

#### `ui/src/services/websocket.ts`
- ✅ 添加了 3 个新方法：
  - `requestConversationStats(conversationId)` - 请求会话统计
  - `requestUserStats(userId)` - 请求用户统计
  - `requestGlobalStats()` - 请求全局统计

**关键代码**：
```typescript
requestConversationStats(conversationId: string): void {
  if (this.ws && this.ws.readyState === WebSocket.OPEN) {
    const message = {
      type: 'get_conversation_stats',
      conversationId,
      timestamp: new Date().toISOString(),
    }
    this.ws.send(JSON.stringify(message))
  }
}
```

### 3. 前端 Store 扩展

#### `ui/src/store/useAppStore.ts`
- ✅ 添加了新的接口：
  - `UserBillingStats` - 用户计费统计
  - `GlobalBillingStats` - 全局计费统计
- ✅ 添加了新的状态：
  - `userBillingStats: UserBillingStats | null`
  - `globalBillingStats: GlobalBillingStats | null`
- ✅ 添加了新的 setter：
  - `setUserBillingStats(data)`
  - `setGlobalBillingStats(data)`

### 4. BillingStatsPanel 重构

#### `ui/src/components/BillingStatsPanel.tsx`
- ✅ 移除了对 HTTP API 的依赖（`getConversationBillingStats`, `getUserBillingStats`, `getGlobalBillingStats`）
- ✅ 改为通过 WebSocket 请求数据
- ✅ 从 store 读取数据（`userBillingStats`, `globalBillingStats`）
- ✅ 监听 `billingData` 更新并同步到 `conversationStats`

**关键变化**：
```typescript
// 旧代码（HTTP API）
const gStats = await getGlobalBillingStats()
setGlobalStats(gStats)

// 新代码（WebSocket）
wsService.requestGlobalStats()
// 数据通过 WebSocket 消息推送到 store
const { globalBillingStats } = useAppStore()
```

### 5. ChatPage 消息监听

#### `ui/src/pages/ChatPage.tsx`
- ✅ 添加了 3 个新的消息类型处理：
  - `conversation_stats` - 会话统计响应
  - `user_stats` - 用户统计响应
  - `global_stats` - 全局统计响应
- ✅ 将接收到的数据更新到 store

**关键代码**：
```typescript
else if (message.type === 'user_stats' && message.data) {
  console.log('📊 [计费统计] 收到用户统计:', message.data)
  if (message.data.success && message.data.data) {
    setUserBillingStats(message.data.data)
  }
}
```

## 📊 数据流

### 旧架构（HTTP API）
```
BillingStatsPanel
  ↓ HTTP GET
/api/billing/stats/conversation/{id}
  ↓ 返回 JSON
BillingStatsPanel (setState)
```

### 新架构（WebSocket）
```
BillingStatsPanel
  ↓ WebSocket 请求
wsService.requestConversationStats(id)
  ↓ WebSocket 消息
后端 handle_get_conversation_stats
  ↓ WebSocket 响应
ChatPage (监听消息)
  ↓ 更新 store
useAppStore.setUserBillingStats(data)
  ↓ 自动更新
BillingStatsPanel (从 store 读取)
```

## 🎯 预期收益

- ✅ **数据一致性**：单一数据源（WebSocket），无缓存不一致问题
- ✅ **实时性**：计费数据实时更新，无需轮询
- ✅ **性能**：减少 HTTP 请求，降低服务器负载
- ✅ **可靠性**：WebSocket 连接状态可监控，断线重连机制已有

## 🔧 向后兼容

- ✅ HTTP API 端点保留（`/api/billing/stats/*`），可作为备用
- ✅ 前端优先使用 WebSocket，HTTP API 可用于调试或降级

## 🐛 修复的问题

1. **JSX 语法错误**：
   - 移除了未使用的条件渲染代码块（`{false && (...)`）
   - 清理了对旧数据结构的引用（`userStats.conversations`）
   - 移除了未使用的 setter（`setUserBillingStats`, `setGlobalBillingStats` 在 BillingStatsPanel 中）

2. **数据结构对齐**：
   - 用户统计：`total_conversations` → `conversation_count`
   - 全局统计：`total_requests` → `request_count`，`total_sessions` → `conversation_count`
   - 移除了不存在的字段（`billing_config`, `start_time`, `current_time`）

## 📝 测试建议

1. **功能测试**：
   - 打开 BillingStatsPanel，验证数据正确显示
   - 发送消息后，验证计费数据实时更新
   - 切换标签页（会话/用户/全局），验证数据正确

2. **性能测试**：
   - 监控 WebSocket 消息大小和频率
   - 验证无重复请求
   - 验证 loading 状态正确

3. **错误处理**：
   - 断开 WebSocket 连接，验证降级行为
   - 请求不存在的会话，验证错误提示
   - 网络延迟时，验证超时处理

## 🚀 后续优化

1. **缓存优化**：在前端添加短期缓存，避免频繁请求
2. **批量请求**：合并多个统计请求为一个 WebSocket 消息
3. **增量更新**：只推送变化的数据，减少传输量
4. **离线支持**：WebSocket 断开时，回退到 HTTP API

## 📚 相关文件

### 后端
- `services/message_handler.py` - WebSocket 消息处理器
- `services/user_billing_config.py` - 计费上下文管理
- `services/billing_api.py` - HTTP API（保留作为备用）

### 前端
- `ui/src/services/websocket.ts` - WebSocket 服务
- `ui/src/store/useAppStore.ts` - 全局状态管理
- `ui/src/components/BillingStatsPanel.tsx` - 计费统计面板
- `ui/src/pages/ChatPage.tsx` - 主页面（消息监听）

