# Semantic Scholar API 集成文档

## 概述

本文档说明如何在 ResearchMind 中配置和使用 Semantic Scholar API Key，以提高 API 请求限额并获取完整的期刊信息。

## 配置状态

### ✅ 已完成的配置

1. **根目录 `.env` 文件**（后端配置）
   ```env
   SEMANTIC_SCHOLAR_API_KEY=56kY8t3oc7ag85oXUQ9EVM1r2P1sPS39JAlBGdre
   ```

2. **前端 `ui/.env` 文件**（前端配置）
   ```env
   VITE_SEMANTIC_SCHOLAR_API_KEY=56kY8t3oc7ag85oXUQ9EVM1r2P1sPS39JAlBGdre
   ```

3. **后端代码**（`mcp_servers/paper_search/modules/search/semantic_scholar.py`）
   - 第 51 行：从环境变量读取 API Key
   - 第 70-71 行：如果配置了 API Key，添加到请求头 `x-api-key`

4. **前端代码**（`ui/src/services/easyScholarService.ts`）
   - 第 12 行：从环境变量读取 API Key
   - 第 204-206 行：如果配置了 API Key，添加到请求头 `x-api-key`

## API 使用说明

### Semantic Scholar API Key 的作用

- **未认证访问**：每 5 分钟 100 次请求
- **认证访问**：每 5 分钟 5000 次请求（使用 API Key）

### API 调用流程

1. **后端搜索论文**
   - 用户在前端搜索论文
   - 后端调用 Semantic Scholar API 搜索论文
   - 使用 API Key 提高请求限额

2. **前端获取期刊信息**
   - 用户展开文献详情
   - 前端检测到 Semantic Scholar 来源的文献
   - 调用 `getDOIFromSemanticScholar()` 获取 DOI
   - 使用 API Key 提高请求限额
   - 调用 CrossRef API 获取期刊名称
   - 调用 EasyScholar API 获取期刊信息（IF、JCR 分区等）

## 完整的期刊信息获取流程

```
用户展开文献详情
    ↓
检测文献来源（Semantic Scholar）
    ↓
调用 Semantic Scholar API 获取 DOI
    ↓
调用 CrossRef API 获取期刊名称
    ↓
调用 EasyScholar API 获取期刊信息
    ↓
显示完整的期刊信息：
  - 期刊名称
  - 影响因子（IF）
  - JCR 分区（Q1/Q2/Q3/Q4）
  - 中科院分区（1区/2区/3区/4区）
  - Top 期刊标识
```

## 测试步骤

### 1. 重启服务

修改环境变量后，需要重启前端和后端服务：

```bash
# 停止所有服务
# 按 Ctrl+C 停止当前运行的服务

# 重新启动
./start.sh
```

### 2. 测试后端 API

在浏览器中访问：
```
http://localhost:50001
```

### 3. 测试期刊信息获取

1. 在搜索框中输入关键词，例如：`machine learning`
2. 选择 Semantic Scholar 作为数据源
3. 点击搜索
4. 展开任意一篇文献的详情
5. 查看浏览器控制台日志，确认以下信息：
   - `🔑 [Semantic Scholar] 使用 API Key 认证`
   - `✅ [Semantic Scholar] 获取 DOI 成功`
   - `✅ [DOI] 从 DOI 获取期刊名称成功`
   - `✅ [EasyScholar] 解析后的期刊信息`

### 4. 验证期刊信息显示

在文献详情中，应该能看到：
- 📚 期刊名称
- 📊 影响因子（IF）
- 🏆 JCR 分区（Q1/Q2/Q3/Q4）
- 🎯 中科院分区（1区/2区/3区/4区）
- ⭐ Top 期刊标识（如果是 Top 期刊）

## 故障排查

### 问题 1：API Key 未生效

**症状**：控制台显示 `⚠️ [Semantic Scholar] 未配置 API Key，使用未认证访问`

**解决方案**：
1. 确认 `ui/.env` 文件中已添加 `VITE_SEMANTIC_SCHOLAR_API_KEY`
2. 重启前端服务（Vite 需要重启才能读取新的环境变量）

### 问题 2：API 请求失败

**症状**：控制台显示 `⚠️ [Semantic Scholar] API 请求失败: 429`

**解决方案**：
1. 429 错误表示请求过于频繁
2. 确认 API Key 已正确配置
3. 等待几分钟后重试

### 问题 3：期刊信息未显示

**症状**：文献详情中没有期刊信息

**可能原因**：
1. 该文献没有 DOI（预印本、会议论文等）
2. CrossRef API 未返回期刊名称
3. EasyScholar API 未找到该期刊的信息

**解决方案**：
1. 查看浏览器控制台日志，确认每一步的执行情况
2. 如果是预印本（arXiv），则不会有期刊信息
3. 如果是会议论文，可能没有影响因子

## 相关文件

- **后端配置**：`.env`（根目录）
- **前端配置**：`ui/.env`
- **后端代码**：`mcp_servers/paper_search/modules/search/semantic_scholar.py`
- **前端代码**：`ui/src/services/easyScholarService.ts`
- **EasyScholar 集成文档**：`docs/easyscholar-integration.md`

