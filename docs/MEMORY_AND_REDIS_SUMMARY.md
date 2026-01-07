# ResearchMind 记忆系统与 Redis 工作机制

本文汇总当前项目的会话记忆（对话历史/上下文）与 Redis 持久化实现方式，方便快速定位代码与配置。

## 1. 记忆系统（会话上下文）总体结构

- **运行时上下文**：AgentCoordinator 使用 Google ADK 的 `InMemorySessionService` 保存会话事件（events），用于当前进程内的上下文记忆。
- **持久化历史**：通过 HybridSessionManager 自动在 Redis 与文件存储间切换，保证跨重启的会话记忆。
- **上下文裁剪**：AgentCoordinator 在消息数接近上限时警告或自动截断，避免超出模型上下文限制。

关键代码：
- `services/agent_coordinator.py`
- `services/hybrid_session_manager.py`
- `services/redis_session_manager.py`
- `services/session_manager.py`

## 2. 运行时会话记忆（内存）

### 2.1 InMemorySessionService
- `AgentCoordinator` 维护 `InMemorySessionService` 实例与 `session.events`。
- `session_key` 的构造方式：`{client_id}_{agent_id}_{session_id or 'default'}`。
- 会话历史在内存中以 `events` 形式保存。

代码位置：`services/agent_coordinator.py`

### 2.2 上下文同步与恢复
- 从持久化存储加载历史：`_restore_history_from_disk()`。
- 使用 `history_key = session_id`（稳定跨设备）作为唯一加载键。
- 恢复后写回 `session.events`。

代码位置：`services/agent_coordinator.py`

### 2.3 上下文裁剪策略
- 通过消息计数做阈值控制：
  - `MAX_CONTEXT_MESSAGES = 16`
  - `CONTEXT_SUMMARY_THRESHOLD = 10`
  - `CONTEXT_AUTO_CLEAR_THRESHOLD = 12`
- 超限时调用 `_truncate_session_history()`，只保留最近消息并更新计数。

代码位置：`services/agent_coordinator.py`

## 3. 持久化记忆（Redis / 文件）

### 3.1 HybridSessionManager：自动切换
- Redis 可用时走 Redis；不可用时自动降级到本地文件。
- `save_history/load_history/create_session/...` 均支持降级。

代码位置：`services/hybrid_session_manager.py`

### 3.2 RedisSessionManager：Redis 实现细节
- 使用 `redis.ConnectionPool` + `redis.Redis`。
- 关键 Key 前缀：
  - `session:{session_id}`：会话元数据
  - `history:{session_id}`：会话历史
  - `metadata:{session_id}`：扩展元数据
  - `sessions:index`：有序集合索引（按创建时间）
- TTL 策略：
  - 会话元数据 24h
  - 会话历史 7d
- `save_history()` 会把 ADK 事件序列化为 JSON 列表存入 Redis。

代码位置：`services/redis_session_manager.py`

### 3.3 SessionManager：文件存储实现
- 使用 `data/session_data/` 作为根目录（由 `utils/paths.py` 决定）。
- 保存：
  - `metadata/{session_id}.json`（会话元数据）
  - `history/{session_id}.json`（会话历史）
  - `session_registry.json`（索引）
- `save_history()` 使用临时文件写入后替换，避免写坏文件。

代码位置：`services/session_manager.py`

## 4. Redis 配置与部署

### 4.1 环境变量
- `.env` / `.env.redis.example`
  - `REDIS_HOST`
  - `REDIS_PORT`
  - `REDIS_DB`
  - `REDIS_PASSWORD`（可选）

### 4.2 Docker 部署与默认配置
- `docker-compose.redis.yml` 使用 `redis.conf`。
- `redis.conf` 设置 AOF/RDB、`maxmemory` 与淘汰策略。

说明文档：`docs/REDIS_DEPLOYMENT.md`

## 5. 其他“记忆”相关模块（纸面检索上下文）

项目还有搜索与文献检索的上下文缓存，不属于聊天会话本身，但同样起到“记忆/缓存”作用：

### 5.1 SearchContextManager：搜索缓存
- 记录查询历史与结果缓存（文件系统）。
- 缓存结构：
  - `search_history.json` 维护索引
  - `results/` 存储具体查询结果
- 缓存过期默认 24 小时。

代码位置：`mcp_servers/paper_search/modules/context_manager/cache.py`

### 5.2 向量检索记忆（Embedding + Vector Store）
- `services.py` 按 session 或全局创建向量库（ChromaDB）。
- `vector_store.py` 提供内存向量检索实现（备用/简化场景）。

代码位置：
- `mcp_servers/paper_search/modules/context_manager/services.py`
- `mcp_servers/paper_search/modules/context_manager/vector_store.py`

## 6. 关键数据流（简化）

1) 前端消息 -> WebSocket -> AgentCoordinator
2) AgentCoordinator 读取/恢复历史（HybridSessionManager）
3) 内存 session.events 作为上下文输入给 ADK Runner
4) 会话结束/更新 -> HybridSessionManager.save_history()
5) Redis 可用时写 Redis，不可用写本地 JSON

## 7. 代码索引速查

- 会话上下文与裁剪：`services/agent_coordinator.py`
- Redis 接入层：`services/redis_session_manager.py`
- 自动降级：`services/hybrid_session_manager.py`
- 文件持久化：`services/session_manager.py`
- Redis 部署说明：`docs/REDIS_DEPLOYMENT.md`
- 搜索上下文缓存：`mcp_servers/paper_search/modules/context_manager/cache.py`
- 向量检索服务：`mcp_servers/paper_search/modules/context_manager/services.py`
