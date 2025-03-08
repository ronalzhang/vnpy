#!/bin/bash

# 加密货币套利监控Web应用停止脚本

# 检查PID文件
PID_FILE="web_app.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Web应用似乎未运行，未找到PID文件: $PID_FILE"
    exit 1
fi

# 读取PID
PID=$(cat "$PID_FILE")

if [ -z "$PID" ]; then
    echo "PID文件为空"
    rm -f "$PID_FILE"
    exit 1
fi

# 检查进程是否存在
if ! ps -p $PID > /dev/null; then
    echo "进程 $PID 不存在，可能已经停止"
    rm -f "$PID_FILE"
    exit 0
fi

# 尝试优雅地停止进程
echo "正在停止加密货币套利监控Web应用 (PID: $PID)..."
kill $PID

# 等待进程停止
COUNTER=0
while ps -p $PID > /dev/null && [ $COUNTER -lt 10 ]; do
    echo "等待Web应用停止..."
    sleep 1
    COUNTER=$((COUNTER+1))
done

# 如果进程仍在运行，强制终止
if ps -p $PID > /dev/null; then
    echo "Web应用未能正常停止，正在强制终止进程..."
    kill -9 $PID
fi

# 删除PID文件
rm -f "$PID_FILE"

echo "Web应用已停止"
exit 0 