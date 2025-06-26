#!/bin/bash
# 量化交易系统最小化启动脚本
# 仅启动核心组件，适合资源受限的环境

echo "🚀 启动量化交易系统2.0 (最小化模式)..."

# 设置工作目录
cd "$(dirname "$0")"

# 创建必要的目录
mkdir -p logs data backups

# 检查数据库和配置文件
if [ ! -f "quantitative.db" ]; then
    echo "⚠️ 警告: 数据库文件不存在，请确保已初始化数据库"
fi

if [ ! -f "auto_trading_config.json" ]; then
    echo "⚠️ 警告: 配置文件不存在，将使用默认配置"
fi

# 启动稳定性监控 (后台运行)
echo "启动系统稳定性监控..."
python3 stability_monitor.py > logs/stability_monitor.log 2>&1 &
sleep 2

# 启动自动交易引擎 (后台运行)
echo "启动自动交易引擎..."
python3 auto_trading_engine.py > logs/auto_trading_engine.log 2>&1 &
sleep 2

# 显示运行状态
echo "系统已启动，检查状态..."
python3 start_auto_trading.py --status

echo ""
echo "====================================================="
echo "🎉 量化交易系统已在最小化模式下启动"
echo "📊 使用以下命令查看运行状态:"
echo "    python3 start_auto_trading.py --status"
echo "💡 使用以下命令停止系统:"
echo "    python3 start_auto_trading.py --stop"
echo "=====================================================" 