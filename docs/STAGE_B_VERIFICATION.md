# 阶段 B 验证步骤：Markdown 报告生成优化

## 概述

本文档提供完整的验证流程，确保 Markdown 报告生成优化功能正常工作。

## 前置条件

1. 已完成阶段 A 和阶段 B 的所有代码修改
2. 已安装所有依赖（`uv sync`）
3. 已配置 `.env` 文件

## 验证步骤

### 步骤 1：运行单元测试

```bash
# 进入项目根目录
cd /path/to/ResearchMind

# 运行引用格式化测试
python tests/test_citation_formatting.py
```

**预期输出：**
```
开始测试引用格式化功能...

============================================================
测试 1: 引用标记转换为 Markdown 锚点链接
============================================================

输入: 单个引用：^[1]^
预期: 单个引用：[1](#ref-1)
实际: 单个引用：[1](#ref-1)
状态: ✅ 通过

输入: 范围引用：^[1-3]^
预期: 范围引用：[1](#ref-1), [2](#ref-2), [3](#ref-3)
实际: 范围引用：[1](#ref-1), [2](#ref-2), [3](#ref-3)
状态: ✅ 通过

...

============================================================
测试总结
============================================================
测试 1 (引用标记转换): ✅ 通过
测试 2 (参考文献锚点): ✅ 通过

🎉 所有测试通过！
```

### 步骤 2：验证环境变量配置

```bash
# 测试内容截断上限
export REPORT_CONTENT_MAX_LENGTH=15000
export LLM_ANALYSIS_MAX_TOKENS=3000
export LLM_SYNTHESIS_MAX_TOKENS=10000

# 启动服务
bash start_linux.sh

# 查看日志确认配置生效
tail -f logs/mcp_paper_search.log | grep -i "max"
```

**预期日志输出：**
```
Analyzing paper 1 using 全文 (15000 chars, max=15000)
LLM analysis max_tokens: 3000
LLM synthesis max_tokens: 10000
```

### 步骤 3：生成测试报告

```bash
# 使用 API 生成报告
curl -X POST http://localhost:8000/api/paper-search/generate-report \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "topic": "quantum computing",
    "paper_ids": ["arxiv:2401.00001", "arxiv:2401.00002"]
  }'
```

**预期返回：**
```json
{
  "status": "success",
  "report_path": "/api/download/papers/test_session_123/research_report.md",
  "message": "Report generated successfully"
}
```

### 步骤 4：验证报告内容

```bash
# 下载生成的报告
curl http://localhost:8000/api/download/papers/test_session_123/research_report.md -o test_report.md

# 检查引用格式
cat test_report.md | grep -E '\[([0-9]+)\]\(#ref-[0-9]+\)'
```

**预期输出：**
```
量子计算的发展[1](#ref-1)表明...
近年来的研究[2](#ref-2), [3](#ref-3)显示...
```

### 步骤 5：验证参考文献列表

```bash
# 检查参考文献锚点
cat test_report.md | grep -E '<a id="ref-[0-9]+"></a>'
```

**预期输出：**
```
<a id="ref-1"></a>[1] Author A, Author B. Test Paper 1[EB/OL]. (2024)[2024-12-04]. [https://arxiv.org/abs/2401.00001](https://arxiv.org/abs/2401.00001).

<a id="ref-2"></a>[2] Author C, Author D. Test Paper 2[J/OL]. Nature, 2023, 600(1): 1-10. DOI: [10.1038/s41586-023-00001-0](https://doi.org/10.1038/s41586-023-00001-0).
```

### 步骤 6：在 Markdown 渲染器中验证

```bash
# 使用 Markdown 预览工具（如 VS Code、Typora）打开报告
code test_report.md

# 或使用在线 Markdown 编辑器
# 将 test_report.md 内容复制到 https://dillinger.io/
```

**验证要点：**
- [ ] 点击正文中的引用编号 `[1]` 能跳转到参考文献列表的对应条目
- [ ] 参考文献列表中的 URL 可以点击访问
- [ ] DOI 链接可以点击并跳转到 https://doi.org/
- [ ] 引用编号格式正确（不是上标，而是普通链接）

### 步骤 7：验证内容完整性

```bash
# 检查报告长度
wc -l test_report.md
wc -c test_report.md
```

**预期结果：**
- 报告行数 > 100 行（包含详细分析）
- 报告大小 > 10KB（内容未被过度截断）

## 常见问题排查

### 问题 1：引用标记未转换

**症状：**
报告中仍然显示 `^[1]^` 而不是 `[1](#ref-1)`

**排查步骤：**
1. 检查 `citation_manager.py` 中的 `process_citations` 函数
2. 确认 `use_anchor_links=True` 参数传递正确
3. 查看日志：
   ```bash
   tail -f logs/mcp_paper_search.log | grep -i "citation"
   ```

### 问题 2：锚点跳转不工作

**症状：**
点击引用编号无法跳转到参考文献

**解决方案：**
1. 确认参考文献列表包含 `<a id="ref-n"></a>` 锚点
2. 检查 Markdown 渲染器是否支持 HTML 锚点
3. 使用支持 HTML 的 Markdown 渲染器（如 GitHub、VS Code）

### 问题 3：URL 不可点击

**症状：**
参考文献中的 URL 显示为纯文本

**解决方案：**
确认 URL 格式为 `[url](url)` 而不是纯文本 `url`

## 验收标准

- [ ] 单元测试全部通过
- [ ] 环境变量配置生效
- [ ] 生成的报告包含可点击的引用链接
- [ ] 参考文献列表包含 HTML 锚点
- [ ] 所有 URL 和 DOI 可点击
- [ ] 报告内容完整，未被过度截断
- [ ] 在 Markdown 渲染器中引用跳转正常工作

## 配置参数说明

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `REPORT_CONTENT_MAX_LENGTH` | 12000 | 论文内容截断上限（字符数） |
| `LLM_ANALYSIS_MAX_TOKENS` | 2500 | 分析阶段 LLM 最大 token 数 |
| `LLM_SYNTHESIS_MAX_TOKENS` | 8000 | 综合阶段 LLM 最大 token 数 |

## 下一步

完成阶段 B 验证后，继续进行阶段 C：多 Agent 架构统一。

