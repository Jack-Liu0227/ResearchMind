"""
路径配置验证脚本

验证所有路径配置是否正确，包括：
1. 会话数据根目录
2. 论文存储目录
3. 声子/仿真数据目录
4. 数据库文件路径
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

# 导入数据库模型
sys.path.insert(0, str(project_root / "services" / "database"))
from models import DB_PATH, DB_DIR

print("=" * 70)
print("路径配置验证")
print("=" * 70)

# 1. 环境变量
print("\n【环境变量】")
print(f"SESSION_DATA_ROOT: {os.getenv('SESSION_DATA_ROOT', '(未设置，使用默认值)')}")
print(f"PAPERS_ROOT:       {os.getenv('PAPERS_ROOT', '(未设置，使用默认值)')}")
print(f"PHONON_ROOT:       {os.getenv('PHONON_ROOT', '(未设置，使用默认值)')}")

# 2. 实际路径
print("\n【实际路径】")
session_root = session_data_root()
papers = papers_root()
phonon = phonon_root()

print(f"会话数据根目录:   {session_root}")
print(f"论文存储目录:     {papers}")
print(f"声子/仿真目录:    {phonon}")
print(f"数据库目录:       {DB_DIR}")
print(f"数据库文件:       {DB_PATH}")

# 3. 路径验证
print("\n【路径验证】")
checks = [
    (session_root.is_absolute(), f"会话数据根目录是绝对路径: {session_root}"),
    (papers.is_absolute(), f"论文存储目录是绝对路径: {papers}"),
    (phonon.is_absolute(), f"声子/仿真目录是绝对路径: {phonon}"),
    (DB_PATH.is_absolute(), f"数据库文件是绝对路径: {DB_PATH}"),
    (papers.parent == session_root, f"论文目录在会话数据根目录下"),
    (phonon.parent == session_root, f"声子目录在会话数据根目录下"),
    (DB_DIR == session_root.parent, f"数据库目录是会话数据根目录的父目录"),
]

all_passed = True
for check, description in checks:
    status = "✅" if check else "❌"
    print(f"{status} {description}")
    all_passed = all_passed and check

# 4. 目录创建
print("\n【目录创建】")
try:
    ensure_dirs(session_root, papers, phonon, DB_DIR)
    print("✅ 所有目录已创建（如果不存在）")
    
    # 检查目录是否存在
    dirs_to_check = [
        (session_root, "会话数据根目录"),
        (papers, "论文存储目录"),
        (phonon, "声子/仿真目录"),
        (DB_DIR, "数据库目录"),
    ]
    
    for dir_path, name in dirs_to_check:
        if dir_path.exists():
            print(f"  ✅ {name}: {dir_path}")
        else:
            print(f"  ❌ {name} 不存在: {dir_path}")
            all_passed = False
            
except Exception as e:
    print(f"❌ 目录创建失败: {e}")
    all_passed = False

# 5. 总结
print("\n" + "=" * 70)
if all_passed:
    print("🎉 所有路径配置验证通过！")
    print("\n预期数据存储位置：")
    print(f"  - 会话数据: {session_root}")
    print(f"  - 论文文件: {papers}")
    print(f"  - 仿真结果: {phonon}")
    print(f"  - 数据库:   {DB_PATH}")
    sys.exit(0)
else:
    print("❌ 路径配置验证失败，请检查上述错误。")
    sys.exit(1)

