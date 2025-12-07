#!/usr/bin/env python3
"""
修复 Hydration 错误的自动化脚本

此脚本会：
1. 清除前端构建缓存
2. 重新构建前端
3. 提供修复建议
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
UI_DIR = PROJECT_ROOT / "ui"

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_step(step, text):
    """打印步骤"""
    print(f"[步骤 {step}] {text}")

def run_command(cmd, cwd=None):
    """运行命令"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    print_header("ResearchMind Hydration 错误修复工具")
    
    # 步骤 1: 清除前端缓存
    print_step(1, "清除前端构建缓存...")
    cache_dirs = [
        UI_DIR / "node_modules" / ".vite",
        UI_DIR / "dist",
        UI_DIR / ".vite",
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            print(f"  删除: {cache_dir}")
            shutil.rmtree(cache_dir, ignore_errors=True)
    
    print("  ✅ 缓存清除完成\n")
    
    # 步骤 2: 检查 Node.js 和 npm
    print_step(2, "检查 Node.js 环境...")
    success, output = run_command("node --version")
    if success:
        print(f"  Node.js 版本: {output.strip()}")
    else:
        print("  ❌ Node.js 未安装或不在 PATH 中")
        return
    
    success, output = run_command("npm --version")
    if success:
        print(f"  npm 版本: {output.strip()}")
    else:
        print("  ❌ npm 未安装或不在 PATH 中")
        return
    
    print("  ✅ 环境检查通过\n")
    
    # 步骤 3: 重新安装依赖（可选）
    print_step(3, "检查依赖...")
    node_modules = UI_DIR / "node_modules"
    if not node_modules.exists():
        print("  node_modules 不存在，正在安装依赖...")
        success, output = run_command("npm install", cwd=UI_DIR)
        if success:
            print("  ✅ 依赖安装完成")
        else:
            print(f"  ❌ 依赖安装失败:\n{output}")
            return
    else:
        print("  ✅ 依赖已存在\n")
    
    # 步骤 4: 重新构建
    print_step(4, "重新构建前端...")
    print("  正在构建，请稍候...")
    success, output = run_command("npm run build", cwd=UI_DIR)
    if success:
        print("  ✅ 构建完成")
    else:
        print(f"  ⚠️ 构建可能有警告:\n{output[:500]}")
    
    # 步骤 5: 提供修复建议
    print_header("修复建议")
    
    print("1. 清除浏览器缓存和 localStorage:")
    print("   - 打开浏览器开发者工具 (F12)")
    print("   - 进入 Console 标签")
    print("   - 运行: localStorage.clear(); location.reload()")
    print()
    
    print("2. 使用修复工具页面:")
    print("   - 启动应用后访问: http://localhost:50010/fix-storage.html")
    print("   - 点击 '修复存储' 按钮")
    print()
    
    print("3. 在无痕模式下测试:")
    print("   - 打开浏览器的无痕/隐私模式")
    print("   - 访问: http://localhost:50010")
    print("   - 如果正常，说明是浏览器扩展或缓存问题")
    print()
    
    print("4. 禁用浏览器扩展:")
    print("   - 特别是 React DevTools、Redux DevTools")
    print("   - 在扩展管理中临时禁用它们")
    print()
    
    print_header("启动应用")
    print("运行以下命令启动应用:")
    print()
    print("  cd ui")
    print("  npm run dev")
    print()
    print("然后访问: http://localhost:50010")
    print()
    
    print_header("完成")
    print("如果问题仍然存在，请查看:")
    print("  - ui/fix-hydration-error.md (详细修复指南)")
    print("  - http://localhost:50010/fix-storage.html (在线修复工具)")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

