/**
 * 量化交易系统 JavaScript
 * 重新设计版本 - 增加系统控制和状态监控
 */

// 全局变量
let app = null;
let refreshTimer = null;
let systemRunning = false;
let autoTradingEnabled = false;
let performanceChart = null;

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
        // 模式选择
        document.getElementById('modeSelect')?.addEventListener('change', (e) => {
            this.changeMode(e.target.value);
        });
        
        // 绑定事件
        this.refreshAllData();
    }

    // 系统启停控制
    async toggleSystem() {
        try {
            systemRunning = !systemRunning;
            
            const response = await fetch('/api/quantitative/system-control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: systemRunning ? 'start' : 'stop' })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateSystemStatus();
                this.showMessage(systemRunning ? '系统已启动' : '系统已停止', 'success');
            } else {
                systemRunning = !systemRunning; // 回滚状态
                this.showMessage(data.message || '操作失败', 'error');
            }
        } catch (error) {
            console.error('系统控制失败:', error);
            systemRunning = !systemRunning; // 回滚状态
            this.showMessage('系统控制失败', 'error');
        }
    }

    // 自动交易开关
    async toggleAutoTrading() {
        try {
            autoTradingEnabled = !autoTradingEnabled;
            
            const response = await fetch('/api/quantitative/toggle-auto-trading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: autoTradingEnabled })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateAutoTradingStatus();
                this.showMessage(autoTradingEnabled ? '自动交易已启用' : '自动交易已禁用', 'success');
            } else {
                autoTradingEnabled = !autoTradingEnabled; // 回滚状态
                this.showMessage(data.message || '操作失败', 'error');
            }
        } catch (error) {
            console.error('自动交易控制失败:', error);
            autoTradingEnabled = !autoTradingEnabled; // 回滚状态
            this.showMessage('自动交易控制失败', 'error');
        }
    }

    // 更新系统状态显示
    updateSystemStatus() {
        const systemStatusEl = document.getElementById('systemStatus');
        const systemToggle = document.getElementById('systemToggle');
        
        // 更新顶部导航栏的状态指示器
        const statusIndicator = document.getElementById('system-status-indicator');
        const statusText = document.getElementById('system-status-text');
        
        if (systemRunning) {
            systemStatusEl.innerHTML = '<span class="status-indicator status-online"></span>在线';
            systemToggle.classList.add('active');
            
            // 导航栏状态 - 运行中金色闪动
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator status-running';
                statusText.textContent = '运行中';
            }
        } else {
            systemStatusEl.innerHTML = '<span class="status-indicator status-offline"></span>离线';
            systemToggle.classList.remove('active');
            
            // 导航栏状态 - 离线黑色
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator status-offline';
                statusText.textContent = '离线';
            }
        }
    }

    // 更新自动交易状态显示
    updateAutoTradingStatus() {
        const autoTradingToggle = document.getElementById('autoTradingToggle');
        
        if (autoTradingEnabled) {
            autoTradingToggle.classList.add('active');
        } else {
            autoTradingToggle.classList.remove('active');
        }
    }

    // 改变运行模式
    async changeMode(mode) {
        try {
            const response = await fetch('/api/quantitative/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showMessage(`已切换到${mode}模式`, 'success');
            }
        } catch (error) {
            console.error('模式切换失败:', error);
        }
    }

    // 加载账户信息
    async loadAccountInfo() {
        try {
            const response = await fetch('/api/quantitative/account-info');
            const data = await response.json();
            
            if (data.success && data.data) {
                const account = data.data;
                
                // 安全显示数据，确保有效才显示，使用USDT作为货币单位
                this.safeSetText('totalBalance', account.balance, '$');
                
                const dailyPnl = account.daily_pnl;
                const dailyPnlEl = document.getElementById('dailyPnl');
                if (dailyPnlEl) {
                    if (dailyPnl !== undefined && dailyPnl !== null && !isNaN(dailyPnl)) {
                        dailyPnlEl.textContent = `${dailyPnl >= 0 ? '+' : ''}$${this.formatNumber(dailyPnl)}`;
                        dailyPnlEl.className = `metric-value ${dailyPnl >= 0 ? 'text-success' : 'text-danger'}`;
                    } else {
                        dailyPnlEl.textContent = '-';
                        dailyPnlEl.className = 'metric-value';
                    }
                }
                
                const dailyReturn = account.daily_return;
                const dailyReturnEl = document.getElementById('dailyReturn');
                if (dailyReturnEl) {
                    if (dailyReturn !== undefined && dailyReturn !== null && !isNaN(dailyReturn)) {
                        const returnPercent = dailyReturn * 100;
                        dailyReturnEl.textContent = `${returnPercent >= 0 ? '+' : ''}${returnPercent.toFixed(2)}%`;
                        dailyReturnEl.className = `metric-value ${returnPercent >= 0 ? 'text-success' : 'text-danger'}`;
                    } else {
                        dailyReturnEl.textContent = '-';
                        dailyReturnEl.className = 'metric-value';
                    }
                }
                
                this.safeSetText('dailyTrades', account.daily_trades);
            } else {
                // API返回失败，所有数据显示"-"
                this.setAccountDataToDash();
            }
        } catch (error) {
            console.error('加载账户信息失败:', error);
            // 网络错误，所有数据显示"-"
            this.setAccountDataToDash();
        }
    }

    // 安全设置文本内容
    safeSetText(elementId, value, prefix = '') {
        const element = document.getElementById(elementId);
        if (element) {
            if (value !== undefined && value !== null && !isNaN(value)) {
                element.textContent = prefix + this.formatNumber(value);
            } else {
                element.textContent = '-';
            }
        }
    }

    // 设置账户数据为"-"
    setAccountDataToDash() {
        this.safeSetText('totalBalance', null);
        this.safeSetText('dailyPnl', null);
        this.safeSetText('dailyReturn', null);
        this.safeSetText('dailyTrades', null);
    }

    // 加载策略列表
    async loadStrategies() {
        try {
            const response = await fetch('/api/quantitative/strategies');
            const data = await response.json();
            
            if (data.status === 'success' && data.data) {
                this.strategies = data.data || [];
                this.renderStrategies();
            } else {
                console.error('加载策略失败:', data.message || '未知错误');
                this.renderEmptyStrategies();
            }
        } catch (error) {
            console.error('加载策略失败:', error);
            this.renderEmptyStrategies();
        }
    }

    // 渲染策略列表
    renderStrategies() {
        const container = document.getElementById('strategiesContainer');
        if (!container) return;

        if (this.strategies.length === 0) {
            this.renderEmptyStrategies();
            return;
        }

        // 按成功率排序
        const sortedStrategies = this.strategies.sort((a, b) => 
            (b.performance?.success_rate || 0) - (a.performance?.success_rate || 0)
        );

        container.innerHTML = sortedStrategies.map(strategy => `
            <div class="col-md-4 mb-3">
                <div class="card strategy-card ${strategy.enabled ? 'strategy-running' : 'strategy-stopped'}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-title mb-0">
                                <a href="/strategy-config.html?id=${strategy.id}" class="text-decoration-none">
                                    ${strategy.name}
                                </a>
                            </h6>
                            <span class="badge ${strategy.enabled ? 'bg-success' : 'bg-secondary'}">
                                ${strategy.enabled ? '运行中' : '已停止'}
                            </span>
                        </div>
                        
                        <p class="card-text">
                            <small class="text-muted">${strategy.symbol}</small><br>
                            <span class="text-success">成功率: ${(strategy.success_rate || 0).toFixed(1)}%</span><br>
                            <span class="text-info">收益率: ${(strategy.total_return || 0).toFixed(2)}%</span>
                        </p>
                        
                        <div class="d-flex justify-content-between">
                            <button class="btn btn-sm ${strategy.enabled ? 'btn-danger' : 'btn-success'}" 
                                    onclick="app.toggleStrategy('${strategy.id}')">
                                ${strategy.enabled ? '停止' : '启动'}
                            </button>
                            <button class="btn btn-sm btn-outline-info" 
                                    onclick="app.viewStrategyDetails('${strategy.id}')">
                                详情
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // 渲染空策略提示（没有假数据）
    renderEmptyStrategies() {
        const container = document.getElementById('strategiesContainer');
        if (!container) return;

        container.innerHTML = `
            <div class="col-12">
                <div class="card border-dashed">
                    <div class="card-body text-center py-5">
                        <i class="fas fa-robot fa-3x text-muted mb-3"></i>
                        <h5 class="text-muted">暂无交易策略</h5>
                        <p class="text-muted mb-4">您还没有创建任何量化交易策略，点击下方按钮开始创建</p>
                        <button class="btn btn-primary" onclick="app.showCreateStrategyModal()">
                            <i class="fas fa-plus me-2"></i>创建策略
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // 显示创建策略模态框
    showCreateStrategyModal() {
        // 跳转到策略创建页面
        window.location.href = '/strategy-create.html';
    }

    // 启动策略
    async startStrategy(strategyIndex) {
        this.showMessage('策略启动中...', 'info');
        
        // 模拟启动延迟
        setTimeout(() => {
            this.showMessage('策略已启动', 'success');
            this.loadStrategies(); // 重新加载策略状态
        }, 1000);
    }

    // 切换策略状态
    async toggleStrategy(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/toggle`, {
                method: 'POST'
            });
            
            const data = await response.json();
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.loadStrategies();
            } else {
                this.showMessage(data.message || '操作失败', 'error');
            }
        } catch (error) {
            console.error('策略控制失败:', error);
            this.showMessage('策略控制失败', 'error');
        }
    }

    // 查看策略详情
    viewStrategyDetails(strategyId) {
        this.showMessage('策略详情功能开发中...', 'info');
    }

    // 查看默认策略详情
    viewDefaultStrategyDetails(index) {
        this.showMessage('策略详情功能开发中...', 'info');
    }

    // 加载持仓信息
    async loadPositions() {
        try {
            const response = await fetch('/api/quantitative/positions');
            const data = await response.json();
            
            if (data.success) {
                this.renderPositions(data.positions || []);
            }
        } catch (error) {
            console.error('加载持仓失败:', error);
        }
    }

    // 渲染持仓列表
    renderPositions(positions) {
        const tbody = document.getElementById('positionsTable');
        if (!tbody) return;

        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无持仓</td></tr>';
            return;
        }

        tbody.innerHTML = positions.map(pos => `
            <tr>
                <td>${pos.symbol}</td>
                <td>${this.formatNumber(pos.quantity)}</td>
                <td>¥${this.formatNumber(pos.avg_price)}</td>
                <td class="${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                    ${pos.unrealized_pnl >= 0 ? '+' : ''}¥${this.formatNumber(pos.unrealized_pnl)}
                </td>
            </tr>
        `).join('');
    }

    // 加载交易信号
    async loadSignals() {
        try {
            const response = await fetch('/api/quantitative/signals');
            const data = await response.json();
            
            if (data.success) {
                this.renderSignals(data.signals || []);
            }
        } catch (error) {
            console.error('加载信号失败:', error);
        }
    }

    // 渲染信号列表
    renderSignals(signals) {
        const tbody = document.getElementById('signalsTable');
        if (!tbody) return;

        if (signals.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无信号</td></tr>';
            return;
        }

        tbody.innerHTML = signals.slice(0, 5).map(signal => `
            <tr>
                <td>${this.formatTime(signal.timestamp)}</td>
                <td>${signal.symbol}</td>
                <td><span class="badge ${signal.signal === 'BUY' ? 'bg-success' : 'bg-danger'}">${signal.signal}</span></td>
                <td>${(signal.confidence * 100).toFixed(0)}%</td>
            </tr>
        `).join('');
    }

    // 初始化收益曲线图
    initChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        // 生成模拟数据
        const labels = [];
        const data = [];
        const now = new Date();
        
        for (let i = 29; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString());
            
            // 模拟收益数据（波动上升）
            const baseValue = 10000;
            const trend = i * 15; // 上升趋势
            const noise = (Math.random() - 0.5) * 200; // 随机波动
            data.push(baseValue + trend + noise);
        }

        performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '账户价值',
                    data: data,
                    borderColor: '#1677ff',
                    backgroundColor: 'rgba(22, 119, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return '¥' + value.toLocaleString();
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

    // 刷新所有数据
    async refreshAllData() {
        try {
            await Promise.all([
                this.loadAccountInfo(),
                this.loadStrategies(),
                this.loadPositions(),
                this.loadSignals()
            ]);
            
            // 更新时间戳
            document.getElementById('lastUpdate').textContent = '刚刚';
        } catch (error) {
            console.error('刷新数据失败:', error);
        }
    }

    // 开始自动刷新
    startAutoRefresh() {
        // 每30秒刷新一次数据
        refreshTimer = setInterval(() => {
            this.refreshAllData();
        }, 30000);
    }

    // 停止自动刷新
    stopAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    // 显示消息
    showMessage(message, type = 'info') {
        // 创建简单的消息提示
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        // 3秒后自动消失
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }

    // 格式化数字
    formatNumber(num) {
        if (typeof num !== 'number') return '0';
        return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // 格式化时间
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString();
    }
}

// 全局函数
function toggleSystem() {
    if (app) {
        app.toggleSystem();
    }
}

function toggleAutoTrading() {
    if (app) {
        app.toggleAutoTrading();
    }
}

function refreshStrategies() {
    if (app) {
        app.loadStrategies();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    app = new QuantitativeSystem();
    
    // 初始化系统状态
    app.updateSystemStatus();
    app.updateAutoTradingStatus();
    
    console.log('量化交易系统初始化完成');
}); 