"""
测试引用格式化功能

验证：
1. 引用标记转换为 Markdown 锚点链接
2. 参考文献列表包含 HTML 锚点
3. URL 可点击
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp_servers" / "paper_search"))

from modules.report_generator.citation_manager import CitationManager


def test_citation_marker_conversion():
    """测试引用标记转换"""
    print("=" * 60)
    print("测试 1: 引用标记转换为 Markdown 锚点链接")
    print("=" * 60)
    
    # 创建测试数据
    papers_info = [
        {
            'title': 'Test Paper 1',
            'authors': ['Author A', 'Author B'],
            'year': '2024',
            'source': 'arxiv',
            'paper_id': '2401.00001',
            'url': 'https://arxiv.org/abs/2401.00001',
            'journal': None,
            'volume': None,
            'issue': None,
            'pages': None,
            'doi': None
        },
        {
            'title': 'Test Paper 2',
            'authors': ['Author C', 'Author D'],
            'year': '2023',
            'source': 'semantic_scholar',
            'paper_id': 'ss123',
            'url': 'https://example.com/paper2',
            'journal': 'Nature',
            'volume': '600',
            'issue': '1',
            'pages': '1-10',
            'doi': '10.1038/s41586-023-00001-0'
        },
        {
            'title': 'Test Paper 3',
            'authors': ['Author E'],
            'year': '2022',
            'source': 'pubmed',
            'paper_id': 'pm456',
            'url': 'https://pubmed.ncbi.nlm.nih.gov/456',
            'journal': 'Science',
            'volume': '380',
            'issue': '2',
            'pages': '100-120',
            'doi': None
        }
    ]
    
    cm = CitationManager(papers_info)
    
    # 测试用例
    test_cases = [
        ("单个引用：^[1]^", "单个引用：[1](#ref-1)"),
        ("范围引用：^[1-3]^", "范围引用：[1](#ref-1), [2](#ref-2), [3](#ref-3)"),
        ("多个引用：^[1,3]^", "多个引用：[1](#ref-1), [3](#ref-3)"),
        ("混合引用：^[1-2,3]^", "混合引用：[1](#ref-1), [2](#ref-2), [3](#ref-3)"),
    ]
    
    all_passed = True
    for input_text, expected_output in test_cases:
        result = cm.process_citations(input_text, use_anchor_links=True)
        passed = result == expected_output
        all_passed = all_passed and passed
        
        print(f"\n输入: {input_text}")
        print(f"预期: {expected_output}")
        print(f"实际: {result}")
        print(f"状态: {'✅ 通过' if passed else '❌ 失败'}")
    
    return all_passed


def test_reference_list_with_anchors():
    """测试参考文献列表包含 HTML 锚点"""
    print("\n" + "=" * 60)
    print("测试 2: 参考文献列表包含 HTML 锚点和可点击链接")
    print("=" * 60)
    
    papers_info = [
        {
            'title': 'Test Paper 1',
            'authors': ['Author A', 'Author B'],
            'year': '2024',
            'source': 'arxiv',
            'paper_id': '2401.00001',
            'url': 'https://arxiv.org/abs/2401.00001',
            'journal': None,
            'volume': None,
            'issue': None,
            'pages': None,
            'doi': None
        },
        {
            'title': 'Test Paper 2',
            'authors': ['Author C', 'Author D'],
            'year': '2023',
            'source': 'semantic_scholar',
            'paper_id': 'ss123',
            'url': 'https://example.com/paper2',
            'journal': 'Nature',
            'volume': '600',
            'issue': '1',
            'pages': '1-10',
            'doi': '10.1038/s41586-023-00001-0'
        }
    ]
    
    cm = CitationManager(papers_info)
    references = cm.generate_all_references_gb7714(use_anchor_links=True)
    
    print("\n生成的参考文献列表：")
    print(references)
    
    # 验证锚点存在
    checks = [
        ('<a id="ref-1"></a>' in references, "包含锚点 ref-1"),
        ('<a id="ref-2"></a>' in references, "包含锚点 ref-2"),
        ('[https://arxiv.org/abs/2401.00001](https://arxiv.org/abs/2401.00001)' in references, "arXiv URL 可点击"),
        ('[10.1038/s41586-023-00001-0](https://doi.org/10.1038/s41586-023-00001-0)' in references, "DOI 可点击"),
    ]
    
    all_passed = True
    for check, description in checks:
        all_passed = all_passed and check
        print(f"{'✅' if check else '❌'} {description}")
    
    return all_passed


if __name__ == "__main__":
    print("开始测试引用格式化功能...\n")
    
    test1_passed = test_citation_marker_conversion()
    test2_passed = test_reference_list_with_anchors()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"测试 1 (引用标记转换): {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"测试 2 (参考文献锚点): {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查代码。")
        sys.exit(1)

