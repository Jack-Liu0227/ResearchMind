#!/bin/bash

# ResearchMind 停止所有服务脚本

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}正在停止所有 ResearchMind 服务...${NC}\n"

# 从 PID 文件停止服务
if [ -f .service_pids ]; then
    while read pid; do
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}停止进程 $pid...${NC}"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        fi
    done < .service_pids
    rm -f .service_pids
    echo -e "${GREEN}✓ 已停止所有记录的服务${NC}"
else
    echo -e "${YELLOW}未找到 .service_pids 文件${NC}"
fi

# 按端口停止服务
echo -e "\n${YELLOW}检查并停止占用端口的进程...${NC}"

ports=(50001 50002 50003 50004 50005 50006)

for port in "${ports[@]}"; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}停止端口 $port 上的进程 $pid...${NC}"
        kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        echo -e "${GREEN}✓ 端口 $port 已释放${NC}"
    fi
done

echo -e "\n${GREEN}所有服务已停止${NC}"
