"""
Citation Manager 测试脚本

用于验证引用管理系统的核心功能
"""

from citation_manager import CitationManager


def create_test_papers():
    """创建测试用的论文数据"""
    return [
        {
            'paper_id': 'arxiv:2301.12345',
            'title': 'Machine Learning for Materials Discovery',
            'authors': ['Smith J', 'Doe A', 'Brown C', 'Wilson D'],
            'published': '2023-01-15',
            'source': 'arxiv',
            'abstract': 'This paper presents a novel approach to materials discovery using machine learning...',
            'url': 'https://arxiv.org/abs/2301.12345'
        },
        {
            'paper_id': 'ss:12345678',
            'title': '材料科学中的深度学习应用',
            'authors': ['张三', '李四', '王五'],
            'published': '2023-03-20',
            'source': 'semantic_scholar',
            'journal': '材料研究学报',
            'volume': '45',
            'issue': '3',
            'pages': '234-245',
            'abstract': '本文综述了深度学习在材料科学中的最新应用...',
            'url': 'https://example.com/paper2'
        },
        {
            'paper_id': 'ss:87654321',
            'title': 'Graph Neural Networks for Crystal Structure Prediction',
            'authors': ['Chen X', 'Wang Y'],
            'published': '2024-02-10',
            'source': 'semantic_scholar',
            'journal': 'Nature Materials',
            'volume': '23',
            'issue': '2',
            'pages': '156-167',
            'doi': '10.1038/s41563-024-01234-5',
            'abstract': 'We propose a graph neural network approach for predicting crystal structures...',
            'url': 'https://example.com/paper3'
        }
    ]


def test_citation_manager():
    """测试引用管理器的核心功能"""
    
    print("=" * 80)
    print("引用管理系统测试")
    print("=" * 80)
    
    # 创建测试数据
    papers = create_test_papers()
    print(f"\n✓ 创建了 {len(papers)} 篇测试论文")
    
    # 初始化引用管理器
    cm = CitationManager(papers)
    print(f"✓ 引用管理器初始化成功")
    
    # 测试1：生成文献列表
    print("\n" + "-" * 80)
    print("测试1：生成文献列表供LLM参考")
    print("-" * 80)
    ref_list = cm.generate_reference_list_for_prompt()
    print(ref_list[:500] + "...\n")
    
    # 测试2：引用标注处理
    print("-" * 80)
    print("测试2：引用标注处理")
    print("-" * 80)
    
    test_text = """
机器学习在材料设计中展现出巨大潜力^[1,2]^。深度神经网络可以预测材料性能^[3]^，
而图神经网络则直接处理晶体结构^[1-3]^。这些方法显著提高了材料发现的效率^[2]^。
"""
    
    print("原始文本（带引用标记）：")
    print(test_text)
    
    processed_text = cm.process_citations(test_text)
    print("\n处理后文本（HTML格式）：")
    print(processed_text)
    
    # 测试3：引用验证
    print("\n" + "-" * 80)
    print("测试3：引用验证")
    print("-" * 80)
    
    is_valid, errors = cm.validate_citations(processed_text)
    if is_valid:
        print("✓ 所有引用验证通过")
    else:
        print(f"✗ 发现 {len(errors)} 个引用错误：")
        for error in errors:
            print(f"  - {error}")
    
    # 测试4：引用统计
    print("\n" + "-" * 80)
    print("测试4：引用统计")
    print("-" * 80)
    
    stats = cm.get_citation_statistics()
    print("引用频次统计：")
    for i, count in stats.items():
        title = cm.reference_map[i]['title'][:50]
        print(f"  [{i}] {title}... : {count} 次")
    
    uncited = cm.get_uncited_papers()
    if uncited:
        print(f"\n未被引用的文献：{uncited}")
    else:
        print("\n✓ 所有文献都被引用")
    
    cited_count = sum(1 for c in stats.values() if c > 0)
    coverage = cited_count / len(papers) * 100
    print(f"\n引用覆盖率：{coverage:.1f}% ({cited_count}/{len(papers)})")
    
    # 测试5：GB/T 7714-2015 格式化
    print("\n" + "-" * 80)
    print("测试5：GB/T 7714-2015 参考文献格式")
    print("-" * 80)
    
    for i in range(1, len(papers) + 1):
        ref = cm.format_reference_gb7714(i)
        print(f"\n{ref}")
    
    # 测试6：完整参考文献列表
    print("\n" + "-" * 80)
    print("测试6：完整参考文献列表")
    print("-" * 80)
    
    all_refs = cm.generate_all_references_gb7714()
    print(all_refs)
    
    # 测试7：引用统计报告
    print("\n" + "-" * 80)
    print("测试7：引用统计报告")
    print("-" * 80)
    
    report = cm.generate_citation_report()
    print(report)
    
    # 测试8：无效引用检测
    print("\n" + "-" * 80)
    print("测试8：无效引用检测")
    print("-" * 80)
    
    invalid_text = """
这是一个包含无效引用的测试^[99]^。
范围引用错误^[5-2]^。
超出范围^[1-10]^。
"""
    
    processed_invalid = cm.process_citations(invalid_text)
    is_valid, errors = cm.validate_citations(processed_invalid)
    
    if not is_valid:
        print(f"✓ 成功检测到 {len(errors)} 个引用错误：")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✗ 未能检测到无效引用")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == '__main__':
    test_citation_manager()

