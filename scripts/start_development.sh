#!/bin/bash

# ResearchMind开发环境启动脚本
# 用于快速启动开发环境和测试MCP服务器

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    echo "=================================================="
    print_message $BLUE "$1"
    echo "=================================================="
}

print_success() {
    print_message $GREEN "✅ $1"
}

print_warning() {
    print_message $YELLOW "⚠️  $1"
}

print_error() {
    print_message $RED "❌ $1"
}

# 检查Python环境
check_python() {
    print_header "检查Python环境"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3未安装，请先安装Python 3.9或更高版本"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_success "Python版本: $python_version"
    
    # 检查虚拟环境
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "虚拟环境已激活: $VIRTUAL_ENV"
    else
        print_warning "建议使用虚拟环境"
        read -p "是否创建并激活虚拟环境? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 -m venv venv
            source venv/bin/activate
            print_success "虚拟环境已创建并激活"
        fi
    fi
}

# 安装依赖
install_dependencies() {
    print_header "安装依赖包"
    
    if [ -f "requirements.txt" ]; then
        print_message $BLUE "安装Python依赖..."
        pip install -r requirements.txt
        print_success "Python依赖安装完成"
    else
        print_warning "requirements.txt文件不存在"
    fi
    
    # 检查Google ADK
    if python3 -c "import google.adk" 2>/dev/null; then
        print_success "Google ADK已安装"
    else
        print_message $BLUE "安装Google ADK..."
        pip install google-adk
        print_success "Google ADK安装完成"
    fi
    
    # 检查MCP
    if python3 -c "import mcp" 2>/dev/null; then
        print_success "MCP库已安装"
    else
        print_message $BLUE "安装MCP库..."
        pip install mcp
        print_success "MCP库安装完成"
    fi
}

# 检查环境变量
check_environment() {
    print_header "检查环境变量"
    
    # 创建.env文件模板（如果不存在）
    if [ ! -f ".env" ]; then
        print_message $BLUE "创建.env文件模板..."
        cat > .env << EOF
# ResearchMind环境变量配置

# API密钥
MATERIALS_PROJECT_API_KEY=your_materials_project_api_key_here
GOOGLE_SCHOLAR_API_KEY=your_google_scholar_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# MatterSim配置
MATTERSIM_LICENSE=your_mattersim_license_here
MATTERSIM_MODEL_PATH=/path/to/mattersim/models

# CrystaLLM配置
CRYSTALLM_MODEL_PATH=/path/to/crystallm/models

# 其他配置
PYTHONPATH=.
CUDA_VISIBLE_DEVICES=0
EOF
        print_success ".env文件已创建，请编辑并填入正确的API密钥"
    else
        print_success ".env文件已存在"
    fi
    
    # 加载环境变量
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
}

# 测试MCP服务器
test_mcp_servers() {
    print_header "测试MCP服务器"
    
    # 测试文献检索MCP服务器
    print_message $BLUE "测试文献检索MCP服务器..."
    if python3 -c "
import asyncio
import sys
sys.path.append('mcp_servers/literature')
from tools.arxiv_search import ArxivSearchTool

async def test():
    tool = ArxivSearchTool()
    result = await tool.search('machine learning', max_results=2)
    await tool.close()
    return result['status'] == 'success'

print(asyncio.run(test()))
" 2>/dev/null | grep -q "True"; then
        print_success "文献检索MCP服务器测试通过"
    else
        print_warning "文献检索MCP服务器测试失败（可能需要网络连接）"
    fi
}

# 启动选项菜单
show_menu() {
    print_header "ResearchMind启动选项"
    echo "请选择启动模式："
    echo "1) 交互式模式 (推荐)"
    echo "2) ADK Web界面"
    echo "3) 测试MCP服务器"
    echo "4) 运行特定研究任务"
    echo "5) 退出"
    echo ""
}

# 启动交互式模式
start_interactive() {
    print_header "启动交互式模式"
    python3 main_mcp.py --interactive
}

# 启动ADK Web界面
start_web() {
    print_header "启动ADK Web界面"
    print_message $BLUE "正在启动ADK Web界面..."
    print_message $YELLOW "请在浏览器中访问 http://localhost:8080"
    print_message $YELLOW "选择 'research_coordinator' 智能体开始使用"
    
    # 检查agents目录是否在当前目录
    if [ -d "agents" ]; then
        adk web --port 8080
    else
        print_error "agents目录不存在，请确保在项目根目录运行此脚本"
    fi
}

# 测试特定功能
test_functionality() {
    print_header "测试MCP服务器功能"
    
    echo "选择要测试的功能："
    echo "1) 文献检索"
    echo "2) 论文分析"
    echo "3) 报告生成"
    echo "4) 返回主菜单"
    
    read -p "请选择 (1-4): " choice
    
    case $choice in
        1)
            print_message $BLUE "测试ArXiv搜索..."
            python3 mcp_servers/literature/tools/arxiv_search.py
            ;;
        2)
            print_message $BLUE "测试论文分析..."
            python3 mcp_servers/literature/tools/paper_analysis.py
            ;;
        3)
            print_message $BLUE "测试Google Scholar搜索..."
            python3 mcp_servers/literature/tools/scholar_search.py
            ;;
        4)
            return
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 运行特定研究任务
run_research_task() {
    print_header "运行研究任务"
    
    echo "预定义研究任务："
    echo "1) 锂电池材料调研"
    echo "2) 钙钛矿太阳能电池研究"
    echo "3) 机器学习在材料科学中的应用"
    echo "4) 自定义研究主题"
    echo "5) 返回主菜单"
    
    read -p "请选择 (1-5): " choice
    
    case $choice in
        1)
            python3 main_mcp.py --research "锂电池材料的最新研究进展" --workflow sequential
            ;;
        2)
            python3 main_mcp.py --research "钙钛矿太阳能电池效率优化方法" --workflow parallel
            ;;
        3)
            python3 main_mcp.py --research "机器学习在新材料发现中的应用" --workflow iterative
            ;;
        4)
            read -p "请输入研究主题: " topic
            python3 main_mcp.py --research "$topic" --workflow sequential
            ;;
        5)
            return
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 主函数
main() {
    print_header "ResearchMind开发环境启动器"
    print_message $BLUE "基于Google ADK多智能体架构和MCP工具生态"
    
    # 检查环境
    check_python
    install_dependencies
    check_environment
    test_mcp_servers
    
    # 主循环
    while true; do
        show_menu
        read -p "请选择 (1-5): " choice
        
        case $choice in
            1)
                start_interactive
                ;;
            2)
                start_web
                ;;
            3)
                test_functionality
                ;;
            4)
                run_research_task
                ;;
            5)
                print_success "感谢使用ResearchMind！"
                exit 0
                ;;
            *)
                print_error "无效选择，请输入1-5"
                ;;
        esac
        
        echo ""
        read -p "按回车键继续..." -r
    done
}

# 运行主函数
main "$@"
