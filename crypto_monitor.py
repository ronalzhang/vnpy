#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币套利监控命令行版本
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 导入自定义模块
from vnpy_cryptoarbitrage.engine import CryptoArbitrageEngine
from vnpy_cryptoarbitrage.utility import load_json, save_json

# 配置文件路径
CONFIG_FILE = "crypto_config.json"
CONFIG_PATH = Path(current_dir).joinpath(CONFIG_FILE)


def main(use_real_api: bool = False, verbose: bool = False, enable_trading: bool = False, simulate: bool = True):
    """主函数"""
    print("\n========================================")
    print("     加密货币跨交易所套利监控     ")
    print("========================================\n")
    
    # 打印启动参数
    mode_str = "模拟模式" if simulate else "真实API模式" if use_real_api else "仅监控模式"
    trade_str = "已启用交易" if enable_trading else "仅监控"
    verbose_str = "详细日志" if verbose else "简洁日志"
    
    print(f"运行模式: {mode_str}")
    print(f"交易状态: {trade_str}")
    print(f"日志模式: {verbose_str}\n")
    
    try:
        # 准备配置
        if use_real_api and not simulate:
            print("加载API配置...")
            config = prepare_config(api_keys_required=True)
        else:
            print("加载基本配置（无需API密钥）...")
            config = prepare_config(api_keys_required=False)
        
        # 创建套利引擎
        engine = CryptoArbitrageEngine()
        init_result = engine.init_engine(
            settings=config, 
            verbose=verbose, 
            enable_trading=enable_trading,
            simulate=simulate
        )
        
        if not init_result and use_real_api and not simulate:
            print("初始化交易所API连接失败，请检查配置和网络。")
            print("切换到模拟模式...")
            engine = CryptoArbitrageEngine()
            engine.init_engine(
                settings=config, 
                verbose=verbose, 
                enable_trading=False,  # 模拟模式禁用交易
                simulate=True
            )
        
        # 显示表头
        print("\n开始监控价格差异...")
        print("\n时间         | 交易对      | 低价交易所  | 高价交易所  | 低价      | 高价      | 差价     | 差价率")
        print("-" * 100)
        
        # 主循环
        try:
            while True:
                # 获取价格数据
                prices = engine.fetch_all_prices()
                
                # 计算价格差异
                diff_data = engine.calculate_price_differences(prices)
                
                # 显示价格差异
                if diff_data:
                    # 清空屏幕
                    if not verbose:
                        print("\033c", end="")
                        print("\n时间         | 交易对      | 低价交易所  | 高价交易所  | 低价      | 高价      | 差价     | 差价率")
                        print("-" * 100)
                    
                    # 显示时间
                    now = datetime.now().strftime("%H:%M:%S")
                    
                    # 显示价格差异
                    for item in diff_data:
                        if item["price_diff_pct"] >= 0.001:  # 只显示差价大于0.1%的
                            print(f"{now} | {item['symbol']:<10} | {item['min_exchange']:<10} | {item['max_exchange']:<10} | "
                                  f"{item['min_price']:<9.2f} | {item['max_price']:<9.2f} | {item['price_diff']:<8.2f} | "
                                  f"{item['price_diff_pct']*100:<6.2f}%")
                    
                    # 显示套利机会
                    for item in diff_data:
                        if item["price_diff_pct"] >= engine.arbitrage_threshold:
                            print(f"\n*** 套利机会: {item['symbol']} - 从 {item['min_exchange']}({item['min_price']:.2f}) 买入并在 "
                                  f"{item['max_exchange']}({item['max_price']:.2f}) 卖出 - "
                                  f"差价: {item['price_diff']:.2f} ({item['price_diff_pct']*100:.2f}%) ***")
                            
                            if enable_trading:
                                print(f"    [自动交易已启用] 将执行套利交易")
                                engine.execute_arbitrage([item])
                
                # 等待更新
                time.sleep(engine.update_interval)
                
        except KeyboardInterrupt:
            print("\n用户中断，停止监控...")
        
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def prepare_config(api_keys_required: bool = True):
    """准备配置文件"""
    # 创建默认配置
    if not CONFIG_PATH.exists():
        default_config = {
            "api_keys": {
                "okex": {
                    "key": "",
                    "secret": "",
                    "passphrase": ""
                },
                "binance": {
                    "key": "",
                    "secret": ""
                },
                "bitget": {
                    "key": "",
                    "secret": "",
                    "passphrase": ""
                }
            },
            "proxy": {
                "enabled": False,
                "host": "127.0.0.1",
                "port": 7890
            },
            "update_interval": 10,
            "trade_amount": {
                "BTC/USDT": 0.001,
                "ETH/USDT": 0.01,
                "SOL/USDT": 0.1,
                "XRP/USDT": 100,
                "BNB/USDT": 0.1,
                "ADA/USDT": 100,
                "DOGE/USDT": 1000,
                "DOT/USDT": 10
            },
            "symbols": [
                "BTC/USDT",
                "ETH/USDT",
                "SOL/USDT"
            ],
            "arbitrage_threshold": 0.5,
            "close_threshold": 0.2
        }
        save_json(CONFIG_PATH, default_config)
        print(f"已创建默认配置文件: {CONFIG_PATH}")
    
    # 加载配置
    config = load_json(CONFIG_PATH)
    print(f"已加载配置文件: {CONFIG_PATH}")
    
    # 检查API配置
    if api_keys_required:
        api_configured = False
        for exchange, api_info in config.get("api_keys", {}).items():
            if api_info.get("key") and api_info.get("secret"):
                api_configured = True
                break
        
        if not api_configured:
            print("警告: 未配置任何交易所API密钥，将无法获取实时数据")
    
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="加密货币交易套利监控")
    parser.add_argument("--real", action="store_true", help="使用真实API连接")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--trade", action="store_true", help="启用交易功能")
    parser.add_argument("--simulate", action="store_true", help="使用模拟数据（无需API连接）")
    
    args = parser.parse_args()
    
    # 确定是使用真实API还是模拟模式
    use_real_api = args.real and not args.simulate
    use_simulate = args.simulate or not args.real  # 默认使用模拟模式
    
    main(
        use_real_api=use_real_api,
        verbose=args.verbose,
        enable_trading=args.trade,
        simulate=use_simulate
    ) 