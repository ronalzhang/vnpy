#!/bin/bash

# 加密货币跨交易所套利监控服务启动脚本

# 创建日志目录
mkdir -p logs

# 获取当前日期时间作为日志文件名
LOG_DATE=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/nohup_${LOG_DATE}.log"

# 检查是否使用交易模式
TRADE_FLAG=""
if [ "$1" = "--trade" ]; then
  TRADE_FLAG="--trade"
  echo "启动自动交易模式"
else
  echo "启动只监控模式（不会执行交易）"
fi

# 杀死现有的监控进程
echo "尝试终止现有的监控进程..."
pkill -f "python crypto_monitor_service.py"
sleep 2

# 启动监控服务
echo "启动加密货币跨交易所套利监控服务..."
nohup python crypto_monitor_service.py $TRADE_FLAG > $LOG_FILE 2>&1 &

# 获取进程ID
PID=$!
echo "服务已在后台启动，PID: $PID"
echo "日志文件: $LOG_FILE"
echo "可使用 'tail -f $LOG_FILE' 命令查看实时日志"
echo "使用 'kill $PID' 命令停止服务"

# 保存PID到文件中，便于后续管理
echo $PID > logs/monitor_pid.txt
echo "PID已保存到 logs/monitor_pid.txt"

echo "服务启动完成！" 