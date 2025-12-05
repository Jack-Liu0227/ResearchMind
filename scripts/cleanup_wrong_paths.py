"""
清理错误的路径和映射文件

问题：
1. 系统创建了错误的目录 ..datasession_data（缺少路径分隔符）
2. 映射文件中保留了错误的路径引用

解决方案：
1. 清理错误的映射文件条目
2. 提示用户手动删除错误的目录（避免误删数据）
"""

import os
import json
import sys
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "utils"))

from utils.paths import session_data_root, papers_root

def main():
    print("=" * 80)
    print("清理错误路径和映射文件")
    print("=" * 80)
    
    # 1. 获取正确的路径
    correct_session_root = session_data_root()
    correct_papers_root = papers_root()
    
    print(f"\n【正确的路径】")
    print(f"会话数据根目录: {correct_session_root}")
    print(f"论文存储目录:   {correct_papers_root}")
    
    # 2. 检查映射文件
    mapping_file = correct_session_root / "paper_sessions.json"
    print(f"\n【检查映射文件】")
    print(f"映射文件路径: {mapping_file}")
    
    if not mapping_file.exists():
        print("✅ 映射文件不存在，无需清理")
        return
    
    # 3. 读取映射文件
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        print(f"当前映射数量: {len(mappings)}")
        
        # 4. 查找错误的映射
        wrong_mappings = {}
        correct_mappings = {}
        
        for session_id, folder_path in mappings.items():
            if "..datasession_data" in folder_path or "\\..data\\session_data" in folder_path:
                wrong_mappings[session_id] = folder_path
            else:
                correct_mappings[session_id] = folder_path
        
        print(f"\n【映射分析】")
        print(f"错误映射数量: {len(wrong_mappings)}")
        print(f"正确映射数量: {len(correct_mappings)}")
        
        if wrong_mappings:
            print(f"\n【错误的映射】")
            for session_id, folder_path in list(wrong_mappings.items())[:5]:
                print(f"  {session_id}: {folder_path}")
            if len(wrong_mappings) > 5:
                print(f"  ... 还有 {len(wrong_mappings) - 5} 个错误映射")
        
        # 5. 备份原映射文件
        if wrong_mappings:
            backup_file = mapping_file.with_suffix('.json.backup')
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)
            print(f"\n✅ 已备份原映射文件到: {backup_file}")
            
            # 6. 保存清理后的映射
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(correct_mappings, f, indent=2, ensure_ascii=False)
            print(f"✅ 已清理映射文件，移除 {len(wrong_mappings)} 个错误映射")
        else:
            print("\n✅ 映射文件中没有错误路径")
    
    except Exception as e:
        print(f"❌ 处理映射文件时出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. 检查错误目录
    wrong_dir = project_root / "..datasession_data"
    print(f"\n【检查错误目录】")
    print(f"错误目录路径: {wrong_dir}")
    print(f"存在: {wrong_dir.exists()}")
    
    if wrong_dir.exists():
        print(f"\n⚠️  警告：发现错误目录")
        print(f"   路径: {wrong_dir.absolute()}")
        print(f"\n建议手动删除该目录（避免误删数据）：")
        print(f"   Windows: rmdir /s /q \"{wrong_dir.absolute()}\"")
        print(f"   Linux:   rm -rf \"{wrong_dir.absolute()}\"")
    else:
        print("✅ 错误目录不存在")
    
    print("\n" + "=" * 80)
    print("清理完成")
    print("=" * 80)

if __name__ == "__main__":
    main()

