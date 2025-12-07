# 批量分析综合总结功能使用示例

## 📖 基本用法

### 1. 使用默认设置（自动生成综合总结）

```python
from modules.paper_manager.analysis import batch_paper_analysis

# 准备论文数据
papers = [
    {
        'paper_id': 'arxiv:2301.00001',
        'title': 'Deep Learning for Materials Discovery',
        'authors': ['Zhang, A.', 'Li, B.'],
        'abstract': 'We propose a novel deep learning method...',
        'source': 'arxiv'
    },
    # ... 更多论文
]

# 执行批量分析（默认生成综合总结）
result = await batch_paper_analysis(
    papers=papers,
    topic="机器学习在材料科学中的应用"  # 建议提供主题
)

# 检查结果
if result.get('status') == 'success':
    print(f"成功分析: {result['successful_analyses']} 篇")
    
    # 获取综合总结
    if result.get('overall_analysis'):
        print("综合总结：")
        print(result['overall_analysis'])
```

### 2. 禁用综合总结（仅分析单篇论文）

```python
# 如果只需要单篇分析，不需要综合总结
result = await batch_paper_analysis(
    papers=papers,
    generate_summary=False  # 禁用综合总结
)
```

### 3. 使用进度回调

```python
async def progress_callback(progress_data):
    """进度回调函数"""
    current = progress_data.get('current', 0)
    total = progress_data.get('total', 0)
    message = progress_data.get('message', '')
    print(f"[{current}/{total}] {message}")

# 执行批量分析（带进度追踪）
result = await batch_paper_analysis(
    papers=papers,
    topic="深度学习",
    progress_callback=progress_callback
)
```

## 📊 返回结果结构

```python
{
    'status': 'success',
    'total_papers': 10,
    'successful_analyses': 9,
    'failed_analyses': 1,
    'results': [
        {
            'paper_id': 'arxiv:2301.00001',
            'title': 'Deep Learning for Materials Discovery',
            'key_info': {
                'objective': '开发基于深度学习的材料发现方法',
                'method': '使用图神经网络预测材料性质',
                'result': '在多个数据集上达到了最先进的性能',
                'innovation': '提出了新的图卷积架构'
            },
            'abstract_zh': '本文提出了一种基于深度学习的材料发现方法...'
        },
        # ... 更多论文分析结果
    ],
    'failures': [
        {
            'id': 'arxiv:2301.00010',
            'title': 'Failed Paper',
            'error': 'Analysis timeout'
        }
    ],
    'overall_analysis': '''
## 1. 研究趋势总结
该领域主要聚焦于深度学习方法在材料科学中的应用...

## 2. 方法论对比分析
不同研究采用了多种深度学习架构，包括图神经网络、卷积神经网络...

## 3. 关键发现汇总
研究表明深度学习方法能够显著提高材料性质预测的准确性...

## 4. 研究空白识别
当前研究主要集中在监督学习方法，而无监督学习和强化学习...

## 5. 技术路线总结
主流技术路线包括：1) 基于图神经网络的方法...
    ''',
    'timestamp': '2024-01-15T10:30:00'
}
```

## 🎯 综合总结内容示例

生成的综合总结包含以下五个部分：

### 1. 研究趋势总结
```
该领域主要聚焦于深度学习方法在材料科学中的应用，特别是图神经网络
和迁移学习技术。研究热点包括材料性质预测、材料设计优化和高通量筛选。
近年来，研究者越来越关注数据效率和模型可解释性问题。
```

### 2. 方法论对比分析
```
不同研究采用了多种深度学习架构，包括图神经网络（GNN）、卷积神经网络
（CNN）和循环神经网络（RNN）。GNN 在处理材料结构数据方面表现优异，
而迁移学习方法能够显著减少所需的训练数据量。主动学习策略则在材料
优化任务中展现出独特优势。
```

### 3. 关键发现汇总
```
研究表明深度学习方法能够显著提高材料性质预测的准确性，在多个基准
数据集上达到了最先进的性能。迁移学习技术可以将预训练模型的知识
迁移到新的材料体系，减少了对大规模标注数据的依赖。主动学习策略
能够加速材料优化过程 10 倍以上。
```

### 4. 研究空白识别
```
当前研究主要集中在监督学习方法，而无监督学习和强化学习在材料科学
中的应用仍然有限。此外，模型的可解释性和泛化能力仍需进一步提升。
如何将深度学习方法与物理约束相结合，以及如何处理小样本和不平衡
数据问题，都是值得深入研究的方向。
```

### 5. 技术路线总结
```
主流技术路线包括：1) 基于图神经网络的材料性质预测；2) 迁移学习
和领域自适应方法；3) 主动学习和贝叶斯优化相结合的材料设计策略；
4) 多任务学习和元学习方法。这些技术路线为后续研究提供了重要参考，
特别是在数据稀缺和计算资源受限的场景下。
```

## 🔧 高级用法

### 1. 自定义并发数

```python
result = await batch_paper_analysis(
    papers=papers,
    topic="深度学习",
    max_concurrent=5  # 限制最大并发数
)
```

### 2. 结合 CSV 导出

```python
from modules.paper_manager.export_tools import save_summary_to_file

# 执行批量分析
result = await batch_paper_analysis(
    papers=papers,
    topic="机器学习在材料科学中的应用"
)

# 保存到 Markdown 文件
if result.get('status') == 'success':
    summary_result = save_summary_to_file(
        summary_result=result,
        session_id="my_session",
        topic="机器学习在材料科学中的应用",
        file_prefix='analysis_summary'
    )
    
    print(f"总结已保存到: {summary_result['file_path']}")
```

### 3. 错误处理

```python
try:
    result = await batch_paper_analysis(
        papers=papers,
        topic="深度学习"
    )
    
    if result.get('status') == 'error':
        print(f"批量分析失败: {result.get('error')}")
    else:
        # 检查是否有失败的论文
        if result.get('failed_analyses') > 0:
            print(f"警告: {result['failed_analyses']} 篇论文分析失败")
            for failure in result.get('failures', []):
                print(f"  - {failure['id']}: {failure['error']}")
        
        # 检查综合总结是否生成
        if not result.get('overall_analysis'):
            print("警告: 综合总结生成失败")
            
except Exception as e:
    print(f"发生异常: {str(e)}")
```

## 💡 最佳实践

1. **提供研究主题**：建议始终提供 `topic` 参数，以生成更准确的综合总结
2. **控制论文数量**：建议每次分析 5-50 篇论文，过多可能导致综合总结质量下降
3. **使用进度回调**：对于大批量分析，使用进度回调可以实时了解处理进度
4. **错误处理**：检查 `failed_analyses` 和 `failures` 字段，了解哪些论文分析失败
5. **保存结果**：使用 `save_summary_to_file()` 将结果保存到文件，避免重复分析

## ⚠️ 注意事项

1. **API 成本**：每次批量分析会调用 N+1 次 LLM（N 篇论文 + 1 次综合总结）
2. **处理时间**：综合总结需要额外 10-30 秒的处理时间
3. **主题重要性**：如果不提供 `topic`，将使用默认值"研究主题"，可能影响总结质量
4. **失败处理**：综合总结生成失败不会影响单篇分析结果
5. **并发限制**：默认并发数为 8，可根据 API 限流情况调整

