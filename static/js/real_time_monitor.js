/**
 * 实时监控前端脚本
 * 连接WebSocket服务器，实时更新策略状态、系统指标等
 */

class RealTimeMonitorClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3秒
        this.isConnected = false;
        
        // 数据存储
        this.strategiesData = {};
        this.systemMetrics = {};
        this.evolutionProgress = {};
        this.alerts = [];
        
        this.initializeConnection();
        this.setupEventListeners();
    }
    
    initializeConnection() {
        try {
            // 尝试连接WebSocket服务器
            this.socket = new WebSocket('ws://47.236.39.134:8765');
            
            this.socket.onopen = (event) => {
                console.log('✅ WebSocket连接已建立');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };
            
            this.socket.onclose = (event) => {
                console.log('WebSocket连接已关闭:', event.code, event.reason);
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.attemptReconnection();
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.updateConnectionStatus('error');
            };
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateConnectionStatus('error');
            this.attemptReconnection();
        }
    }
    
    attemptReconnection() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.initializeConnection();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('WebSocket重连失败，已达到最大重连次数');
            this.updateConnectionStatus('failed');
        }
    }
    
    handleMessage(data) {
        console.log('收到实时数据:', data.type);
        
        switch (data.type) {
            case 'initial_state':
                this.handleInitialState(data.data);
                break;
            case 'strategy_update':
                this.handleStrategyUpdate(data.data);
                break;
            case 'system_metrics':
                this.handleSystemMetrics(data.data);
                break;
            case 'evolution_progress':
                this.handleEvolutionProgress(data.data);
                break;
            case 'alert':
                this.handleAlert(data.data);
                break;
            default:
                console.log('未知消息类型:', data.type);
        }
    }
    
    handleInitialState(data) {
        console.log('接收初始状态数据');
        this.strategiesData = data.strategies || {};
        this.systemMetrics = data.system_metrics || {};
        this.evolutionProgress = data.evolution_progress || {};
        this.alerts = data.alerts || [];
        
        this.updateAllDisplays();
    }
    
    handleStrategyUpdate(data) {
        this.strategiesData = data;
        this.updateStrategyCards();
        this.updateStrategyTable();
    }
    
    handleSystemMetrics(data) {
        this.systemMetrics = data;
        this.updateSystemMetricsDisplay();
    }
    
    handleEvolutionProgress(data) {
        this.evolutionProgress = data;
        this.updateEvolutionDisplay();
    }
    
    handleAlert(data) {
        this.alerts.unshift(data);
        if (this.alerts.length > 50) {
            this.alerts = this.alerts.slice(0, 50); // 保持最新50条
        }
        this.updateAlertsDisplay();
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('realtime-connection-status');
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            statusElement.innerHTML = this.getStatusDisplay(status);
        }
        
        // 更新全局状态指示器
        const globalStatus = document.getElementById('system-status');
        if (globalStatus) {
            const statusText = status === 'connected' ? '实时在线' : '离线';
            const statusClass = status === 'connected' ? 'online' : 'offline';
            
            globalStatus.innerHTML = `
                <span class="status-indicator ${statusClass}"></span>
                ${statusText}
            `;
        }
    }
    
    getStatusDisplay(status) {
        const displays = {
            'connected': '<i class="fas fa-wifi"></i> 实时连接',
            'disconnected': '<i class="fas fa-times-circle"></i> 连接断开',
            'error': '<i class="fas fa-exclamation-triangle"></i> 连接错误',
            'failed': '<i class="fas fa-ban"></i> 连接失败'
        };
        return displays[status] || '<i class="fas fa-question-circle"></i> 未知状态';
    }
    
    updateAllDisplays() {
        this.updateStrategyCards();
        this.updateStrategyTable();
        this.updateSystemMetricsDisplay();
        this.updateEvolutionDisplay();
        this.updateAlertsDisplay();
    }
    
    updateStrategyCards() {
        // 更新策略卡片的实时数据
        Object.entries(this.strategiesData).forEach(([strategyId, data]) => {
            const card = document.querySelector(`[data-strategy-id="${strategyId}"]`);
            if (card) {
                this.updateStrategyCard(card, data);
            }
        });
    }
    
    updateStrategyCard(card, data) {
        const basicInfo = data.basic_info;
        const recentPerf = data.recent_performance;
        
        // 更新交易次数
        const tradesElement = card.querySelector('.trade-count');
        if (tradesElement) {
            tradesElement.textContent = basicInfo.total_trades || 0;
        }
        
        // 更新24小时交易
        const trades24h = card.querySelector('.trades-24h');
        if (trades24h) {
            trades24h.textContent = recentPerf.trades_24h || 0;
        }
        
        // 更新胜率
        const winRate = card.querySelector('.win-rate');
        if (winRate) {
            const rate = recentPerf.win_rate_24h || 0;
            winRate.textContent = `${rate.toFixed(1)}%`;
            winRate.className = `win-rate ${rate > 60 ? 'good' : rate > 40 ? 'average' : 'poor'}`;
        }
        
        // 更新PnL
        const pnl = card.querySelector('.pnl-24h');
        if (pnl) {
            const pnlValue = recentPerf.total_pnl_24h || 0;
            pnl.textContent = pnlValue > 0 ? `+${pnlValue.toFixed(4)}` : pnlValue.toFixed(4);
            pnl.className = `pnl-24h ${pnlValue > 0 ? 'profit' : pnlValue < 0 ? 'loss' : 'neutral'}`;
        }
        
        // 更新分数
        const scoreElement = card.querySelector('.strategy-score');
        if (scoreElement) {
            const score = basicInfo.score || 0;
            scoreElement.textContent = score.toFixed(2);
            scoreElement.className = `strategy-score ${score > 80 ? 'excellent' : score > 60 ? 'good' : score > 40 ? 'average' : 'poor'}`;
        }
        
        // 更新最后交易时间
        const lastTrade = card.querySelector('.last-trade');
        if (lastTrade && basicInfo.last_trade) {
            const time = new Date(basicInfo.last_trade);
            lastTrade.textContent = this.formatTimeAgo(time);
        }
        
        // 添加实时状态指示器
        let statusIndicator = card.querySelector('.realtime-status');
        if (!statusIndicator) {
            statusIndicator = document.createElement('div');
            statusIndicator.className = 'realtime-status';
            card.appendChild(statusIndicator);
        }
        
        const isActive = recentPerf.trades_24h > 0;
        statusIndicator.innerHTML = `
            <div class="status-dot ${isActive ? 'active' : 'inactive'}"></div>
            <span>${isActive ? '活跃' : '待机'}</span>
        `;
    }
    
    updateStrategyTable() {
        // 如果有策略表格，更新表格数据
        const tableBody = document.querySelector('#strategies-table tbody');
        if (tableBody && Object.keys(this.strategiesData).length > 0) {
            this.refreshStrategyTable(tableBody);
        }
    }
    
    refreshStrategyTable(tableBody) {
        // 清空现有行
        tableBody.innerHTML = '';
        
        // 按分数排序策略
        const sortedStrategies = Object.entries(this.strategiesData)
            .sort(([, a], [, b]) => (b.basic_info.score || 0) - (a.basic_info.score || 0));
        
        sortedStrategies.forEach(([strategyId, data], index) => {
            const row = this.createStrategyTableRow(strategyId, data, index + 1);
            tableBody.appendChild(row);
        });
    }
    
    createStrategyTableRow(strategyId, data, rank) {
        const row = document.createElement('tr');
        row.dataset.strategyId = strategyId;
        
        const basicInfo = data.basic_info;
        const recentPerf = data.recent_performance;
        
        row.innerHTML = `
            <td>${rank}</td>
            <td>
                <div class="strategy-name">${basicInfo.name}</div>
                <div class="strategy-symbol">${basicInfo.symbol}</div>
            </td>
            <td>
                <span class="score ${basicInfo.score > 80 ? 'excellent' : basicInfo.score > 60 ? 'good' : 'average'}">
                    ${(basicInfo.score || 0).toFixed(2)}
                </span>
            </td>
            <td>${basicInfo.total_trades || 0}</td>
            <td>${recentPerf.trades_24h || 0}</td>
            <td>
                <span class="win-rate ${recentPerf.win_rate_24h > 60 ? 'good' : recentPerf.win_rate_24h > 40 ? 'average' : 'poor'}">
                    ${(recentPerf.win_rate_24h || 0).toFixed(1)}%
                </span>
            </td>
            <td>
                <span class="pnl ${recentPerf.total_pnl_24h > 0 ? 'profit' : recentPerf.total_pnl_24h < 0 ? 'loss' : 'neutral'}">
                    ${recentPerf.total_pnl_24h > 0 ? '+' : ''}${(recentPerf.total_pnl_24h || 0).toFixed(4)}
                </span>
            </td>
            <td>
                <span class="status ${basicInfo.enabled ? 'enabled' : 'disabled'}">
                    ${basicInfo.enabled ? '启用' : '禁用'}
                </span>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn-small btn-primary" onclick="showStrategyDetails('${strategyId}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-small btn-secondary" onclick="showStrategyLogs('${strategyId}')">
                        <i class="fas fa-list"></i>
                    </button>
                </div>
            </td>
        `;
        
        return row;
    }
    
    updateSystemMetricsDisplay() {
        // 更新系统指标显示
        if (Object.keys(this.systemMetrics).length === 0) return;
        
        // CPU使用率
        const cpuElement = document.getElementById('cpu-usage');
        if (cpuElement) {
            cpuElement.textContent = `${this.systemMetrics.cpu_percent || 0}%`;
        }
        
        // 内存使用率
        const memoryElement = document.getElementById('memory-usage');
        if (memoryElement) {
            memoryElement.textContent = `${this.systemMetrics.memory_percent || 0}%`;
        }
        
        // 数据库状态
        const dbStatusElement = document.getElementById('database-status');
        if (dbStatusElement) {
            const status = this.systemMetrics.database_status || 'unknown';
            dbStatusElement.innerHTML = `
                <span class="status-indicator ${status}"></span>
                ${status === 'online' ? '在线' : '离线'}
            `;
        }
    }
    
    updateEvolutionDisplay() {
        // 更新进化进度显示
        const evolutionContainer = document.getElementById('evolution-progress');
        if (evolutionContainer && Object.keys(this.evolutionProgress).length > 0) {
            this.refreshEvolutionDisplay(evolutionContainer);
        }
    }
    
    updateAlertsDisplay() {
        // 更新警报显示
        const alertsContainer = document.getElementById('alerts-container');
        if (alertsContainer && this.alerts.length > 0) {
            this.refreshAlertsDisplay(alertsContainer);
        }
    }
    
    setupEventListeners() {
        // 页面可见性变化时重连
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.isConnected) {
                console.log('页面重新可见，尝试重连WebSocket');
                this.initializeConnection();
            }
        });
        
        // 窗口获得焦点时检查连接
        window.addEventListener('focus', () => {
            if (!this.isConnected) {
                console.log('窗口获得焦点，检查WebSocket连接');
                this.initializeConnection();
            }
        });
    }
    
    formatTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMinutes = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMinutes < 1) return '刚刚';
        if (diffMinutes < 60) return `${diffMinutes}分钟前`;
        if (diffHours < 24) return `${diffHours}小时前`;
        return `${diffDays}天前`;
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// 页面加载完成后初始化实时监控
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在量化交易页面
    if (window.location.pathname.includes('quantitative') || 
        document.querySelector('.quantitative-container')) {
        
        console.log('🚀 初始化实时监控客户端');
        window.realtimeMonitor = new RealTimeMonitorClient();
        
        // 添加页面卸载时断开连接
        window.addEventListener('beforeunload', () => {
            if (window.realtimeMonitor) {
                window.realtimeMonitor.disconnect();
            }
        });
    }
});

// 导出类供其他脚本使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealTimeMonitorClient;
} 