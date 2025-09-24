# 快速教程

在不到10分钟内启动并运行ResearchMind。本指南将引导您创建第一个智能研究工作流。

> 🇺🇸 **English Users**: [Click here for English version](../quickstart.md) | **英文用户**: [点击这里查看英文版本](../quickstart.md)

## 先决条件

- 已安装ResearchMind（[安装指南](installation.md)）
- 已配置Google API密钥
- 基本熟悉命令行

## 您的第一个研究查询

### 1. 交互模式

从交互模式开始熟悉ResearchMind：

```bash
python main_mcp.py --interactive
```

您将看到欢迎消息：
```
🧠 欢迎使用ResearchMind - 智能科研助手！
基于Google ADK多智能体系统和MCP工具生态
输入'help'查看帮助，输入'quit'退出
────────────────────────────────────────────────────────────

📝 请输入您的研究需求:
```

尝试这个示例查询：
```
研究高能量密度的锂离子电池正极材料
```

### 2. 接下来会发生什么

ResearchMind将自动：

1. **🔍 文献搜索**: 在ArXiv和Google Scholar上查找相关论文
2. **🗄️ 数据库查询**: 在Materials Project中搜索正极结构
3. **⚛️ 性质分析**: 预测电化学性质
4. **🧪 实验设计**: 建议合成协议

您将看到实时进度：
```
🤖 智能体正在处理您的请求...
📊 文献智能体: 找到15篇关于锂离子正极的相关论文
📊 数据库智能体: 检索到8个高容量正极结构
📊 仿真智能体: 计算了顶级候选材料的电压曲线
📊 实验智能体: 为LiNi0.8Co0.1Mn0.1O2生成了合成协议
✅ 处理完成！
```

## 理解输出

ResearchMind提供结构化结果：

### 文献综述摘要
```
📚 文献综述摘要
────────────────────────────
• 找到15篇论文（2020-2024）
• 关键材料：NCM、NCA、LFP变体
• 趋势：单晶正极、涂层策略
• 性能指标：200-250 mAh/g容量
```

### 材料数据库结果
```
🗄️ 材料数据库结果
────────────────────────────
• LiNi0.8Co0.1Mn0.1O2 (mp-1234567)
  - 理论容量: 278 mAh/g
  - 平均电压: 3.8 V
  - 形成能: -2.1 eV/atom
```

### 仿真洞察
```
⚛️ 仿真预测
────────────────────────────
• 电子结构: 金属行为
• Li扩散势垒: 0.3 eV
• 热稳定性: 稳定至300°C
```

### 实验协议
```
🧪 合成协议
────────────────────────────
• 方法: 溶胶-凝胶合成
• 温度: 850°C，12小时
• 气氛: 空气
• 前驱体: Li2CO3、Ni(NO3)2、Co(NO3)2、Mn(NO3)2
```

## 工作流模式

### 混合模式（推荐）
自动选择最佳策略：

```bash
python main_mcp.py --research "钙钛矿太阳能电池" --workflow hybrid
```

**最适合**: 大多数研究任务，平衡速度和深度

### 顺序模式
逐步深度研究：

```bash
python main_mcp.py --research "二维材料" --workflow sequential
```

**最适合**: 需要深度分析的复杂研究

### 并行模式
快速并发执行：

```bash
python main_mcp.py --research "催化剂筛选" --workflow parallel
```

**最适合**: 快速探索和验证

## 专业智能体

### 文献研究专家

```bash
python main_mcp.py --agent literature_agent --research "材料科学中的机器学习"
```

**能力**:
- 使用高级过滤的ArXiv论文搜索
- Google Scholar引用分析
- 方法论提取和比较
- 趋势分析和研究空白识别

### 数据库搜索专家

```bash
python main_mcp.py --agent database_agent --research "高熵合金"
```

**能力**:
- 多数据库搜索（Materials Project、OQMD、NOMAD）
- 使用CrystaLLM进行AI结构生成
- 性质预测和验证
- 3D结构可视化

### 仿真专家

```bash
python main_mcp.py --agent simulation_agent --research "电子能带结构"
```

**能力**:
- MatterSim集成进行精确计算
- 多尺度建模（原子→材料→器件）
- 性质预测（电子、机械、热）
- 结果分析和可视化

### 实验设计师

```bash
python main_mcp.py --agent experiment_agent --research "纳米粒子合成"
```

**能力**:
- 实验设计（DOE）优化
- 安全风险评估
- 成本和时间估算
- 详细程序的协议生成

## 高级用法

### 自定义研究工作流

创建有针对性的研究查询：

```bash
# 关注最新发展
python main_mcp.py --research "2023年后发表的固态电池"

# 特定性质要求
python main_mcp.py --research "带隙在1-2 eV之间的光伏材料"

# 合成导向研究
python main_mcp.py --research "氧化石墨烯的可扩展合成方法"
```

### Web界面

获得可视化体验：

```bash
python main_mcp.py --web --port 8080
```

打开 http://localhost:8080 并：
1. 选择 `research_coordinator` 智能体
2. 输入您的研究查询
3. 观看实时智能体协调
4. 以多种格式导出结果

### 批处理

处理多个查询：

```bash
# 创建查询文件
echo "显示器用量子点" > queries.txt
echo "热电材料" >> queries.txt
echo "超导材料" >> queries.txt

# 批处理
for query in $(cat queries.txt); do
    python main_mcp.py --research "$query" --workflow hybrid
done
```

## 获得更好结果的技巧

### 1. 具体明确
❌ "寻找材料"
✅ "寻找容量>200 mAh/g的锂离子电池正极材料"

### 2. 包含上下文
❌ "合成方法"
✅ "钙钛矿太阳能电池工业生产的可扩展合成方法"

### 3. 指定约束
❌ "设计实验"
✅ "设计预算<1000美元的石墨烯合成低成本实验"

### 4. 使用领域关键词
包含相关技术术语：
- "DFT计算"、"能带结构"、"形成能"
- "溶胶-凝胶合成"、"水热法"、"化学气相沉积"
- "电化学性能"、"循环稳定性"、"倍率性能"

## 常见用例

### 1. 文献综述
```bash
python main_mcp.py --agent literature_agent --research "锂电池固态电解质的最新进展"
```

### 2. 材料发现
```bash
python main_mcp.py --agent database_agent --research "具有直接带隙的新型二维材料"
```

### 3. 性质预测
```bash
python main_mcp.py --agent simulation_agent --research "高熵合金的机械性质"
```

### 4. 实验规划
```bash
python main_mcp.py --agent experiment_agent --research "优化单晶正极的合成条件"
```

### 5. 综合研究
```bash
python main_mcp.py --research "开发下一代电池材料" --workflow hybrid
```

## 故障排除

### 未找到结果
- 检查拼写和技术术语
- 尝试更广泛或更具体的查询
- 验证API密钥配置正确

### 性能缓慢
- 使用并行模式获得更快结果
- 检查互联网连接
- 考虑使用开发模式进行测试

### 错误消息
- 运行 `python test_agents.py` 诊断问题
- 检查 `logs/researchmind.log` 中的日志
- 验证所有依赖项已安装

## 下一步

现在您已完成快速教程：

1. **探索[智能体配置](agent-config.md)** 自定义行为
2. **尝试[示例项目](samples/)** 获得领域特定示例
3. **学习[工作流模式](workflow-patterns.md)** 进行高级编排
4. **阅读[最佳实践](best-practices.md)** 获得最佳使用效果

## 获取帮助

- **文档**: 浏览完整[文档](README.md)
- **示例**: 查看[示例项目](samples/)
- **社区**: 加入[讨论](https://github.com/your-org/researchmind/discussions)
- **问题**: 在[GitHub](https://github.com/your-org/researchmind/issues)上报告错误

---

**恭喜！** 🎉 您已成功使用ResearchMind创建了第一个智能研究工作流。准备深入了解？接下来探索我们的[高级教程](tutorials/)。


