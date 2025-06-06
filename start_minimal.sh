#!/bin/bash
# 最小化服务启动脚本

echo "🚀 启动最小化量化服务..."

# 检查日志目录
mkdir -p logs

# 检查数据库
if [ ! -f "quantitative.db" ]; then
    echo "⚠️ 数据库文件不存在，将自动创建"
fi

# 启动最小化服务
echo "✅ 启动最小化服务..."
python3 minimal_quantitative_service.py 