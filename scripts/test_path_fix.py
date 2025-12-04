"""
测试路径修复是否成功

验证：
1. 项目内部的 data/session_data 不会被创建
2. 所有数据都保存到正确的外部路径
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "utils"))

# 加载 .env 文件
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}\n")
else:
    print(f"⚠️  未找到 .env 文件: {env_path}\n")

# 导入路径管理模块
from utils.paths import session_data_root, papers_root, phonon_root, ensure_dirs

print("=" * 70)
print("路径修复测试")
print("=" * 70)

# 1. 检查项目内部路径
print("\n【检查项目内部路径】")
internal_data_dir = project_root / "data" / "session_data"
if internal_data_dir.exists():
    print(f"❌ 错误：项目内部仍存在 data/session_data 目录")
    print(f"   路径: {internal_data_dir}")
    sys.exit(1)
else:
    print(f"✅ 项目内部不存在 data/session_data 目录")

# 2. 检查外部路径
print("\n【检查外部路径】")
session_root = session_data_root()
papers = papers_root()
phonon = phonon_root()

print(f"会话数据根目录:   {session_root}")
print(f"论文存储目录:     {papers}")
print(f"声子/仿真目录:    {phonon}")

# 验证路径是否在项目外部
if session_root.is_relative_to(project_root):
    print(f"❌ 错误：会话数据根目录仍在项目内部")
    print(f"   项目根目录: {project_root}")
    print(f"   会话根目录: {session_root}")
    sys.exit(1)
else:
    print(f"✅ 会话数据根目录在项目外部")

# 3. 模拟目录创建
print("\n【模拟目录创建】")
ensure_dirs(session_root, papers, phonon)
print(f"✅ 目录创建成功（如果不存在）")

# 4. 再次检查项目内部
print("\n【再次检查项目内部】")
if internal_data_dir.exists():
    print(f"❌ 错误：目录创建后，项目内部出现了 data/session_data 目录")
    print(f"   路径: {internal_data_dir}")
    sys.exit(1)
else:
    print(f"✅ 项目内部仍然不存在 data/session_data 目录")

# 5. 验证外部目录存在
print("\n【验证外部目录】")
if session_root.exists() and papers.exists() and phonon.exists():
    print(f"✅ 所有外部目录已创建")
    print(f"   会话数据: {session_root}")
    print(f"   论文文件: {papers}")
    print(f"   仿真结果: {phonon}")
else:
    print(f"❌ 错误：外部目录创建失败")
    sys.exit(1)

# 总结
print("\n" + "=" * 70)
print("🎉 路径修复测试通过！")
print("\n✅ 确认：")
print("  1. 项目内部不会创建 data/session_data 目录")
print("  2. 所有数据都保存到外部路径")
print(f"  3. 外部路径: {session_root.parent}")
print("=" * 70)

