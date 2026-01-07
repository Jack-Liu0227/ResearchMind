"""Fix all encoding issues in agent_coordinator.py"""

filepath = 'd:\\XJTU\\Research\\PHD\\Agent\\ST\\ResearchMind\\services\\agent_coordinator.py'

with open(filepath, 'rb') as f:
    raw_content = f.read()

# Replace the UTF-8 replacement character (EF BF BD) with nothing
# This character is 0xFFFD in Unicode
fixed_content = raw_content.decode('utf-8', errors='replace')

# Find and list all lines with replacement character
lines_with_issues = []
for i, line in enumerate(fixed_content.split('\n'), 1):
    if '\ufffd' in line:
        lines_with_issues.append((i, line))
        
print(f"Found {len(lines_with_issues)} lines with replacement characters")
for line_num, line in lines_with_issues[:20]:  # Show first 20
    print(f"Line {line_num}: {repr(line[:100])}")

# Manual fixes for known problematic strings
fixes = [
    ('\ufffd[WebSocket] 已发\ufffdcomplete 状\ufffd', '✅[WebSocket] 已发送complete 状态'),
    ('\ufffd[WebSocket] 准备发\ufffd', '📤[WebSocket] 准备发送'),
    ('\ufffd', ''),  # Remove remaining replacement chars
]

for old, new in fixes:
    if old in fixed_content:
        fixed_content = fixed_content.replace(old, new)
        print(f"Replaced: {repr(old)} -> {repr(new)}")

#  Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print(f"\nFixed file written")
