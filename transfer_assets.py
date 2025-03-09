"""
加密货币资产转移模块

本模块实现了交易所之间的资产转移功能，包括：
1. 交易所余额检查
2. 提币请求创建
3. 提币状态监控
4. 充值确认
5. 转账手续费计算

用于支持经典跨交易所套利策略。
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import ccxt

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("asset_transfer")

# 转账状态常量
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_FAILED = "failed"

# 交易所配置信息（示例）
EXCHANGE_CONFIGS = {
    "binance": {
        "api_key": "",
        "api_secret": "",
        "withdrawal_fees": {
            "BTC": 0.0005,
            "ETH": 0.005,
            "USDT": 1.0
        }
    },
    "okx": {
        "api_key": "",
        "api_secret": "",
        "passphrase": "",
        "withdrawal_fees": {
            "BTC": 0.0006,
            "ETH": 0.006,
            "USDT": 1.5
        }
    },
    "bitget": {
        "api_key": "",
        "api_secret": "",
        "withdrawal_fees": {
            "BTC": 0.0007,
            "ETH": 0.007,
            "USDT": 2.0
        }
    }
}

# 币种网络映射
NETWORK_MAPPING = {
    "BTC": "BTC",
    "ETH": "ETH",
    "USDT": "TRC20"  # 使用Tron网络转USDT手续费低
}

class AssetTransfer:
    """资产转移管理器"""
    
    def __init__(self, exchange_configs=None):
        """初始化资产转移管理器"""
        self.exchange_configs = exchange_configs or EXCHANGE_CONFIGS
        self.exchanges = {}
        self.transfer_history = []
        self.active_transfers = {}
        
        # 初始化交易所连接
        self._init_exchanges()
    
    def _init_exchanges(self):
        """初始化交易所连接"""
        for exchange_id, config in self.exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'apiKey': config.get('api_key', ''),
                    'secret': config.get('api_secret', ''),
                    'password': config.get('passphrase', ''),
                    'enableRateLimit': True,
                })
                logger.info(f"初始化交易所 {exchange_id} 成功")
            except Exception as e:
                logger.error(f"初始化交易所 {exchange_id} 失败: {e}")
    
    def check_balance(self, exchange_id: str, currency: str) -> float:
        """检查指定交易所的指定币种余额"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                logger.error(f"交易所 {exchange_id} 未初始化")
                return 0
            
            # 获取余额
            balance = exchange.fetch_balance()
            free_balance = balance.get('free', {}).get(currency, 0)
            
            logger.info(f"交易所 {exchange_id} 的 {currency} 可用余额为: {free_balance}")
            return free_balance
        except Exception as e:
            logger.error(f"获取交易所 {exchange_id} 的 {currency} 余额失败: {e}")
            return 0
    
    def get_deposit_address(self, exchange_id: str, currency: str, network: str = None) -> Dict:
        """获取币种的充值地址"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                logger.error(f"交易所 {exchange_id} 未初始化")
                return {}
            
            # 如果未指定网络，使用默认映射
            if not network:
                network = NETWORK_MAPPING.get(currency, currency)
            
            # 获取充值地址
            params = {"network": network} if network else {}
            address_info = exchange.fetch_deposit_address(currency, params)
            
            logger.info(f"获取交易所 {exchange_id} 的 {currency} 充值地址成功")
            return address_info
        except Exception as e:
            logger.error(f"获取交易所 {exchange_id} 的 {currency} 充值地址失败: {e}")
            return {}
    
    def withdraw(
        self, 
        from_exchange: str, 
        to_exchange: str, 
        currency: str, 
        amount: float,
        network: str = None
    ) -> Dict:
        """从一个交易所提币到另一个交易所"""
        try:
            # 检查余额是否足够
            available_balance = self.check_balance(from_exchange, currency)
            if available_balance < amount:
                logger.error(f"交易所 {from_exchange} 的 {currency} 余额不足: {available_balance} < {amount}")
                return {"status": STATUS_FAILED, "message": "余额不足"}
            
            # 获取目标交易所的充值地址
            to_address_info = self.get_deposit_address(to_exchange, currency, network)
            if not to_address_info or 'address' not in to_address_info:
                logger.error(f"获取交易所 {to_exchange} 的 {currency} 充值地址失败")
                return {"status": STATUS_FAILED, "message": "获取充值地址失败"}
            
            to_address = to_address_info['address']
            to_tag = to_address_info.get('tag')  # 某些币种需要标签/备注
            
            # 如果未指定网络，使用默认映射
            if not network:
                network = NETWORK_MAPPING.get(currency, currency)
            
            # 发起提币请求
            from_exchange_obj = self.exchanges.get(from_exchange)
            if not from_exchange_obj:
                logger.error(f"交易所 {from_exchange} 未初始化")
                return {"status": STATUS_FAILED, "message": "源交易所未初始化"}
            
            # 提币参数
            params = {"network": network}
            if to_tag:
                params["tag"] = to_tag
            
            # 执行提币
            withdrawal = from_exchange_obj.withdraw(
                currency, 
                amount, 
                to_address, 
                tag=to_tag, 
                params=params
            )
            
            # 记录转账
            transfer_id = withdrawal.get('id', str(time.time()))
            transfer_record = {
                "id": transfer_id,
                "from_exchange": from_exchange,
                "to_exchange": to_exchange,
                "currency": currency,
                "amount": amount,
                "network": network,
                "status": STATUS_PENDING,
                "txid": withdrawal.get('txid'),
                "timestamp": time.time(),
                "fee": withdrawal.get('fee', {}).get('cost', 0)
            }
            
            self.transfer_history.append(transfer_record)
            self.active_transfers[transfer_id] = transfer_record
            
            logger.info(f"从交易所 {from_exchange} 提币 {amount} {currency} 到交易所 {to_exchange} 成功，交易ID: {transfer_id}")
            return {**transfer_record, "status": STATUS_PENDING}
        
        except Exception as e:
            logger.error(f"从交易所 {from_exchange} 提币到交易所 {to_exchange} 失败: {e}")
            return {"status": STATUS_FAILED, "message": str(e)}
    
    def check_transfer_status(self, transfer_id: str) -> Dict:
        """检查转账状态"""
        if transfer_id not in self.active_transfers:
            logger.error(f"转账记录 {transfer_id} 不存在")
            return {"status": STATUS_FAILED, "message": "转账记录不存在"}
        
        transfer = self.active_transfers[transfer_id]
        from_exchange = transfer['from_exchange']
        currency = transfer['currency']
        txid = transfer.get('txid')
        
        try:
            # 获取提币历史
            from_exchange_obj = self.exchanges.get(from_exchange)
            if not from_exchange_obj or not txid:
                return {**transfer}
            
            # 查询提币状态
            withdrawals = from_exchange_obj.fetch_withdrawals(currency)
            for withdrawal in withdrawals:
                if withdrawal['id'] == txid:
                    # 更新状态
                    status = withdrawal['status']
                    if status == 'ok' or status == 'complete' or status == 'completed':
                        transfer['status'] = STATUS_CONFIRMED
                    elif status == 'failed' or status == 'canceled':
                        transfer['status'] = STATUS_FAILED
                    else:
                        transfer['status'] = STATUS_PENDING
                    
                    # 如果已确认或失败，从活动转账中移除
                    if transfer['status'] in [STATUS_CONFIRMED, STATUS_FAILED]:
                        del self.active_transfers[transfer_id]
                    
                    return {**transfer}
            
            # 如果未找到记录，保持原状态
            return {**transfer}
        
        except Exception as e:
            logger.error(f"检查转账状态失败: {e}")
            return {**transfer}
    
    def check_all_active_transfers(self) -> List[Dict]:
        """检查所有活动转账状态"""
        results = []
        for transfer_id in list(self.active_transfers.keys()):
            status = self.check_transfer_status(transfer_id)
            results.append(status)
        return results
    
    def calculate_transfer_cost(self, from_exchange: str, to_exchange: str, currency: str, amount: float) -> Dict:
        """计算转账成本（手续费+时间）"""
        # 获取提币手续费
        from_exchange_config = self.exchange_configs.get(from_exchange, {})
        withdrawal_fees = from_exchange_config.get("withdrawal_fees", {})
        fee = withdrawal_fees.get(currency, 0)
        
        # 估计确认时间（根据币种和网络）
        estimated_time = {
            "BTC": 30,  # 分钟
            "ETH": 15,
            "USDT": 10  # USDT在TRC20网络上
        }.get(currency, 20)
        
        # 计算手续费百分比
        fee_percent = (fee / amount) * 100 if amount > 0 else 0
        
        return {
            "from_exchange": from_exchange,
            "to_exchange": to_exchange,
            "currency": currency,
            "amount": amount,
            "fee": fee,
            "fee_percent": fee_percent,
            "estimated_time_minutes": estimated_time
        }

# 单例模式
_asset_transfer_instance = None

def get_asset_transfer(exchange_configs=None):
    """获取资产转移管理器单例"""
    global _asset_transfer_instance
    if _asset_transfer_instance is None:
        _asset_transfer_instance = AssetTransfer(exchange_configs)
    return _asset_transfer_instance

# 使用示例
if __name__ == "__main__":
    # 初始化转账管理器
    transfer_manager = get_asset_transfer()
    
    # 查询余额
    balance = transfer_manager.check_balance("binance", "USDT")
    print(f"Binance USDT余额: {balance}")
    
    # 获取充值地址
    address = transfer_manager.get_deposit_address("okx", "USDT", "TRC20")
    print(f"OKX USDT充值地址: {address}")
    
    # 计算转账成本
    cost = transfer_manager.calculate_transfer_cost("binance", "okx", "USDT", 100)
    print(f"转账成本: {cost}") 