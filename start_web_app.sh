#!/bin/bash

# 加密货币套利监控Web应用启动脚本

# 日志目录
LOG_DIR="./logs"
mkdir -p $LOG_DIR

# 获取当前时间
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/web_app_$TIMESTAMP.log"

# 默认参数
SIMULATE=true
TRADE=false
PORT=8888

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --real)
            SIMULATE=false
            shift
            ;;
        --trade)
            TRADE=true
            shift
            ;;
        --port)
            PORT="$2"
            shift
            shift
            ;;
        *)
            echo "未知参数: $1"
            shift
            ;;
    esac
done

# 构建命令
CMD="python web_app.py"

if [ "$SIMULATE" = true ]; then
    CMD="$CMD --simulate"
else
    CMD="$CMD --real"
fi

if [ "$TRADE" = true ]; then
    CMD="$CMD --trade"
fi

CMD="$CMD --port $PORT"

# 输出启动信息
echo "启动加密货币套利监控Web应用"
echo "运行模式: $([ "$SIMULATE" = true ] && echo '模拟数据' || echo '真实API连接')"
echo "交易功能: $([ "$TRADE" = true ] && echo '已启用' || echo '未启用（仅监控）')"
echo "Web端口: $PORT"
echo "日志文件: $LOG_FILE"
echo

# 启动服务器
echo "正在启动Web应用，日志将写入: $LOG_FILE"
echo "使用 Ctrl+C 停止服务器"
echo

# 在后台运行并将输出重定向到日志文件
nohup $CMD > "$LOG_FILE" 2>&1 &

# 存储进程ID
PID=$!
echo $PID > web_app.pid
echo "Web应用已启动，进程ID: $PID"
echo "可以使用 'kill $PID' 或 './stop_web_app.sh' 来停止Web应用"

# 显示日志
echo
echo "显示日志输出..."
tail -f "$LOG_FILE" 