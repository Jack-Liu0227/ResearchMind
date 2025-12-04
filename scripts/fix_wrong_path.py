"""
修复错误路径问题 - 清理错误的 ..datasession_data 目录
"""

import os
import sys
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "utils"))

print("=" * 70)
print("修复错误路径问题")
print("=" * 70)

# 1. 加载环境变量
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"\n✅ 已加载 .env 文件")
else:
    print(f"\n❌ .env 文件不存在")
    sys.exit(1)

# 2. 检查环境变量
session_data_root_env = os.getenv('SESSION_DATA_ROOT')
print(f"\n【环境变量】")
print(f"SESSION_DATA_ROOT: {session_data_root_env}")

# 3. 获取正确的路径
from utils.paths import session_data_root, papers_root
correct_session_root = session_data_root()
correct_papers_root = papers_root()

print(f"\n【正确的路径】")
print(f"session_data_root: {correct_session_root}")
print(f"papers_root: {correct_papers_root}")

# 4. 检查错误的路径
wrong_path = project_root / "..datasession_data"
print(f"\n【错误的路径】")
print(f"错误路径: {wrong_path}")
print(f"存在: {wrong_path.exists()}")

if wrong_path.exists():
    # 5. 列出错误路径中的文件
    print(f"\n【错误路径中的文件】")
    files = list(wrong_path.rglob("*"))
    print(f"文件数量: {len(files)}")
    
    if files:
        print(f"\n前 10 个文件:")
        for f in files[:10]:
            print(f"  - {f.relative_to(wrong_path)}")
    
    # 6. 询问是否删除
    print(f"\n{'=' * 70}")
    print(f"⚠️  警告：即将删除错误的目录及其所有内容！")
    print(f"{'=' * 70}")
    response = input(f"\n是否删除 {wrong_path}？(yes/no): ")
    
    if response.lower() == 'yes':
        try:
            shutil.rmtree(wrong_path)
            print(f"\n✅ 已删除错误的目录: {wrong_path}")
        except Exception as e:
            print(f"\n❌ 删除失败: {e}")
            sys.exit(1)
    else:
        print(f"\n❌ 用户取消操作")
        sys.exit(0)
else:
    print(f"\n✅ 错误路径不存在，无需清理")

# 7. 检查并清理正确路径中的错误映射文件
correct_mapping_file = correct_session_root / "paper_sessions.json"
print(f"\n【检查映射文件】")
print(f"映射文件: {correct_mapping_file}")
print(f"存在: {correct_mapping_file.exists()}")

if correct_mapping_file.exists():
    import json
    try:
        with open(correct_mapping_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        print(f"\n当前映射数量: {len(mappings)}")
        
        # 检查是否有错误的路径
        wrong_mappings = {k: v for k, v in mappings.items() if "..datasession_data" in v}
        
        if wrong_mappings:
            print(f"\n发现 {len(wrong_mappings)} 个错误的映射:")
            for session_id, path in wrong_mappings.items():
                print(f"  - {session_id}: {path}")
            
            print(f"\n{'=' * 70}")
            print(f"⚠️  警告：即将清理错误的映射！")
            print(f"{'=' * 70}")
            response = input(f"\n是否清理错误的映射？(yes/no): ")
            
            if response.lower() == 'yes':
                # 移除错误的映射
                for session_id in wrong_mappings.keys():
                    del mappings[session_id]
                
                # 保存更新后的映射
                with open(correct_mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(mappings, f, indent=2, ensure_ascii=False)
                
                print(f"\n✅ 已清理 {len(wrong_mappings)} 个错误的映射")
                print(f"剩余映射数量: {len(mappings)}")
            else:
                print(f"\n❌ 用户取消操作")
        else:
            print(f"\n✅ 没有发现错误的映射")
    
    except Exception as e:
        print(f"\n❌ 处理映射文件失败: {e}")
        import traceback
        traceback.print_exc()

# 8. 验证修复结果
print(f"\n{'=' * 70}")
print(f"修复完成 - 验证结果")
print(f"{'=' * 70}")

print(f"\n【验证】")
print(f"错误路径存在: {wrong_path.exists()}")
print(f"正确路径存在: {correct_session_root.exists()}")

if correct_mapping_file.exists():
    with open(correct_mapping_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    wrong_count = sum(1 for v in mappings.values() if "..datasession_data" in v)
    print(f"错误映射数量: {wrong_count}")

print(f"\n✅ 修复完成！")
print(f"\n下一步：")
print(f"1. 重启所有服务")
print(f"2. 测试论文搜索功能")
print(f"3. 确认文件保存到正确的外部路径")

