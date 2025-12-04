# 引用系统快速参考卡片

## 🚀 快速开始

### 1. 导入模块

```python
from citation_manager import CitationManager
```

### 2. 初始化

```python
citation_manager = CitationManager(papers_info)
```

### 3. 生成报告

```python
# 生成文献列表
ref_list = citation_manager.generate_reference_list_for_prompt()

# 在Prompt中使用
prompt = f"""
**文献资料**：
{ref_list}

请在陈述观点时用 ^[序号]^ 标注引用...
"""

# 处理LLM输出
report = citation_manager.process_citations(llm_output)

# 生成参考文献
refs = citation_manager.generate_all_references_gb7714()
```

## 📝 引用标记格式

| 类型 | LLM输出 | 最终显示 |
|------|---------|---------|
| 单个引用 | `^[1]^` | `<sup>[1]</sup>` |
| 范围引用 | `^[1-3]^` | `<sup>[1-3]</sup>` |
| 多个引用 | `^[1,3,5]^` | `<sup>[1,3,5]</sup>` |

## 📚 GB/T 7714-2015 格式

### 期刊论文 [J]

```
[1] 作者. 题名[J]. 刊名, 年, 卷(期): 页码.
```

### 在线期刊 [J/OL]

```
[2] 作者. 题名[J/OL]. 刊名, 年, 卷(期): 页码[访问日期]. DOI.
```

### arXiv预印本 [EB/OL]

```
[3] 作者. 题名[EB/OL]. (发布日期)[访问日期]. URL.
```

## 🔍 常用方法

### 引用处理

```python
# 转换引用标记
text = citation_manager.process_citations(llm_output)
```

### 引用验证

```python
# 验证引用有效性
is_valid, errors = citation_manager.validate_citations(text)
if not is_valid:
    for error in errors:
        print(error)
```

### 引用统计

```python
# 获取统计信息
stats = citation_manager.get_citation_statistics()
# 输出：{1: 3, 2: 5, 3: 0, ...}

# 获取未引用文献
uncited = citation_manager.get_uncited_papers()
# 输出：[3, 7, 10]

# 生成统计报告
report = citation_manager.generate_citation_report()
```

### 参考文献生成

```python
# 单条参考文献
ref = citation_manager.format_reference_gb7714(1)

# 完整参考文献列表
all_refs = citation_manager.generate_all_references_gb7714()
```

## ⚠️ 常见问题

### Q1: LLM不生成引用标记？

**解决**：在Prompt中明确要求并提供示例

```python
prompt = f"""
**引用规范**：
- 在陈述观点时用 ^[序号]^ 标注
- 示例："深度学习可以预测材料性能^[1]^"

**文献资料**：
{ref_list}
"""
```

### Q2: 引用编号超出范围？

**解决**：使用验证功能检测

```python
is_valid, errors = citation_manager.validate_citations(text)
# 会检测并报告超出范围的引用
```

### Q3: 部分文献未被引用？

**解决**：检查未引用文献并在Prompt中强调

```python
uncited = citation_manager.get_uncited_papers()
if uncited:
    print(f"未引用文献：{uncited}")
    
# 在Prompt中添加：
# "引用要均衡分布，避免某些文献被忽略"
```

## 📊 引用覆盖率目标

- ✅ **优秀**：>80% 文献被引用
- ⚠️ **良好**：60-80% 文献被引用
- ❌ **需改进**：<60% 文献被引用

## 🔧 调试技巧

### 查看引用映射

```python
# 查看文献编号映射
for i, ref in citation_manager.reference_map.items():
    print(f"[{i}] {ref['title'][:50]}...")
```

### 查看引用统计

```python
stats = citation_manager.get_citation_statistics()
for i, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
    title = citation_manager.reference_map[i]['title'][:40]
    print(f"[{i}] {title}... : {count} 次")
```

### 生成详细报告

```python
report = citation_manager.generate_citation_report()
print(report)
```

## 📖 完整文档

- **使用指南**：`CITATION_GUIDE.md`
- **实施方案**：`docs/citation_implementation_plan.md`
- **实施总结**：`docs/citation_implementation_summary.md`
- **测试脚本**：`test_citation_manager.py`

## 🎯 最佳实践

1. **Prompt设计**
   - 明确引用格式要求
   - 提供完整文献列表
   - 强调引用均衡分布

2. **引用验证**
   - 总是验证引用有效性
   - 记录并处理验证错误
   - 监控引用覆盖率

3. **数据来源标注**
   - 单篇分析标注"基于摘要"
   - 在Prompt中提醒数据来源
   - 在结果中添加data_source字段

4. **质量控制**
   - 目标引用覆盖率 >80%
   - 检查未引用文献
   - 验证参考文献格式

## 💡 示例代码

### 完整流程示例

```python
from citation_manager import CitationManager
from litellm import completion

# 1. 初始化
cm = CitationManager(papers_info)

# 2. 生成Prompt
ref_list = cm.generate_reference_list_for_prompt()
prompt = f"""
**引用规范**：用 ^[序号]^ 标注引用
**文献资料**：
{ref_list}

请生成关于"{topic}"的综述...
"""

# 3. LLM生成
response = completion(model="...", messages=[{"role": "user", "content": prompt}])
llm_output = response.choices[0].message.content

# 4. 处理引用
report_content = cm.process_citations(llm_output)

# 5. 验证
is_valid, errors = cm.validate_citations(report_content)
if not is_valid:
    print(f"发现 {len(errors)} 个引用错误")

# 6. 生成参考文献
references = cm.generate_all_references_gb7714()

# 7. 组装报告
full_report = header + report_content + appendix + references

# 8. 统计
stats = cm.get_citation_statistics()
cited_count = sum(1 for c in stats.values() if c > 0)
print(f"引用覆盖率：{cited_count}/{len(papers_info)}")
```

## 🔗 相关资源

- **GB/T 7714-2015 标准**：中国国家标准
- **CitationManager源码**：`citation_manager.py`
- **测试脚本**：`test_citation_manager.py`

