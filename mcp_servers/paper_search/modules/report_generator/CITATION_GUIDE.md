# 引用管理系统使用指南

## 概述

本系统实现了符合 **GB/T 7714-2015** 国家标准的参考文献引用管理机制，支持在学术报告中自动插入引用标注并生成规范的参考文献列表。

## 核心组件

### 1. CitationManager（引用管理器）

位置：`mcp_servers/paper_search/modules/report_generator/citation_manager.py`

**主要功能：**
- 文献编号映射管理
- GB/T 7714-2015 格式化
- 引用标注处理（`^[1]^` → `<sup>[1]</sup>`）
- 引用验证与统计

**使用示例：**

```python
from citation_manager import CitationManager

# 初始化
citation_manager = CitationManager(papers_info)

# 生成文献列表供LLM参考
ref_list = citation_manager.generate_reference_list_for_prompt()

# 处理引用标注
text_with_citations = citation_manager.process_citations(llm_output)

# 验证引用
is_valid, errors = citation_manager.validate_citations(text_with_citations)

# 生成参考文献列表
references = citation_manager.generate_all_references_gb7714()

# 获取统计信息
stats = citation_manager.get_citation_statistics()
uncited = citation_manager.get_uncited_papers()
```

## 引用标注格式

### LLM输出格式（中间格式）

在LLM生成的文本中使用以下标记：

- **单个引用**：`^[1]^`
- **范围引用**：`^[1-3]^`
- **多个引用**：`^[1,3,5]^`

**示例：**
```
机器学习在材料设计中展现出巨大潜力^[1,2]^。深度神经网络可以预测材料性能^[3]^，
而图神经网络则直接处理晶体结构^[4-6]^。
```

### 最终输出格式（HTML）

系统自动转换为HTML上标格式：

```html
机器学习在材料设计中展现出巨大潜力<sup>[1,2]</sup>。深度神经网络可以预测材料性能<sup>[3]</sup>，
而图神经网络则直接处理晶体结构<sup>[4-6]</sup>。
```

## GB/T 7714-2015 参考文献格式

### 期刊论文 [J]

```
[1] 张三, 李四, 王五. 材料科学中的机器学习应用[J]. 材料研究学报, 2023, 45(3): 123-135.
[2] SMITH J, DOE A. Machine learning for materials discovery[J]. Nature Materials, 2024, 23(1): 45-58.
```

### 在线期刊 [J/OL]

```
[3] BROWN T, et al. Language models are few-shot learners[J/OL]. Nature, 2020, 585(7825): 456-467[2024-12-04]. DOI: 10.1038/s41586-020-2649-2.
```

### arXiv预印本 [EB/OL]

```
[4] CHEN X, WANG Y. Deep learning for crystal structure prediction[EB/OL]. (2023)[2024-12-04]. https://arxiv.org/abs/2301.12345.
```

### 会议论文 [C]

```
[5] 张三. 深度学习在材料设计中的应用[C]// 第十届材料科学国际会议论文集. 北京: 科学出版社, 2023: 56-62.
```

## 工作流程

### 1. 综合报告生成（reporting.py）

```python
# 步骤1：初始化引用管理器
citation_manager = CitationManager(papers_info)

# 步骤2：生成文献列表供LLM参考
reference_list_for_llm = citation_manager.generate_reference_list_for_prompt()

# 步骤3：在Prompt中包含文献列表和引用要求
synthesis_prompt = f"""
你是一位资深学术研究员，正在撰写关于"{topic}"的综合研究报告。

**引用规范**：
- 在陈述观点时，必须用 ^[序号]^ 标注文献来源
- 多篇文献：^[1,2,5]^ 或 ^[1-3]^

**文献资料**：
{reference_list_for_llm}

请生成报告...
"""

# 步骤4：LLM生成带引用标记的内容
llm_output = completion(model=model, messages=[{"role": "user", "content": synthesis_prompt}])

# 步骤5：处理引用标注
report_content = citation_manager.process_citations(llm_output)

# 步骤6：验证引用
is_valid, errors = citation_manager.validate_citations(report_content)

# 步骤7：生成参考文献列表
references = citation_manager.generate_all_references_gb7714()

# 步骤8：组装完整报告
full_report = header + report_content + appendix + references
```

### 2. 单篇论文分析（analysis.py）

```python
# 在分析结果中添加引用信息
citation_info = format_paper_citation_info(paper)

result = {
    'paper_id': paper_id,
    'title': title,
    'citation_info': citation_info,  # 引用信息
    'data_source': '基于论文摘要分析',  # 数据来源标注
    'key_info': key_info,
    ...
}
```

## 引用统计与验证

### 获取统计信息

```python
# 引用次数统计
stats = citation_manager.get_citation_statistics()
# 输出：{1: 3, 2: 5, 3: 0, ...}  # 文献编号: 被引用次数

# 未被引用的文献
uncited = citation_manager.get_uncited_papers()
# 输出：[3, 7, 10]  # 未被引用的文献编号列表

# 生成统计报告
report = citation_manager.generate_citation_report()
```

### 引用验证

```python
is_valid, errors = citation_manager.validate_citations(text)

if not is_valid:
    for error in errors:
        print(f"引用错误: {error}")
```

**验证内容：**
- 引用编号是否在有效范围内（1 到文献总数）
- 范围引用的起止编号是否合理
- 引用格式是否正确

## 最佳实践

### 1. Prompt设计

✅ **推荐做法：**
```python
prompt = f"""
**引用规范**：
1. 在陈述观点、数据、方法时，必须标注文献来源
2. 引用格式：^[序号]^
3. 每个关键论断都要有文献支撑

**文献资料**（共{len(papers)}篇）：
{reference_list}

请生成报告...
"""
```

❌ **避免：**
- 不在Prompt中提供文献列表
- 不明确引用格式要求
- 不要求LLM标注引用来源

### 2. 引用覆盖率

- 目标：至少80%的文献被引用
- 监控：使用`get_uncited_papers()`检查未引用文献
- 优化：在Prompt中强调"引用要均衡分布"

### 3. 数据来源标注

对于基于摘要的分析，明确标注：
```python
result['data_source'] = '基于论文摘要分析'
```

在Prompt中提醒：
```
**重要提示**：本分析基于论文摘要，非全文
```

## 故障排查

### 问题1：LLM不生成引用标记

**原因**：Prompt不够明确

**解决**：
- 在Prompt中提供引用示例
- 强调"必须标注文献来源"
- 增加引用格式说明

### 问题2：引用编号超出范围

**原因**：LLM生成了不存在的文献编号

**解决**：
- 在Prompt中明确文献总数
- 使用`validate_citations()`检测并记录错误
- 考虑在后处理中修正或删除无效引用

### 问题3：部分文献未被引用

**原因**：LLM选择性引用

**解决**：
- 在Prompt中强调"引用要均衡分布"
- 检查文献列表是否完整传递给LLM
- 考虑分批生成，确保每批文献都被覆盖

## 扩展功能

### 自定义引用格式

如需支持其他引用格式（如IEEE、APA），可扩展`CitationManager`：

```python
def format_reference_ieee(self, index: int) -> str:
    """IEEE格式"""
    ref = self.reference_map[index]
    return f"[{index}] {authors}, \"{title},\" {journal}, vol. {volume}, no. {issue}, pp. {pages}, {year}."

def format_reference_apa(self, index: int) -> str:
    """APA格式"""
    ref = self.reference_map[index]
    return f"{authors} ({year}). {title}. {journal}, {volume}({issue}), {pages}."
```

### 引用分析

```python
def analyze_citation_patterns(self):
    """分析引用模式"""
    # 识别高频引用文献
    # 检测引用聚类
    # 生成引用网络图
    pass
```

