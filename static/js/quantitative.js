/**
 * 量化交易系统 JavaScript
 * 重新设计版本 - 增加系统控制和状态监控
 */

// 全局变量
let app = null;
let refreshTimer = null;
let systemRunning = false;
let autoTradingEnabled = false;

// 系统状态管理类
class QuantitativeSystem {
    constructor() {
        this.strategies = [];
        this.positions = [];
        this.signals = [];
        this.performance = {};
        this.systemStatus = 'offline';
        this.accountInfo = {};
        this.exchangeStatus = {};
        
        this.bindEvents();
        this.initChart();
        this.startAutoRefresh();
    }

    bindEvents() {
        // 系统控制按钮
        document.getElementById('startSystemBtn')?.addEventListener('click', () => this.startSystem());
        document.getElementById('stopSystemBtn')?.addEventListener('click', () => this.stopSystem());
        
        // 自动交易开关
        document.getElementById('autoTradingSwitch')?.addEventListener('change', (e) => this.toggleAutoTrading(e.target.checked));
        
        // 策略类型选择事件
        document.getElementById('strategyType')?.addEventListener('change', (e) => this.handleStrategyTypeChange(e.target.value));
    }

    // ========== 系统控制功能 ==========
    async startSystem() {
        try {
            this.showAlert('正在启动量化交易系统...', 'info');
            
            const response = await fetch('/api/quantitative/system-control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'start' })
            });
            
            const data = await response.json();
            
            if (data.success) {
                systemRunning = true;
                this.updateSystemStatus('online');
                this.showAlert('量化交易系统启动成功！', 'success');
                this.refreshAllData();
            } else {
                this.showAlert('系统启动失败: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('启动系统失败:', error);
            this.showAlert('系统启动失败，请检查网络连接', 'error');
        }
    }

    async stopSystem() {
        if (!confirm('确定要停止量化交易系统吗？这将停止所有运行中的策略。')) {
            return;
        }

        try {
            this.showAlert('正在停止量化交易系统...', 'warning');
            
            const response = await fetch('/api/quantitative/system-control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'stop' })
            });
            
            const data = await response.json();
            
            if (data.success) {
                systemRunning = false;
                this.updateSystemStatus('offline');
                this.showAlert('量化交易系统已停止', 'warning');
            } else {
                this.showAlert('系统停止失败: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('停止系统失败:', error);
            this.showAlert('系统停止失败，请检查网络连接', 'error');
        }
    }

    async toggleAutoTrading(enabled) {
        try {
            const response = await fetch('/api/quantitative/toggle-auto-trading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            
            const data = await response.json();
            
            if (data.success) {
                autoTradingEnabled = enabled;
                this.showAlert(`自动交易已${enabled ? '启用' : '禁用'}`, enabled ? 'success' : 'warning');
            } else {
                // 恢复开关状态
                document.getElementById('autoTradingSwitch').checked = !enabled;
                this.showAlert('自动交易设置失败: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('设置自动交易失败:', error);
            document.getElementById('autoTradingSwitch').checked = !enabled;
            this.showAlert('自动交易设置失败', 'error');
        }
    }

    // ========== 状态显示功能 ==========
    updateSystemStatus(status) {
        const statusIndicator = document.getElementById('systemStatus');
        const statusText = document.getElementById('systemStatusText');
        
        if (statusIndicator && statusText) {
            statusIndicator.className = `status-indicator status-${status}`;
            
            switch (status) {
                case 'online':
                    statusText.textContent = '系统运行中';
                    break;
                case 'offline':
                    statusText.textContent = '系统离线';
                    break;
                case 'warning':
                    statusText.textContent = '系统警告';
                    break;
                default:
                    statusText.textContent = '未知状态';
            }
        }
    }

    updateAccountInfo(info) {
        this.accountInfo = info;
        
        // 更新界面显示
        const totalBalance = document.getElementById('totalBalance');
        const todayPnl = document.getElementById('todayPnl');
        const todayReturn = document.getElementById('todayReturn');
        const totalTrades = document.getElementById('totalTrades');
        
        if (totalBalance) totalBalance.textContent = `¥${Number(info.balance || 0).toLocaleString()}`;
        
        if (todayPnl) {
            const pnl = Number(info.daily_pnl || 0);
            todayPnl.textContent = `${pnl >= 0 ? '+' : ''}¥${pnl.toLocaleString()}`;
            todayPnl.className = `metric-value ${pnl >= 0 ? 'positive' : 'negative'}`;
        }
        
        if (todayReturn) {
            const returnRate = Number(info.daily_return || 0);
            todayReturn.textContent = `${returnRate >= 0 ? '+' : ''}${(returnRate * 100).toFixed(2)}%`;
            todayReturn.className = `metric-value ${returnRate >= 0 ? 'positive' : 'negative'}`;
        }
        
        if (totalTrades) totalTrades.textContent = info.daily_trades || 0;
    }

    updateExchangeStatus(status) {
        this.exchangeStatus = status;
        
        const binanceStatus = document.getElementById('binanceStatus');
        const binancePermissions = document.getElementById('binancePermissions');
        const binanceLatency = document.getElementById('binanceLatency');
        
        if (status.binance) {
            if (binanceStatus) {
                if (status.binance.connected) {
                    binanceStatus.className = 'exchange-status bg-success text-white';
                    binanceStatus.innerHTML = '<i class="fas fa-check me-1"></i>已连接';
                } else {
                    binanceStatus.className = 'exchange-status bg-danger text-white';
                    binanceStatus.innerHTML = '<i class="fas fa-times me-1"></i>连接失败';
                }
            }
            
            if (binancePermissions) binancePermissions.textContent = status.binance.permissions || '未知';
            if (binanceLatency) binanceLatency.textContent = `${status.binance.latency || '--'}ms`;
        }
    }

    // ========== 数据加载功能 ==========
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/quantitative/system-status');
            const data = await response.json();
            
            if (data.success) {
                systemRunning = data.running;
                autoTradingEnabled = data.auto_trading_enabled;
                
                this.updateSystemStatus(data.running ? 'online' : 'offline');
                document.getElementById('autoTradingSwitch').checked = autoTradingEnabled;
            }
        } catch (error) {
            console.error('加载系统状态失败:', error);
        }
    }

    async loadAccountInfo() {
        try {
            const response = await fetch('/api/quantitative/account-info');
            const data = await response.json();
            
            if (data.success) {
                this.updateAccountInfo(data.data);
            }
        } catch (error) {
            console.error('加载账户信息失败:', error);
        }
    }

    async loadExchangeStatus() {
        try {
            const response = await fetch('/api/quantitative/exchange-status');
            const data = await response.json();
            
            if (data.success) {
                this.updateExchangeStatus(data.data);
            }
        } catch (error) {
            console.error('加载交易所状态失败:', error);
        }
    }

    async loadStrategies() {
        try {
            const response = await fetch('/api/quantitative/strategies');
            const data = await response.json();
            
            if (data.success) {
                this.strategies = data.data;
                this.updateStrategiesUI();
            }
        } catch (error) {
            console.error('加载策略失败:', error);
        }
    }

    async loadPositions() {
        try {
            const response = await fetch('/api/quantitative/positions');
            const data = await response.json();
            
            if (data.success) {
                this.positions = data.data;
                this.updatePositionsUI();
            }
        } catch (error) {
            console.error('加载持仓失败:', error);
        }
    }

    async loadSignals() {
        try {
            const response = await fetch('/api/quantitative/signals');
            const data = await response.json();
            
            if (data.success) {
                this.signals = data.data;
                this.updateSignalsUI();
            }
        } catch (error) {
            console.error('加载信号失败:', error);
        }
    }

    async loadPerformance() {
        try {
            const response = await fetch('/api/quantitative/performance');
            const data = await response.json();
            
            if (data.success) {
                this.performance = data.data;
                this.updatePerformanceChart();
            }
        } catch (error) {
            console.error('加载绩效数据失败:', error);
        }
    }

    // ========== UI更新功能 ==========
    updateStrategiesUI() {
        const container = document.getElementById('strategiesList');
        if (!container) return;

        if (this.strategies.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-robot fs-1 mb-2"></i>
                    <p>暂无策略，点击"新建策略"开始</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.strategies.map(strategy => `
            <div class="list-group-item strategy-item ${strategy.running ? 'running' : 'stopped'} p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-2">
                            <h6 class="mb-0 me-2">${strategy.name}</h6>
                            <span class="badge ${strategy.running ? 'bg-success' : 'bg-secondary'} me-2">
                                ${strategy.running ? '运行中' : '已停止'}
                            </span>
                            <small class="text-muted">${this.getStrategyTypeName(strategy.type)}</small>
                        </div>
                        <div class="row text-center">
                            <div class="col-3">
                                <small class="text-muted d-block">交易对</small>
                                <span class="fw-bold">${strategy.symbol}</span>
                            </div>
                            <div class="col-3">
                                <small class="text-muted d-block">总收益</small>
                                <span class="fw-bold ${strategy.total_return >= 0 ? 'text-success' : 'text-danger'}">
                                    ${(strategy.total_return * 100).toFixed(2)}%
                                </span>
                            </div>
                            <div class="col-3">
                                <small class="text-muted d-block">胜率</small>
                                <span class="fw-bold">${(strategy.win_rate * 100).toFixed(1)}%</span>
                            </div>
                            <div class="col-3">
                                <small class="text-muted d-block">交易次数</small>
                                <span class="fw-bold">${strategy.total_trades}</span>
                            </div>
                        </div>
                    </div>
                    <div class="btn-group-vertical btn-group-sm ms-3">
                        <button class="btn ${strategy.running ? 'btn-outline-warning' : 'btn-outline-success'} btn-sm"
                                onclick="app.toggleStrategy('${strategy.id}')">
                            <i class="fas fa-${strategy.running ? 'pause' : 'play'} me-1"></i>
                            ${strategy.running ? '停止' : '启动'}
                        </button>
                        <button class="btn btn-outline-danger btn-sm"
                                onclick="app.deleteStrategy('${strategy.id}')">
                            <i class="fas fa-trash me-1"></i>删除
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updatePositionsUI() {
        const container = document.getElementById('positionsList');
        const countElement = document.getElementById('positionsCount');
        
        if (countElement) countElement.textContent = this.positions.length;
        
        if (!container) return;

        if (this.positions.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-inbox fs-2 mb-2"></i>
                    <p>暂无持仓</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.positions.map(position => `
            <div class="position-item p-3 mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${position.symbol}</h6>
                        <small class="text-muted">数量: ${position.quantity}</small>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold ${position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                            ${position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)} USDT
                        </div>
                        <small class="text-muted">成本: ${position.avg_price.toFixed(6)}</small>
                    </div>
                </div>
                <div class="progress mt-2" style="height: 4px;">
                    <div class="progress-bar ${position.unrealized_pnl >= 0 ? 'bg-success' : 'bg-danger'}" 
                         style="width: ${Math.min(Math.abs(position.unrealized_pnl / position.avg_price / position.quantity * 100), 100)}%"></div>
                </div>
            </div>
        `).join('');
    }

    updateSignalsUI() {
        const container = document.getElementById('signalsList');
        const countElement = document.getElementById('signalsCount');
        
        if (countElement) countElement.textContent = this.signals.length;
        
        if (!container) return;

        if (this.signals.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-satellite-dish fs-2 mb-2"></i>
                    <p>暂无交易信号</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.signals.slice(0, 10).map(signal => `
            <div class="d-flex justify-content-between align-items-center p-3 border-bottom">
                <div>
                    <div class="d-flex align-items-center mb-1">
                        <span class="signal-badge signal-${signal.signal_type.toLowerCase()}">${signal.signal_type.toUpperCase()}</span>
                        <span class="fw-bold ms-2">${signal.symbol}</span>
                    </div>
                    <small class="text-muted">${new Date(signal.timestamp).toLocaleString()}</small>
                </div>
                <div class="text-end">
                    <div class="fw-bold">¥${signal.price.toFixed(6)}</div>
                    <small class="text-muted">置信度: ${(signal.confidence * 100).toFixed(0)}%</small>
                </div>
            </div>
        `).join('');
    }

    // ========== 策略管理功能 ==========
    handleStrategyTypeChange(strategyType) {
        // 根据策略类型显示相应的参数输入
        // 这里可以扩展特定策略的参数输入界面
    }

    async submitStrategy() {
        const form = document.getElementById('newStrategyForm');
        const formData = new FormData(form);
        
        const strategyData = {
            name: formData.get('strategyName') || document.getElementById('strategyName').value,
            type: formData.get('strategyType') || document.getElementById('strategyType').value,
            symbol: formData.get('strategySymbol') || document.getElementById('strategySymbol').value,
            parameters: {
                quantity: parseFloat(document.getElementById('quantity').value),
                lookback_period: parseInt(document.getElementById('lookback_period').value)
            }
        };

        if (!strategyData.name || !strategyData.type || !strategyData.symbol) {
            this.showAlert('请填写完整的策略信息', 'error');
            return;
        }

        try {
            const response = await fetch('/api/quantitative/strategies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(strategyData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('策略创建成功！', 'success');
                form.reset();
                bootstrap.Modal.getInstance(document.getElementById('newStrategyModal')).hide();
                this.loadStrategies();
            } else {
                this.showAlert('策略创建失败: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('创建策略失败:', error);
            this.showAlert('策略创建失败，请检查网络连接', 'error');
        }
    }

    async toggleStrategy(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/toggle`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(data.message, 'success');
                this.loadStrategies();
            } else {
                this.showAlert('操作失败: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('策略操作失败:', error);
            this.showAlert('策略操作失败', 'error');
        }
    }

    async deleteStrategy(strategyId) {
        if (!confirm('确定要删除这个策略吗？此操作不可恢复。')) {
            return;
        }

        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('策略删除成功', 'success');
                this.loadStrategies();
            } else {
                this.showAlert('策略删除失败: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('删除策略失败:', error);
            this.showAlert('策略删除失败', 'error');
        }
    }

    // ========== 图表功能 ==========
    initChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '累计收益率',
                    data: [],
                    borderColor: '#1677ff',
                    backgroundColor: 'rgba(22, 119, 255, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    updatePerformanceChart() {
        if (!this.chart || !this.performance.metrics) return;

        const metrics = this.performance.metrics.slice(-30); // 最近30个数据点
        const labels = metrics.map(m => new Date(m.timestamp).toLocaleDateString());
        const data = metrics.map(m => (m.total_return * 100).toFixed(2));

        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.update();
    }

    // ========== 工具功能 ==========
    getStrategyTypeName(type) {
        const types = {
            momentum: '动量策略',
            mean_reversion: '均值回归',
            breakout: '突破策略',
            grid_trading: '网格交易',
            high_frequency: '高频交易',
            trend_following: '趋势跟踪'
        };
        return types[type] || type;
    }

    showAlert(message, type = 'info') {
        // 创建一个简单的通知系统
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        alertContainer.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertContainer.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertContainer);
        
        // 自动移除
        setTimeout(() => {
            if (alertContainer.parentNode) {
                alertContainer.remove();
            }
        }, 5000);
    }

    // ========== 定时刷新 ==========
    startAutoRefresh() {
        if (refreshTimer) clearInterval(refreshTimer);
        
        refreshTimer = setInterval(() => {
            if (systemRunning) {
                this.refreshAllData();
            }
        }, 5000); // 每5秒刷新一次
    }

    refreshAllData() {
        this.loadAccountInfo();
        this.loadStrategies();
        this.loadPositions();
        this.loadSignals();
        this.loadPerformance();
    }

    stopAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }
}

// ========== 全局函数 ==========
function initQuantitative() {
    app = new QuantitativeSystem();
    window.app = app; // 暴露到全局作用域
}

function loadSystemStatus() {
    if (app) app.loadSystemStatus();
}

function loadAccountInfo() {
    if (app) app.loadAccountInfo();
}

function loadExchangeStatus() {
    if (app) app.loadExchangeStatus();
}

function submitStrategy() {
    if (app) app.submitStrategy();
}

// 页面卸载时清理定时器
window.addEventListener('beforeunload', () => {
    if (app) app.stopAutoRefresh();
}); 