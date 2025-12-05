"""
Domain-Specific Prompts (领域特定Prompt)

功能：
1. 领域检测 - 基于论文关键词、期刊名称、摘要内容自动检测研究领域
2. 领域Prompt - 为不同研究领域提供专用的分析Prompt
3. 手动指定 - 支持用户手动指定领域

支持的领域：
- Materials Science (材料科学)
- Biomedical (生物医学)
- Computer Science (计算机科学)
- Physics (物理学)
- Chemistry (化学)
- General (通用领域，默认)
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# 领域关键词定义
# ============================================================================

DOMAIN_KEYWORDS = {
    'materials_science': {
        'keywords': [
            'material', 'crystal', 'alloy', 'composite', 'ceramic', 'polymer',
            'nanomaterial', 'thin film', 'coating', 'metallurgy', 'semiconductor',
            'superconductor', 'ferroelectric', 'magnetic', 'optical properties',
            'mechanical properties', 'thermal properties', 'microstructure',
            'phase transition', 'doping', 'synthesis', 'characterization',
            'XRD', 'SEM', 'TEM', 'DFT', 'molecular dynamics'
        ],
        'journals': [
            'Nature Materials', 'Advanced Materials', 'Acta Materialia',
            'Materials Science and Engineering', 'Journal of Materials Chemistry',
            'Materials Today', 'Scripta Materialia'
        ]
    },
    'biomedical': {
        'keywords': [
            'disease', 'therapy', 'drug', 'protein', 'gene', 'cell', 'tissue',
            'clinical', 'patient', 'diagnosis', 'treatment', 'cancer', 'tumor',
            'immune', 'antibody', 'vaccine', 'biomarker', 'pathology', 'surgery',
            'medical imaging', 'genomics', 'proteomics', 'metabolomics',
            'CRISPR', 'stem cell', 'regenerative medicine', 'pharmacology'
        ],
        'journals': [
            'Nature Medicine', 'The Lancet', 'JAMA', 'New England Journal of Medicine',
            'Cell', 'Science Translational Medicine', 'Nature Biotechnology'
        ]
    },
    'computer_science': {
        'keywords': [
            'algorithm', 'machine learning', 'deep learning', 'neural network',
            'artificial intelligence', 'data mining', 'computer vision', 'NLP',
            'natural language processing', 'reinforcement learning', 'optimization',
            'distributed system', 'cloud computing', 'database', 'software engineering',
            'cybersecurity', 'blockchain', 'quantum computing', 'GPU', 'parallel computing',
            'transformer', 'CNN', 'RNN', 'GAN', 'BERT', 'GPT'
        ],
        'journals': [
            'Nature Machine Intelligence', 'IEEE Transactions', 'ACM Transactions',
            'Journal of Machine Learning Research', 'Neural Information Processing Systems'
        ]
    },
    'physics': {
        'keywords': [
            'quantum', 'particle', 'photon', 'electron', 'atom', 'molecule',
            'wave', 'field', 'energy', 'momentum', 'relativity', 'cosmology',
            'astrophysics', 'condensed matter', 'plasma', 'optics', 'laser',
            'spectroscopy', 'scattering', 'diffraction', 'interferometry',
            'Hamiltonian', 'Lagrangian', 'Schrödinger', 'Maxwell', 'Einstein'
        ],
        'journals': [
            'Physical Review Letters', 'Nature Physics', 'Physical Review',
            'Journal of Physics', 'Applied Physics Letters'
        ]
    },
    'chemistry': {
        'keywords': [
            'molecule', 'reaction', 'synthesis', 'catalyst', 'organic', 'inorganic',
            'analytical', 'physical chemistry', 'electrochemistry', 'photochemistry',
            'spectroscopy', 'chromatography', 'NMR', 'mass spectrometry', 'IR',
            'bond', 'orbital', 'electron', 'ion', 'acid', 'base', 'oxidation',
            'reduction', 'kinetics', 'thermodynamics', 'equilibrium'
        ],
        'journals': [
            'Journal of the American Chemical Society', 'Angewandte Chemie',
            'Chemical Reviews', 'Nature Chemistry', 'Chemical Science'
        ]
    }
}


# ============================================================================
# 领域检测函数
# ============================================================================

def detect_domain(
    paper: Dict[str, Any],
    manual_domain: Optional[str] = None
) -> str:
    """
    检测论文的研究领域
    
    Args:
        paper: 论文信息字典（包含title, abstract, journal等）
        manual_domain: 手动指定的领域（可选）
    
    Returns:
        领域名称（如 'materials_science', 'biomedical', 'general'）
    """
    # 如果手动指定了领域，直接返回
    if manual_domain and manual_domain in DOMAIN_KEYWORDS:
        logger.info(f"Using manually specified domain: {manual_domain}")
        return manual_domain
    
    # 提取论文文本
    title = paper.get('title', '').lower()
    abstract = paper.get('abstract', '').lower()
    journal = paper.get('journal', '').lower()
    
    combined_text = f"{title} {abstract} {journal}"
    
    # 计算每个领域的匹配分数
    domain_scores = {}
    
    for domain, config in DOMAIN_KEYWORDS.items():
        score = 0
        
        # 关键词匹配
        for keyword in config['keywords']:
            if keyword.lower() in combined_text:
                score += 1
        
        # 期刊匹配（权重更高）
        for journal_name in config['journals']:
            if journal_name.lower() in journal:
                score += 5
        
        domain_scores[domain] = score
    
    # 选择得分最高的领域
    if domain_scores:
        best_domain = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain]
        
        # 如果得分太低，使用通用领域
        if best_score < 2:
            logger.info(f"Low confidence in domain detection (score={best_score}), using general domain")
            return 'general'
        
        logger.info(f"Detected domain: {best_domain} (score={best_score})")
        return best_domain
    
    logger.info("No domain detected, using general domain")
    return 'general'


# ============================================================================
# 领域特定Prompt模板
# ============================================================================

DOMAIN_PROMPTS = {
    'materials_science': """分析以下材料科学论文（中文输出）：

**论文信息**
标题: {title}
作者: {authors}
发表: {published}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[具体材料体系]的[性能问题]，该问题在[应用领域]中至关重要，因为[原因]。

### 2. 研究目标
旨在[设计/合成/优化][材料名称]，实现[目标性能]的提升。

### 3. 方法论
采用[制备方法]（如溅射、CVD、溶胶-凝胶等）制备样品，使用[表征手段]（如XRD、SEM、TEM、DFT计算等）分析[微观结构/电子结构/性能]。创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[材料结构特征]
- 关键发现2：[性能数据]（如强度、导电率、磁性等）
- 关键发现3：[结构-性能关系]

### 5. 创新点与贡献
- 创新：[新材料体系/新制备方法/新性能调控机制]
- 贡献：[对材料设计/应用的具体贡献]

### 6. 局限性
- 局限1：[制备条件限制/成本问题]
- 未解决：[长期稳定性/大规模制备/机理理解]

**要求**：专业、客观、简洁（每部分2-3句），关注材料结构、性能和应用
""",

    'biomedical': """分析以下生物医学论文（中文输出）：

**论文信息**
标题: {title}
作者: {authors}
发表: {published}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[疾病名称]的[临床问题]，该问题影响[患者群体]，因为[发病机制/治疗难点]。

### 2. 研究目标
旨在[开发新疗法/发现生物标志物/阐明疾病机制]，改善[临床结局/诊断准确性]。

### 3. 方法论
采用[研究设计]（如随机对照试验、队列研究、细胞实验、动物模型等），使用[技术手段]（如基因测序、蛋白质组学、医学影像等）分析[生物学指标]。创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[疾病机制/靶点发现]
- 关键发现2：[治疗效果数据]（如生存率、缓解率、副作用等）
- 关键发现3：[临床意义]

### 5. 创新点与贡献
- 创新：[新靶点/新疗法/新诊断方法]
- 贡献：[对临床实践/疾病理解的具体贡献]

### 6. 局限性
- 局限1：[样本量/随访时间/模型局限]
- 未解决：[长期疗效/安全性/机制细节]

**要求**：专业、客观、简洁（每部分2-3句），关注临床意义和转化应用
""",

    'computer_science': """分析以下计算机科学论文（中文输出）：

**论文信息**
标题: {title}
作者: {authors}
发表: {published}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[技术问题]（如模型性能、计算效率、数据处理等），该问题在[应用场景]中至关重要，因为[原因]。

### 2. 研究目标
旨在[提升性能/降低复杂度/解决特定问题]，实现[具体目标]（如准确率、速度、可扩展性等）。

### 3. 方法论
采用[算法/模型/架构]（如Transformer、CNN、强化学习等），使用[技术手段]（如注意力机制、正则化、优化算法等）解决[核心挑战]。创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[性能指标]（如准确率、F1分数、推理速度等）
- 关键发现2：[与基线方法的对比]
- 关键发现3：[泛化能力/鲁棒性]

### 5. 创新点与贡献
- 创新：[新算法/新架构/新训练策略]
- 贡献：[对领域的具体贡献/开源代码/数据集]

### 6. 局限性
- 局限1：[计算资源需求/数据依赖]
- 未解决：[可解释性/公平性/实际部署]

**要求**：专业、客观、简洁（每部分2-3句），关注算法创新和实验结果
""",

    'physics': """分析以下物理学论文（中文输出）：

**论文信息**
标题: {title}
作者: {authors}
发表: {published}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[物理现象/理论问题]，该问题在[物理领域]中至关重要，因为[理论意义/实验挑战]。

### 2. 研究目标
旨在[验证理论预测/发现新现象/测量物理量]，实现[具体目标]。

### 3. 方法论
采用[实验方法/理论计算]（如激光光谱、粒子加速器、量子模拟、第一性原理计算等），使用[技术手段]分析[物理量/相互作用]。创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[实验观测/理论预测]
- 关键发现2：[物理量测量结果]（如能量、动量、相位等）
- 关键发现3：[物理机制/规律]

### 5. 创新点与贡献
- 创新：[新实验技术/新理论框架/新物理现象]
- 贡献：[对物理理解/技术应用的具体贡献]

### 6. 局限性
- 局限1：[实验精度/理论近似]
- 未解决：[机制细节/更高能量区域/实际应用]

**要求**：专业、客观、简洁（每部分2-3句），关注物理机制和实验验证
""",

    'chemistry': """分析以下化学论文（中文输出）：

**论文信息**
标题: {title}
作者: {authors}
发表: {published}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[化学反应/分子设计/催化问题]，该问题在[应用领域]中至关重要，因为[原因]。

### 2. 研究目标
旨在[合成新化合物/开发新催化剂/阐明反应机理]，实现[目标性能]（如选择性、产率、活性等）。

### 3. 方法论
采用[合成方法/表征技术]（如有机合成、催化反应、NMR、质谱、X射线晶体学等），使用[分析手段]研究[分子结构/反应机理]。创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[化合物结构/反应条件]
- 关键发现2：[性能数据]（如产率、选择性、催化活性等）
- 关键发现3：[反应机理/结构-活性关系]

### 5. 创新点与贡献
- 创新：[新反应/新催化剂/新合成策略]
- 贡献：[对化学合成/催化/材料的具体贡献]

### 6. 局限性
- 局限1：[底物范围/反应条件/成本]
- 未解决：[机理细节/工业化/环境影响]

**要求**：专业、客观、简洁（每部分2-3句），关注分子结构、反应机理和应用
""",

    'general': """分析以下论文（中文输出）：

**论文信息**
标题: {title}
作者: {authors}
发表: {published}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[具体问题]，该问题在[领域]中至关重要，因为[原因]。

### 2. 研究目标
旨在[具体目标1]、[具体目标2]。

### 3. 方法论
采用[方法名称]，创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[具体结果]
- 关键发现2：[具体结果]

### 5. 创新点与贡献
- 创新：[具体创新点]
- 贡献：[对领域的具体贡献]

### 6. 局限性
- 局限1：[具体局限]
- 未解决：[具体问题]

**要求**：专业、客观、简洁（每部分2-3句）
"""
}


# ============================================================================
# Prompt获取函数
# ============================================================================

def get_domain_prompt(
    paper: Dict[str, Any],
    content: str,
    content_type: str = "摘要",
    manual_domain: Optional[str] = None
) -> Tuple[str, str]:
    """
    获取领域特定的分析Prompt

    Args:
        paper: 论文信息字典
        content: 论文内容（摘要或全文）
        content_type: 内容类型（如"摘要"、"全文"）
        manual_domain: 手动指定的领域（可选）

    Returns:
        Tuple[prompt, domain]
        - prompt: 格式化后的Prompt
        - domain: 检测到的领域名称
    """
    # 检测领域
    domain = detect_domain(paper, manual_domain)

    # 获取领域Prompt模板
    prompt_template = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS['general'])

    # 格式化Prompt
    title = paper.get('title', 'Unknown')
    authors_list = paper.get('authors', [])
    authors = ', '.join(authors_list[:3])
    if len(authors_list) > 3:
        authors += '等'
    published = paper.get('published', 'Unknown')

    prompt = prompt_template.format(
        title=title,
        authors=authors,
        published=published,
        content_type=content_type,
        content=content
    )

    logger.info(f"Generated {domain} domain prompt for paper: {title[:50]}...")
    return prompt, domain


def get_supported_domains() -> List[str]:
    """
    获取支持的领域列表

    Returns:
        领域名称列表
    """
    return list(DOMAIN_KEYWORDS.keys()) + ['general']


def get_domain_statistics(papers: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    统计论文的领域分布

    Args:
        papers: 论文列表

    Returns:
        领域分布字典（领域名称 -> 论文数量）
    """
    domain_counts = {}

    for paper in papers:
        domain = detect_domain(paper)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    logger.info(f"Domain statistics: {domain_counts}")
    return domain_counts

