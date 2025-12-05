# ResearchMind 快速修复指南

## 问题 1：导入错误 ✅ 已修复

### 症状
```
Error: attempted relative import beyond top-level package
```

### 解决方案
已修复所有三级相对导入，改为绝对导入。

### 验证
```bash
python scripts/test_imports.py
```

预期输出：`✅ 所有导入测试通过！`

---

## 问题 2：进度更新失败 ⚠️ 需要手动修复

### 症状
- 前端进度条一直转圈
- 后端日志显示：`'gbk' codec can't encode character '\u2705'`

### 原因
日志中使用了 emoji 字符，Windows GBK 编码无法处理。

### 解决方案（二选一）

#### 方案 A：自动修复（推荐）
```bash
python scripts/fix_emoji_in_logs.py
```

#### 方案 B：手动配置 UTF-8
在 `main.py` 或日志配置文件中添加：
```python
import logging
logging.basicConfig(
    encoding='utf-8',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 验证
1. 重启服务：`uv run python main.py`
2. 执行批量分析
3. 观察前端进度条是否正常更新
4. 检查日志是否还有编码错误

---

## 问题 3：报告生成质量 ✅ 应该已修复

### 症状
- 综合分析显示"生成失败"
- 参考文献格式不完整

### 原因
由于问题 1 的导入错误，LLM 综合分析功能失败。

### 解决方案
问题 1 修复后，此问题应该自动解决。

### 验证
1. 重新生成报告
2. 检查是否有综合分析内容
3. 查看参考文献格式是否正确

---

## 完整修复流程

### 步骤 1：验证导入修复
```bash
python scripts/test_imports.py
```

### 步骤 2：修复日志编码（可选）
```bash
python scripts/fix_emoji_in_logs.py
```

### 步骤 3：重启服务
```bash
# 停止当前服务（Ctrl+C）
# 重新启动
uv run python main.py
```

### 步骤 4：测试功能
1. 打开前端界面
2. 选择 3 篇论文
3. 执行"批量分析"
4. 观察进度条是否正常
5. 执行"生成报告"
6. 检查报告质量

---

## 故障排查

### 如果导入测试失败
```bash
# 检查 Python 版本
python --version  # 应该是 3.11+

# 检查依赖
uv pip list | grep structlog
uv pip list | grep litellm
```

### 如果进度更新仍然失败
```bash
# 查看实时日志
tail -f logs/backend.log

# 搜索编码错误
grep "codec" logs/backend.log
grep "encode" logs/backend.log
```

### 如果报告生成仍然失败
```bash
# 查看 paper_search 日志
tail -f logs/paper_search.log

# 搜索错误
grep "ERROR" logs/paper_search.log
grep "synthesis failed" logs/paper_search.log
```

---

## 联系支持

如果以上步骤无法解决问题，请提供：
1. 错误日志（`logs/backend.log` 和 `logs/paper_search.log`）
2. 操作步骤
3. 系统环境（OS、Python 版本）

