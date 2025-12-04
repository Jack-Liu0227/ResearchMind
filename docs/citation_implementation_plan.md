# 参考文献引用系统实施方案

## 一、核心问题分析

### 问题1：如何在两种不同场景（全文 vs 摘要）下实现参考文献的正确引用？

**场景对比：**

| 维度 | 综合报告（reporting.py） | 单篇分析（analysis.py） |
|------|------------------------|----------------------|
| 数据来源 | 多篇论文全文/摘要 | 单篇论文摘要 |
| 分析深度 | 综合性学术调研 | 单篇详细分析 |
| 引用需求 | 正文中标注多篇文献引用 | 标注信息来源（摘要） |
| 输出格式 | 完整学术报告+参考文献列表 | 结构化分析结果 |

**解决方案：**

#### 场景A：综合报告生成（基于多篇文献）

```python
# 1. 初始化引用管理器
citation_manager = CitationManager(papers_info)

# 2. 生成文献列表供LLM参考
reference_list = citation_manager.generate_reference_list_for_prompt()

# 3. 在Prompt中要求LLM标注引用
prompt = f"""
**引用规范**：在陈述观点时用 ^[序号]^ 标注文献来源

**文献资料**：
{reference_list}

请生成报告...
"""

# 4. LLM生成带引用标记的内容
llm_output = completion(...)

# 5. 处理引用标注：^[1]^ → <sup>[1]</sup>
report_content = citation_manager.process_citations(llm_output)

# 6. 生成参考文献列表（GB/T 7714-2015格式）
references = citation_manager.generate_all_references_gb7714()

# 7. 组装完整报告
full_report = header + report_content + appendix + references
```

#### 场景B：单篇论文分析（基于摘要）

```python
# 1. 生成引用信息
citation_info = format_paper_citation_info(paper)
# 输出：Smith J, et al. (2023). Machine learning for materials discovery

# 2. 在分析结果中添加引用信息和数据来源标注
result = {
    'paper_id': paper_id,
    'title': title,
    'citation_info': citation_info,  # 引用信息
    'data_source': '基于论文摘要分析',  # 数据来源
    'key_info': {...},
    ...
}

# 3. 在Prompt中提醒LLM
prompt = """
**重要提示**：本分析基于论文摘要，非全文

### 数据来源说明
本分析基于论文摘要，未使用全文。具体技术细节请参考原文。
"""
```

### 问题2：如何确保LLM生成内容时能够追踪并标注文献来源？

**挑战：**
- LLM可能忘记标注引用
- 引用编号可能错误或超出范围
- 引用分布可能不均衡

**解决方案：**

#### 1. Prompt工程优化

```python
synthesis_prompt = f"""
你是一位资深学术研究员，正在撰写关于"{topic}"的综合研究报告。

**重要要求 - 引用规范**：
1. 在陈述观点、数据、方法时，必须标注文献来源
2. 引用格式：在句末用 ^[序号]^ 标注
   示例："深度学习可以预测材料性能^[1]^"
3. 多篇文献：^[1,2,5]^ 或 ^[1-3]^
4. 每个关键论断都要有文献支撑
5. 引用要均衡分布，避免某些文献被忽略

**文献资料**（共{len(papers_info)}篇）：

[1] Smith J, et al. (2023). Machine learning for materials discovery
    来源: semantic_scholar
    摘要: This paper presents a novel approach to materials discovery...

[2] Zhang S, Li S (2024). Deep learning in materials science
    来源: arxiv
    摘要: We propose a deep neural network for predicting...

...

**详细分析**：
{analyses_summary[:5]}  # 前5篇详细分析

请生成以下部分（使用中文，符合学术写作规范）：

## 摘要
- 研究背景（1-2句，标注引用）
- 调研范围与方法（1句）
- 主要发现（2-3句，标注引用）
- 研究意义（1句）

## 1. 引言
### 1.1 研究背景
[在此陈述背景，并标注引用来源]

...
"""
```

#### 2. 引用追踪与验证

```python
# 处理引用标注
report_content = citation_manager.process_citations(llm_output)

# 验证引用有效性
is_valid, errors = citation_manager.validate_citations(report_content)
if not is_valid:
    logger.warning(f"发现 {len(errors)} 个引用错误：")
    for error in errors:
        logger.warning(f"  - {error}")

# 统计引用覆盖率
uncited = citation_manager.get_uncited_papers()
if uncited:
    logger.warning(f"{len(uncited)} 篇文献未被引用：{uncited[:10]}")

# 记录引用统计
stats = citation_manager.get_citation_statistics()
cited_count = sum(1 for c in stats.values() if c > 0)
logger.info(f"引用覆盖率：{cited_count}/{len(papers_info)} ({cited_count/len(papers_info)*100:.1f}%)")
```

### 问题3：如何在最终生成的Markdown报告中保证结构完整性？

**要求：**
- 正文中的引用标注（上标格式）
- 文末的参考文献列表（GB/T 7714-2015格式）
- 引用编号与参考文献列表的一致性

**解决方案：**

#### 报告结构模板

```markdown
# {topic}
## 学术调研报告

---

**报告信息**
| 项目 | 内容 |
|------|------|
| 生成时间 | {timestamp} |
| 文献数量 | {paper_count} 篇 |
| 分析方法 | AI深度分析（基于LLM） |
| 报告类型 | 综合性学术调研报告 |

---

{report_content}  # LLM生成的综述内容，包含 <sup>[1]</sup> 引用标注

---

# 附录：详细文献分析

{appendix_content}  # 每篇文献的详细分析

---

# 参考文献

{references}  # GB/T 7714-2015 格式的参考文献列表
```

#### 一致性保证

```python
# 1. 统一编号管理
citation_manager = CitationManager(papers_info)
# 所有引用编号由CitationManager统一分配和管理

# 2. 引用标注处理
report_content = citation_manager.process_citations(llm_output)
# 确保正文中的引用格式统一：<sup>[1]</sup>

# 3. 参考文献生成
references = citation_manager.generate_all_references_gb7714()
# 确保参考文献列表的编号与正文一致

# 4. 引用验证
is_valid, errors = citation_manager.validate_citations(report_content)
# 验证所有引用编号都在有效范围内
```

## 二、技术实现

### 核心模块：CitationManager

**文件位置**：`mcp_servers/paper_search/modules/report_generator/citation_manager.py`

**主要功能**：

1. **文献编号映射**
   ```python
   reference_map = {
       1: {'paper_id': '...', 'title': '...', 'authors': [...], ...},
       2: {...},
       ...
   }
   ```

2. **GB/T 7714-2015 格式化**
   - 期刊论文 [J]
   - 在线期刊 [J/OL]
   - arXiv预印本 [EB/OL]
   - 会议论文 [C]（预留）

3. **引用标注处理**
   - `^[1]^` → `<sup>[1]</sup>`
   - `^[1-3]^` → `<sup>[1-3]</sup>`
   - `^[1,3,5]^` → `<sup>[1,3,5]</sup>`

4. **引用验证**
   - 编号范围检查
   - 范围引用合理性检查
   - 格式验证

5. **引用统计**
   - 引用频次统计
   - 未引用文献识别
   - 引用覆盖率计算

### 集成点

#### 1. reporting.py 修改

```python
# 导入CitationManager
from .citation_manager import CitationManager

# 在generate_comprehensive_report()中：

# 步骤1：初始化引用管理器
citation_manager = CitationManager(papers_info)

# 步骤2：生成文献列表
reference_list = citation_manager.generate_reference_list_for_prompt()

# 步骤3：修改Prompt
synthesis_prompt = f"""
**引用规范**：...
**文献资料**：
{reference_list}
...
"""

# 步骤4：处理LLM输出
report_content = citation_manager.process_citations(llm_output)

# 步骤5：验证引用
is_valid, errors = citation_manager.validate_citations(report_content)

# 步骤6：生成参考文献
references = citation_manager.generate_all_references_gb7714()

# 步骤7：组装报告
full_report = header + report_content + appendix + references
```

#### 2. analysis.py 修改

```python
# 添加引用信息生成函数
def format_paper_citation_info(paper, index=None):
    """生成引用信息"""
    ...

# 在analyze_paper_content()中：
citation_info = format_paper_citation_info(paper)

result = {
    ...
    'citation_info': citation_info,
    'data_source': '基于论文摘要分析',
    ...
}
```

#### 3. prompts.py 修改

```python
PAPER_SUMMARY_PROMPT_BRIEF = """
**重要提示**：
- 本分析基于论文摘要，非全文
- 所有结论和观点均来自摘要内容

...

### 数据来源说明
本分析基于论文摘要，未使用全文。具体技术细节请参考原文。
"""
```

## 三、GB/T 7714-2015 格式规范

### 期刊论文 [J]

```
[序号] 作者. 题名[J]. 刊名, 年, 卷(期): 起止页码.
```

**示例：**
```
[1] 张三, 李四, 王五. 材料科学中的机器学习应用[J]. 材料研究学报, 2023, 45(3): 123-135.
```

### 在线期刊 [J/OL]

```
[序号] 作者. 题名[J/OL]. 刊名, 年, 卷(期): 起止页码[访问日期]. DOI或URL.
```

**示例：**
```
[2] SMITH J, DOE A. Machine learning for materials[J/OL]. Nature Materials, 2024, 23(1): 45-58[2024-12-04]. DOI: 10.1038/s41563-024-01234-5.
```

### arXiv预印本 [EB/OL]

```
[序号] 作者. 题名[EB/OL]. (发布日期)[访问日期]. URL.
```

**示例：**
```
[3] CHEN X, et al. Deep learning for crystal structure prediction[EB/OL]. (2023)[2024-12-04]. https://arxiv.org/abs/2301.12345.
```

## 四、验证与测试

### 1. 单元测试

运行测试脚本：
```bash
cd mcp_servers/paper_search/modules/report_generator
python test_citation_manager.py
```

### 2. 集成测试

生成完整报告并检查：
- 引用标注是否正确显示为上标
- 参考文献格式是否符合GB/T 7714-2015
- 引用编号与参考文献列表是否一致

### 3. 手动验证清单

- [ ] 正文中的引用显示为上标格式
- [ ] 所有引用编号在有效范围内
- [ ] 参考文献列表格式正确
- [ ] 引用编号与参考文献列表一致
- [ ] 附录中的文献分析包含引用信息
- [ ] 单篇分析结果包含数据来源标注

## 五、使用指南

详见：`mcp_servers/paper_search/modules/report_generator/CITATION_GUIDE.md`

## 六、总结

本实施方案通过以下机制解决了参考文献引用问题：

1. **统一的引用管理**：CitationManager统一管理所有文献编号和引用
2. **智能的Prompt工程**：明确要求LLM标注引用来源
3. **自动化的格式转换**：自动将引用标记转换为标准格式
4. **完善的验证机制**：验证引用有效性并提供统计信息
5. **规范的格式输出**：符合GB/T 7714-2015国家标准

系统已实现并可投入使用。

