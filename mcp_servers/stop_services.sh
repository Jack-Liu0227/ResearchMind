#!/bin/bash

echo "Stopping all services..."

# 方法1：通过进程名停止
pkill -f "uv run python"

# 方法2：如果使用PID文件
if [ -f "service_pids.txt" ]; then
    while read -r pids; do
        for pid in $pids; do
            kill $pid 2>/dev/null
        done
    done < service_pids.txt
    rm -f service_pids.txt
fi

echo "All services stopped."