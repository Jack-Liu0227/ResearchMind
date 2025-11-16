# 前端显示优化 - 变更日志

## 修改日期
2025-01-17

## 修改概述

完成了三项前端显示优化任务：
1. 确保 Agent 工具执行结果在前端正确展示
2. 调整声子谱图片在对话框中的显示尺寸为 60%
3. 优化声子谱 CSV 数据的传输方式（只传递 URL，不传递完整内容）

---

## 任务1：确保 Agent 工具执行结果在前端正确展示

### 现状分析

工具执行结果已经通过以下流程正确展示：

1. **后端处理流程**：
   - `agent_coordinator.py` 的 `_handle_agent_event` 方法捕获工具返回结果
   - 调用 `DataProcessor.process_tool_result` 处理工具结果
   - 提取结构数据、图片数据、文件链接等
   - 通过 WebSocket 发送 `structure_data`、`image_data`、`file_data`、`file_metadata` 消息

2. **前端处理流程**：
   - `ChatPage.tsx` 监听 WebSocket 消息
   - 处理 `file_data` 消息：添加文件到右侧面板
   - 处理 `file_metadata` 消息：更新消息的 metadata，并创建 SessionFile
   - 处理 `image_data` 消息：附加图片到最后一条 assistant 消息
   - `MessageList.tsx` 渲染消息时显示图片、文件链接等

### 验证要点

- ✅ 工具返回结果通过 `DataProcessor.process_tool_result` 正确处理
- ✅ 文件链接（CSV、MD）通过 `file_metadata` 消息发送到前端
- ✅ 图片数据通过 `image_data` 消息发送到前端
- ✅ 前端正确解析和渲染工具返回的内容

---

## 任务2：调整声子谱图片在对话框中的显示尺寸

### 修改位置

**文件**：`ui/src/components/MessageList.tsx`

**代码位置**：第 738-742 行

### 修改内容

图片显示样式已经设置为：

```typescript
style={{
  width: '60%',           // 图片宽度为对话框的 60%
  maxWidth: '100%',       // 不超过容器宽度
  objectFit: 'contain'    // 保持宽高比
}}
```

### 效果

- ✅ 声子谱图片（phonon_dispersion、phonon_dos）在对话框中显示宽度为 60%
- ✅ 保持图片的宽高比，避免变形
- ✅ 在不同屏幕尺寸下都能正常显示
- ✅ 右侧面板的 `PhononViewer.tsx` 使用 `w-full`，不受影响

---

## 任务3：优化声子谱 CSV 数据的传输方式

### 问题描述

之前的实现将完整的 CSV 文件内容（`phonon_dispersion_csv_content` 和 `phonon_dos_csv_content`）通过 WebSocket 传输到前端，导致：
- WebSocket 消息体积过大
- 网络负载增加
- 内存占用增加

### 修改位置

**文件**：`services/data_processor.py`

**修改内容**：

1. **声子色散 CSV**（第 349-376 行）：
   - ❌ 移除：读取并传输完整 CSV 内容
   - ✅ 新增：只传递下载 URL（`phonon_dispersion_csv_url`）
   - ✅ 新增：发送 `file_data` 消息到右侧面板

2. **声子态密度 CSV**（第 378-423 行）：
   - ❌ 移除：读取并传输完整 CSV 内容
   - ✅ 新增：只传递下载 URL（`phonon_dos_csv_url`）
   - ✅ 新增：发送 `file_data` 消息到右侧面板

### 修改详情

```python
# 🔧 优化：不传输完整 CSV 内容，只传递下载 URL
# 前端可以通过 URL 按需下载 CSV 文件
# inline_csv = DataProcessor._read_text_file(csv_path)
# if inline_csv is not None:
#     file_metadata['phonon_dispersion_csv_content'] = inline_csv

# 🔧 同时发送为独立的文件数据，确保在右侧面板显示
await DataProcessor._send_message(websocket, "file_data", {
    "files": [{
        "id": f"phonon_dispersion_{filename}",
        "type": "csv",
        "name": f"声子色散数据 - {filename}",
        "downloadUrl": csv_url,
        "filePath": csv_path,
        "createdAt": datetime.now().timestamp() * 1000,
        "extra": {
            "category": "phonon_dispersion"
        }
    }],
    "agentId": agent_id,
    "sessionId": session_id,
    "timestamp": datetime.now().isoformat()
})
```

### 前端处理

**文件**：`ui/src/pages/ChatPage.tsx`

前端已经正确处理：
- `file_data` 消息：添加文件到右侧面板（第 706-733 行）
- `file_metadata` 消息：从 metadata 中提取 CSV URL（第 153-165 行）
- `CsvViewer` 组件：通过 URL 按需加载 CSV 内容

### 效果

- ✅ WebSocket 消息体积显著减小（不再包含完整 CSV 内容）
- ✅ 前端可以通过下载链接正常访问 CSV 文件
- ✅ CSV 文件在右侧面板正确显示
- ✅ 不影响声子谱图片的正常显示

---

## 影响范围

### 修改的文件

1. `services/data_processor.py` - 优化声子谱 CSV 传输方式
2. `services/agent_coordinator.py` - 添加 session_id 到消息（之前的修改）

### 未修改的文件

1. `ui/src/components/MessageList.tsx` - 图片宽度已经是 60%，无需修改
2. `ui/src/pages/ChatPage.tsx` - 已经正确处理 `file_data` 和 `file_metadata` 消息
3. `mcp_servers/simulation/server.py` - 已经返回 CSV 文件路径和 URL

---

## 测试建议

1. **工具执行结果展示测试**：
   - 上传 CIF 文件
   - 调用 `calculate_phonon` 工具
   - 验证声子谱图片在对话框中正确显示
   - 验证 CSV 文件在右侧面板正确显示

2. **图片尺寸测试**：
   - 检查声子谱图片在对话框中的显示宽度是否为 60%
   - 在不同屏幕尺寸下测试图片显示效果

3. **CSV 传输优化测试**：
   - 使用浏览器开发者工具监控 WebSocket 消息大小
   - 验证消息中不包含 `phonon_dispersion_csv_content` 和 `phonon_dos_csv_content`
   - 验证前端可以通过 URL 正常下载 CSV 文件
   - 验证 CSV 文件在右侧面板可以正常预览

---

## 注意事项

1. **热导率 CSV 未优化**：
   - 热导率计算结果的 CSV 仍然传输完整内容（`inlineContent`）
   - 如果需要优化，可以参考声子谱 CSV 的实现方式

2. **向后兼容性**：
   - 前端的 `createSessionFilesFromMetadata` 函数已经支持从 URL 加载 CSV
   - 旧的消息（如果有 `csv_content`）仍然可以正常显示

3. **URL 格式**：
   - 声子谱 CSV URL 格式：`/api/images/phonon/{session_id}/phonon_results/{filename}`
   - 确保后端的静态文件服务正确配置了这个路由

---

## 修改的文件

1. ✅ `services/data_processor.py` - 优化声子谱 CSV 传输方式（第 349-423 行）
   - 移除完整 CSV 内容的传输
   - 添加 `file_data` 消息发送到右侧面板

2. ✅ `mcp_servers/simulation/server.py` - 多项修复
   - `calculate_phonon` 函数（第 902-907 行）：确保 CSV 路径在返回结果中
   - `extract_and_validate_cif` 函数（第 1013-1052 行）：添加 CIF 标准化功能
     - 使用 pymatgen 重新生成干净的 CIF 文件
     - 移除 `_symmetry_Int_Tables_number` 等问题字段
     - **关键修复**：修复空间群名称中的下标问题（`Pmn2_1` → `Pmn21`）
     - 覆盖保存标准化后的 CIF 文件

3. ✅ `mcp_servers/simulation/modules/mattersim_energy.py` - 增强 CIF 文件解析容错性
   - **核心修复**：所有 `ase_io.read()` 调用强制使用 `format='cif'`（第 134、958、977、1033、1367 行）
     - 避免 ASE 根据文件名误判格式（如 `POSCAR.cif` 被当作 VASP 文件）
     - 确保所有 CIF 文件都通过 CIF 解析器处理
   - 修复 `_clean_cif_content` 函数（第 821-895 行）：
     - 移除多余的空行（POSCAR 转 CIF 时产生的格式问题）
     - 处理可能导致 "scaling factors" 错误的对称性标签
     - 移除 `_symmetry_Int_Tables_number` 和 `_space_group_IT_number` 字段
     - 修复空间群名称中的下标问题（`_1` → `1`）
   - 修复 `relax_structure_impl` 函数（第 986-1035 行）：
     - 添加 pymatgen 重新生成 CIF 的后备方案
     - 清理 pymatgen 生成的 CIF 中的问题字段
     - 修复空间群名称中的下标问题
   - 解决 "The number of scaling factors must be 1 or 3" 错误（根本原因：文件名误判）
   - 解决 "invalid spacegroup `Pmn2_1`" 错误（pymatgen 下标格式问题）

4. ✅ `services/agent_coordinator.py` - 添加 session_id 到消息（之前的修改）

## 未修改的文件（已经符合要求）

1. ✅ `ui/src/components/MessageList.tsx` - 图片宽度已经是 60%，无需修改
2. ✅ `ui/src/pages/ChatPage.tsx` - 已经正确处理 `file_data` 和 `file_metadata` 消息
3. ✅ `mcp_servers/simulation/modules/mattersim_energy.py` - 已经返回 CSV 文件路径（第 1619-1620 行）

