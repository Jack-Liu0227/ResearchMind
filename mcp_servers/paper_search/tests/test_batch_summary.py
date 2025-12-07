"""
测试批量分析综合总结功能

测试 generate_batch_summary() 函数是否能正确生成综合研究报告
"""
import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from modules.paper_manager.analysis import generate_batch_summary, batch_paper_analysis


async def test_generate_batch_summary():
    """测试综合总结生成功能"""
    
    # 模拟批量分析结果
    mock_analysis_results = [
        {
            'paper_id': 'paper1',
            'title': 'Deep Learning for Materials Discovery',
            'key_info': {
                'objective': '开发基于深度学习的材料发现方法',
                'method': '使用图神经网络预测材料性质',
                'result': '在多个数据集上达到了最先进的性能',
                'innovation': '提出了新的图卷积架构'
            }
        },
        {
            'paper_id': 'paper2',
            'title': 'Transfer Learning in Materials Science',
            'key_info': {
                'objective': '研究迁移学习在材料科学中的应用',
                'method': '使用预训练模型进行微调',
                'result': '显著减少了所需的训练数据量',
                'innovation': '提出了领域自适应策略'
            }
        },
        {
            'paper_id': 'paper3',
            'title': 'Active Learning for Materials Optimization',
            'key_info': {
                'objective': '优化材料设计的主动学习策略',
                'method': '结合贝叶斯优化和深度学习',
                'result': '加速了材料优化过程10倍',
                'innovation': '提出了新的采样策略'
            }
        }
    ]
    
    topic = "机器学习在材料科学中的应用"
    
    print(f"🧪 测试综合总结生成功能")
    print(f"📊 论文数量: {len(mock_analysis_results)}")
    print(f"🎯 研究主题: {topic}")
    print("-" * 80)
    
    # 调用综合总结生成函数
    result = await generate_batch_summary(
        analysis_results=mock_analysis_results,
        topic=topic
    )
    
    # 检查结果
    if result.get('status') == 'success':
        print("✅ 综合总结生成成功！")
        print(f"📝 总结长度: {len(result.get('overall_analysis', ''))} 字符")
        print("-" * 80)
        print("📄 综合总结内容：")
        print(result.get('overall_analysis'))
        print("-" * 80)
        print(f"✅ 测试通过！")
        return True
    else:
        print(f"❌ 综合总结生成失败: {result.get('error')}")
        return False


async def test_batch_paper_analysis_with_summary():
    """测试完整的批量分析流程（包含综合总结）"""
    
    # 模拟论文数据
    mock_papers = [
        {
            'paper_id': 'arxiv:2301.00001',
            'title': 'Graph Neural Networks for Materials Property Prediction',
            'authors': ['Zhang, A.', 'Li, B.', 'Wang, C.'],
            'abstract': 'We propose a novel graph neural network architecture for predicting materials properties. Our method achieves state-of-the-art performance on multiple benchmark datasets.',
            'source': 'arxiv'
        },
        {
            'paper_id': 'arxiv:2301.00002',
            'title': 'Transfer Learning Approaches in Computational Materials Science',
            'authors': ['Chen, D.', 'Liu, E.'],
            'abstract': 'This work explores transfer learning techniques for materials science applications. We demonstrate significant improvements in data efficiency.',
            'source': 'arxiv'
        }
    ]
    
    topic = "深度学习在材料科学中的应用"
    
    print(f"\n🧪 测试完整批量分析流程（包含综合总结）")
    print(f"📊 论文数量: {len(mock_papers)}")
    print(f"🎯 研究主题: {topic}")
    print("-" * 80)
    
    # 调用批量分析（启用综合总结）
    result = await batch_paper_analysis(
        papers=mock_papers,
        generate_summary=True,
        topic=topic
    )
    
    # 检查结果
    if result.get('status') == 'success':
        print("✅ 批量分析完成！")
        print(f"📊 成功分析: {result.get('successful_analyses')} 篇")
        print(f"❌ 失败分析: {result.get('failed_analyses')} 篇")
        
        if result.get('overall_analysis'):
            print(f"📝 综合总结已生成（长度: {len(result.get('overall_analysis'))} 字符）")
            print("-" * 80)
            print("📄 综合总结内容：")
            print(result.get('overall_analysis'))
            print("-" * 80)
        else:
            print("⚠️ 未生成综合总结")
        
        print(f"✅ 测试通过！")
        return True
    else:
        print(f"❌ 批量分析失败: {result.get('error')}")
        return False


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 批量分析综合总结功能测试")
    print("=" * 80)
    
    # 测试 1: 单独测试综合总结生成
    asyncio.run(test_generate_batch_summary())
    
    # 测试 2: 测试完整流程（需要 LLM API，可能会失败）
    # asyncio.run(test_batch_paper_analysis_with_summary())

