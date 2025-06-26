#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场环境分类器
识别不同市场状态并推荐最适合的策略类型

作者: 系统架构优化团队
日期: 2025年6月8日
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
import json
import os
from datetime import datetime, timedelta
from collections import deque
import talib
import sqlite3
import pickle

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/market_classifier.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 从配置文件中导入市场状态和策略类型
try:
    from strategy_parameters_config import MARKET_STATES, STRATEGY_TYPES
except ImportError:
    # 如果找不到导入，则使用默认值
    MARKET_STATES = {
        "TRENDING_UP": "趋势上涨",
        "TRENDING_DOWN": "趋势下跌",
        "SIDEWAYS": "横盘震荡",
        "VOLATILE": "高波动",
        "LOW_VOLATILITY": "低波动",
        "BREAKOUT": "突破",
        "REVERSAL": "反转",
        "RANGING": "区间震荡",
    }
    
    STRATEGY_TYPES = [
        "momentum", "mean_reversion", "breakout", 
        "grid_trading", "trend_following", "high_frequency",
        "scalping", "arbitrage", "pattern_recognition",
    ]


class MarketEnvironmentClassifier:
    """市场环境分类器 - 识别不同市场状态并推荐策略"""
    
    def __init__(self, config_file="market_classifier_config.json"):
        """初始化市场环境分类器"""
        self.config = self._load_config(config_file)
        
        # 市场状态历史
        self.market_state_history = []
        # 状态持续时间记录
        self.state_duration_history = {}
        # 最近使用的特征缓存
        self.feature_cache = {}
        # 市场状态转换计数
        self.state_transitions = {}
        # 市场状态运行时间追踪
        self.state_start_time = {}
        # 策略表现在各市场状态下的历史记录
        self.strategy_market_performance = {}
        
        # 时序模型状态
        self.long_state_history = deque(maxlen=100)
        self.medium_state_history = deque(maxlen=24)
        self.short_state_history = deque(maxlen=6)
        
        # 加载模型
        self._load_models()
        
        logger.info("🚀 市场环境分类器初始化完成")
    
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "feature_window": 50,
            "trend_lookback": 20,
            "volatility_window": 14,
            "trend_strength_threshold": 0.03,
            "volatility_threshold": 0.02,
            "breakout_threshold": 2.5,
            "reversal_threshold": 0.05,
            "persist_threshold": 3,
            "performance_history_length": 100,
            "market_state_ttl": 12,  # 市场状态生存时间(小时)
            "classification_sampling_interval": 15,  # 分钟
            "advanced_features_enabled": true,
            "strategy_market_maps": {
                "TRENDING_UP": ["trend_following", "momentum"],
                "TRENDING_DOWN": ["trend_following", "momentum"],
                "SIDEWAYS": ["mean_reversion", "grid_trading"],
                "VOLATILE": ["breakout", "high_frequency"],
                "LOW_VOLATILITY": ["scalping", "grid_trading"],
                "BREAKOUT": ["breakout", "momentum"],
                "REVERSAL": ["mean_reversion", "pattern_recognition"],
                "RANGING": ["grid_trading", "mean_reversion"]
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # 合并配置与默认值
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return default_config
    
    def _load_models(self):
        """加载市场分类模型"""
        self.models = {}
        model_files = {
            "state_classifier": "models/market_state_classifier.pkl",
            "state_predictor": "models/market_state_predictor.pkl"
        }
        
        # 检查模型文件是否存在并尝试加载
        for name, filepath in model_files.items():
            try:
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        self.models[name] = pickle.load(f)
                    logger.info(f"模型 {name} 加载成功")
                else:
                    logger.warning(f"模型文件 {filepath} 不存在")
            except Exception as e:
                logger.error(f"加载模型 {name} 失败: {e}")
    
    def save_state(self, filepath="data/market_classifier_state.pkl"):
        """保存分类器状态"""
        try:
            state = {
                "market_state_history": self.market_state_history,
                "state_duration_history": self.state_duration_history,
                "state_transitions": self.state_transitions,
                "strategy_market_performance": self.strategy_market_performance,
                "long_state_history": list(self.long_state_history),
                "medium_state_history": list(self.medium_state_history),
                "short_state_history": list(self.short_state_history),
                "timestamp": datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(state, f)
            logger.info(f"市场分类器状态已保存到 {filepath}")
            return True
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
            return False
    
    def load_state(self, filepath="data/market_classifier_state.pkl"):
        """加载分类器状态"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    state = pickle.load(f)
                
                self.market_state_history = state.get("market_state_history", [])
                self.state_duration_history = state.get("state_duration_history", {})
                self.state_transitions = state.get("state_transitions", {})
                self.strategy_market_performance = state.get("strategy_market_performance", {})
                
                # 恢复队列状态
                self.long_state_history = deque(state.get("long_state_history", []), maxlen=100)
                self.medium_state_history = deque(state.get("medium_state_history", []), maxlen=24)
                self.short_state_history = deque(state.get("short_state_history", []), maxlen=6)
                
                logger.info(f"市场分类器状态已从 {filepath} 加载")
                return True
            else:
                logger.warning(f"状态文件 {filepath} 不存在")
                return False
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
            return False
    
    def detect_market_state(self, ohlcv_data: pd.DataFrame) -> str:
        """
        检测当前市场状态
        :param ohlcv_data: OHLCV数据框，包含 open, high, low, close, volume 列
        :return: 市场状态
        """
        # 检查数据完整性
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlcv_data.columns for col in required_columns):
            logger.warning("OHLCV数据缺少必要列")
            return "SIDEWAYS"  # 默认状态
        
        if len(ohlcv_data) < self.config["feature_window"]:
            logger.warning(f"数据点数不足，最小要求 {self.config['feature_window']} 个数据点")
            return "SIDEWAYS"  # 默认状态
        
        # 准备特征
        features = self._extract_features(ohlcv_data)
        
        # 尝试使用模型分类
        if "state_classifier" in self.models and self.config["advanced_features_enabled"]:
            try:
                # 转换特征为模型输入格式
                model_input = self._prepare_model_input(features)
                # 使用模型预测
                state = self._predict_with_model(model_input)
                logger.info(f"模型分类市场状态: {state}")
                return state
            except Exception as e:
                logger.error(f"模型分类失败: {e}")
                # 继续使用规则分类作为备选
        
        # 使用规则进行分类
        return self._rule_based_classification(features, ohlcv_data)
    
    def _extract_features(self, ohlcv_data: pd.DataFrame) -> Dict:
        """提取市场特征"""
        df = ohlcv_data.copy()
        prices = df['close'].values
        
        # 基本特征计算
        window = self.config["feature_window"]
        trend_lookback = self.config["trend_lookback"]
        vol_window = self.config["volatility_window"]
        
        # 计算各项特征
        features = {}
        
        # 趋势特征
        features['price_change'] = (prices[-1] / prices[-(trend_lookback+1)] - 1)
        features['trend_strength'] = np.abs(prices[-1] - prices[-trend_lookback]) / (np.std(prices[-window:]) * np.sqrt(trend_lookback))
        
        # 波动性特征
        features['volatility'] = np.std(prices[-vol_window:]) / np.mean(prices[-vol_window:])
        returns = np.diff(prices[-window:]) / prices[-(window):-1]
        features['volatility_recent'] = np.std(returns[-vol_window:])
        
        # 计算ATR (Average True Range)
        try:
            features['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=vol_window)[-1]
            features['atr_ratio'] = features['atr'] / prices[-1]
        except:
            features['atr'] = np.std(prices[-vol_window:])
            features['atr_ratio'] = features['atr'] / prices[-1]
        
        # 突破特征
        if len(prices) > 2*window:
            long_term_std = np.std(prices[-2*window:])
            recent_move = abs(prices[-1] - prices[-5])
            features['breakout_strength'] = recent_move / long_term_std
        else:
            features['breakout_strength'] = 0.0
        
        # 区间特征
        high_low_range = (np.max(prices[-window:]) - np.min(prices[-window:])) / np.mean(prices[-window:])
        features['range_bound'] = high_low_range
        
        # 趋势方向
        features['is_uptrend'] = int(prices[-1] > prices[-trend_lookback])
        
        # 反转特征
        if len(prices) > window:
            prev_trend = (prices[-window//2] - prices[-window]) / prices[-window]
            recent_trend = (prices[-1] - prices[-window//2]) / prices[-window//2]
            features['trend_change'] = recent_trend - prev_trend
            features['reversal_strength'] = abs(features['trend_change'])
        else:
            features['trend_change'] = 0.0
            features['reversal_strength'] = 0.0
        
        # 成交量特征
        if 'volume' in df.columns:
            volumes = df['volume'].values
            features['volume_change'] = volumes[-1] / np.mean(volumes[-window:])
            
            # 成交量趋势
            if len(volumes) > trend_lookback:
                volume_trend = (volumes[-1] - volumes[-trend_lookback]) / volumes[-trend_lookback]
                features['volume_trend'] = volume_trend
            else:
                features['volume_trend'] = 0.0
        else:
            features['volume_change'] = 1.0
            features['volume_trend'] = 0.0
        
        # 加入技术指标
        try:
            # RSI
            features['rsi'] = talib.RSI(prices, timeperiod=14)[-1]
            
            # 布林带宽度
            upper, middle, lower = talib.BBANDS(prices, timeperiod=20)
            features['bb_width'] = (upper[-1] - lower[-1]) / middle[-1]
            
            # MACD
            macd, signal, hist = talib.MACD(prices)
            features['macd_hist'] = hist[-1]
            
            # ADX (趋势强度指标)
            features['adx'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)[-1]
        except:
            features['rsi'] = 50.0
            features['bb_width'] = 0.04
            features['macd_hist'] = 0.0
            features['adx'] = 25.0
        
        # 更新特征缓存
        self.feature_cache = features
        
        return features
    
    def _prepare_model_input(self, features: Dict) -> np.ndarray:
        """准备模型输入格式"""
        # 从特征字典创建模型输入数组
        feature_list = [
            'trend_strength', 'volatility', 'breakout_strength', 'range_bound',
            'is_uptrend', 'reversal_strength', 'volume_change', 'rsi',
            'bb_width', 'adx'
        ]
        
        # 创建输入数组
        X = np.array([features.get(feat, 0.0) for feat in feature_list]).reshape(1, -1)
        return X
    
    def _predict_with_model(self, model_input: np.ndarray) -> str:
        """使用模型进行预测"""
        model = self.models.get("state_classifier")
        if model is None:
            raise ValueError("模型未加载")
            
        # 预测市场状态类别
        try:
            # 假设模型输出是状态的索引或名称
            prediction = model.predict(model_input)[0]
            
            # 如果预测是索引，转换为状态名称
            if isinstance(prediction, (int, np.integer)):
                states = list(MARKET_STATES.keys())
                if 0 <= prediction < len(states):
                    return states[prediction]
            
            # 如果预测已经是字符串
            if isinstance(prediction, str) and prediction in MARKET_STATES:
                return prediction
            
            # 预测结果不符合预期
            logger.warning(f"模型预测结果无法解析: {prediction}")
            return "SIDEWAYS"  # 默认状态
            
        except Exception as e:
            logger.error(f"模型预测失败: {e}")
            return "SIDEWAYS"  # 默认状态
    
    def _rule_based_classification(self, features: Dict, df: pd.DataFrame) -> str:
        """基于规则的市场状态分类"""
        # 获取配置阈值
        trend_threshold = self.config["trend_strength_threshold"]
        volatility_threshold = self.config["volatility_threshold"]
        breakout_threshold = self.config["breakout_threshold"]
        reversal_threshold = self.config["reversal_threshold"]
        
        # 判断突破状态
        if features['breakout_strength'] > breakout_threshold:
            return "BREAKOUT"
        
        # 判断反转状态
        if features['reversal_strength'] > reversal_threshold:
            return "REVERSAL"
        
        # 判断趋势状态
        if features['trend_strength'] > trend_threshold:
            return "TRENDING_UP" if features['is_uptrend'] else "TRENDING_DOWN"
        
        # 判断波动性
        if features['volatility'] > volatility_threshold:
            return "VOLATILE"
        
        # 判断低波动性
        if features['volatility'] < volatility_threshold * 0.5:
            return "LOW_VOLATILITY"
        
        # 判断横盘区间
        if features['range_bound'] < 0.03:
            return "SIDEWAYS"
        
        # 默认为区间震荡
        return "RANGING"
    
    def update_market_state_history(self, state: str) -> None:
        """更新市场状态历史"""
        now = datetime.now()
        
        # 记录状态及时间
        self.market_state_history.append({
            "state": state,
            "timestamp": now.isoformat()
        })
        
        # 保持历史记录在合理范围内
        max_history = self.config.get("performance_history_length", 100)
        if len(self.market_state_history) > max_history:
            self.market_state_history = self.market_state_history[-max_history:]
        
        # 更新状态持续时间
        if state not in self.state_start_time:
            # 新状态
            self.state_start_time[state] = now
        
        # 更新状态转换计数
        if len(self.market_state_history) >= 2:
            prev_state = self.market_state_history[-2]["state"]
            if prev_state != state:
                transition_key = f"{prev_state}->{state}"
                self.state_transitions[transition_key] = self.state_transitions.get(transition_key, 0) + 1
                
                # 记录之前状态的持续时间
                if prev_state in self.state_start_time:
                    duration = (now - self.state_start_time[prev_state]).total_seconds() / 3600  # 小时
                    if prev_state not in self.state_duration_history:
                        self.state_duration_history[prev_state] = []
                    self.state_duration_history[prev_state].append(duration)
                    
                # 更新当前状态开始时间
                self.state_start_time[state] = now
        
        # 更新状态队列
        self.short_state_history.append(state)
        
        # 每小时更新中期状态历史一次
        hour_now = now.replace(minute=0, second=0, microsecond=0)
        if not self.medium_state_history or \
           datetime.fromisoformat(self.market_state_history[-2]["timestamp"]).replace(minute=0, second=0, microsecond=0) != hour_now:
            most_common_state = self._get_most_common_state(list(self.short_state_history))
            self.medium_state_history.append(most_common_state)
        
        # 每天更新长期状态历史一次
        day_now = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if not self.long_state_history or \
           datetime.fromisoformat(self.market_state_history[-2]["timestamp"]).replace(hour=0, minute=0, second=0, microsecond=0) != day_now:
            most_common_state = self._get_most_common_state(list(self.medium_state_history))
            self.long_state_history.append(most_common_state)
    
    def _get_most_common_state(self, states: List[str]) -> str:
        """获取最常见的状态"""
        if not states:
            return "SIDEWAYS"
        
        # 计数
        state_counts = {}
        for state in states:
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # 找出最多的状态
        most_common = max(state_counts.items(), key=lambda x: x[1])
        return most_common[0]
    
    def get_current_market_state(self) -> Dict:
        """获取当前市场状态信息"""
        if not self.market_state_history:
            return {
                "state": "SIDEWAYS",
                "timestamp": datetime.now().isoformat(),
                "duration": 0,
                "confidence": 0.5,
                "features": {},
                "next_predicted_state": "SIDEWAYS"
            }
        
        # 当前状态
        current = self.market_state_history[-1]
        state = current["state"]
        timestamp = current["timestamp"]
        
        # 计算持续时间
        start_time = self.state_start_time.get(state, datetime.fromisoformat(timestamp))
        duration_hours = (datetime.now() - start_time).total_seconds() / 3600
        
        # 估计置信度
        confidence = self._estimate_state_confidence(state)
        
        # 预测下一个状态
        next_state = self._predict_next_state(state)
        
        return {
            "state": state,
            "timestamp": timestamp,
            "duration": round(duration_hours, 2),
            "confidence": confidence,
            "features": self.feature_cache,
            "next_predicted_state": next_state,
            "recent_states": list(self.short_state_history),
            "hourly_states": list(self.medium_state_history)[-5:] if self.medium_state_history else []
        }
    
    def _estimate_state_confidence(self, state: str) -> float:
        """估计状态置信度"""
        # 计算状态在短期历史中的频率
        if not self.short_state_history:
            return 0.5
        
        # 状态持久性检查
        state_count = list(self.short_state_history).count(state)
        persistence = state_count / len(self.short_state_history)
        
        # 使用特征值估计置信度
        confidence = persistence
        
        # 根据特征调整置信度
        if state in ["TRENDING_UP", "TRENDING_DOWN"] and self.feature_cache:
            trend_strength = self.feature_cache.get('trend_strength', 0)
            # 趋势越强，置信度越高
            confidence = confidence * 0.6 + min(1.0, trend_strength / 0.1) * 0.4
        
        elif state == "VOLATILE" and self.feature_cache:
            volatility = self.feature_cache.get('volatility', 0)
            # 波动性越高，置信度越高
            confidence = confidence * 0.6 + min(1.0, volatility / 0.05) * 0.4
        
        elif state == "BREAKOUT" and self.feature_cache:
            breakout = self.feature_cache.get('breakout_strength', 0)
            # 突破强度越高，置信度越高
            confidence = confidence * 0.6 + min(1.0, breakout / 3.0) * 0.4
        
        # 限制置信度范围
        return round(max(0.1, min(0.95, confidence)), 2)
    
    def _predict_next_state(self, current_state: str) -> str:
        """预测下一个可能的市场状态"""
        # 如果有模型，使用模型预测
        if "state_predictor" in self.models and self.feature_cache:
            try:
                # 准备模型输入
                model_input = self._prepare_prediction_input(current_state)
                
                # 使用状态预测模型
                model = self.models["state_predictor"]
                prediction = model.predict(model_input)[0]
                
                # 解析预测结果
                if isinstance(prediction, (int, np.integer)):
                    states = list(MARKET_STATES.keys())
                    if 0 <= prediction < len(states):
                        return states[prediction]
                
                if isinstance(prediction, str) and prediction in MARKET_STATES:
                    return prediction
                
                # 预测结果无法解析，使用规则预测
            except Exception as e:
                logger.error(f"状态预测失败: {e}")
        
        # 规则预测：基于状态转换频率
        next_states = {}
        for transition, count in self.state_transitions.items():
            if transition.startswith(f"{current_state}->"):
                next_state = transition.split("->")[1]
                next_states[next_state] = next_states.get(next_state, 0) + count
        
        # 如果有历史转换记录，选择最常见的下一个状态
        if next_states:
            return max(next_states.items(), key=lambda x: x[1])[0]
        
        # 无历史数据时的预测规则
        if current_state == "TRENDING_UP":
            return "SIDEWAYS"  # 上升趋势后横盘概率高
        elif current_state == "TRENDING_DOWN":
            return "SIDEWAYS"  # 下降趋势后横盘概率高
        elif current_state == "BREAKOUT":
            return "TRENDING_UP" if self.feature_cache.get('is_uptrend', 0) else "TRENDING_DOWN"
        elif current_state == "VOLATILE":
            return "RANGING"  # 高波动后进入震荡概率高
        elif current_state == "SIDEWAYS":
            # 横盘后各种状态都有可能，随机选择
            return "BREAKOUT"  # 一般横盘后突破概率较高
        else:
            # 默认预测保持当前状态
            return current_state
    
    def _prepare_prediction_input(self, current_state: str) -> np.ndarray:
        """准备状态预测模型输入"""
        # 编码当前状态
        state_idx = list(MARKET_STATES.keys()).index(current_state) if current_state in MARKET_STATES else 0
        
        # 特征向量
        features = list(self.feature_cache.values()) if self.feature_cache else [0.0] * 10
        
        # 组合输入：状态 + 特征
        X = np.array([state_idx] + features).reshape(1, -1)
        return X
    
    def record_strategy_performance(self, strategy_id: str, state: str, 
                                   performance_metrics: Dict) -> None:
        """记录策略在特定市场状态下的表现"""
        if strategy_id not in self.strategy_market_performance:
            self.strategy_market_performance[strategy_id] = {}
        
        if state not in self.strategy_market_performance[strategy_id]:
            self.strategy_market_performance[strategy_id][state] = []
        
        # 记录表现
        self.strategy_market_performance[strategy_id][state].append({
            "timestamp": datetime.now().isoformat(),
            "metrics": performance_metrics
        })
        
        # 限制历史记录长度
        max_records = self.config.get("performance_history_length", 100)
        if len(self.strategy_market_performance[strategy_id][state]) > max_records:
            self.strategy_market_performance[strategy_id][state] = \
                self.strategy_market_performance[strategy_id][state][-max_records:]
    
    def get_best_strategies_for_state(self, state: str, top_n: int = 2) -> List[str]:
        """获取特定市场状态下表现最好的策略"""
        # 首先使用配置的策略-市场映射
        if "strategy_market_maps" in self.config and state in self.config["strategy_market_maps"]:
            return self.config["strategy_market_maps"][state][:top_n]
        
        # 如果没有性能数据，返回默认推荐
        if not self.strategy_market_performance:
            default_recommendations = {
                "TRENDING_UP": ["trend_following", "momentum"],
                "TRENDING_DOWN": ["trend_following", "momentum"],
                "SIDEWAYS": ["mean_reversion", "grid_trading"],
                "VOLATILE": ["breakout", "high_frequency"],
                "LOW_VOLATILITY": ["scalping", "grid_trading"],
                "BREAKOUT": ["breakout", "momentum"],
                "REVERSAL": ["mean_reversion", "pattern_recognition"],
                "RANGING": ["grid_trading", "mean_reversion"]
            }
            return default_recommendations.get(state, ["mean_reversion", "grid_trading"])[:top_n]
        
        # 计算各策略在当前状态下的平均表现
        strategy_scores = {}
        
        for strategy_id, state_data in self.strategy_market_performance.items():
            if state in state_data and state_data[state]:
                # 计算该状态下的平均绩效
                performance = [record["metrics"].get("score", 0) for record in state_data[state]]
                if performance:
                    avg_score = sum(performance) / len(performance)
                    strategy_scores[strategy_id] = avg_score
        
        # 如果有性能数据，按分数排序选择最佳策略
        if strategy_scores:
            top_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
            return [s[0] for s in top_strategies[:top_n]]
        
        # 无数据时返回默认推荐
        default_map = {
            "TRENDING_UP": ["trend_following", "momentum"],
            "TRENDING_DOWN": ["trend_following", "momentum"],
            "SIDEWAYS": ["mean_reversion", "grid_trading"],
            "VOLATILE": ["breakout", "high_frequency"],
            "LOW_VOLATILITY": ["scalping", "grid_trading"],
            "BREAKOUT": ["breakout", "momentum"],
            "REVERSAL": ["mean_reversion", "pattern_recognition"],
            "RANGING": ["grid_trading", "mean_reversion"]
        }
        
        return default_map.get(state, ["mean_reversion", "grid_trading"])[:top_n]
    
    def get_strategy_market_matrix(self) -> Dict:
        """获取策略-市场状态适配矩阵"""
        
        # 初始化适配矩阵
        matrix = {}
        for strategy_type in STRATEGY_TYPES:
            matrix[strategy_type] = {}
            for state in MARKET_STATES:
                matrix[strategy_type][state] = {
                    "score": 0.0,
                    "count": 0,
                    "recommendation": False
                }
        
        # 填充实际性能数据
        for strategy_id, state_data in self.strategy_market_performance.items():
            strategy_type = strategy_id.split('_')[0] if '_' in strategy_id else strategy_id
            if strategy_type not in matrix:
                continue
                
            for state, records in state_data.items():
                if state not in MARKET_STATES:
                    continue
                    
                scores = [record["metrics"].get("score", 0) for record in records]
                if scores:
                    matrix[strategy_type][state]["score"] = sum(scores) / len(scores)
                    matrix[strategy_type][state]["count"] = len(scores)
        
        # 标记推荐策略
        for state in MARKET_STATES:
            best_strategies = self.get_best_strategies_for_state(state, top_n=2)
            for strategy_type in best_strategies:
                if strategy_type in matrix:
                    matrix[strategy_type][state]["recommendation"] = True
        
        return matrix
    
    def generate_market_report(self) -> Dict:
        """生成市场环境综合报告"""
        current = self.get_current_market_state()
        
        # 统计状态持续时间
        state_durations = {}
        for state, durations in self.state_duration_history.items():
            if durations:
                state_durations[state] = {
                    "avg": sum(durations) / len(durations),
                    "max": max(durations),
                    "min": min(durations) if durations else 0,
                    "total_occurrences": len(durations)
                }
        
        # 获取策略推荐
        recommended_strategies = self.get_best_strategies_for_state(current["state"], top_n=3)
        
        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "current_state": current,
            "state_durations": state_durations,
            "state_transitions": self.state_transitions,
            "recommended_strategies": recommended_strategies,
            "strategy_market_matrix": self.get_strategy_market_matrix(),
            "hourly_market_history": list(self.medium_state_history)[-24:] if self.medium_state_history else [],
            "daily_market_history": list(self.long_state_history)[-30:] if self.long_state_history else []
        }
        
        return report


# 单例实例
_classifier_instance = None

def get_market_classifier():
    """获取市场环境分类器实例"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = MarketEnvironmentClassifier()
    return _classifier_instance


if __name__ == "__main__":
    # 测试代码
    import yfinance as yf
    
    # 获取测试数据
    try:
        data = yf.download("BTC-USD", period="1mo", interval="1h")
        data.columns = [c.lower() for c in data.columns]
        
        classifier = MarketEnvironmentClassifier()
        state = classifier.detect_market_state(data)
        classifier.update_market_state_history(state)
        
        current = classifier.get_current_market_state()
        print(f"当前市场状态: {current['state']}")
        print(f"置信度: {current['confidence']}")
        print(f"持续时间: {current['duration']} 小时")
        print(f"预测下一状态: {current['next_predicted_state']}")
        
        print("\n推荐策略:")
        recommended = classifier.get_best_strategies_for_state(current['state'])
        for strategy in recommended:
            print(f" - {strategy}")
        
        # 保存状态
        classifier.save_state()
        
    except Exception as e:
        print(f"测试失败: {e}") 