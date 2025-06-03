#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
量化交易系统集成测试脚本
测试主要功能模块是否正常工作
"""

import sys
import json
import time
import requests
from pathlib import Path
from loguru import logger

# 配置测试参数
BASE_URL = "http://localhost:8888"
TEST_TIMEOUT = 5

def test_module_imports():
    """测试模块导入"""
    logger.info("🔍 测试模块导入...")
    
    try:
        # 测试量化交易服务模块导入
        from quantitative_service import quantitative_service, StrategyType
        logger.success("✅ 量化交易模块导入成功")
        
        # 测试Flask应用导入
        from web_app import app
        logger.success("✅ Flask应用导入成功")
        
        return True
    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False

def test_quantitative_service():
    """测试量化交易服务"""
    logger.info("🔍 测试量化交易服务...")
    
    try:
        from quantitative_service import quantitative_service, StrategyType
        
        # 测试数据库初始化
        quantitative_service.init_database()
        logger.success("✅ 数据库初始化成功")
        
        # 测试创建策略
        strategy_id = quantitative_service.create_strategy(
            name="测试策略",
            strategy_type=StrategyType.MOMENTUM,
            symbol="BTC/USDT",
            position_size=1000,
            parameters={"lookback_period": 20, "threshold": 0.02}
        )
        logger.success(f"✅ 策略创建成功，ID: {strategy_id}")
        
        # 测试获取策略列表
        strategies = quantitative_service.get_strategies()
        logger.success(f"✅ 获取策略列表成功，数量: {len(strategies)}")
        
        # 测试获取信号
        signals = quantitative_service.get_signals(10)
        logger.success(f"✅ 获取信号成功，数量: {len(signals)}")
        
        # 测试获取持仓
        positions = quantitative_service.get_positions()
        logger.success(f"✅ 获取持仓成功，数量: {len(positions)}")
        
        # 测试删除策略
        quantitative_service.delete_strategy(strategy_id)
        logger.success("✅ 策略删除成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 量化交易服务测试失败: {e}")
        return False

def test_web_server():
    """测试Web服务器启动"""
    logger.info("🔍 测试Web服务器连接...")
    
    try:
        # 测试主页访问
        response = requests.get(f"{BASE_URL}/", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            logger.success("✅ 主页访问成功")
        else:
            logger.warning(f"⚠️ 主页状态码: {response.status_code}")
        
        # 测试量化交易页面
        response = requests.get(f"{BASE_URL}/quantitative.html", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            logger.success("✅ 量化交易页面访问成功")
        else:
            logger.warning(f"⚠️ 量化交易页面状态码: {response.status_code}")
        
        # 测试操作日志页面
        response = requests.get(f"{BASE_URL}/operations-log.html", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            logger.success("✅ 操作日志页面访问成功")
        else:
            logger.warning(f"⚠️ 操作日志页面状态码: {response.status_code}")
        
        return True
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ Web服务器未启动或无法连接")
        return False
    except Exception as e:
        logger.error(f"❌ Web服务器测试失败: {e}")
        return False

def test_api_endpoints():
    """测试API端点"""
    logger.info("🔍 测试API端点...")
    
    try:
        # 测试量化交易策略API
        response = requests.get(f"{BASE_URL}/api/quantitative/strategies", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                logger.success("✅ 策略列表API正常")
            else:
                logger.warning(f"⚠️ 策略列表API返回错误: {data.get('message')}")
        
        # 测试信号API
        response = requests.get(f"{BASE_URL}/api/quantitative/signals", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                logger.success("✅ 信号API正常")
            else:
                logger.warning(f"⚠️ 信号API返回错误: {data.get('message')}")
        
        # 测试持仓API
        response = requests.get(f"{BASE_URL}/api/quantitative/positions", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                logger.success("✅ 持仓API正常")
            else:
                logger.warning(f"⚠️ 持仓API返回错误: {data.get('message')}")
        
        # 测试绩效API
        response = requests.get(f"{BASE_URL}/api/quantitative/performance", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                logger.success("✅ 绩效API正常")
            else:
                logger.warning(f"⚠️ 绩效API返回错误: {data.get('message')}")
        
        return True
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ 无法连接到API服务器")
        return False
    except Exception as e:
        logger.error(f"❌ API端点测试失败: {e}")
        return False

def test_file_structure():
    """测试文件结构"""
    logger.info("🔍 测试文件结构...")
    
    required_files = [
        "quantitative_service.py",
        "web_app.py",
        "templates/quantitative.html",
        "templates/operations-log.html",
        "static/css/quantitative.css",
        "static/js/quantitative.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            logger.success(f"✅ {file_path} 存在")
    
    if missing_files:
        logger.error(f"❌ 缺少文件: {missing_files}")
        return False
    else:
        logger.success("✅ 所有必需文件都存在")
        return True

def test_strategy_creation():
    """测试策略创建API"""
    logger.info("🔍 测试策略创建API...")
    
    try:
        # 创建测试策略
        strategy_data = {
            "name": "API测试策略",
            "strategy_type": "momentum",
            "symbol": "ETH/USDT",
            "position_size": 500,
            "parameters": {
                "lookback_period": 15,
                "threshold": 0.03
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/quantitative/strategies",
            json=strategy_data,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                strategy_id = data['data']['strategy_id']
                logger.success(f"✅ 策略创建API正常，策略ID: {strategy_id}")
                
                # 删除测试策略
                delete_response = requests.delete(
                    f"{BASE_URL}/api/quantitative/strategies/{strategy_id}",
                    timeout=TEST_TIMEOUT
                )
                if delete_response.status_code == 200:
                    logger.success("✅ 策略删除API正常")
                
                return True
            else:
                logger.warning(f"⚠️ 策略创建API返回错误: {data.get('message')}")
        else:
            logger.warning(f"⚠️ 策略创建API状态码: {response.status_code}")
        
        return False
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ 无法连接到API服务器")
        return False
    except Exception as e:
        logger.error(f"❌ 策略创建API测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始量化交易系统集成测试")
    
    tests = [
        ("模块导入测试", test_module_imports),
        ("文件结构测试", test_file_structure),
        ("量化交易服务测试", test_quantitative_service),
        ("Web服务器测试", test_web_server),
        ("API端点测试", test_api_endpoints),
        ("策略创建API测试", test_strategy_creation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 执行: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.success(f"✅ {test_name} 通过")
            else:
                logger.error(f"❌ {test_name} 失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 异常: {e}")
    
    logger.info(f"\n📊 测试总结: {passed}/{total} 通过")
    
    if passed == total:
        logger.success("🎉 所有测试通过！系统集成成功！")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} 个测试失败，请检查相关组件")
        return False

if __name__ == "__main__":
    main() 