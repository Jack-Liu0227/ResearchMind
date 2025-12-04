# 阶段 A & B 实施总结

## 修改概览

本次实施完成了阶段 A（路径管理统一）和阶段 B（Markdown 报告生成优化）的所有任务。

---

## 【阶段 A：路径管理统一】

### 目标
消除所有硬编码路径，统一使用环境变量配置的路径管理系统，修复 404 文件访问错误。

### 新增文件

#### 1. `utils/__init__.py`
- Utils 包初始化文件

#### 2. `utils/paths.py`
统一路径管理模块，提供以下函数：
- `session_data_root()`: 返回会话数据根目录（从环境变量 `SESSION_DATA_ROOT` 读取，默认 `data/session_data`）
- `papers_root()`: 返回论文存储目录（从环境变量 `PAPERS_ROOT` 读取，默认 `data/session_data/papers`）
- `phonon_root()`: 返回声子数据目录（从环境变量 `PHONON_ROOT` 读取，默认 `data/session_data/simulation`）
- `ensure_dirs(*paths)`: 确保指定的所有目录存在
- `get_session_path(session_id, data_type)`: 获取特定会话的数据路径

#### 3. `utils/urls.py`
URL 转换工具模块，提供以下函数：
- `file_to_download_url(file_path, session_id)`: 文件路径 → `/api/download/papers/{session_id}/{filename}`
- `file_to_image_url(file_path, session_id, subpath)`: 图片路径 → `/api/images/phonon/{session_id}/{subpath}/{filename}`
- `extract_session_id_from_path(file_path)`: 从路径提取会话 ID
- `normalize_api_url(url)`: 规范化 API URL

#### 4. `docs/STAGE_A_VERIFICATION.md`
完整的验证文档，包含测试步骤和预期结果。

### 修改文件

#### 1. `services/config.py` (Lines 66-86)
**修改内容：**
- 移除硬编码路径 `os.path.join(STATIC_FILES_ROOT, "..", "data", "session_data")`
- 导入 `utils.paths` 模块
- 使用 `session_data_root()` 和 `phonon_root()` 获取路径

**关键代码：**
```python
from utils.paths import session_data_root, phonon_root
SESSION_DATA_DIR = str(session_data_root())
PHONON_RESULTS_DIR = str(phonon_root())
```

#### 2. `services/static_file_service.py` (Lines 68-125)
**修改内容：**
- 导入 `utils.paths` 模块
- 使用 `session_data_root()`, `phonon_root()`, `ensure_dirs()` 替代硬编码路径
- 修复缩进错误（Line 125）

**关键代码：**
```python
from utils.paths import session_data_root, phonon_root, ensure_dirs
paper_search_dir = str(session_data_root())
ensure_dirs(paper_search_dir)
```

#### 3. `mcp_servers/shared/storage_manager.py` (Lines 1-33)
**修改内容：**
- 移除硬编码路径 `_MODULE_DIR / "data" / "session_data"`
- 使用 `session_data_root()` 和 `ensure_dirs()`

#### 4. `mcp_servers/paper_search/modules/shared/session_folder_manager.py` (Lines 1-33)
**修改内容：**
- 移除硬编码路径
- 使用 `session_data_root()`, `papers_root()`, `ensure_dirs()`

#### 5. `mcp_servers/database_call/content_storage.py` (Lines 1-34)
**修改内容：**
- 移除硬编码路径
- 使用 `session_data_root()` 和 `ensure_dirs()`

#### 6. `services/session_manager.py` (Lines 26-53)
**修改内容：**
- 移除硬编码 `BASE_DATA_DIR`
- 使用 `session_data_root()`

#### 7. `start_linux.sh` (Lines 1-25, 132-162, 196-210)
**修改内容：**
- 添加 Docker 挂载说明注释
- 在 `load_config()` 中导出环境变量：
  ```bash
  export SESSION_DATA_ROOT="${SESSION_DATA_ROOT:-data/session_data}"
  export PAPERS_ROOT="${PAPERS_ROOT:-data/session_data/papers}"
  export PHONON_ROOT="${PHONON_ROOT:-data/session_data/simulation}"
  ```
- 在 `prepare_workspace()` 中创建必要目录

#### 8. `services/database/models.py` (Lines 1-29)
**修改内容：**
- 移除硬编码数据库路径 `Path(__file__).parent.parent.parent / "data"`
- 使用 `session_data_root().parent` 获取数据库目录
- 确保数据库文件与会话数据在同一父目录下

**关键代码：**
```python
from utils.paths import session_data_root
DB_DIR = session_data_root().parent
DB_PATH = DB_DIR / "researchmind.db"
```

#### 9. `.env` (Lines 130-148)
**新增内容：**
- 添加路径配置环境变量
- 设置 `SESSION_DATA_ROOT=D:\XJTU\Research\PHD\Agent\ST\data\session_data`
- 添加注释说明 `PAPERS_ROOT` 和 `PHONON_ROOT` 的默认值

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SESSION_DATA_ROOT` | `data/session_data` | 会话数据根目录 |
| `PAPERS_ROOT` | `data/session_data/papers` | 论文存储目录 |
| `PHONON_ROOT` | `data/session_data/simulation` | 声子/仿真数据目录 |

---

## 【阶段 B：Markdown 报告生成优化】

### 目标
修复内容截断和引用格式问题，使生成的 Markdown 报告具有可点击的引用链接。

### 修改文件

#### 1. `mcp_servers/paper_search/modules/report_generator/reporting.py`

**新增配置参数（Lines 23-27）：**
```python
REPORT_CONTENT_MAX_LENGTH = int(os.getenv('REPORT_CONTENT_MAX_LENGTH', '12000'))
LLM_ANALYSIS_MAX_TOKENS = int(os.getenv('LLM_ANALYSIS_MAX_TOKENS', '2500'))
LLM_SYNTHESIS_MAX_TOKENS = int(os.getenv('LLM_SYNTHESIS_MAX_TOKENS', '8000'))
```

**修改内容截断（Line 242-245）：**
- 从固定 3000 字符改为使用 `REPORT_CONTENT_MAX_LENGTH` 环境变量（默认 12000）

**修改 LLM max_tokens（Lines 290-304, 671-677）：**
- 分析阶段：1500 → `LLM_ANALYSIS_MAX_TOKENS`（默认 2500）
- 综合阶段：4000 → `LLM_SYNTHESIS_MAX_TOKENS`（默认 8000）

#### 2. `mcp_servers/paper_search/modules/report_generator/citation_manager.py`

**新增函数 `_convert_citation_markers_to_md_links()`（Lines 218-265）：**
- 将上标引用格式转换为 Markdown 锚点链接
- 支持单个引用：`^[1]^` → `[1](#ref-1)`
- 支持范围引用：`^[1-3]^` → `[1](#ref-1), [2](#ref-2), [3](#ref-3)`
- 支持多个引用：`^[1,3,5]^` → `[1](#ref-1), [3](#ref-3), [5](#ref-5)`
- 支持混合格式：`^[1-3,5]^` → `[1](#ref-1), [2](#ref-2), [3](#ref-3), [5](#ref-5)`

**修改 `process_citations()` 函数（Lines 184-217）：**
- 添加 `use_anchor_links` 参数（默认 True）
- 调用 `_convert_citation_markers_to_md_links()` 进行转换

**修改 `generate_all_references_gb7714()` 函数（Lines 171-192）：**
- 添加 `use_anchor_links` 参数（默认 True）
- 为每个参考文献添加 HTML 锚点：`<a id="ref-n"></a>`

**修改 `format_reference_gb7714()` 函数（Lines 114-176）：**
- 使所有 URL 可点击：`url` → `[url](url)`
- 使 DOI 可点击：`doi` → `[doi](https://doi.org/doi)`

### 新增文件

#### 1. `tests/test_citation_formatting.py`
单元测试文件，验证：
- 引用标记转换功能
- 参考文献列表锚点
- URL 可点击性

#### 2. `docs/STAGE_B_VERIFICATION.md`
完整的验证文档，包含测试步骤和预期结果。

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REPORT_CONTENT_MAX_LENGTH` | 12000 | 论文内容截断上限（字符数） |
| `LLM_ANALYSIS_MAX_TOKENS` | 2500 | 分析阶段 LLM 最大 token 数 |
| `LLM_SYNTHESIS_MAX_TOKENS` | 8000 | 综合阶段 LLM 最大 token 数 |

---

## 验证步骤

### 阶段 A 验证
详见 `docs/STAGE_A_VERIFICATION.md`

### 阶段 B 验证
详见 `docs/STAGE_B_VERIFICATION.md`

---

## 修改文件统计

| 类型 | 数量 | 文件列表 |
|------|------|----------|
| 新增 | 8 | `utils/__init__.py`, `utils/paths.py`, `utils/urls.py`, `tests/test_citation_formatting.py`, `scripts/verify_paths.py`, `docs/STAGE_A_VERIFICATION.md`, `docs/STAGE_B_VERIFICATION.md`, `docs/STAGE_AB_SUMMARY.md` |
| 修改 | 10 | `services/config.py`, `services/static_file_service.py`, `services/session_manager.py`, `services/database/models.py`, `.env`, `mcp_servers/shared/storage_manager.py`, `mcp_servers/paper_search/modules/shared/session_folder_manager.py`, `mcp_servers/database_call/content_storage.py`, `mcp_servers/paper_search/modules/report_generator/reporting.py`, `mcp_servers/paper_search/modules/report_generator/citation_manager.py`, `start_linux.sh` |

---

## 已修复问题

1. ✅ 404 文件访问错误（路径硬编码）
2. ✅ 内容截断过度（3000 → 12000 字符）
3. ✅ 引用标记无法跳转（`^[1]^` → `[1](#ref-1)`）
4. ✅ 参考文献 URL 不可点击（纯文本 → Markdown 链接）
5. ✅ 缩进错误（`services/static_file_service.py` Line 125）
6. ✅ 数据库路径不一致（现在使用 `SESSION_DATA_ROOT` 的父目录）

---

## 路径配置验证

运行验证脚本：
```bash
python scripts/verify_paths.py
```

**预期输出：**
```
🎉 所有路径配置验证通过！

预期数据存储位置：
  - 会话数据: D:\XJTU\Research\PHD\Agent\ST\data\session_data
  - 论文文件: D:\XJTU\Research\PHD\Agent\ST\data\session_data\papers
  - 仿真结果: D:\XJTU\Research\PHD\Agent\ST\data\session_data\simulation
  - 数据库:   D:\XJTU\Research\PHD\Agent\ST\data\researchmind.db
```

---

## 下一步

如需继续，可进行阶段 C：多 Agent 架构统一。

