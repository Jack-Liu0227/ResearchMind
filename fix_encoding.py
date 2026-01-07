"""Fix encoding issues in agent_coordinator.py"""

import re

def fix_file_encoding(filepath):
    """Fix encoding and quote issues in the file"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Replace problematic replacement characters followed by '?'  
    content = content.replace('\ufffd?', '息')  # Common case for "信息"
    content = content.replace('\ufffd', '')  # Remove remaining replacement chars
    
    # Fix specific problematic strings
    replacements = {
        "已停止响�?": "已停止响应",
        "已停止�?": "已停止",
        "自动重�?": "自动重试",
        "错误消�?": "错误消息",
        "自动清�?": "自动清理",
        "保留最�?": "保留最近",
        "数据�?": "数据库",
        "热导�?": "热导率",
        "声子�?": "声子谱",
        "个文�?": "个文件",
        "个结�?": "个结构",
        "on doesn't": "on does not",  # Fix quote issue
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

if __name__ == '__main__':
    fix_file_encoding('d:\\XJTU\\Research\\PHD\\Agent\\ST\\ResearchMind\\services\\agent_coordinator.py')
