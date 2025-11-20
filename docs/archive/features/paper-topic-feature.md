# 文献主题分组功能实现文档

## 功能概述

实现了文献按主题（topic）分组管理的功能，解决了在同一个对话中检索多个主题时文献混淆的问题。

## 核心特性

### 1. 数据结构改进

**CSV 文件新增 `Topic` 列：**
- 每条文献记录都关联到对应的 topic
- 支持向后兼容：旧数据没有 topic 列时自动设置为空字符串

**示例 CSV 结构：**
```csv
ID,Title,Authors,Abstract,URL,PDF_URL,Published,Source,Categories,DOI,CitationCount,FullText,LocalFile,Topic,Score
arxiv_001,Paper Title,Author1; Author2,Abstract text,...,2024-01-01,arxiv,cs.AI,10.1234/...,10,...,,machine_learning,0.95
```

### 2. 后端功能

#### 新增 MCP 工具

1. **`get_paper_topics`** - 获取所有主题列表
   - 从缓存的文献数据中提取所有唯一的 topic
   - 统计每个 topic 的文献数量
   - 返回格式：
     ```json
     {
       "status": "success",
       "topics": [
         {"name": "机器学习", "count": 15, "value": "machine_learning"},
         {"name": "深度学习", "count": 10, "value": "deep_learning"}
       ]
     }
     ```

2. **`filter_papers_by_topic`** - 按主题筛选文献
   - 支持多个主题（OR 逻辑）
   - topics 为空或 None 时返回所有文献
   - 返回精简的字段列表

#### 修改的工具

1. **`list_papers_from_csv`**
   - 默认返回字段中添加了 `topic`
   - 自动处理没有 topic 列的旧 CSV 文件

2. **`select_papers`** 和 **`get_selected_papers`**
   - 支持跨 topic 选择文献
   - 可以同时选择多个 topic 的文献进行融合分析

### 3. 前端功能

#### UI 改进

1. **主题筛选器**
   - 下拉菜单显示所有主题及其文献数量
   - 支持筛选特定主题的文献

2. **分组显示切换**
   - "分组显示"：按主题分组展示文献
   - "列表显示"：传统的列表展示方式

3. **分组展示样式**
   - 每个主题有独立的标题栏（蓝色渐变背景）
   - 显示主题名称和文献数量
   - 主题标题栏固定在顶部（sticky）

#### 跨主题选择

- 用户可以在不同主题的文献中自由选择
- 选择的文献可以来自多个主题
- 批量分析和报告生成支持跨主题文献

## 向后兼容性

### 处理旧数据

1. **读取旧 CSV 文件**
   - 如果 CSV 文件没有 `Topic` 列，自动为每条记录添加空的 topic 字段
   - 不会修改原始文件

2. **合并新旧数据**
   - 追加模式下，如果现有 CSV 没有 `Topic` 列，自动添加空列
   - 新数据和旧数据可以无缝合并

3. **前端显示**
   - 没有 topic 的文献显示为"未分类"
   - 只有一个主题时不显示主题筛选器

## 使用场景

### 场景 1：多主题文献检索

```
用户：请帮我检索关于"机器学习"和"深度学习"的文献

Agent：
1. 检索"机器学习"相关文献（topic="machine_learning"）
2. 检索"深度学习"相关文献（topic="deep_learning"）
3. 所有文献保存到同一个 CSV，但带有不同的 topic 标识

前端显示：
- 分组显示：
  - 机器学习 (15 篇)
    - Paper 1
    - Paper 2
    ...
  - 深度学习 (10 篇)
    - Paper 3
    - Paper 4
    ...
```

### 场景 2：跨主题融合分析

```
用户：请对我选中的文献进行分析

操作：
1. 用户从"机器学习"主题选择 5 篇文献
2. 用户从"深度学习"主题选择 3 篇文献
3. 点击"确认选择"按钮
4. 点击"批量分析"或"生成报告"

结果：
- Agent 收到 8 篇文献（来自不同主题）
- 生成融合分析报告
```

## 测试指南

### 测试 1：向后兼容性

1. 准备一个旧的 CSV 文件（没有 Topic 列）
2. 使用 `list_papers_from_csv` 加载
3. 验证：
   - 文献能正常加载
   - 每篇文献的 topic 字段为空字符串
   - 前端显示为"未分类"

### 测试 2：多主题检索

1. 在同一个会话中检索两个不同的主题
2. 验证：
   - CSV 文件包含两个主题的文献
   - 每篇文献的 Topic 列正确
   - 前端能正确分组显示

### 测试 3：跨主题选择

1. 从不同主题选择文献
2. 点击"确认选择"
3. 执行批量分析或生成报告
4. 验证：
   - 选择的文献正确传递给后端
   - 分析结果包含所有选中的文献

## 技术细节

### 数据流

```
检索 → save_papers_to_csv (添加 topic 列) → CSV 文件
                                                ↓
前端加载 ← list_papers_from_csv ← 读取 CSV (兼容旧格式)
    ↓
按 topic 分组显示
    ↓
用户选择文献 (可跨 topic)
    ↓
select_papers → 后端缓存选择状态
    ↓
批量分析/生成报告 → get_selected_papers → 获取完整文献信息
```

### 关键代码位置

**后端：**
- `mcp_servers/paper_search/modules/paper_manager/export_tools.py`
  - `save_papers_to_csv()` - 添加 Topic 列
  - `read_papers_from_csv()` - 读取并兼容旧格式

- `mcp_servers/paper_search/server.py`
  - `get_paper_topics()` - 新增工具
  - `filter_papers_by_topic()` - 新增工具
  - `list_papers_from_csv()` - 修改默认字段
  - `select_papers()` - 支持跨 topic
  - `get_selected_papers()` - 支持跨 topic

**前端：**
- `ui/src/types/index.ts`
  - `Paper` 接口添加 `topic` 字段

- `ui/src/components/RightPanel.tsx`
  - `PapersTab` 组件添加主题筛选和分组显示

## 未来改进

1. **主题管理**
   - 支持重命名主题
   - 支持合并主题
   - 支持删除主题

2. **高级筛选**
   - 支持多主题 AND/OR 逻辑
   - 支持主题标签系统

3. **可视化**
   - 主题关系图
   - 文献分布统计

