#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting all services...${NC}"

# 函数：检查服务是否在运行
check_service() {
    local service_name=$1
    local port=$2
    if ss -tln | grep -q ":$port "; then
        echo -e "${GREEN}✓ $service_name is running on port $port${NC}"
        return 0
    else
        echo -e "${YELLOW}✗ $service_name is not running on port $port${NC}"
        return 1
    fi
}

# 启动数据库服务
echo -e "${YELLOW}Starting Database Service...${NC}"
uv run python database_call/server.py &
DB_PID=$!
echo "Database Service PID: $DB_PID"

# 等待服务启动
sleep 3

# 启动论文搜索服务
echo -e "${YELLOW}Starting Paper Search Service...${NC}"
uv run python paper_search/server.py &
PAPER_PID=$!
echo "Paper Search Service PID: $PAPER_PID"

# 等待服务启动
sleep 3

# 启动模拟服务
echo -e "${YELLOW}Starting Simulation Service...${NC}"
uv run python simulation/server.py &
SIM_PID=$!
echo "Simulation Service PID: $SIM_PID"

# 保存 PID 到文件（用于后续停止服务）
echo "$DB_PID $PAPER_PID $SIM_PID" > service_pids.txt

echo -e "${GREEN}All services started!${NC}"
echo -e "${YELLOW}PIDs saved to service_pids.txt${NC}"
echo -e "${GREEN}Services are running in the background.${NC}"

# 等待用户输入以停止服务
echo -e "\nPress Ctrl+C to stop all services..."

# 设置信号处理，确保优雅退出
cleanup() {
    echo -e "\n${YELLOW}Stopping all services...${NC}"
    kill $DB_PID $PAPER_PID $SIM_PID 2>/dev/null
    rm -f service_pids.txt
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT

# 保持脚本运行
while true; do
    sleep 1
done