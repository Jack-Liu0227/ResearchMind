"""
路径调试脚本 - 检查环境变量加载和路径解析
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "utils"))

print("=" * 70)
print("路径调试脚本")
print("=" * 70)

# 1. 检查 .env 文件
env_path = project_root / ".env"
print(f"\n【.env 文件】")
print(f"路径: {env_path}")
print(f"存在: {env_path.exists()}")

# 2. 加载 .env 文件
from dotenv import load_dotenv
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载 .env 文件")
else:
    print(f"❌ .env 文件不存在")

# 3. 检查环境变量
print(f"\n【环境变量】")
session_data_root_env = os.getenv('SESSION_DATA_ROOT')
print(f"SESSION_DATA_ROOT: {session_data_root_env}")
print(f"PAPERS_ROOT: {os.getenv('PAPERS_ROOT', '(未设置)')}")
print(f"PHONON_ROOT: {os.getenv('PHONON_ROOT', '(未设置)')}")

# 4. 测试路径解析
print(f"\n【路径解析测试】")
print(f"项目根目录: {project_root}")

if session_data_root_env:
    test_path = Path(session_data_root_env)
    print(f"\n原始路径: {test_path}")
    print(f"是否绝对路径: {test_path.is_absolute()}")
    
    if not test_path.is_absolute():
        joined_path = project_root / test_path
        print(f"拼接后路径: {joined_path}")
        resolved_path = joined_path.resolve()
        print(f"解析后路径: {resolved_path}")
    else:
        resolved_path = test_path.resolve()
        print(f"解析后路径: {resolved_path}")
    
    print(f"\n路径存在: {resolved_path.exists()}")
    print(f"是否在项目内部: {str(resolved_path).startswith(str(project_root))}")

# 5. 导入 utils.paths 模块
print(f"\n【utils.paths 模块】")
try:
    from utils.paths import session_data_root, papers_root, phonon_root
    
    session_root = session_data_root()
    papers = papers_root()
    phonon = phonon_root()
    
    print(f"session_data_root(): {session_root}")
    print(f"papers_root(): {papers}")
    print(f"phonon_root(): {phonon}")
    
    print(f"\n【路径验证】")
    print(f"session_data_root 存在: {session_root.exists()}")
    print(f"papers_root 存在: {papers.exists()}")
    print(f"phonon_root 存在: {phonon.exists()}")
    
    print(f"\n【路径位置】")
    if str(session_root).startswith(str(project_root)):
        print(f"❌ session_data_root 在项目内部: {session_root}")
    else:
        print(f"✅ session_data_root 在项目外部: {session_root}")
    
except Exception as e:
    print(f"❌ 导入 utils.paths 失败: {e}")
    import traceback
    traceback.print_exc()

# 6. 检查实际文件
print(f"\n【实际文件检查】")
external_path = project_root.parent / "data" / "session_data"
internal_path = project_root / "data" / "session_data"

print(f"外部路径: {external_path}")
print(f"外部路径存在: {external_path.exists()}")

print(f"\n内部路径: {internal_path}")
print(f"内部路径存在: {internal_path.exists()}")

if external_path.exists():
    papers_dir = external_path / "papers"
    if papers_dir.exists():
        csv_files = list(papers_dir.rglob("*.csv"))
        print(f"\n外部路径中的 CSV 文件数量: {len(csv_files)}")
        if csv_files:
            print(f"示例文件: {csv_files[0]}")

if internal_path.exists():
    papers_dir = internal_path / "papers"
    if papers_dir.exists():
        csv_files = list(papers_dir.rglob("*.csv"))
        print(f"\n内部路径中的 CSV 文件数量: {len(csv_files)}")
        if csv_files:
            print(f"示例文件: {csv_files[0]}")

print("\n" + "=" * 70)
print("调试完成")
print("=" * 70)

