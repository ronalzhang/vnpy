/**
 * 量化交易系统前端交互逻辑
 * 包含策略管理、信号监控、图表展示、实时数据更新等功能
 */

class QuantitativeApp {
    constructor() {
        this.strategies = [];
        this.signals = [];
        this.positions = [];
        this.performanceChart = null;
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5秒刷新一次
    }

    /**
     * 初始化应用
     */
    static init() {
        const app = new QuantitativeApp();
        app.bindEvents();
        app.loadStrategies();
        app.loadSignals();
        app.loadPositions();
        app.loadPerformance();
        app.initChart();
        app.startAutoRefresh();
        return app;
    }

    /**
     * 绑定事件处理器
     */
    bindEvents() {
        // 策略类型选择事件
        document.getElementById('strategyType').addEventListener('change', (e) => {
            this.toggleStrategyParams(e.target.value);
        });

        // 编辑策略类型选择事件
        document.getElementById('editStrategyType').addEventListener('change', (e) => {
            this.toggleEditStrategyParams(e.target.value);
        });

        // 策略表单提交 - 修复表单ID
        document.getElementById('createStrategyForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitStrategy();
        });
        
        // 创建策略按钮点击事件
        document.getElementById('createStrategyBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.submitStrategy();
        });

        // 编辑策略表单提交
        document.getElementById('editStrategyForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateStrategy();
        });
        
        // 更新策略按钮点击事件
        document.getElementById('updateStrategyBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.updateStrategy();
        });

        // 添加策略名称点击事件委托
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('strategy-name-link')) {
                e.preventDefault();
                const strategyId = e.target.getAttribute('data-strategy-id');
                this.openEditStrategy(strategyId);
            }
            
            // 策略切换按钮事件
            if (e.target.closest('.toggle-strategy-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.toggle-strategy-btn');
                const strategyId = btn.getAttribute('data-strategy-id');
                this.toggleStrategy(strategyId);
            }
            
            // 策略删除按钮事件
            if (e.target.closest('.delete-strategy-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.delete-strategy-btn');
                const strategyId = btn.getAttribute('data-strategy-id');
                this.deleteStrategy(strategyId);
            }
        });

        // 自动刷新切换
        const autoRefreshSwitch = document.getElementById('autoRefreshSwitch');
        if (autoRefreshSwitch) {
            autoRefreshSwitch.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // 刷新按钮
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAllData();
            });
        }
    }

    /**
     * 切换策略参数显示
     */
    toggleStrategyParams(strategyType) {
        // 隐藏所有参数区域
        document.querySelectorAll('.strategy-params').forEach(div => {
            div.style.display = 'none';
        });
        
        // 显示对应的参数区域
        if (strategyType) {
            const paramMapping = {
                'momentum': 'momentumParams',
                'mean_reversion': 'meanReversionParams',
                'breakout': 'breakoutParams',
                'grid_trading': 'gridTradingParams',
                'high_frequency': 'highFrequencyParams',
                'trend_following': 'trendFollowingParams'
            };
            
            const paramDivId = paramMapping[strategyType];
            if (paramDivId) {
                const paramDiv = document.getElementById(paramDivId);
                if (paramDiv) {
                    paramDiv.style.display = 'block';
                }
            }
        }
    }

    /**
     * 切换编辑策略参数显示
     */
    toggleEditStrategyParams(strategyType) {
        // 隐藏所有编辑参数区域
        document.querySelectorAll('.edit-strategy-params').forEach(div => {
            div.style.display = 'none';
        });
        
        // 显示对应的编辑参数区域
        if (strategyType) {
            const paramMapping = {
                'momentum': 'editMomentumParams',
                'mean_reversion': 'editMeanReversionParams',
                'breakout': 'editBreakoutParams',
                'grid_trading': 'editGridTradingParams',
                'high_frequency': 'editHighFrequencyParams',
                'trend_following': 'editTrendFollowingParams'
            };
            
            const paramDivId = paramMapping[strategyType];
            if (paramDivId) {
                const paramDiv = document.getElementById(paramDivId);
                if (paramDiv) {
                    paramDiv.style.display = 'block';
                }
            }
        }
    }
    
    /**
     * 隐藏所有策略参数组
     */
    hideAllStrategyParams() {
        const paramGroups = ['momentumParams', 'meanReversionParams', 'breakoutParams'];
        paramGroups.forEach(groupId => {
            const element = document.getElementById(groupId);
            if (element) {
                element.style.display = 'none';
            }
        });
    }

    /**
     * 隐藏所有编辑策略参数组
     */
    hideAllEditStrategyParams() {
        const paramGroups = ['editMomentumParams', 'editMeanReversionParams', 'editBreakoutParams'];
        paramGroups.forEach(groupId => {
            const element = document.getElementById(groupId);
            if (element) {
                element.style.display = 'none';
            }
        });
    }

    /**
     * 提交策略创建
     */
    async submitStrategy() {
        // 获取表单数据
        const strategyName = document.getElementById('strategyName').value;
        const strategyType = document.getElementById('strategyType').value;
        const strategySymbol = document.getElementById('strategySymbol').value;
        const lookbackPeriod = parseInt(document.getElementById('lookbackPeriod').value) || 20;
        const quantity = parseFloat(document.getElementById('quantity').value) || 1.0;

        if (!strategyName || !strategyType || !strategySymbol) {
            this.showAlert('请填写完整的策略信息！', 'error');
            return;
        }

        // 根据策略类型收集特定参数
        const params = {
            lookback_period: lookbackPeriod,
            quantity: quantity
        };

        if (strategyType === 'momentum') {
            const threshold = parseFloat(document.getElementById('momentumThreshold').value) || 0.001;
            params.threshold = threshold;
        } else if (strategyType === 'mean_reversion') {
            const stdMultiplier = parseFloat(document.getElementById('stdMultiplier').value) || 2.0;
            params.std_multiplier = stdMultiplier;
        } else if (strategyType === 'breakout') {
            const breakoutThreshold = parseFloat(document.getElementById('breakoutThreshold').value) || 0.01;
            params.breakout_threshold = breakoutThreshold;
        } else if (strategyType === 'grid_trading') {
            const gridSpacing = parseFloat(document.getElementById('gridSpacing').value) || 0.02;
            const gridCount = parseInt(document.getElementById('gridCount').value) || 10;
            params.grid_spacing = gridSpacing;
            params.grid_count = gridCount;
        } else if (strategyType === 'high_frequency') {
            const volatilityThreshold = parseFloat(document.getElementById('volatilityThreshold').value) || 0.001;
            const minProfit = parseFloat(document.getElementById('minProfit').value) || 0.0005;
            params.volatility_threshold = volatilityThreshold;
            params.min_profit = minProfit;
        } else if (strategyType === 'trend_following') {
            const trendThreshold = parseFloat(document.getElementById('trendThreshold').value) || 0.02;
            params.trend_threshold = trendThreshold;
        }

        const payload = {
            name: strategyName,
            strategy_type: strategyType,
            symbol: strategySymbol,
            parameters: params
        };

        try {
            const response = await fetch('/api/quantitative/strategies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showAlert('策略创建成功！', 'success');
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('createStrategyModal'));
                modal.hide();
                // 重新加载策略列表
                this.loadStrategies();
                // 重置表单
                document.getElementById('createStrategyForm').reset();
                this.hideAllStrategyParams();
            } else {
                this.showAlert('策略创建失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('创建策略时出错:', error);
            this.showAlert('策略创建失败：网络错误', 'error');
        }
    }

    /**
     * 显示消息提示 - 改为浮层toast样式
     */
    showAlert(message, type = 'info') {
        // 创建toast容器（如果不存在）
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 350px;
                pointer-events: none;
            `;
            document.body.appendChild(toastContainer);
        }

        // 创建toast元素
        const toast = document.createElement('div');
        toast.style.cssText = `
            background: rgba(${type === 'success' ? '40, 167, 69' : type === 'error' ? '220, 53, 69' : '13, 110, 253'}, 0.95);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            font-size: 14px;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            pointer-events: auto;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        `;
        
        // 添加图标
        const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
        toast.innerHTML = `<span style="margin-right: 8px; font-weight: bold;">${icon}</span>${message}`;
        
        toastContainer.appendChild(toast);
        
        // 动画显示
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        }, 10);
        
        // 自动隐藏
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, 3000);
    }

    /**
     * 加载策略列表
     */
    async loadStrategies() {
        try {
            const response = await fetch('/api/quantitative/strategies');
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.strategies = result.data;
                this.updateStrategiesUI();
                this.updateStatsUI();
            } else {
                console.error('加载策略失败:', result.message);
            }
        } catch (error) {
            console.error('加载策略时出错:', error);
        }
    }

    /**
     * 加载交易信号
     */
    async loadSignals() {
        try {
            const response = await fetch('/api/quantitative/signals');
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.signals = result.data;
                this.updateSignalsUI();
            } else {
                console.error('加载信号失败:', result.message);
            }
        } catch (error) {
            console.error('加载信号时出错:', error);
        }
    }

    /**
     * 加载持仓信息
     */
    async loadPositions() {
        try {
            const response = await fetch('/api/quantitative/positions');
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.positions = result.data;
                this.updatePositionsUI();
            } else {
                console.error('加载持仓失败:', result.message);
            }
        } catch (error) {
            console.error('加载持仓时出错:', error);
        }
    }

    /**
     * 加载绩效数据
     */
    async loadPerformance() {
        try {
            const response = await fetch('/api/quantitative/performance');
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.updatePerformanceChart(result.data);
            } else {
                console.error('加载绩效失败:', result.message);
            }
        } catch (error) {
            console.error('加载绩效时出错:', error);
        }
    }

    /**
     * 更新策略列表UI
     */
    updateStrategiesUI() {
        const tbody = document.getElementById('strategies-table');
        if (!tbody) return;

        if (this.strategies.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4"><i class="fas fa-inbox me-2"></i>暂无策略</td></tr>';
            return;
        }

        tbody.innerHTML = this.strategies.map(strategy => this.renderStrategy(strategy)).join('');
    }

    /**
     * 渲染单个策略
     */
    renderStrategy(strategy) {
        const typeMapping = this.getStrategyTypeMapping();
        const strategyTypeName = typeMapping[strategy.type] || strategy.type;
        
        // 格式化收益率显示
        const totalReturn = (strategy.total_return * 100).toFixed(2);
        const dailyReturn = (strategy.daily_return * 100).toFixed(2);
        const winRate = (strategy.win_rate * 100).toFixed(1);
        
        // 收益率颜色
        const returnColor = strategy.total_return >= 0 ? 'text-success' : 'text-danger';
        const dailyReturnColor = strategy.daily_return >= 0 ? 'text-success' : 'text-danger';
        
        // 排名徽章
        const rankBadge = strategy.total_return > 0.1 ? 'bg-warning' : strategy.total_return > 0.05 ? 'bg-info' : 'bg-secondary';
        
        return `
            <tr>
                <td>
                    <a href="#" class="text-decoration-none fw-bold text-primary strategy-name-link" 
                       data-strategy-id="${strategy.id}" 
                       title="点击编辑策略配置">
                        ${strategy.name}
                    </a>
                    <div class="small text-muted">${strategyTypeName}</div>
                </td>
                <td>
                    <span class="badge bg-secondary">${strategy.symbol}</span>
                    <div class="small text-muted">交易${strategy.total_trades}次</div>
                </td>
                <td>
                    <div class="${returnColor} fw-bold">${totalReturn >= 0 ? '+' : ''}${totalReturn}%</div>
                    <div class="small ${dailyReturnColor}">今日: ${dailyReturn >= 0 ? '+' : ''}${dailyReturn}%</div>
                </td>
                <td>
                    <div class="text-info fw-bold">${winRate}%</div>
                    <div class="small text-muted">胜率</div>
                </td>
                <td>
                    ${strategy.enabled ? 
                        '<span class="badge bg-success"><i class="fas fa-play me-1"></i>运行中</span>' : 
                        '<span class="badge bg-secondary"><i class="fas fa-pause me-1"></i>已停止</span>'
                    }
                    ${strategy.total_return > 0.1 ? '<div class="small"><span class="badge bg-warning">冠军</span></div>' : 
                      strategy.total_return > 0.05 ? '<div class="small"><span class="badge bg-info">优秀</span></div>' : ''}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary btn-sm toggle-strategy-btn" 
                                data-strategy-id="${strategy.id}" 
                                data-is-active="${strategy.enabled}"
                                title="${strategy.enabled ? '停止策略' : '启动策略'}">
                            <i class="fas ${strategy.enabled ? 'fa-pause' : 'fa-play'}"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm delete-strategy-btn" 
                                data-strategy-id="${strategy.id}"
                                title="删除策略">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * 更新信号列表UI
     */
    updateSignalsUI() {
        const container = document.getElementById('signals-list');
        if (!container) return;

        const signalsCount = document.getElementById('signals-count');
        if (signalsCount) {
            signalsCount.textContent = `${this.signals.length} 条信号`;
        }

        if (this.signals.length === 0) {
            container.innerHTML = '<div class="list-group-item text-center text-muted py-4"><i class="fas fa-radio me-2"></i>等待交易信号...</div>';
            return;
        }

        container.innerHTML = this.signals.slice(0, 10).map(signal => `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge ${signal.signal_type === 'BUY' ? 'bg-success' : 'bg-danger'}">${signal.signal_type}</span>
                    <strong class="ms-2">${signal.symbol}</strong>
                    <small class="text-muted ms-2">${signal.strategy_name}</small>
                </div>
                <div class="text-end">
                    <div><strong>¥${signal.price.toFixed(2)}</strong></div>
                    <small class="text-muted">${new Date(signal.timestamp).toLocaleTimeString()}</small>
                </div>
            </div>
        `).join('');
    }

    /**
     * 更新持仓列表UI
     */
    updatePositionsUI() {
        const container = document.getElementById('positions-list');
        if (!container) return;

        if (this.positions.length === 0) {
            container.innerHTML = '<div class="list-group-item text-center text-muted py-4"><i class="fas fa-inbox me-2"></i>暂无持仓</div>';
            return;
        }

        container.innerHTML = this.positions.map(position => `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>${position.symbol}</strong>
                    <span class="badge bg-primary">${position.strategy_name}</span>
                </div>
                <div class="row text-sm">
                    <div class="col-4">
                        <div>数量: ${position.quantity}</div>
                        <div>入价: ¥${position.entry_price.toFixed(2)}</div>
                    </div>
                    <div class="col-4">
                        <div>现价: ¥${position.current_price.toFixed(2)}</div>
                        <div class="${position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">盈亏: ¥${position.unrealized_pnl.toFixed(2)}</div>
                    </div>
                    <div class="col-4 text-end">
                        <button class="btn btn-sm btn-warning" onclick="app.closePosition(${position.id})">平仓</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * 更新统计卡片UI
     */
    updateStatsUI() {
        const activeStrategies = this.strategies.filter(s => s.enabled).length;
        const totalReturn = this.strategies.reduce((sum, s) => sum + (s.total_return || 0), 0);
        const todaySignals = this.signals.filter(s => {
            const today = new Date().toDateString();
            return new Date(s.timestamp).toDateString() === today;
        }).length;

        // 更新统计卡片
        const totalStrategiesElement = document.getElementById('total-strategies');
        if (totalStrategiesElement) {
            totalStrategiesElement.textContent = this.strategies.length;
        }

        const runningStrategiesElement = document.getElementById('running-strategies');
        if (runningStrategiesElement) {
            runningStrategiesElement.textContent = activeStrategies;
        }

        const recentSignalsElement = document.getElementById('recent-signals');
        if (recentSignalsElement) {
            recentSignalsElement.textContent = todaySignals;
        }

        const totalReturnElement = document.getElementById('total-return');
        if (totalReturnElement) {
            const returnText = (totalReturn * 100).toFixed(2) + '%';
            totalReturnElement.textContent = totalReturn >= 0 ? '+' + returnText : returnText;
            totalReturnElement.className = totalReturn >= 0 ? 'text-success' : 'text-danger';
        }

        // 更新绩效指标
        const metricTotalReturnElement = document.getElementById('metric-total-return');
        if (metricTotalReturnElement) {
            const returnText = (totalReturn * 100).toFixed(2) + '%';
            metricTotalReturnElement.textContent = totalReturn >= 0 ? '+' + returnText : returnText;
            metricTotalReturnElement.className = totalReturn >= 0 ? 'metric-value text-success' : 'metric-value text-danger';
        }
    }

    /**
     * 初始化图表
     */
    initChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '累计收益',
                    data: [],
                    borderColor: '#1677ff',
                    backgroundColor: 'rgba(22, 119, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return (value * 100).toFixed(1) + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * 更新绩效图表
     */
    updatePerformanceChart(data) {
        if (!this.performanceChart || !data || !Array.isArray(data)) return;

        const labels = data.map(item => new Date(item.date).toLocaleDateString());
        const values = data.map(item => item.cumulative_return);

        this.performanceChart.data.labels = labels;
        this.performanceChart.data.datasets[0].data = values;
        this.performanceChart.update();
    }

    /**
     * 获取策略类型名称
     */
    getStrategyTypeName(type) {
        const typeNames = {
            'momentum': '动量策略',
            'mean_reversion': '均值回归',
            'breakout': '突破策略'
        };
        return typeNames[type] || type;
    }

    /**
     * 切换策略状态
     */
    async toggleStrategy(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/toggle`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showAlert('策略状态更新成功！', 'success');
                this.loadStrategies();
            } else {
                this.showAlert('策略状态更新失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('切换策略状态时出错:', error);
            this.showAlert('策略状态更新失败：网络错误', 'error');
        }
    }

    /**
     * 删除策略
     */
    async deleteStrategy(strategyId) {
        if (!confirm('确定要删除这个策略吗？')) return;

        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showAlert('策略删除成功！', 'success');
                this.loadStrategies();
            } else {
                this.showAlert('策略删除失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('删除策略时出错:', error);
            this.showAlert('策略删除失败：网络错误', 'error');
        }
    }

    /**
     * 平仓
     */
    async closePosition(positionId) {
        if (!confirm('确定要平仓吗？')) return;

        try {
            const response = await fetch(`/api/quantitative/positions/${positionId}/close`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showAlert('平仓成功！', 'success');
                this.loadPositions();
            } else {
                this.showAlert('平仓失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('平仓时出错:', error);
            this.showAlert('平仓失败：网络错误', 'error');
        }
    }

    /**
     * 刷新所有数据
     */
    refreshAllData() {
        this.loadStrategies();
        this.loadSignals();
        this.loadPositions();
        this.loadPerformance();
    }

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.refreshInterval = setInterval(() => {
            this.refreshAllData();
        }, this.refreshRate);
    }

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * 打开编辑策略对话框
     */
    async openEditStrategy(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`);
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                const strategy = result.data;
                
                // 填充编辑表单
                document.getElementById('editStrategyId').value = strategy.id;
                document.getElementById('editStrategyName').value = strategy.name;
                document.getElementById('editStrategyType').value = strategy.type;
                document.getElementById('editStrategySymbol').value = strategy.symbol;
                
                // 填充基础参数
                document.getElementById('editLookbackPeriod').value = strategy.parameters.lookback_period || 20;
                document.getElementById('editQuantity').value = strategy.parameters.quantity || 1.0;
                
                // 根据策略类型显示对应参数并填充值
                this.toggleEditStrategyParams(strategy.type);
                
                if (strategy.type === 'momentum') {
                    document.getElementById('editMomentumThreshold').value = strategy.parameters.momentum_threshold || strategy.parameters.threshold || 0.001;
                } else if (strategy.type === 'mean_reversion') {
                    document.getElementById('editStdMultiplier').value = strategy.parameters.std_multiplier || 2.0;
                } else if (strategy.type === 'breakout') {
                    document.getElementById('editBreakoutThreshold').value = strategy.parameters.breakout_threshold || 0.01;
                }
                
                // 显示编辑模态框
                const modal = new bootstrap.Modal(document.getElementById('editStrategyModal'));
                modal.show();
                
            } else {
                this.showAlert('获取策略信息失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('获取策略信息时出错:', error);
            this.showAlert('获取策略信息失败：网络错误', 'error');
        }
    }

    /**
     * 更新策略配置
     */
    async updateStrategy() {
        const strategyId = document.getElementById('editStrategyId').value;
        const strategyName = document.getElementById('editStrategyName').value;
        const strategyType = document.getElementById('editStrategyType').value;
        const strategySymbol = document.getElementById('editStrategySymbol').value;
        const lookbackPeriod = parseInt(document.getElementById('editLookbackPeriod').value) || 20;
        const quantity = parseFloat(document.getElementById('editQuantity').value) || 1.0;

        if (!strategyName || !strategyType || !strategySymbol) {
            this.showAlert('请填写完整的策略信息！', 'error');
            return;
        }

        // 根据策略类型收集特定参数
        const params = {
            lookback_period: lookbackPeriod,
            quantity: quantity
        };

        if (strategyType === 'momentum') {
            const threshold = parseFloat(document.getElementById('editMomentumThreshold').value) || 0.001;
            params.momentum_threshold = threshold;
            params.threshold = threshold; // 保持兼容性
        } else if (strategyType === 'mean_reversion') {
            const stdMultiplier = parseFloat(document.getElementById('editStdMultiplier').value) || 2.0;
            params.std_multiplier = stdMultiplier;
        } else if (strategyType === 'breakout') {
            const breakoutThreshold = parseFloat(document.getElementById('editBreakoutThreshold').value) || 0.01;
            params.breakout_threshold = breakoutThreshold;
        } else if (strategyType === 'grid_trading') {
            const gridSpacing = parseFloat(document.getElementById('editGridSpacing').value) || 0.02;
            const gridCount = parseInt(document.getElementById('editGridCount').value) || 10;
            params.grid_spacing = gridSpacing;
            params.grid_count = gridCount;
        } else if (strategyType === 'high_frequency') {
            const volatilityThreshold = parseFloat(document.getElementById('editVolatilityThreshold').value) || 0.001;
            const minProfit = parseFloat(document.getElementById('editMinProfit').value) || 0.0005;
            params.volatility_threshold = volatilityThreshold;
            params.min_profit = minProfit;
        } else if (strategyType === 'trend_following') {
            const trendThreshold = parseFloat(document.getElementById('editTrendThreshold').value) || 0.02;
            params.trend_threshold = trendThreshold;
        }

        const payload = {
            name: strategyName,
            symbol: strategySymbol,
            parameters: params
        };

        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showAlert('策略更新成功！', 'success');
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('editStrategyModal'));
                modal.hide();
                // 重新加载策略列表
                this.loadStrategies();
            } else {
                this.showAlert('策略更新失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('更新策略时出错:', error);
            this.showAlert('策略更新失败：网络错误', 'error');
        }
    }

    /**
     * 策略类型映射
     */
    getStrategyTypeMapping() {
        return {
            'momentum': '动量策略',
            'mean_reversion': '均值回归策略',
            'breakout': '突破策略',
            'grid_trading': '网格交易策略',
            'high_frequency': '高频交易策略',
            'trend_following': '趋势跟踪策略'
        };
    }
}

// 全局函数，用于按钮点击事件
window.QuantitativeApp = QuantitativeApp;

// 自动交易控制
let autoTradingEnabled = false;

// 初始化自动交易功能
function initAutoTrading() {
    // 加载交易状态
    loadTradingStatus();
    
    // 绑定自动交易开关
    document.getElementById('autoTradingSwitch').addEventListener('change', function() {
        const enabled = this.checked;
        toggleAutoTrading(enabled);
    });
    
    // 定时更新交易状态
    setInterval(loadTradingStatus, 10000); // 每10秒更新一次
    
    // 定时更新持仓信息
    setInterval(loadRealPositions, 5000); // 每5秒更新一次
}

// 加载交易状态
async function loadTradingStatus() {
    try {
        const response = await fetch('/api/quantitative/trading-status');
        const result = await response.json();
        
        if (result.success) {
            updateTradingStatusUI(result.data);
        } else {
            console.error('获取交易状态失败:', result.message);
            document.getElementById('autoTradingStatus').textContent = '获取状态失败';
        }
    } catch (error) {
        console.error('请求交易状态失败:', error);
        document.getElementById('autoTradingStatus').textContent = '连接失败';
    }
}

// 更新交易状态UI
function updateTradingStatusUI(data) {
    const switchElement = document.getElementById('autoTradingSwitch');
    const statusElement = document.getElementById('autoTradingStatus');
    
    autoTradingEnabled = data.auto_trading_enabled || false;
    switchElement.checked = autoTradingEnabled;
    statusElement.textContent = autoTradingEnabled ? '已启用' : '已禁用';
    statusElement.className = autoTradingEnabled ? 'text-success' : 'text-secondary';
    
    // 更新数据显示
    if (data.balance !== undefined) {
        document.getElementById('accountBalance').textContent = `${data.balance.toFixed(2)} USDT`;
    }
    
    if (data.daily_pnl !== undefined) {
        const pnlElement = document.getElementById('dailyPnl');
        pnlElement.textContent = `${data.daily_pnl.toFixed(2)} USDT`;
        pnlElement.className = `metric-value ${data.daily_pnl >= 0 ? 'text-success' : 'text-danger'}`;
    }
    
    if (data.daily_trades !== undefined) {
        document.getElementById('dailyTrades').textContent = `${data.daily_trades} 笔`;
    }
    
    if (data.daily_win_rate !== undefined) {
        const winRateElement = document.getElementById('dailyWinRate');
        const winRate = (data.daily_win_rate * 100).toFixed(1);
        winRateElement.textContent = `${winRate}%`;
        winRateElement.className = `metric-value ${data.daily_win_rate >= 0.6 ? 'text-success' : data.daily_win_rate >= 0.4 ? 'text-warning' : 'text-danger'}`;
    }
    
    if (data.positions_count !== undefined) {
        document.getElementById('currentPositions').textContent = `${data.positions_count} 个`;
    }
    
    if (data.daily_return !== undefined) {
        const returnElement = document.getElementById('dailyReturn');
        const returnPercent = (data.daily_return * 100).toFixed(2);
        returnElement.textContent = `${returnPercent}%`;
        returnElement.className = `metric-value ${data.daily_return >= 0 ? 'text-success' : 'text-danger'}`;
        
        // 如果接近目标收益，高亮显示
        if (data.daily_return >= 0.045) { // 接近5%目标时
            returnElement.className += ' fw-bold';
        }
    }
}

// 切换自动交易
async function toggleAutoTrading(enabled) {
    try {
        const response = await fetch('/api/quantitative/toggle-auto-trading', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ enabled: enabled })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message, 'success');
            autoTradingEnabled = enabled;
            
            // 立即更新状态
            setTimeout(loadTradingStatus, 1000);
        } else {
            showToast(`操作失败: ${result.message}`, 'error');
            // 恢复开关状态
            document.getElementById('autoTradingSwitch').checked = autoTradingEnabled;
        }
    } catch (error) {
        console.error('切换自动交易失败:', error);
        showToast('网络错误，请稍后重试', 'error');
        // 恢复开关状态
        document.getElementById('autoTradingSwitch').checked = autoTradingEnabled;
    }
}

// 加载实时持仓
async function loadRealPositions() {
    try {
        const response = await fetch('/api/quantitative/positions');
        const result = await response.json();
        
        if (result.success) {
            updatePositionsUI(result.data);
        }
    } catch (error) {
        console.error('获取持仓失败:', error);
    }
}

// 更新持仓UI
function updatePositionsUI(positions) {
    const container = document.getElementById('realPositions');
    
    if (!positions || positions.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-inbox me-2"></i>暂无持仓
            </div>
        `;
        return;
    }
    
    // 分别显示真实持仓和模拟持仓
    const realPositions = positions.filter(p => p.source === 'real');
    const simPositions = positions.filter(p => p.source === 'simulation');
    
    let html = '';
    
    if (realPositions.length > 0) {
        html += '<div class="mb-3"><h6 class="text-primary mb-2">真实持仓</h6>';
        realPositions.forEach(position => {
            const pnlClass = position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger';
            const pnlIcon = position.unrealized_pnl >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
            
            html += `
                <div class="border rounded p-2 mb-2 bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${position.symbol}</strong>
                            <span class="text-muted ms-2">${position.side.toUpperCase()}</span>
                        </div>
                        <div class="text-end">
                            <div class="${pnlClass}">
                                <i class="fas ${pnlIcon} me-1"></i>
                                ${position.unrealized_pnl.toFixed(2)} USDT
                            </div>
                        </div>
                    </div>
                    <div class="row text-sm text-muted mt-1">
                        <div class="col-6">数量: ${position.quantity.toFixed(6)}</div>
                        <div class="col-6">成本: ${position.entry_price.toFixed(6)}</div>
                    </div>
                    <div class="mt-2">
                        <button class="btn btn-outline-danger btn-sm" onclick="forceClosePosition('${position.symbol}')">
                            <i class="fas fa-times me-1"></i>强制平仓
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    if (simPositions.length > 0) {
        html += '<div><h6 class="text-secondary mb-2">模拟持仓</h6>';
        simPositions.slice(0, 3).forEach(position => { // 只显示前3个模拟持仓
            const pnlClass = position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger';
            
            html += `
                <div class="border rounded p-2 mb-2" style="background-color: #f8f9fa;">
                    <div class="d-flex justify-content-between">
                        <span>${position.symbol}</span>
                        <span class="${pnlClass}">${position.unrealized_pnl.toFixed(2)} USDT</span>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    container.innerHTML = html;
}

// 强制平仓
async function forceClosePosition(symbol) {
    if (!confirm(`确定要强制平仓 ${symbol} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/quantitative/force-close/${symbol}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('平仓指令已发送', 'success');
            // 立即刷新持仓
            setTimeout(loadRealPositions, 1000);
        } else {
            showToast(`平仓失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('强制平仓失败:', error);
        showToast('操作失败，请稍后重试', 'error');
    }
}

// 修改原有的 initQuantitative 函数
function initQuantitative() {
    loadStrategies();
    loadSignals();
    loadPositions();
    loadPerformance();
    
    // 初始化自动交易功能
    initAutoTrading();
    
    // 定时刷新（保持原有频率）
    setInterval(() => {
        loadStrategies();
        loadSignals();
        loadPositions();
        loadPerformance();
    }, 30000);
} 