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

// 策略卡分页和参数更新功能增强
class StrategyCardManager {
    constructor() {
        this.currentStrategyId = null;
        this.currentPage = 1;
        this.pageSize = 30;
        this.totalPages = 0;
        this.logType = 'all'; // all, evolution, validation, real_trading
        this.logs = [];
        this.pagination = {};
    }

    // 加载策略详细信息和日志
    async loadStrategyDetails(strategyId) {
        this.currentStrategyId = strategyId;
        this.currentPage = 1;
        
        try {
            // 并行加载策略信息和日志
            const [strategyResponse, logsResponse] = await Promise.all([
                fetch(`/api/quantitative/strategies/${strategyId}`),
                this.loadStrategyLogs()
            ]);

            if (strategyResponse.ok) {
                const strategyData = await strategyResponse.json();
                this.displayStrategyCard(strategyData);
            }

            if (logsResponse) {
                this.displayStrategyLogs(logsResponse);
            }

        } catch (error) {
            console.error('加载策略详情失败:', error);
            this.showError('加载策略详情失败');
        }
    }

    // 加载策略日志（支持分页和筛选）
    async loadStrategyLogs(page = 1, logType = 'all') {
        if (!this.currentStrategyId) return null;

        this.currentPage = page;
        this.logType = logType;

        try {
            const url = `/api/quantitative/strategies/${this.currentStrategyId}/logs-by-category?` +
                       `page=${page}&limit=${this.pageSize}&type=${logType}`;
            
            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                this.logs = data.logs;
                this.pagination = data.pagination;
                this.totalPages = data.pagination.total_pages;
                return data;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('加载策略日志失败:', error);
            this.showError('加载策略日志失败: ' + error.message);
            return null;
        }
    }

    // 显示策略卡
    displayStrategyCard(strategyData) {
        const strategyCard = document.getElementById('strategy-detail-card');
        if (!strategyCard) return;

        // 更新策略基本信息
        this.updateStrategyBasicInfo(strategyCard, strategyData);
        
        // 更新实时参数
        this.updateStrategyParameters(strategyCard, strategyData);
        
        // 更新性能指标
        this.updatePerformanceMetrics(strategyCard, strategyData);
    }

    // 更新策略基本信息
    updateStrategyBasicInfo(container, data) {
        const basicInfoHTML = `
            <div class="strategy-header">
                <h3>${data.name || data.id}</h3>
                <span class="strategy-status ${data.enabled ? 'enabled' : 'disabled'}">
                    ${data.enabled ? '运行中' : '已停用'}
                </span>
            </div>
            <div class="strategy-summary">
                <div class="metric-group">
                    <div class="metric">
                        <label>当前评分</label>
                        <span class="score-value ${this.getScoreClass(data.final_score)}">
                            ${(data.final_score || 0).toFixed(1)}
                        </span>
                    </div>
                    <div class="metric">
                        <label>当前代数</label>
                        <span class="generation-value">${data.generation || 1}</span>
                    </div>
                    <div class="metric">
                        <label>总交易次数</label>
                        <span class="trades-value">${data.total_trades || 0}</span>
                    </div>
                    <div class="metric">
                        <label>胜率</label>
                        <span class="winrate-value">${((data.success_rate || 0) * 100).toFixed(1)}%</span>
                    </div>
                </div>
            </div>
        `;
        
        const basicInfoElement = container.querySelector('.strategy-basic-info') || 
                                container.appendChild(document.createElement('div'));
        basicInfoElement.className = 'strategy-basic-info';
        basicInfoElement.innerHTML = basicInfoHTML;
    }

    // 更新策略参数显示
    updateStrategyParameters(container, data) {
        const parameters = data.parameters || {};
        
        const parametersHTML = `
            <div class="parameters-section">
                <h4>策略参数 <span class="last-update">最后更新: ${data.last_evolution_time || '未知'}</span></h4>
                <div class="parameters-grid">
                    ${Object.entries(parameters).map(([key, value]) => `
                        <div class="parameter-item">
                            <label class="parameter-name">${this.formatParameterName(key)}</label>
                            <span class="parameter-value" data-param="${key}">${this.formatParameterValue(value)}</span>
                        </div>
                    `).join('')}
                </div>
                <div class="parameter-evolution-info">
                    <span class="evolution-count">进化次数: ${data.evolution_count || 0}</span>
                    <span class="last-evolution">最后进化: ${data.last_evolution_time || '未知'}</span>
                </div>
            </div>
        `;
        
        const parametersElement = container.querySelector('.strategy-parameters') || 
                                 container.appendChild(document.createElement('div'));
        parametersElement.className = 'strategy-parameters';
        parametersElement.innerHTML = parametersHTML;
    }

    // 更新性能指标
    updatePerformanceMetrics(container, data) {
        const metricsHTML = `
            <div class="performance-metrics">
                <h4>性能指标</h4>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">累计盈亏</div>
                        <div class="metric-value pnl ${(data.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">
                            ${this.formatCurrency(data.total_pnl || 0)}
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">最大回撤</div>
                        <div class="metric-value drawdown">
                            ${((data.max_drawdown || 0) * 100).toFixed(2)}%
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">夏普比率</div>
                        <div class="metric-value sharpe">
                            ${(data.sharpe_ratio || 0).toFixed(3)}
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">年化收益率</div>
                        <div class="metric-value return">
                            ${((data.annual_return || 0) * 100).toFixed(2)}%
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const metricsElement = container.querySelector('.performance-metrics') || 
                              container.appendChild(document.createElement('div'));
        metricsElement.className = 'performance-metrics';
        metricsElement.innerHTML = metricsHTML;
    }

    // 显示策略日志（支持分页）
    displayStrategyLogs(data) {
        const logsContainer = document.getElementById('strategy-logs-container');
        if (!logsContainer) return;

        // 创建日志筛选器
        this.createLogFilter(logsContainer);
        
        // 创建日志表格
        this.createLogsTable(logsContainer, data.logs);
        
        // 创建分页控件
        this.createPagination(logsContainer, data.pagination);
    }

    // 创建日志筛选器
    createLogFilter(container) {
        const filterHTML = `
            <div class="logs-filter">
                <div class="filter-buttons">
                    <button class="filter-btn ${this.logType === 'all' ? 'active' : ''}" 
                            onclick="strategyCardManager.filterLogs('all')">全部</button>
                    <button class="filter-btn ${this.logType === 'evolution' ? 'active' : ''}" 
                            onclick="strategyCardManager.filterLogs('evolution')">进化日志</button>
                    <button class="filter-btn ${this.logType === 'validation' ? 'active' : ''}" 
                            onclick="strategyCardManager.filterLogs('validation')">验证交易</button>
                    <button class="filter-btn ${this.logType === 'real_trading' ? 'active' : ''}" 
                            onclick="strategyCardManager.filterLogs('real_trading')">真实交易</button>
                </div>
                <div class="logs-stats">
                    <span>共 ${this.pagination.total_count || 0} 条记录</span>
                    <span>第 ${this.pagination.current_page || 1} 页 / 共 ${this.pagination.total_pages || 1} 页</span>
                </div>
            </div>
        `;

        const filterElement = container.querySelector('.logs-filter') || 
                             container.appendChild(document.createElement('div'));
        filterElement.outerHTML = filterHTML;
    }

    // 创建日志表格
    createLogsTable(container, logs) {
        const tableHTML = `
            <div class="logs-table-container">
                <table class="logs-table">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>类型</th>
                            <th>操作</th>
                            <th>详情</th>
                            <th>结果</th>
                            <th>参数变化</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${logs.map(log => this.createLogRow(log)).join('')}
                    </tbody>
                </table>
            </div>
        `;

        const tableElement = container.querySelector('.logs-table-container') || 
                           container.appendChild(document.createElement('div'));
        tableElement.outerHTML = tableHTML;
    }

    // 创建单条日志行
    createLogRow(log) {
        const time = new Date(log.timestamp).toLocaleString();
        const logTypeClass = `log-type-${log.log_type}`;
        
        let detailsContent = '';
        let resultContent = '';
        let parametersContent = '';

        // 根据日志类型显示不同内容
        switch (log.log_type) {
            case 'evolution':
                detailsContent = `
                    <div class="evolution-details">
                        <span class="evolution-type">${log.evolution_type || '参数优化'}</span>
                        <span class="trigger-reason">${log.trigger_reason || '定期优化'}</span>
                    </div>
                `;
                resultContent = `
                    <div class="evolution-result">
                        <span class="score-change ${log.improvement >= 0 ? 'positive' : 'negative'}">
                            ${log.improvement >= 0 ? '+' : ''}${(log.improvement || 0).toFixed(2)}
                        </span>
                        <span class="success-indicator ${log.success ? 'success' : 'failed'}">
                            ${log.success ? '✓' : '✗'}
                        </span>
                    </div>
                `;
                parametersContent = this.formatParameterChanges(log);
                break;
            
            case 'validation':
                detailsContent = `
                    <div class="validation-details">
                        <span class="symbol">${log.symbol || 'N/A'}</span>
                        <span class="signal">${log.signal_type || 'N/A'}</span>
                        <span class="price">$${(log.price || 0).toFixed(2)}</span>
                    </div>
                `;
                resultContent = `
                    <div class="validation-result">
                        <span class="pnl ${log.pnl >= 0 ? 'positive' : 'negative'}">
                            ${log.pnl >= 0 ? '+' : ''}${(log.pnl || 0).toFixed(2)}
                        </span>
                        <span class="executed ${log.executed ? 'executed' : 'pending'}">
                            ${log.executed ? '已执行' : '待执行'}
                        </span>
                    </div>
                `;
                break;
                
            case 'real_trading':
                detailsContent = `
                    <div class="trading-details">
                        <span class="symbol">${log.symbol || 'N/A'}</span>
                        <span class="signal">${log.signal_type || 'N/A'}</span>
                        <span class="quantity">${log.quantity || 0}</span>
                    </div>
                `;
                resultContent = `
                    <div class="trading-result">
                        <span class="pnl ${log.pnl >= 0 ? 'positive' : 'negative'}">
                            ${log.pnl >= 0 ? '+' : ''}${(log.pnl || 0).toFixed(2)}
                        </span>
                        <span class="confidence">置信度: ${(log.confidence || 0).toFixed(1)}%</span>
                    </div>
                `;
                break;
        }

        return `
            <tr class="log-row ${logTypeClass}">
                <td class="log-time">${time}</td>
                <td class="log-type">
                    <span class="type-badge ${log.log_type}">${this.formatLogType(log.log_type)}</span>
                </td>
                <td class="log-operation">${log.signal_type || log.evolution_type || 'N/A'}</td>
                <td class="log-details">${detailsContent}</td>
                <td class="log-result">${resultContent}</td>
                <td class="log-parameters">${parametersContent}</td>
            </tr>
        `;
    }

    // 格式化参数变化
    formatParameterChanges(log) {
        if (!log.parameter_changes || log.parameter_changes.length === 0) {
            return '<span class="no-changes">无参数变化</span>';
        }

        const changesHTML = log.parameter_changes.map(change => {
            const changeClass = change.change_type;
            const impact = change.impact_level || 'low';
            
            return `
                <div class="parameter-change ${changeClass} impact-${impact}">
                    <span class="param-name">${change.parameter}</span>
                    <span class="param-change-arrow">→</span>
                    <span class="param-values">
                        <span class="old-value">${change.old_value}</span>
                        <span class="new-value">${change.new_value}</span>
                    </span>
                    ${change.change_percent ? 
                        `<span class="change-percent">(${change.change_percent >= 0 ? '+' : ''}${change.change_percent.toFixed(1)}%)</span>` 
                        : ''
                    }
                </div>
            `;
        }).join('');

        return `
            <div class="parameters-changes">
                <div class="changes-summary">${log.changes_count || 0}项变化</div>
                <div class="changes-details">${changesHTML}</div>
            </div>
        `;
    }

    // 创建分页控件
    createPagination(container, pagination) {
        if (!pagination || pagination.total_pages <= 1) return;

        const paginationHTML = `
            <div class="pagination-container">
                <div class="pagination-info">
                    显示第 ${(pagination.current_page - 1) * this.pageSize + 1} - 
                    ${Math.min(pagination.current_page * this.pageSize, pagination.total_count)} 条，
                    共 ${pagination.total_count} 条记录
                </div>
                <div class="pagination-controls">
                    ${this.createPaginationButtons(pagination)}
                </div>
            </div>
        `;

        const paginationElement = container.querySelector('.pagination-container') || 
                                 container.appendChild(document.createElement('div'));
        paginationElement.outerHTML = paginationHTML;
    }

    // 创建分页按钮
    createPaginationButtons(pagination) {
        const current = pagination.current_page;
        const total = pagination.total_pages;
        const maxVisible = 10; // 最多显示10个页码按钮
        
        let buttons = [];

        // 首页和上一页
        buttons.push(`
            <button class="page-btn ${current === 1 ? 'disabled' : ''}" 
                    onclick="strategyCardManager.goToPage(1)" ${current === 1 ? 'disabled' : ''}>
                首页
            </button>
            <button class="page-btn ${current === 1 ? 'disabled' : ''}" 
                    onclick="strategyCardManager.goToPage(${current - 1})" ${current === 1 ? 'disabled' : ''}>
                上一页
            </button>
        `);

        // 页码按钮
        let start = Math.max(1, current - Math.floor(maxVisible / 2));
        let end = Math.min(total, start + maxVisible - 1);
        
        if (end - start + 1 < maxVisible) {
            start = Math.max(1, end - maxVisible + 1);
        }

        if (start > 1) {
            buttons.push(`<span class="pagination-ellipsis">...</span>`);
        }

        for (let i = start; i <= end; i++) {
            buttons.push(`
                <button class="page-btn ${i === current ? 'active' : ''}" 
                        onclick="strategyCardManager.goToPage(${i})">
                    ${i}
                </button>
            `);
        }

        if (end < total) {
            buttons.push(`<span class="pagination-ellipsis">...</span>`);
        }

        // 下一页和末页
        buttons.push(`
            <button class="page-btn ${current === total ? 'disabled' : ''}" 
                    onclick="strategyCardManager.goToPage(${current + 1})" ${current === total ? 'disabled' : ''}>
                下一页
            </button>
            <button class="page-btn ${current === total ? 'disabled' : ''}" 
                    onclick="strategyCardManager.goToPage(${total})" ${current === total ? 'disabled' : ''}>
                末页
            </button>
        `);

        return buttons.join('');
    }

    // 跳转到指定页
    async goToPage(page) {
        if (page < 1 || page > this.totalPages || page === this.currentPage) return;
        
        const data = await this.loadStrategyLogs(page, this.logType);
        if (data) {
            this.displayStrategyLogs(data);
        }
    }

    // 筛选日志类型
    async filterLogs(logType) {
        if (logType === this.logType) return;
        
        const data = await this.loadStrategyLogs(1, logType);
        if (data) {
            this.displayStrategyLogs(data);
        }
    }

    // 辅助函数
    getScoreClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 70) return 'good';
        if (score >= 60) return 'average';
        return 'poor';
    }

    formatParameterName(name) {
        const nameMap = {
            'stop_loss': '止损',
            'take_profit': '止盈', 
            'quantity': '数量',
            'period': '周期',
            'threshold': '阈值'
        };
        return nameMap[name] || name;
    }

    formatParameterValue(value) {
        if (typeof value === 'number') {
            return value.toFixed(4);
        }
        return String(value);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('zh-CN', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    formatLogType(type) {
        const typeMap = {
            'evolution': '进化',
            'validation': '验证',
            'real_trading': '交易',
            'system_operation': '系统'
        };
        return typeMap[type] || type;
    }

    showError(message) {
        console.error(message);
        // 可以添加用户友好的错误显示
    }
}

// 全局实例
const strategyCardManager = new StrategyCardManager(); 