# 完整工作流程测试文档

## 目录结构

```
mcp_servers/simulation/
├── cif/
│   └── {session_id}/
│       ├── uploads/                    # 用户上传的原始 CIF 文件
│       │   └── structure.cif
│       └── structures/                 # 弛豫后的 CIF 文件
│           └── relaxed_structure_20251105_220000.cif
└── phonon_results/                     # 声子计算结果图片（全局）
    ├── relaxed_structure_band_20251105_220000.png
    └── relaxed_structure_dos_20251105_220000.png

session_data/
├── images/
│   └── {session_id}/                   # 会话隔离的图片
│       ├── relaxed_structure_band_20251105_220000.png
│       └── relaxed_structure_dos_20251105_220000.png
└── structures/
    └── {session_id}/                   # 会话隔离的结构文件（备用）
```

## 静态文件访问路径

| 文件类型 | 物理路径 | URL 路径 |
|---------|---------|---------|
| 原始 CIF | `mcp_servers/simulation/cif/{session_id}/uploads/structure.cif` | 不对外暴露 |
| 弛豫 CIF | `mcp_servers/simulation/cif/{session_id}/structures/relaxed_*.cif` | `/api/structures/{session_id}/structures/relaxed_*.cif` |
| 声子图片 | `session_data/images/{session_id}/relaxed_*_band.png` | `/api/images/{session_id}/relaxed_*_band.png` |

## 完整工作流程

### 步骤 0: 用户上传 CIF 文件

用户通过 Web 界面上传 `structure.cif`，文件自动保存到：
```
mcp_servers/simulation/cif/{session_id}/uploads/structure.cif
```

### 步骤 1: 验证 CIF 文件（可选）

```python
validation = await extract_and_validate_cif(
    session_id="abc123",
    filename="structure.cif"
)

# 返回:
{
    "success": True,
    "is_valid": True,
    "cif_filename": "structure.cif",
    "file_path": "mcp_servers/simulation/cif/abc123/uploads/structure.cif",
    "structure_info": {
        "formula": "C2",
        "num_atoms": 2,
        "cell_volume": 35.42
    },
    "message": "✅ CIF 文件已验证: C2, 2 个原子"
}
```

### 步骤 2: 结构弛豫

```python
relax_result = await relax_structure(
    session_id="abc123",
    cif_filename="structure.cif",
    device="cuda",
    optimizer="BFGS",
    max_steps=500,
    fmax=0.01
)

# 返回:
{
    "success": True,
    "relaxed_cif_file": "mcp_servers/simulation/cif/abc123/structures/relaxed_structure_20251105_220000.cif",
    "relaxed_cif_url": "/structures/abc123/structures/relaxed_structure_20251105_220000.cif",
    "relaxed_cif_filename": "relaxed_structure_20251105_220000.cif",
    "initial_energy": -10.5,
    "final_energy": -11.2,
    "energy_change": -0.7,
    "converged": True,
    "frontend_structures": [...]
}
```

**关键信息**:
- `relaxed_cif_filename`: 用于后续计算的文件名
- `relaxed_cif_url`: 前端可以下载弛豫后的结构
- 弛豫后的 CIF 文件保存在 `structures/` 目录，可被后续函数读取

### 步骤 3: 计算能量属性（使用弛豫后的结构）

```python
energy_result = await calculate_energy_from_cif(
    session_id="abc123",
    cif_filename=relax_result["relaxed_cif_filename"],  # ⚠️ 使用弛豫后的文件名
    device="cuda"
)

# 返回:
{
    "success": True,
    "energy": -11.2,
    "formation_energy": -5.6,
    "forces": [...],
    "stress": [...]
}
```

### 步骤 4: 计算声子谱（使用弛豫后的结构）

```python
phonon_result = await calculate_phonon(
    session_id="abc123",
    cif_filename=relax_result["relaxed_cif_filename"],  # ⚠️ 使用弛豫后的文件名
    device="cuda",
    supercell_matrix=[4, 4, 4],
    amplitude=0.01
)

# 返回:
{
    "success": True,
    "has_imaginary_modes": False,
    "stability_status": "STABLE",
    "images": [
        {
            "name": "relaxed_structure_band_20251105_220000.png",
            "type": "phonon_band",
            "url": "/api/images/abc123/relaxed_structure_band_20251105_220000.png"
        },
        {
            "name": "relaxed_structure_dos_20251105_220000.png",
            "type": "phonon_dos",
            "url": "/api/images/abc123/relaxed_structure_dos_20251105_220000.png"
        }
    ],
    "composition": "C2",
    "n_atoms": 2
}
```

## 关键点总结

1. ✅ **文件路径传递**: 所有函数使用 `session_id` + `cif_filename` 而非完整内容
2. ✅ **弛豫文件保存**: 弛豫后的 CIF 自动保存到 `structures/` 目录
3. ✅ **文件名传递**: 使用 `relaxed_cif_filename` 在函数间传递
4. ✅ **会话隔离**: 每个 session 的文件完全隔离
5. ✅ **静态文件服务**: 所有文件都可通过 URL 访问
6. ✅ **避免 JSON 转义**: 不再在参数中传递大文本

## 错误处理

### 文件不存在
```python
{
    "success": False,
    "error": "CIF file not found: structure.cif. Please ensure the file has been uploaded to session abc123."
}
```

### 弛豫失败
```python
{
    "success": False,
    "error": "Structure relaxation failed: Maximum force 0.15 eV/Å exceeds threshold 0.01 eV/Å"
}
```

### 声子计算失败
```python
{
    "success": False,
    "error": "Phonon calculation failed: Structure is unstable (has imaginary modes)"
}
```

