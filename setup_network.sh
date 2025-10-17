#!/bin/bash

# ResearchMind 网络配置脚本
# 自动检测 IP 地址并更新 .env 配置

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          ResearchMind 网络配置工具                       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

# 检测操作系统
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGw;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${BLUE}检测到操作系统: ${MACHINE}${NC}\n"

# 获取 IP 地址
get_ip_address() {
    if [ "$MACHINE" = "Linux" ]; then
        # Linux: 获取第一个非 lo 接口的 IP
        ip addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1
    elif [ "$MACHINE" = "Mac" ]; then
        # macOS: 获取 en0 接口的 IP
        ifconfig en0 | grep 'inet ' | awk '{print $2}'
    else
        # Windows (Git Bash/MinGW)
        ipconfig | grep -oP '(?<=IPv4.*:\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1
    fi
}

IP_ADDRESS=$(get_ip_address)

if [ -z "$IP_ADDRESS" ]; then
    echo -e "${YELLOW}⚠️  无法自动检测 IP 地址${NC}"
    echo -e "${YELLOW}请手动输入你的 IP 地址:${NC}"
    read -p "IP 地址: " IP_ADDRESS
fi

echo -e "${GREEN}✓ 检测到 IP 地址: ${IP_ADDRESS}${NC}\n"

# 显示配置选项
echo -e "${BLUE}请选择配置模式:${NC}"
echo "1) 本地访问 (localhost) - 仅本机可访问"
echo "2) 局域网访问 (${IP_ADDRESS}) - 局域网内设备可访问"
echo "3) 所有网络访问 (0.0.0.0) - 所有网络可访问"
echo ""
read -p "请选择 [1-3]: " choice

case $choice in
    1)
        API_HOST="localhost"
        echo -e "${GREEN}✓ 选择: 本地访问模式${NC}"
        ;;
    2)
        API_HOST="$IP_ADDRESS"
        echo -e "${GREEN}✓ 选择: 局域网访问模式${NC}"
        ;;
    3)
        API_HOST="0.0.0.0"
        echo -e "${GREEN}✓ 选择: 所有网络访问模式${NC}"
        ;;
    *)
        echo -e "${YELLOW}无效选择，使用默认: 局域网访问模式${NC}"
        API_HOST="$IP_ADDRESS"
        ;;
esac

# 备份原配置
if [ -f .env ]; then
    cp .env .env.backup
    echo -e "${GREEN}✓ 已备份原配置到 .env.backup${NC}"
fi

# 更新 .env 配置
echo -e "\n${BLUE}更新配置文件...${NC}"

# 更新 VITE_API_URL
if grep -q "^VITE_API_URL=" .env; then
    sed -i.bak "s|^VITE_API_URL=.*|VITE_API_URL=http://${API_HOST}:50001|" .env
    echo -e "${GREEN}✓ 更新 VITE_API_URL=http://${API_HOST}:50001${NC}"
else
    echo "VITE_API_URL=http://${API_HOST}:50001" >> .env
    echo -e "${GREEN}✓ 添加 VITE_API_URL=http://${API_HOST}:50001${NC}"
fi

# 更新 VITE_WS_URL
if grep -q "^VITE_WS_URL=" .env; then
    sed -i.bak "s|^VITE_WS_URL=.*|VITE_WS_URL=ws://${API_HOST}:50002/ws|" .env
    echo -e "${GREEN}✓ 更新 VITE_WS_URL=ws://${API_HOST}:50002/ws${NC}"
else
    echo "VITE_WS_URL=ws://${API_HOST}:50002/ws" >> .env
    echo -e "${GREEN}✓ 添加 VITE_WS_URL=ws://${API_HOST}:50002/ws${NC}"
fi

# 清理临时文件
rm -f .env.bak

echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  配置完成！                               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BLUE}📡 服务地址 (可暴露端口 50001-50005):${NC}"
echo -e "   前端 UI:        http://${API_HOST}:50001"
echo -e "   后端 API:       http://${API_HOST}:50002"
echo -e "   WebSocket:      ws://${API_HOST}:50003"
echo -e "   API 文档:       http://${API_HOST}:50002/docs"

if [ "$API_HOST" != "localhost" ] && [ "$API_HOST" != "0.0.0.0" ]; then
    echo -e "\n${YELLOW}💡 提示:${NC}"
    echo -e "   局域网内的其他设备可以通过以下地址访问:"
    echo -e "   ${GREEN}http://${API_HOST}:50001${NC}"
fi

echo -e "\n${BLUE}下一步:${NC}"
echo -e "   运行 ${GREEN}./start_all.sh${NC} 或 ${GREEN}.\start_all.ps1${NC} 启动所有服务"
echo ""
