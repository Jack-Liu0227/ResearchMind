# 后端集成指南：进度追踪功能

## 🎯 目标

为 `batch_paper_analysis()` 和 `generate_research_report()` 函数添加实时进度追踪功能。

---

## 📦 准备工作

### 1. 导入 ProgressTracker

```python
from mcp_servers.paper_search.modules.shared.progress_tracker import ProgressTracker
```

### 2. 准备 WebSocket 发送函数

假设你已经有 WebSocket 管理器，创建一个辅助函数：

```python
async def send_progress_to_frontend(progress_data: dict, session_id: str):
    """发送进度更新到前端"""
    await websocket_manager.send_to_session(session_id, {
        "type": "analysis_progress",
        "data": progress_data
    })
```

---

## 🔧 集成步骤

### Step 1: 修改 `batch_paper_analysis()` 函数签名

**文件**: `mcp_servers/paper_search/modules/paper_manager/analysis.py`

**修改前**:
```python
async def batch_paper_analysis(
    csv_file_path: str,
    paper_ids: List[str] = None,
    session_id: str = None
) -> Dict[str, Any]:
```

**修改后**:
```python
async def batch_paper_analysis(
    csv_file_path: str,
    paper_ids: List[str] = None,
    session_id: str = None,
    progress_callback: Optional[Callable[[dict], Any]] = None  # 🆕 新增
) -> Dict[str, Any]:
```

---

### Step 2: 创建进度追踪器

在函数开始处，创建 ProgressTracker 实例：

```python
async def batch_paper_analysis(...):
    # ... 现有的参数验证和数据加载代码 ...
    
    # 🆕 创建进度追踪器
    tracker = ProgressTracker(
        total=len(papers_to_analyze),
        callback=progress_callback,
        operation_name="批量论文分析"
    )
    
    # ... 继续现有逻辑 ...
```

---

### Step 3: 在循环中更新进度

找到分析论文的循环，在每次迭代后更新进度：

**修改前**:
```python
for i, paper in enumerate(papers_to_analyze):
    try:
        result = await analyze_paper_content(
            paper_id=paper['id'],
            title=paper.get('title', ''),
            abstract=paper.get('abstract', ''),
            authors=paper.get('authors', ''),
            year=paper.get('year', '')
        )
        analysis_results.append(result)
    except Exception as e:
        logger.error(f"分析论文 {paper['id']} 失败: {e}")
        failed_papers.append(paper['id'])
```

**修改后**:
```python
for i, paper in enumerate(papers_to_analyze):
    try:
        # 🆕 更新进度 - 开始分析
        await tracker.update(
            current=i,
            message=f"正在分析第 {i+1}/{len(papers_to_analyze)} 篇论文: {paper.get('title', 'Unknown')[:50]}..."
        )
        
        result = await analyze_paper_content(
            paper_id=paper['id'],
            title=paper.get('title', ''),
            abstract=paper.get('abstract', ''),
            authors=paper.get('authors', ''),
            year=paper.get('year', '')
        )
        analysis_results.append(result)
        
        # 🆕 更新进度 - 完成一篇
        await tracker.update(
            current=i+1,
            message=f"已完成 {i+1}/{len(papers_to_analyze)} 篇论文分析"
        )
        
    except Exception as e:
        logger.error(f"分析论文 {paper['id']} 失败: {e}")
        failed_papers.append(paper['id'])
        
        # 🆕 报告错误（但继续处理）
        await tracker.error(
            error_message=f"论文 {paper['id']} 分析失败",
            details=str(e)
        )
```

---

### Step 4: 标记完成

在函数返回前，标记为完成：

```python
    # ... 所有分析完成后 ...
    
    # 🆕 标记完成
    success_count = len(analysis_results)
    error_count = len(failed_papers)
    await tracker.complete(
        message=f"批量分析已完成！成功: {success_count} 篇，失败: {error_count} 篇"
    )
    
    # 🆕 发送完成消息到前端
    if progress_callback:
        await progress_callback({
            "type": "analysis_complete",
            "data": {
                "message": f"批量分析已完成！",
                "success_count": success_count,
                "error_count": error_count,
                "failed_papers": failed_papers
            }
        })
    
    return {
        "success": True,
        "total_analyzed": success_count,
        "failed_count": error_count,
        "failed_papers": failed_papers,
        "analysis_results": analysis_results
    }
```

---

### Step 5: 在调用处传递回调函数

在 MCP 工具或 API 端点中调用时，传递回调函数：

```python
# 在 MCP 工具中
async def handle_batch_analysis_tool(csv_file_path, paper_ids, session_id):
    # 创建进度回调函数
    async def progress_callback(progress_data):
        await send_progress_to_frontend(progress_data, session_id)
    
    # 调用批量分析函数
    result = await batch_paper_analysis(
        csv_file_path=csv_file_path,
        paper_ids=paper_ids,
        session_id=session_id,
        progress_callback=progress_callback  # 🆕 传递回调
    )
    
    return result
```

---

## 🔄 同样的步骤应用到 `generate_research_report()`

### 修改函数签名

```python
async def generate_research_report(
    csv_file_path: str,
    paper_ids: List[str] = None,
    session_id: str = None,
    topic: str = "综合研究报告",
    progress_callback: Optional[Callable[[dict], Any]] = None  # 🆕 新增
) -> Dict[str, Any]:
```

### 创建进度追踪器

```python
# 总步骤 = 论文分析数 + 1 个综合步骤
tracker = ProgressTracker(
    total=len(papers) + 1,
    callback=progress_callback,
    operation_name="研究报告生成"
)
```

### 更新进度

```python
# 分析阶段
for i, paper in enumerate(papers):
    await tracker.update(
        current=i,
        message=f"正在分析第 {i+1}/{len(papers)} 篇论文..."
    )
    # ... 分析逻辑 ...

# 综合阶段
await tracker.update(
    current=len(papers),
    message="正在综合研究报告..."
)
# ... 综合逻辑 ...

# 完成
await tracker.complete(message="研究报告生成完成！")
```

---

## 🧪 测试

### 1. 单元测试

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_batch_analysis_with_progress():
    # 创建模拟回调
    progress_callback = AsyncMock()
    
    # 调用函数
    result = await batch_paper_analysis(
        csv_file_path="test.csv",
        paper_ids=["1", "2", "3"],
        session_id="test_session",
        progress_callback=progress_callback
    )
    
    # 验证回调被调用
    assert progress_callback.call_count > 0
    
    # 验证进度数据格式
    call_args = progress_callback.call_args_list[0][0][0]
    assert "current" in call_args
    assert "total" in call_args
    assert "progress" in call_args
    assert "message" in call_args
```

### 2. 集成测试

使用真实的 WebSocket 连接测试完整流程：

```python
@pytest.mark.asyncio
async def test_batch_analysis_end_to_end():
    # 连接 WebSocket
    async with websocket_client.connect() as ws:
        # 发送批量分析请求
        await ws.send_json({
            "type": "batch_analysis",
            "data": {
                "csv_file_path": "test.csv",
                "paper_ids": ["1", "2", "3"],
                "session_id": "test_session"
            }
        })
        
        # 接收进度更新
        progress_messages = []
        async for message in ws:
            if message["type"] == "analysis_progress":
                progress_messages.append(message)
            elif message["type"] == "analysis_complete":
                break
        
        # 验证收到进度更新
        assert len(progress_messages) >= 3  # 至少每篇论文一个更新
```

---

## 📝 注意事项

1. **错误处理**: 即使某篇论文分析失败，也要继续处理其他论文，并更新进度
2. **性能**: 不要在每个小步骤都发送进度更新，建议每篇论文发送一次
3. **取消操作**: 可以在循环中调用 `await tracker.check_cancelled()` 来支持取消
4. **并发控制**: 如果使用并发处理，确保进度更新是线程安全的

---

## ✅ 完成检查清单

- [ ] 修改 `batch_paper_analysis()` 函数签名
- [ ] 创建 ProgressTracker 实例
- [ ] 在循环中更新进度
- [ ] 标记完成并发送完成消息
- [ ] 修改 `generate_research_report()` 函数
- [ ] 在 MCP 工具中传递回调函数
- [ ] 编写单元测试
- [ ] 进行集成测试
- [ ] 更新 API 文档

---

## 🔗 相关文件

- `mcp_servers/paper_search/modules/shared/progress_tracker.py` - 进度追踪器类
- `mcp_servers/paper_search/modules/paper_manager/analysis.py` - 批量分析函数
- `mcp_servers/paper_search/modules/report_generator/reporting.py` - 报告生成函数


