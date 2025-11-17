# 声子谱CSV导出配置说明

## 🎯 快速配置

**配置文件位置**：`mcp_servers/simulation/modules/mattersim_energy.py`（第9-30行）

```python
# ========================================
# 🔧 声子谱CSV导出性能优化配置
# ========================================

# 原子数阈值：超过此值将跳过CSV导出
PHONON_CSV_ATOM_THRESHOLD = 10  # 👈 在此修改！

# CSV最大行数：超过此值将进行降采样
PHONON_CSV_MAX_ROWS = 1000  # 👈 在此修改！

# 是否对大结构跳过CSV导出
PHONON_CSV_SKIP_LARGE_STRUCTURES = True  # 👈 在此修改！
```

---

## 📊 配置参数说明

### 1. `PHONON_CSV_ATOM_THRESHOLD`（原子数阈值）

**作用**：当结构原子数超过此值时，自动跳过CSV导出（仅生成图片）

| 值 | 效果 | 适用场景 |
|----|------|---------|
| `8` | 非常严格，只导出小分子 | 超快速模式 |
| `10` | **默认值**，跳过大多数复杂结构 | 推荐日常使用 |
| `15` | 平衡模式 | 需要更多数据 |
| `20` | 宽松模式 | 科研分析 |

**示例**：
- 30原子结构（Ag16Ge2Se4S8）：阈值=10时跳过CSV，节省20-30秒
- 8原子结构（NaCl）：阈值=10时正常导出CSV

### 2. `PHONON_CSV_MAX_ROWS`（CSV最大行数）

**作用**：CSV行数超过此值时进行降采样

| 值 | 文件大小 | 导出速度 | 适用场景 |
|----|---------|---------|---------|
| `500` | ~50KB | <0.5秒 | 快速预览 |
| `1000` | ~100KB | 1-2秒 | **默认，推荐** |
| `2000` | ~200KB | 2-4秒 | 详细分析 |
| `5000` | ~500KB | 5-10秒 | 科研分析 |
| `-1` | >10MB | 10-30秒 | 完整数据 |

**降采样说明**：
- 使用均匀采样，保留数据分布特征
- 对可视化影响极小

### 3. `PHONON_CSV_SKIP_LARGE_STRUCTURES`（总开关）

**作用**：控制是否启用原子数阈值检查

| 值 | 效果 |
|----|------|
| `True` | **默认**，启用阈值检查 |
| `False` | 强制导出所有CSV |

---

## 🚀 推荐配置方案

### 方案1：日常使用（推荐）
```python
PHONON_CSV_ATOM_THRESHOLD = 10
PHONON_CSV_MAX_ROWS = 1000
PHONON_CSV_SKIP_LARGE_STRUCTURES = True
```
- 小结构：导出CSV（1-3秒）
- 大结构：跳过CSV（<0.1秒）

### 方案2：超快速模式
```python
PHONON_CSV_ATOM_THRESHOLD = 8
PHONON_CSV_MAX_ROWS = 500
PHONON_CSV_SKIP_LARGE_STRUCTURES = True
```
- 适合批量计算、快速筛选

### 方案3：科研分析模式
```python
PHONON_CSV_ATOM_THRESHOLD = 20
PHONON_CSV_MAX_ROWS = 5000
PHONON_CSV_SKIP_LARGE_STRUCTURES = False
```
- 导出详细数据，可能较慢

### 方案4：仅生成图片
```python
PHONON_CSV_ATOM_THRESHOLD = 5
PHONON_CSV_MAX_ROWS = 0
PHONON_CSV_SKIP_LARGE_STRUCTURES = True
```
- 只生成图片，不导出CSV

---

## 📝 性能对比

| 结构 | 原子数 | 优化前 | 优化后（默认配置） | 加速比 |
|-----|-------|-------|------------------|-------|
| NaCl | 8 | 2-3秒 | 1-2秒 | 1.5-2x |
| Ag16Ge2Se4S8 | 30 | 20-30秒 | <0.1秒（跳过CSV） | **200-300x** |
| 小分子 | <10 | 1-2秒 | 0.5-1秒 | 2x |

---

## ⚠️ 注意事项

1. **修改配置后无需重启**：配置在函数调用时读取
2. **CSV跳过不影响图片**：图片始终正常生成
3. **降采样不影响可视化**：人眼无法区分1000点和10000点的曲线
4. **需要完整数据时**：设置 `SKIP_LARGE_STRUCTURES=False` 和 `MAX_ROWS=-1`

---

## 🔧 安装libyaml加速（可选）

安装C语言YAML解析器可获得5-10倍加速：

```bash
uv pip install pyyaml --no-build-isolation
```

验证：
```bash
python -c "from yaml import CLoader; print('✅ CLoader available')"
```

---

## 📚 相关文档

- 主配置文件：`mcp_servers/simulation/modules/mattersim_energy.py`
- 详细优化报告：`docs/PHONON_CSV_PERFORMANCE_OPTIMIZATION.md`

