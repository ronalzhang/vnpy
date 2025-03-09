"""
套利系统集成模块

本模块负责将套利系统与Web应用集成，提供以下功能：
1. 套利API接口
2. 套利数据展示
3. 套利操作控制
4. 套利状态监控

通过这个模块，用户可以在网页界面上查看套利机会、执行套利交易、监控套利状态。
"""

import os
import json
import time
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template

# 导入套利模块
from arbitrage_executor import get_arbitrage_executor, ARBITRAGE_TYPE_CROSS_EXCHANGE, ARBITRAGE_TYPE_TRIANGLE

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("arbitrage_integration")

# 创建蓝图
arbitrage_bp = Blueprint('arbitrage', __name__)

# 初始化套利执行器
executor = get_arbitrage_executor()

# API路由
@arbitrage_bp.route('/api/arbitrage/status', methods=['GET'])
def get_arbitrage_status():
    """获取套利系统状态"""
    try:
        status = executor.get_status()
        return jsonify({
            "status": "success",
            "data": status
        })
    except Exception as e:
        logger.error(f"获取套利状态失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@arbitrage_bp.route('/api/arbitrage/opportunities', methods=['GET'])
def get_arbitrage_opportunities():
    """获取套利机会列表"""
    try:
        arbitrage_type = request.args.get('type')
        limit = int(request.args.get('limit', 10))
        
        opportunities = executor.get_opportunities(arbitrage_type, limit)
        
        return jsonify({
            "status": "success",
            "data": opportunities
        })
    except Exception as e:
        logger.error(f"获取套利机会失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@arbitrage_bp.route('/api/arbitrage/tasks', methods=['GET'])
def get_arbitrage_tasks():
    """获取活跃套利任务"""
    try:
        tasks = executor.get_active_tasks()
        return jsonify({
            "status": "success",
            "data": tasks
        })
    except Exception as e:
        logger.error(f"获取套利任务失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@arbitrage_bp.route('/api/arbitrage/history', methods=['GET'])
def get_arbitrage_history():
    """获取套利历史记录"""
    try:
        limit = int(request.args.get('limit', 20))
        history = executor.get_history(limit)
        
        # 简化数据，移除过大的字段
        simplified_history = []
        for item in history:
            simplified = {
                "id": item.get("id"),
                "type": item.get("type"),
                "status": item.get("status"),
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time")
            }
            
            # 添加类型特定的字段
            if item.get("type") == ARBITRAGE_TYPE_CROSS_EXCHANGE:
                opportunity = item.get("opportunity", {})
                simplified.update({
                    "symbol": opportunity.get("symbol"),
                    "buy_exchange": opportunity.get("buy_exchange"),
                    "sell_exchange": opportunity.get("sell_exchange"),
                    "buy_price": opportunity.get("buy_price"),
                    "sell_price": opportunity.get("sell_price"),
                    "amount_usdt": item.get("amount_usdt")
                })
                
                # 添加结果信息
                result = item.get("result", {})
                if result:
                    simplified.update({
                        "profit": result.get("profit"),
                        "profit_percent": result.get("profit_percent")
                    })
            
            elif item.get("type") == ARBITRAGE_TYPE_TRIANGLE:
                opportunity = item.get("opportunity", {})
                simplified.update({
                    "exchange_id": opportunity.get("exchange_id"),
                    "profit_percent": opportunity.get("profit_percent"),
                    "amount": item.get("amount")
                })
                
                # 添加结果信息
                result = item.get("result", {})
                if result:
                    simplified.update({
                        "actual_profit": result.get("actual_profit"),
                        "actual_profit_percent": result.get("actual_profit_percent")
                    })
            
            simplified_history.append(simplified)
        
        return jsonify({
            "status": "success",
            "data": simplified_history
        })
    except Exception as e:
        logger.error(f"获取套利历史失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@arbitrage_bp.route('/api/arbitrage/start', methods=['POST'])
def start_arbitrage_system():
    """启动套利系统"""
    try:
        if executor.running:
            return jsonify({
                "status": "success",
                "message": "套利系统已经在运行中"
            })
        
        result = executor.start()
        message = "套利系统启动成功" if result else "套利系统启动失败"
        
        return jsonify({
            "status": "success" if result else "error",
            "message": message
        })
    except Exception as e:
        logger.error(f"启动套利系统失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@arbitrage_bp.route('/api/arbitrage/stop', methods=['POST'])
def stop_arbitrage_system():
    """停止套利系统"""
    try:
        if not executor.running:
            return jsonify({
                "status": "success",
                "message": "套利系统已经停止"
            })
        
        result = executor.stop()
        message = "套利系统停止成功" if result else "套利系统停止失败"
        
        return jsonify({
            "status": "success" if result else "error",
            "message": message
        })
    except Exception as e:
        logger.error(f"停止套利系统失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@arbitrage_bp.route('/api/arbitrage/config', methods=['GET', 'POST'])
def arbitrage_config():
    """获取或更新套利配置"""
    if request.method == 'GET':
        try:
            # 获取配置
            config = {
                "total_funds": executor.total_funds,
                "allocation_ratio": {
                    "cross_exchange": executor.allocated_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE] / executor.total_funds,
                    "triangle": executor.allocated_funds[ARBITRAGE_TYPE_TRIANGLE] / executor.total_funds
                },
                "exchanges": executor.exchanges,
                "symbols": executor.symbols
            }
            
            return jsonify({
                "status": "success",
                "data": config
            })
        except Exception as e:
            logger.error(f"获取套利配置失败: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            # 更新总资金
            if "total_funds" in data:
                executor.total_funds = float(data["total_funds"])
            
            # 更新资金分配比例
            if "allocation_ratio" in data:
                ratio = data["allocation_ratio"]
                cross_ratio = float(ratio.get("cross_exchange", 0.6))
                triangle_ratio = float(ratio.get("triangle", 0.4))
                
                # 验证比例和为1
                total_ratio = cross_ratio + triangle_ratio
                if abs(total_ratio - 1.0) > 0.001:
                    return jsonify({
                        "status": "error",
                        "message": "资金分配比例总和必须为1"
                    }), 400
                
                # 更新分配
                executor.allocated_funds = {
                    ARBITRAGE_TYPE_CROSS_EXCHANGE: executor.total_funds * cross_ratio,
                    ARBITRAGE_TYPE_TRIANGLE: executor.total_funds * triangle_ratio
                }
                
                # 初始化可用资金
                executor.available_funds = executor.allocated_funds.copy()
            
            # 更新交易所列表
            if "exchanges" in data:
                executor.exchanges = data["exchanges"]
            
            # 更新交易对
            if "symbols" in data:
                executor.symbols = data["symbols"]
            
            return jsonify({
                "status": "success",
                "message": "套利配置更新成功"
            })
        except Exception as e:
            logger.error(f"更新套利配置失败: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

@arbitrage_bp.route('/api/arbitrage/execute', methods=['POST'])
def execute_arbitrage():
    """手动执行套利"""
    try:
        data = request.json
        
        arbitrage_type = data.get("type")
        opportunity_id = data.get("opportunity_id")
        
        # 验证类型
        if arbitrage_type not in [ARBITRAGE_TYPE_CROSS_EXCHANGE, ARBITRAGE_TYPE_TRIANGLE]:
            return jsonify({
                "status": "error",
                "message": "无效的套利类型"
            }), 400
        
        # 查找机会
        opportunities = executor.get_opportunities(arbitrage_type)
        opportunity = None
        
        for opp in opportunities:
            if (arbitrage_type == ARBITRAGE_TYPE_CROSS_EXCHANGE and 
                f"{opp['buy_exchange']}_{opp['sell_exchange']}_{opp['symbol']}" == opportunity_id):
                opportunity = opp
                break
            elif (arbitrage_type == ARBITRAGE_TYPE_TRIANGLE and 
                f"{opp['exchange_id']}_{opp['path'][0]['symbol']}" == opportunity_id):
                opportunity = opp
                break
        
        if not opportunity:
            return jsonify({
                "status": "error",
                "message": "找不到指定的套利机会"
            }), 404
        
        # 执行套利
        if arbitrage_type == ARBITRAGE_TYPE_CROSS_EXCHANGE:
            result = executor._execute_cross_exchange_arbitrage(opportunity)
        else:  # ARBITRAGE_TYPE_TRIANGLE
            result = executor._execute_triangle_arbitrage(opportunity)
        
        return jsonify({
            "status": "success",
            "message": "套利执行已提交",
            "result": result
        })
    except Exception as e:
        logger.error(f"执行套利失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# 页面路由
@arbitrage_bp.route('/arbitrage', methods=['GET'])
def arbitrage_page():
    """套利页面"""
    return render_template('arbitrage.html')

# 初始化函数
def init_arbitrage_system(app, config=None):
    """初始化套利系统"""
    # 注册蓝图
    app.register_blueprint(arbitrage_bp)
    
    # 初始化套利执行器
    if config:
        # 配置套利执行器
        if "total_funds" in config:
            executor.total_funds = config["total_funds"]
        
        if "exchanges" in config:
            executor.exchanges = config["exchanges"]
        
        if "symbols" in config:
            executor.symbols = config["symbols"]
    
    # 尝试加载保存的状态
    state_file = "arbitrage_state.json"
    if os.path.exists(state_file):
        executor.load_state(state_file)
    
    # 启动套利执行器
    executor.start()
    
    logger.info("套利系统初始化完成")
    return executor 