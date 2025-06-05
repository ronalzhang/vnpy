#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥配置向导 - 安全配置币安API
"""

import json
import os
import getpass
from datetime import datetime

def setup_api_keys():
    """配置API密钥向导"""
    print("🔐 币安API密钥配置向导")
    print("=" * 50)
    print()
    print("⚠️  重要安全提示:")
    print("1. 确保您的API密钥有足够的权限（现货交易）")
    print("2. 建议启用IP白名单限制")
    print("3. 切勿与他人分享您的API密钥")
    print("4. 设置合理的交易权限和限额")
    print()
    
    # 读取现有配置
    config_path = "crypto_config.json"
    config = {}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"读取现有配置失败: {e}")
    
    # 获取API密钥
    print("请输入您的币安API信息:")
    print("(如果不想修改某项，直接按回车跳过)")
    print()
    
    current_api_key = config.get('binance', {}).get('api_key', '')
    if current_api_key:
        print(f"当前API Key: {current_api_key[:8]}...{current_api_key[-8:] if len(current_api_key) > 16 else current_api_key}")
    
    api_key = input("请输入API Key: ").strip()
    if not api_key and current_api_key:
        api_key = current_api_key
        print("使用现有API Key")
    
    if not api_key:
        print("❌ 必须提供API Key！")
        return False
    
    print()
    current_secret = config.get('binance', {}).get('api_secret', '')
    if current_secret:
        print(f"当前Secret Key: {current_secret[:8]}...{current_secret[-8:] if len(current_secret) > 16 else current_secret}")
    
    secret_key = getpass.getpass("请输入Secret Key (输入时不显示): ").strip()
    if not secret_key and current_secret:
        secret_key = current_secret
        print("使用现有Secret Key")
    
    if not secret_key:
        print("❌ 必须提供Secret Key！")
        return False
    
    # 更新配置
    if 'binance' not in config:
        config['binance'] = {}
    
    config['binance']['api_key'] = api_key
    config['binance']['api_secret'] = secret_key
    
    # 设置其他默认配置
    if 'auto_trading' not in config:
        config['auto_trading'] = {
            "enabled": False,  # 默认禁用自动交易
            "max_position_size": 0.02,  # 最大仓位2%
            "stop_loss": 0.02,
            "take_profit": 0.05
        }
    
    # 备份现有配置
    if os.path.exists(config_path):
        backup_path = f"crypto_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.rename(config_path, backup_path)
        print(f"✅ 已备份原配置: {backup_path}")
    
    # 保存新配置
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("✅ API配置保存成功！")
        print()
        print("📊 配置概览:")
        print(f"  API Key: {api_key[:8]}...{api_key[-8:]}")
        print(f"  Secret:  {secret_key[:8]}...{secret_key[-8:]}")
        print(f"  自动交易: {'启用' if config['auto_trading']['enabled'] else '禁用'}")
        print(f"  最大仓位: {config['auto_trading']['max_position_size']:.1%}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False

def test_api_connection():
    """测试API连接"""
    print("🔍 测试API连接...")
    
    try:
        from clear_all_positions import PositionCleaner
        
        cleaner = PositionCleaner()
        balances = cleaner.get_account_balances()
        
        if balances:
            print("✅ API连接成功！")
            print(f"📊 发现 {len(balances)} 种资产")
            
            # 显示主要资产
            total_value = 0.0
            for balance in balances[:5]:  # 只显示前5种
                price = cleaner.get_asset_price(balance['asset'])
                value = balance['total'] * price
                total_value += value
                print(f"  {balance['asset']}: {balance['total']:.8f} (约 ${value:.2f})")
            
            if len(balances) > 5:
                print(f"  ... 还有 {len(balances) - 5} 种资产")
            
            print(f"💰 总价值估算: ${total_value:.2f}")
            return True
        else:
            print("❌ API连接失败或账户为空")
            return False
            
    except Exception as e:
        print(f"❌ 测试连接失败: {e}")
        return False

def main():
    """主函数"""
    success = setup_api_keys()
    
    if success:
        print("🔧 是否要测试API连接？ (y/n): ", end="")
        test_choice = input().strip().lower()
        
        if test_choice in ['y', 'yes', '是']:
            test_api_connection()
    
    print()
    print("🎯 下一步操作建议:")
    print("1. 运行 python clear_all_positions.py 查看持仓")
    print("2. 如需清仓，选择选项2")
    print("3. 配置完成后可启动安全自动交易")

if __name__ == "__main__":
    main() 