#!/bin/bash

# 加密货币跨交易所套利监控服务停止脚本

# 尝试从PID文件中获取进程ID
PID_FILE="logs/monitor_pid.txt"

if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    echo "找到监控服务进程ID: $PID"
    
    # 尝试结束进程
    if ps -p $PID > /dev/null; then
        echo "正在停止监控服务..."
        kill $PID
        sleep 2
        
        # 检查进程是否已结束
        if ps -p $PID > /dev/null; then
            echo "进程未响应，强制终止..."
            kill -9 $PID
            sleep 1
        fi
        
        echo "监控服务已停止"
    else
        echo "监控服务进程不存在，可能已经停止"
    fi
    
    # 移除PID文件
    rm -f $PID_FILE
else
    # 尝试通过名称查找和终止进程
    echo "未找到PID文件，尝试通过进程名称终止..."
    pkill -f "python crypto_monitor_service.py"
    echo "已发送终止信号"
fi

# 检查是否还有监控服务在运行
if pgrep -f "python crypto_monitor_service.py" > /dev/null; then
    echo "警告：仍有监控服务进程在运行，强制终止所有实例"
    pkill -9 -f "python crypto_monitor_service.py"
    echo "所有监控服务进程已强制终止"
else
    echo "没有监控服务进程在运行"
fi

echo "停止操作完成！" 