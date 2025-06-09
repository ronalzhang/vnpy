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
let evolutionLogTimer = null;
let managementConfig = {
    evolutionInterval: 10,
    maxStrategies: 20,
    minTrades: 10,
    minWinRate: 65,
    minProfit: 0,
    maxDrawdown: 10,
    minSharpeRatio: 1.0,
    maxPositionSize: 100,
    stopLossPercent: 5,
    eliminationDays: 7,
    minScore: 50
};

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
        this.loadSystemStatus(); // 加载真实系统状态
        this.startAutoRefresh();
        this.initEvolutionLog(); // 初始化进化日志
        this.loadManagementConfig(); // 加载管理配置
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
            // 系统控制台状态 - 运行中金色闪动
            systemStatusEl.innerHTML = '<span class="status-indicator status-running"></span>在线';
            systemToggle.classList.add('active');
            
            // 导航栏状态 - 运行中金色闪动
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator status-running';
                statusText.textContent = '运行中';
            }
        } else {
            // 系统控制台状态 - 离线黑色
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
                
                // 安全显示数据，确保有效才显示，使用U作为货币单位（U放在数字后面）
                this.safeSetText('totalBalance', account.balance, '', 'U');
                
                const dailyPnl = account.daily_pnl;
                const dailyPnlEl = document.getElementById('dailyPnl');
                if (dailyPnlEl) {
                    if (dailyPnl !== undefined && dailyPnl !== null && !isNaN(dailyPnl)) {
                        dailyPnlEl.textContent = `${dailyPnl >= 0 ? '+' : ''}${this.formatNumber(dailyPnl)}U`;
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
    safeSetText(elementId, value, prefix = '', suffix = '') {
        const element = document.getElementById(elementId);
        if (element) {
            if (value !== undefined && value !== null && !isNaN(value)) {
                element.textContent = prefix + this.formatNumber(value) + suffix;
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
            console.log('正在加载策略列表...');
            const response = await fetch('/api/quantitative/strategies');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('策略API响应:', data);
            
            // 处理双层data嵌套：{data: {data: [...]}}
            if (data.data && data.data.data && Array.isArray(data.data.data)) {
                this.strategies = data.data.data;
                console.log(`✅ 成功加载 ${this.strategies.length} 个策略`);
                this.renderStrategies();
            } else if (data.data && Array.isArray(data.data)) {
                // 兼容单层data结构
                this.strategies = data.data;
                console.log(`✅ 成功加载 ${this.strategies.length} 个策略`);
                this.renderStrategies();
            } else {
                console.error('❌ 无效的策略数据结构:', data);
                console.log('尝试渲染空策略状态');
                this.renderEmptyStrategies();
            }
        } catch (error) {
            console.error('❌ 加载策略失败:', error);
            console.log('网络或解析错误，渲染空策略状态');
            this.renderEmptyStrategies();
        }
    }

    // 渲染策略列表
    renderStrategies() {
        const container = document.getElementById('strategiesContainer');
        if (!container) {
            console.error('策略容器不存在');
            return;
        }

        console.log('渲染策略数据:', this.strategies);

        if (!this.strategies || this.strategies.length === 0) {
            console.log('没有策略数据，渲染空状态');
            this.renderEmptyStrategies();
            return;
        }

        // 按评分排序 - 使用正确的字段名
        const sortedStrategies = this.strategies.sort((a, b) => 
            (b.final_score || 0) - (a.final_score || 0)
        );

        console.log('排序后的策略:', sortedStrategies);

        container.innerHTML = sortedStrategies.map(strategy => {
            // 生成评分显示 - 使用正确的字段名
            const score = strategy.final_score || 0;
            // 修复成功率超过100%的问题 - 限制在0-100%之间
            const winRate = Math.min(Math.max(strategy.win_rate || 0, 0), 1);
            const totalReturn = strategy.total_return || 0;
            const totalTrades = strategy.total_trades || 0;
            const generation = strategy.generation || 1;
            const round = strategy.cycle || 1;
            const qualified = strategy.qualified_for_trading || false;
            
            // 评分状态显示 - 使用65分合格线
            let scoreColor = 'text-secondary';
            let scoreStatus = '';
            if (score >= 70) {
                scoreColor = 'text-success';
                scoreStatus = '🏆 优秀';
            } else if (score >= 65) {
                scoreColor = 'text-warning';
                scoreStatus = '✅ 合格';
            } else {
                scoreColor = 'text-danger';
                scoreStatus = '⚠️ 待优化';
            }
            
            // 交易状态 - 根据合格线和交易次数判断
            const isSimulation = score < 65 || totalTrades < 10;
            const tradingStatus = isSimulation ? '模拟中' : '真实交易';
            const tradingBadgeClass = isSimulation ? 'bg-warning' : 'bg-success';
            
            return `
            <div class="col-md-4 mb-3">
                <div class="card strategy-card ${strategy.enabled ? 'strategy-running' : 'strategy-stopped'}">
                    <div class="card-body">
                        <!-- 顶部：标题和状态 -->
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="card-title mb-0">
                                    <a href="javascript:void(0)" onclick="app.showStrategyConfig('${strategy.id}')" class="text-decoration-none">
                                        ${strategy.name}
                                    </a>
                                </h6>
                                <small class="text-muted">${strategy.symbol} • ${strategy.evolution_display || `第${generation}代第${round}轮`}</small>
                            </div>
                            <div class="text-end">
                                <span class="badge ${strategy.enabled ? 'bg-success' : 'bg-secondary'} mb-1">
                                    ${strategy.enabled ? '运行中' : '已停止'}
                                </span><br>
                                <span class="badge ${tradingBadgeClass}">
                                    ${tradingStatus}
                                </span>
                            </div>
                        </div>
                        
                        <!-- 中部：策略指标 -->
                        <div class="strategy-metrics mb-3">
                            <div class="row text-center">
                                <div class="col-4">
                                    <div class="metric-item">
                                        <div class="${scoreColor} fw-bold">${score.toFixed(1)}</div>
                                        <small class="text-muted">评分</small>
                                    </div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-item">
                                        <div class="text-success fw-bold">${(winRate * 100).toFixed(1)}%</div>
                                        <small class="text-muted">成功率</small>
                                    </div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-item">
                                        <div class="text-info fw-bold">${totalTrades}</div>
                                        <small class="text-muted">交易次数</small>
                                    </div>
                                </div>
                            </div>
                            <div class="row text-center mt-2">
                                <div class="col-6">
                                    <div class="metric-item">
                                        <div class="text-primary fw-bold">${(totalReturn * 100).toFixed(2)}%</div>
                                        <small class="text-muted">总收益</small>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="metric-item">
                                        <div class="text-warning fw-bold">${((totalReturn / 30) * 100).toFixed(3)}%</div>
                                        <small class="text-muted">日收益</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 底部：操作按钮 -->
                        <div class="d-flex justify-content-center">
                            <button class="btn btn-sm btn-outline-info" 
                                    onclick="app.showStrategyLogs('${strategy.id}')"
                                    title="查看交易和优化日志">
                                <i class="fas fa-chart-line me-1"></i>日志
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            `;
        }).join('');

        console.log('策略卡片渲染完成');
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

    // 显示策略配置弹窗
    async showStrategyConfig(strategyId) {
        try {
            // 获取策略详情
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showMessage('获取策略信息失败', 'error');
                return;
            }
            
            const strategy = data.data;
            
            // 填充基本信息
            document.getElementById('strategyId').value = strategy.id;
            document.getElementById('strategyName').value = strategy.name;
            document.getElementById('strategySymbol').value = strategy.symbol;
            document.getElementById('strategyType').value = strategy.type;
            document.getElementById('strategyEnabled').checked = strategy.enabled;
            
            // 生成参数表单
            this.generateParameterForm(strategy.type, strategy.parameters);
            
            // 填充统计信息 - 修复NaN问题
            const totalReturn = strategy.total_return || 0;
            const winRate = strategy.win_rate || 0;
            const totalTrades = strategy.total_trades || 0;
            const dailyReturn = strategy.daily_return || 0;
            
            document.getElementById('strategyTotalReturn').textContent = `${(totalReturn * 100).toFixed(2)}%`;
            document.getElementById('strategyWinRate').textContent = `${(winRate * 100).toFixed(1)}%`;
            document.getElementById('strategyTotalTrades').textContent = totalTrades;
            document.getElementById('strategyDailyReturn').textContent = `${(dailyReturn * 100).toFixed(2)}%`;
            
            // 绑定保存事件
            this.bindConfigEvents(strategyId);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('strategyConfigModal'));
            modal.show();
            
        } catch (error) {
            console.error('显示策略配置失败:', error);
            this.showMessage('显示策略配置失败', 'error');
        }
    }

    // 生成参数表单
    generateParameterForm(strategyType, parameters) {
        const container = document.getElementById('strategyParameters');
        let parametersHtml = '';
        
        // 根据策略类型生成对应的参数表单（扩展到18个重要参数）
        const parameterConfigs = {
            'momentum': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 5, max: 100, step: 1},
                {key: 'threshold', label: '动量阈值', type: 'number', min: 0.001, max: 0.1, step: 0.001},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.001, max: 1000, step: 0.001},
                {key: 'momentum_threshold', label: '动量确认阈值', type: 'number', min: 0.001, max: 0.1, step: 0.001},
                {key: 'volume_threshold', label: '成交量倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'stop_loss', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'max_position_size', label: '最大仓位(%)', type: 'number', min: 1, max: 100, step: 1},
                {key: 'min_volume', label: '最小成交量', type: 'number', min: 1000, max: 1000000, step: 1000},
                {key: 'volatility_filter', label: '波动率过滤', type: 'number', min: 0.001, max: 0.1, step: 0.001},
                {key: 'correlation_threshold', label: '相关性阈值', type: 'number', min: 0.1, max: 0.9, step: 0.1},
                {key: 'rsi_upper', label: 'RSI超买线', type: 'number', min: 60, max: 90, step: 1},
                {key: 'rsi_lower', label: 'RSI超卖线', type: 'number', min: 10, max: 40, step: 1},
                {key: 'ma_short', label: '短期均线', type: 'number', min: 5, max: 50, step: 1},
                {key: 'ma_long', label: '长期均线', type: 'number', min: 20, max: 200, step: 1},
                {key: 'signal_strength', label: '信号强度', type: 'number', min: 0.1, max: 1.0, step: 0.1},
                {key: 'holding_period', label: '持仓周期(分钟)', type: 'number', min: 1, max: 1440, step: 1},
                {key: 'risk_reward_ratio', label: '风险收益比', type: 'number', min: 1.0, max: 5.0, step: 0.1}
            ],
            'mean_reversion': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'std_multiplier', label: '标准差倍数', type: 'number', min: 1.0, max: 4.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.001, max: 1000, step: 0.001},
                {key: 'reversion_threshold', label: '回归阈值', type: 'number', min: 0.005, max: 0.05, step: 0.001},
                {key: 'min_deviation', label: '最小偏离度', type: 'number', min: 0.01, max: 0.1, step: 0.001},
                {key: 'stop_loss', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'max_position_size', label: '最大仓位(%)', type: 'number', min: 1, max: 100, step: 1},
                {key: 'bollinger_period', label: '布林带周期', type: 'number', min: 10, max: 50, step: 1},
                {key: 'bollinger_std', label: '布林带标准差', type: 'number', min: 1.5, max: 3.0, step: 0.1},
                {key: 'entry_threshold', label: '入场阈值', type: 'number', min: 0.8, max: 2.0, step: 0.1},
                {key: 'exit_threshold', label: '出场阈值', type: 'number', min: 0.2, max: 1.0, step: 0.1}
            ],
            'grid_trading': [
                {key: 'grid_spacing', label: '网格间距(%)', type: 'number', min: 0.5, max: 5.0, step: 0.1},
                {key: 'grid_count', label: '网格数量', type: 'number', min: 5, max: 30, step: 1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 10000, step: 1},
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 50, max: 200, step: 10},
                {key: 'min_profit', label: '最小利润(%)', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'stop_loss', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'max_position_size', label: '最大仓位(%)', type: 'number', min: 1, max: 100, step: 1},
                {key: 'grid_upper_limit', label: '网格上限(%)', type: 'number', min: 5, max: 50, step: 1},
                {key: 'grid_lower_limit', label: '网格下限(%)', type: 'number', min: 5, max: 50, step: 1}
            ],
            'breakout': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'breakout_threshold', label: '突破阈值(%)', type: 'number', min: 0.5, max: 3.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.1, max: 100, step: 0.1},
                {key: 'volume_threshold', label: '成交量倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'confirmation_periods', label: '确认周期', type: 'number', min: 1, max: 10, step: 1},
                {key: 'stop_loss', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'max_position_size', label: '最大仓位(%)', type: 'number', min: 1, max: 100, step: 1},
                {key: 'atr_multiplier', label: 'ATR倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1}
            ],
            'high_frequency': [
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 1000, step: 1},
                {key: 'min_profit', label: '最小利润(%)', type: 'number', min: 0.01, max: 0.1, step: 0.01},
                {key: 'volatility_threshold', label: '波动率阈值', type: 'number', min: 0.0001, max: 0.01, step: 0.0001},
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 5, max: 20, step: 1},
                {key: 'signal_interval', label: '信号间隔(秒)', type: 'number', min: 10, max: 60, step: 5},
                {key: 'stop_loss', label: '止损百分比(%)', type: 'number', min: 0.5, max: 5.0, step: 0.1},
                {key: 'max_position_size', label: '最大仓位(%)', type: 'number', min: 1, max: 50, step: 1},
                {key: 'spread_threshold', label: '价差阈值', type: 'number', min: 0.0001, max: 0.001, step: 0.0001},
                {key: 'latency_limit', label: '延迟限制(毫秒)', type: 'number', min: 1, max: 100, step: 1}
            ],
            'trend_following': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 20, max: 100, step: 5},
                {key: 'trend_threshold', label: '趋势阈值(%)', type: 'number', min: 0.5, max: 3.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 1000, step: 1},
                {key: 'trend_strength_min', label: '最小趋势强度', type: 'number', min: 0.1, max: 1.0, step: 0.1},
                {key: 'stop_loss', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'max_position_size', label: '最大仓位(%)', type: 'number', min: 1, max: 100, step: 1},
                {key: 'ema_short', label: '短期EMA', type: 'number', min: 5, max: 50, step: 1},
                {key: 'ema_long', label: '长期EMA', type: 'number', min: 20, max: 200, step: 1},
                {key: 'adx_threshold', label: 'ADX趋势阈值', type: 'number', min: 20, max: 50, step: 1}
            ]
        };
        
        const configs = parameterConfigs[strategyType] || [];
        
        configs.forEach(config => {
            const value = parameters[config.key] || '';
            parametersHtml += `
                <div class="row mb-2">
                    <div class="col-6">
                        <label class="form-label">${config.label}</label>
                    </div>
                    <div class="col-6">
                        <input type="${config.type}" 
                               class="form-control form-control-sm" 
                               name="${config.key}"
                               value="${value}"
                               min="${config.min}"
                               max="${config.max}"
                               step="${config.step}">
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = parametersHtml;
    }

    // 绑定配置事件
    bindConfigEvents(strategyId) {
        // 保存配置
        document.getElementById('saveStrategyConfig').onclick = async () => {
            await this.saveStrategyConfig(strategyId);
        };
        
        // 重置参数
        document.getElementById('resetStrategyParams').onclick = async () => {
            await this.resetStrategyParams(strategyId);
        };
    }

    // 保存策略配置
    async saveStrategyConfig(strategyId) {
        try {
            const form = document.getElementById('strategyConfigForm');
            const formData = new FormData(form);
            
            // 收集参数
            const parameters = {};
            const parameterInputs = form.querySelectorAll('#strategyParameters input');
            parameterInputs.forEach(input => {
                parameters[input.name] = parseFloat(input.value) || input.value;
            });
            
            const configData = {
                name: formData.get('strategyName'),
                symbol: formData.get('strategySymbol'),
                enabled: formData.get('strategyEnabled') === 'on',
                parameters: parameters
            };
            
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showMessage('策略配置保存成功', 'success');
                // 关闭模态框
                bootstrap.Modal.getInstance(document.getElementById('strategyConfigModal')).hide();
                // 刷新策略列表
                this.loadStrategies();
            } else {
                this.showMessage(data.message || '保存失败', 'error');
            }
            
        } catch (error) {
            console.error('保存策略配置失败:', error);
            this.showMessage('保存策略配置失败', 'error');
        }
    }

    // 重置策略参数
    async resetStrategyParams(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/reset`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showMessage('策略参数已重置', 'success');
                // 重新加载配置
                this.showStrategyConfig(strategyId);
            } else {
                this.showMessage(data.message || '重置失败', 'error');
            }
            
        } catch (error) {
            console.error('重置策略参数失败:', error);
            this.showMessage('重置策略参数失败', 'error');
        }
    }

    // 显示策略日志
    async showStrategyLogs(strategyId) {
        try {
            // 设置模态框标题
            document.getElementById('strategyLogsModalLabel').innerHTML = 
                `<i class="fas fa-history"></i> 策略日志 - ${this.getStrategyName(strategyId)}`;
            
            // 加载交易日志
            await this.loadTradeLogs(strategyId);
            
            // 加载优化记录
            await this.loadOptimizationLogs(strategyId);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('strategyLogsModal'));
            modal.show();
            
        } catch (error) {
            console.error('显示策略日志失败:', error);
            this.showMessage('显示策略日志失败', 'error');
        }
    }

    // 加载交易日志
    async loadTradeLogs(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/trade-logs`);
            const data = await response.json();
            
            const tbody = document.getElementById('tradeLogsTable');
            
            if (data.success && data.logs && data.logs.length > 0) {
                tbody.innerHTML = data.logs.map(log => `
                    <tr>
                        <td>${this.formatTime(log.timestamp)}</td>
                        <td><span class="badge ${log.signal_type === 'buy' ? 'bg-success' : 'bg-danger'}">${log.signal_type.toUpperCase()}</span></td>
                        <td>${log.price.toFixed(6)}</td>
                        <td>${log.quantity.toFixed(6)}</td>
                        <td>${(log.confidence * 100).toFixed(1)}%</td>
                        <td>${log.executed ? '<span class="badge bg-success">已执行</span>' : '<span class="badge bg-secondary">未执行</span>'}</td>
                        <td class="${log.pnl && log.pnl >= 0 ? 'text-success' : 'text-danger'}">
                            ${log.pnl ? (log.pnl >= 0 ? '+' : '') + log.pnl.toFixed(6) + 'U' : '-'}
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无交易记录</td></tr>';
            }
            
        } catch (error) {
            console.error('加载交易日志失败:', error);
            document.getElementById('tradeLogsTable').innerHTML = 
                '<tr><td colspan="7" class="text-center text-danger">加载失败</td></tr>';
        }
    }

    // 加载优化记录
    async loadOptimizationLogs(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/optimization-logs`);
            const data = await response.json();
            
            const tbody = document.getElementById('optimizationLogsTable');
            
            if (data.success && data.logs && data.logs.length > 0) {
                // 存储完整日志数据用于分页
                this.optimizationLogs = data.logs;
                this.currentLogPage = 1;
                this.logsPerPage = 5;
                
                this.renderOptimizationLogs();
                this.renderLogPagination();
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无优化记录</td></tr>';
                document.getElementById('logPaginationContainer').innerHTML = '';
            }
            
        } catch (error) {
            console.error('加载优化记录失败:', error);
            document.getElementById('optimizationLogsTable').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">加载失败</td></tr>';
            document.getElementById('logPaginationContainer').innerHTML = '';
        }
    }

    // 渲染优化日志
    renderOptimizationLogs() {
        const tbody = document.getElementById('optimizationLogsTable');
        const startIndex = (this.currentLogPage - 1) * this.logsPerPage;
        const endIndex = startIndex + this.logsPerPage;
        const currentLogs = this.optimizationLogs.slice(startIndex, endIndex);
        
        tbody.innerHTML = currentLogs.map(log => `
            <tr>
                <td>${this.formatTime(log.timestamp)}</td>
                <td><span class="badge bg-info">${log.optimization_type || '未知类型'}</span></td>
                <td><code>${JSON.stringify(log.old_params || log.old_parameters || {}, null, 1)}</code></td>
                <td><code>${JSON.stringify(log.new_params || log.new_parameters || {}, null, 1)}</code></td>
                <td>${log.trigger_reason || '无原因'}</td>
                <td>${log.target_success_rate || 0}%</td>
            </tr>
        `).join('');
    }

    // 渲染分页按钮
    renderLogPagination() {
        const container = document.getElementById('logPaginationContainer');
        if (!container) return;
        
        const totalPages = Math.ceil(this.optimizationLogs.length / this.logsPerPage);
        
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let paginationHtml = `
            <nav aria-label="优化日志分页">
                <ul class="pagination pagination-sm justify-content-center">
                    <li class="page-item ${this.currentLogPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="javascript:void(0)" onclick="app.changeLogPage(${this.currentLogPage - 1})">上一页</a>
                    </li>
        `;
        
        // 显示页码
        for (let i = 1; i <= totalPages; i++) {
            paginationHtml += `
                <li class="page-item ${i === this.currentLogPage ? 'active' : ''}">
                    <a class="page-link" href="javascript:void(0)" onclick="app.changeLogPage(${i})">${i}</a>
                </li>
            `;
        }
        
        paginationHtml += `
                    <li class="page-item ${this.currentLogPage === totalPages ? 'disabled' : ''}">
                        <a class="page-link" href="javascript:void(0)" onclick="app.changeLogPage(${this.currentLogPage + 1})">下一页</a>
                    </li>
                </ul>
            </nav>
        `;
        
        container.innerHTML = paginationHtml;
    }

    // 切换日志页面
    changeLogPage(page) {
        if (page < 1 || page > Math.ceil(this.optimizationLogs.length / this.logsPerPage)) {
            return;
        }
        
        this.currentLogPage = page;
        this.renderOptimizationLogs();
        this.renderLogPagination();
    }

    // 获取策略名称
    getStrategyName(strategyId) {
        const strategy = this.strategies.find(s => s.id === strategyId);
        return strategy ? strategy.name : '未知策略';
    }

    // 查看策略详情（保留兼容性）
    viewStrategyDetails(strategyId) {
        this.showStrategyConfig(strategyId);
    }

    // 初始化收益曲线图
    initChart() {
        this.initPerformanceChart();
        this.initBalanceChart();
    }

    // 初始化收益曲线图
    initPerformanceChart() {
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
                                return value.toLocaleString() + 'U';
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

    // 初始化资产历史图表
    initBalanceChart() {
        const ctx = document.getElementById('balanceChart');
        if (!ctx) return;

        // 创建资产历史图表（默认90天）
        this.balanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '总资产',
                    data: [],
                    borderColor: '#52c41a',
                    backgroundColor: 'rgba(82, 196, 26, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '时间'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '资产 (U)'
                        },
                        type: 'logarithmic', // 使用对数刻度显示从10U到10万U的增长
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + 'U';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return context[0].label;
                            },
                            label: function(context) {
                                const value = context.parsed.y;
                                return `总资产: ${value.toLocaleString()}U`;
                            },
                            afterLabel: function(context) {
                                const dataIndex = context.dataIndex;
                                const dataset = context.dataset;
                                // 显示里程碑信息
                                if (this.balanceHistory && this.balanceHistory[dataIndex]?.milestone_note) {
                                    return `🎉 ${this.balanceHistory[dataIndex].milestone_note}`;
                                }
                                return '';
                            }.bind(this)
                        }
                    }
                }
            }
        });

        // 加载默认90天数据
        this.loadBalanceHistory(90);
    }

    // 加载资产历史数据
    async loadBalanceHistory(days = 90) {
        try {
            console.log(`正在加载 ${days} 天的资产历史...`);
            const response = await fetch(`/api/quantitative/balance-history?days=${days}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('资产历史API响应:', data);
            
            if (data.success && data.data && data.data.length > 0) {
                this.balanceHistory = data.data;
                console.log(`成功加载 ${data.data.length} 条资产历史记录`);
                
                // 更新图表数据
                const labels = data.data.map(item => {
                    const date = new Date(item.timestamp);
                    return date.toLocaleDateString();
                });
                
                const balances = data.data.map(item => item.total_balance);
                
                if (this.balanceChart) {
                    this.balanceChart.data.labels = labels;
                    this.balanceChart.data.datasets[0].data = balances;
                    this.balanceChart.update();
                    console.log('资产图表已更新');
                } else {
                    console.warn('资产图表未初始化');
                }
                
                // 更新当前资产显示
                const currentBalance = data.data[data.data.length - 1].total_balance;
                const currentBalanceEl = document.getElementById('currentBalance');
                if (currentBalanceEl) {
                    currentBalanceEl.textContent = `${currentBalance.toLocaleString()}U`;
                    
                    // 根据资产量设置颜色
                    if (currentBalance >= 10000) {
                        currentBalanceEl.className = 'milestone-value text-success';
                    } else if (currentBalance >= 1000) {
                        currentBalanceEl.className = 'milestone-value text-primary';
                    } else if (currentBalance >= 100) {
                        currentBalanceEl.className = 'milestone-value text-info';
                    } else {
                        currentBalanceEl.className = 'milestone-value text-warning';
                    }
                    console.log(`当前资产显示已更新: ${currentBalance}U`);
                }
                
                // 显示里程碑提示
                const milestones = data.data.filter(item => item.milestone_note);
                if (milestones.length > 0) {
                    console.log('🎉 资产里程碑:', milestones.map(m => m.milestone_note).join(', '));
                }
                
            } else {
                console.warn('未获取到资产历史数据，响应数据:', data);
                // 如果没有真实数据，尝试显示模拟数据
                if (data.data && data.data.length === 0) {
                    console.log('返回了空数组，可能是新系统还没有历史数据');
                }
            }
            
        } catch (error) {
            console.error('加载资产历史失败:', error);
            // 显示错误信息给用户
            const currentBalanceEl = document.getElementById('currentBalance');
            if (currentBalanceEl) {
                currentBalanceEl.textContent = '加载失败';
                currentBalanceEl.className = 'milestone-value text-danger';
            }
        }
    }

    // 切换资产图表时间范围
    toggleBalanceChart(days) {
        // 更新按钮状态
        document.querySelectorAll('.card-header .btn-sm').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // 重新加载数据
        this.loadBalanceHistory(parseInt(days));
    }

    // 刷新所有数据
    async refreshAllData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),  // 添加系统状态刷新
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
        if (!timestamp) return '-';
        const date = new Date(timestamp);
        // 返回完整的日期时间格式：YYYY-MM-DD HH:mm:ss
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }

    // 加载系统状态
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/quantitative/system-status');
            const data = await response.json();
            
            if (data.success) {
                // 更新全局状态变量
                systemRunning = data.running || false;
                autoTradingEnabled = data.auto_trading_enabled || false;
                
                // 更新界面显示
                this.updateSystemStatus();
                this.updateAutoTradingStatus();
                
                console.log('系统状态加载成功:', {
                    running: systemRunning,
                    autoTrading: autoTradingEnabled
                });
            } else {
                console.error('获取系统状态失败:', data.message);
            }
        } catch (error) {
            console.error('加载系统状态失败:', error);
        }
    }

    // 加载持仓信息
    async loadPositions() {
        try {
            const response = await fetch('/api/quantitative/positions');
            const data = await response.json();
            
            const tbody = document.getElementById('positionsTable');
            if (!tbody) return;
            
            if (data.success && data.data && data.data.length > 0) {
                tbody.innerHTML = data.data.map(position => `
                    <tr>
                        <td>${position.symbol}</td>
                        <td>${this.formatNumber(position.quantity)}</td>
                        <td>${this.formatNumber(position.avg_price)}U</td>
                        <td class="${position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                            ${position.unrealized_pnl >= 0 ? '+' : ''}${this.formatNumber(position.unrealized_pnl)}U
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无持仓</td></tr>';
            }
        } catch (error) {
            console.error('加载持仓信息失败:', error);
            const tbody = document.getElementById('positionsTable');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无持仓</td></tr>';
            }
        }
    }

    // 加载交易信号
    async loadSignals() {
        try {
            const response = await fetch('/api/quantitative/signals');
            const data = await response.json();
            
            const tbody = document.getElementById('signalsTable');
            if (!tbody) return;
            
            if (data.success && data.data && data.data.length > 0) {
                tbody.innerHTML = data.data.slice(0, 15).map(signal => `
                    <tr>
                        <td>${this.formatTime(signal.timestamp)}</td>
                        <td>${signal.symbol}</td>
                        <td>
                            <span class="badge ${signal.signal_type === 'buy' ? 'bg-success' : signal.signal_type === 'sell' ? 'bg-danger' : 'bg-secondary'}">
                                ${signal.signal_type.toUpperCase()}
                            </span>
                        </td>
                        <td>${(signal.confidence * 100).toFixed(1)}%</td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无信号</td></tr>';
            }
        } catch (error) {
            console.error('加载交易信号失败:', error);
            const tbody = document.getElementById('signalsTable');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无信号</td></tr>';
            }
        }
    }

    // ==================== 策略管理配置功能 ====================
    
    // 加载管理配置
    async loadManagementConfig() {
        try {
            const response = await fetch('/api/quantitative/management-config');
            const data = await response.json();
            
            if (data.success && data.config) {
                Object.assign(managementConfig, data.config);
                this.updateManagementForm();
            }
        } catch (error) {
            console.error('加载管理配置失败:', error);
        }
    }

    // 更新管理配置表单
    updateManagementForm() {
        const form = document.getElementById('strategyManagementForm');
        if (!form) return;

        Object.keys(managementConfig).forEach(key => {
            const input = form.querySelector(`#${key}`);
            if (input) {
                input.value = managementConfig[key];
            }
        });
    }

    // 驼峰转连字符
    camelToKebab(str) {
        return str.replace(/([A-Z])/g, '-$1').toLowerCase();
    }

    // 保存管理配置
    async saveManagementConfig() {
        try {
            const form = document.getElementById('strategyManagementForm');
            if (!form) return;

            // 收集表单数据
            const formData = new FormData(form);
            const newConfig = {};
            
            // 手动获取所有输入值
            ['evolutionInterval', 'maxStrategies', 'minTrades', 'minWinRate', 'minProfit',
             'maxDrawdown', 'minSharpeRatio', 'maxPositionSize', 'stopLossPercent', 
             'eliminationDays', 'minScore'].forEach(key => {
                const input = form.querySelector(`#${key}`);
                if (input) {
                    newConfig[key] = parseFloat(input.value) || 0;
                }
            });

            const response = await fetch('/api/quantitative/management-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: newConfig })
            });

            const data = await response.json();
            
            if (data.success) {
                Object.assign(managementConfig, newConfig);
                this.showMessage('配置保存成功', 'success');
                
                // 关闭弹窗
                const modal = bootstrap.Modal.getInstance(document.getElementById('strategyManagementModal'));
                if (modal) modal.hide();
            } else {
                this.showMessage(data.message || '保存失败', 'error');
            }
        } catch (error) {
            console.error('保存配置失败:', error);
            this.showMessage('保存配置失败', 'error');
        }
    }

    // 重置管理配置
    resetManagementConfig() {
        const defaultConfig = {
            evolutionInterval: 10,
            maxStrategies: 20,
            minTrades: 10,
            minWinRate: 65,
            minProfit: 0,
            maxDrawdown: 10,
            minSharpeRatio: 1.0,
            maxPositionSize: 100,
            stopLossPercent: 5,
            eliminationDays: 7,
            minScore: 50
        };

        Object.assign(managementConfig, defaultConfig);
        this.updateManagementForm();
        this.showMessage('已恢复默认配置', 'info');
    }

    // ==================== 策略进化日志功能 ====================
    
    // 初始化进化日志
    initEvolutionLog() {
        this.startEvolutionLogPolling();
        
        // 绑定管理配置事件
        this.bindManagementEvents();
    }

    // 绑定管理配置事件
    bindManagementEvents() {
        // 保存配置按钮
        document.getElementById('saveManagementConfig')?.addEventListener('click', () => {
            this.saveManagementConfig();
        });

        // 重置配置按钮
        document.getElementById('resetManagementConfig')?.addEventListener('click', () => {
            this.resetManagementConfig();
        });
    }

    // 开始轮询进化日志
    startEvolutionLogPolling() {
        // 立即加载一次
        this.loadEvolutionLog();
        
        // 每10秒更新一次进化日志
        evolutionLogTimer = setInterval(() => {
            this.loadEvolutionLog();
        }, 10000);
    }

    // 停止进化日志轮询
    stopEvolutionLogPolling() {
        if (evolutionLogTimer) {
            clearInterval(evolutionLogTimer);
            evolutionLogTimer = null;
        }
    }

    // 加载进化日志
    async loadEvolutionLog() {
        try {
            const response = await fetch('/api/quantitative/evolution-log');
            const data = await response.json();
            
            if (data.success && data.logs) {
                this.renderEvolutionLog(data.logs);
            }
        } catch (error) {
            console.error('加载进化日志失败:', error);
        }
    }

    // 渲染进化日志 - CNN滚动新闻样式（显示最新15条）
    renderEvolutionLog(logs) {
        const ticker = document.getElementById('evolutionTicker');
        if (!ticker) return;

        // 保存所有日志到全局变量供全部日志页面使用
        this.allEvolutionLogs = logs || [];

        // 增加滚动显示的日志条数到15条
        const recentLogs = this.allEvolutionLogs.slice(-15);
        
        const tickerContent = recentLogs.map(log => {
            const time = new Date(log.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            let actionClass = 'created';
            let actionText = '新增';
            
            switch(log.action) {
                case 'created':
                    actionClass = 'created';
                    actionText = '新增';
                    break;
                case 'eliminated':
                    actionClass = 'eliminated';
                    actionText = '淘汰';
                    break;
                case 'optimized':
                    actionClass = 'optimized';
                    actionText = '优化';
                    break;
                case 'updated':
                    actionClass = 'optimized';
                    actionText = '更新';
                    break;
                default:
                    actionClass = 'created';
                    actionText = '变更';
            }

            return `
                <span class="log-item">
                    <span class="log-time">${time}</span>
                    <span class="log-action ${actionClass}">${actionText}</span>
                    <span class="log-details">${log.details}</span>
                </span>
            `;
        }).join('');

        // 如果日志内容较少，重复显示以确保滚动效果
        const repeatedContent = tickerContent.length < 300 ? 
            Array(3).fill(tickerContent).join('') : tickerContent;

        ticker.innerHTML = repeatedContent;
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

function showStrategyManagement() {
    if (app) {
        app.loadManagementConfig();
        const modal = new bootstrap.Modal(document.getElementById('strategyManagementModal'));
        modal.show();
    }
}

function showAllLogs() {
    if (app && app.allEvolutionLogs) {
        // 创建一个新的模态框显示所有日志
        const modalHtml = `
            <div class="modal fade" id="allLogsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-list me-2"></i>所有策略进化日志
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th style="width: 20%">时间</th>
                                            <th style="width: 15%">操作</th>
                                            <th style="width: 65%">详情</th>
                                        </tr>
                                    </thead>
                                    <tbody id="allLogsTableBody">
                                        <!-- 日志内容 -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 删除已存在的模态框
        const existingModal = document.getElementById('allLogsModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 填充数据
        const tbody = document.getElementById('allLogsTableBody');
        const allLogs = [...app.allEvolutionLogs].reverse(); // 最新的在前
        
        tbody.innerHTML = allLogs.map(log => {
            const time = new Date(log.timestamp).toLocaleString('zh-CN');
            let actionClass = 'secondary';
            let actionText = '变更';
            
            switch(log.action) {
                case 'created':
                    actionClass = 'success';
                    actionText = '新增';
                    break;
                case 'eliminated':
                    actionClass = 'danger';
                    actionText = '淘汰';
                    break;
                case 'optimized':
                    actionClass = 'primary';
                    actionText = '优化';
                    break;
                case 'updated':
                    actionClass = 'info';
                    actionText = '更新';
                    break;
            }
            
            return `
                <tr>
                    <td class="text-muted">${time}</td>
                    <td><span class="badge bg-${actionClass}">${actionText}</span></td>
                    <td>${log.details}</td>
                </tr>
            `;
        }).join('');
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('allLogsModal'));
        modal.show();
    } else {
        console.log('暂无日志数据');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    app = new QuantitativeSystem();
    
    console.log('量化交易系统初始化完成');
}); 