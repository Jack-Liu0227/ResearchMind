"""
修复日志中的 emoji 字符，避免 GBK 编码错误

将所有日志中的 emoji 替换为纯文本标记：
- ✅ → [SUCCESS]
- ❌ → [ERROR]
- 📊 → [PROGRESS]
- 🔍 → [INFO]
- 等等
"""
import re
from pathlib import Path

# Emoji 替换映射
EMOJI_REPLACEMENTS = {
    '✅': '[SUCCESS]',
    '❌': '[ERROR]',
    '📊': '[PROGRESS]',
    '🔍': '[INFO]',
    '📄': '[FILE]',
    '📤': '[SEND]',
    '📥': '[RECEIVE]',
    '💬': '[MESSAGE]',
    '🔧': '[CONFIG]',
    '🆕': '[NEW]',
    '⚠️': '[WARNING]',
    '🎯': '[TARGET]',
    '🔒': '[LOCK]',
    '💎': '[BILLING]',
    '💰': '[PAYMENT]',
    '🤖': '[AGENT]',
    '📝': '[NOTE]',
    '🚀': '[START]',
    '🛑': '[STOP]',
    '📚': '[LIBRARY]',
    '🔄': '[REFRESH]',
    '📁': '[FOLDER]',
    '🎉': '[CELEBRATE]',
}

def fix_emoji_in_file(file_path: Path) -> int:
    """
    修复单个文件中的 emoji
    
    Returns:
        替换的次数
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # 替换所有 emoji
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            content = content.replace(emoji, replacement)
        
        # 如果有修改，写回文件
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            # 计算替换次数
            count = sum(original_content.count(emoji) for emoji in EMOJI_REPLACEMENTS.keys())
            return count
        
        return 0
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return 0

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    
    # 需要处理的文件列表
    files_to_fix = [
        project_root / "mcp_servers" / "paper_search" / "server.py",
        project_root / "services" / "message_handler.py",
        project_root / "services" / "agent_coordinator.py",
        project_root / "services" / "websocket_server.py",
    ]
    
    # 也可以递归处理所有 Python 文件
    # files_to_fix = list(project_root.rglob("*.py"))
    
    total_replacements = 0
    files_modified = 0
    
    print("🔧 开始修复日志中的 emoji 字符...")
    print(f"📁 项目根目录: {project_root}")
    print(f"📝 待处理文件数: {len(files_to_fix)}")
    print()
    
    for file_path in files_to_fix:
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue
        
        count = fix_emoji_in_file(file_path)
        if count > 0:
            files_modified += 1
            total_replacements += count
            print(f"✅ {file_path.relative_to(project_root)}: 替换了 {count} 个 emoji")
    
    print()
    print("="*60)
    print(f"✅ 修复完成！")
    print(f"   修改文件数: {files_modified}")
    print(f"   总替换次数: {total_replacements}")
    print()
    print("💡 建议：")
    print("   1. 重启后端服务以应用更改")
    print("   2. 测试批量分析和报告生成功能")
    print("   3. 检查日志是否还有编码错误")

if __name__ == "__main__":
    main()

