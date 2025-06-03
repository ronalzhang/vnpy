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
        this.loadSystemStatus(); // 加载真实系统状态
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
        
        // 更新量化系统状态（在系统控制台中）
        const quantitativeSystemEl = document.querySelector('[data-system="quantitative"]');
        if (quantitativeSystemEl) {
            const indicator = quantitativeSystemEl.querySelector('.status-indicator');
            if (indicator) {
                if (systemRunning) {
                    indicator.className = 'status-indicator status-running';
                } else {
                    indicator.className = 'status-indicator status-offline';
                }
            }
        }
        
        // 更新自动交易状态（在系统控制台中）
        const autoTradingEl = document.querySelector('[data-system="auto-trading"]');
        if (autoTradingEl) {
            const indicator = autoTradingEl.querySelector('.status-indicator');
            if (indicator) {
                if (autoTradingEnabled) {
                    indicator.className = 'status-indicator status-running';
                } else {
                    indicator.className = 'status-indicator status-offline';
                }
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
                                <a href="javascript:void(0)" onclick="app.showStrategyConfig('${strategy.id}')" class="text-decoration-none">
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
                                    onclick="app.showStrategyLogs('${strategy.id}')">
                                日志
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
            
            // 填充统计信息
            document.getElementById('strategyTotalReturn').textContent = `${(strategy.total_return * 100).toFixed(2)}%`;
            document.getElementById('strategyWinRate').textContent = `${(strategy.win_rate * 100).toFixed(1)}%`;
            document.getElementById('strategyTotalTrades').textContent = strategy.total_trades || 0;
            document.getElementById('strategyDailyReturn').textContent = `${(strategy.daily_return * 100).toFixed(2)}%`;
            
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
        
        // 根据策略类型生成对应的参数表单
        const parameterConfigs = {
            'momentum': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 5, max: 100, step: 1},
                {key: 'threshold', label: '动量阈值', type: 'number', min: 0.001, max: 0.1, step: 0.001},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.001, max: 1000, step: 0.001},
                {key: 'momentum_threshold', label: '动量确认阈值', type: 'number', min: 0.001, max: 0.1, step: 0.001},
                {key: 'volume_threshold', label: '成交量倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1}
            ],
            'mean_reversion': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'std_multiplier', label: '标准差倍数', type: 'number', min: 1.0, max: 4.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.001, max: 1000, step: 0.001},
                {key: 'reversion_threshold', label: '回归阈值', type: 'number', min: 0.005, max: 0.05, step: 0.001},
                {key: 'min_deviation', label: '最小偏离度', type: 'number', min: 0.01, max: 0.1, step: 0.001}
            ],
            'grid_trading': [
                {key: 'grid_spacing', label: '网格间距(%)', type: 'number', min: 0.5, max: 5.0, step: 0.1},
                {key: 'grid_count', label: '网格数量', type: 'number', min: 5, max: 30, step: 1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 10000, step: 1},
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 50, max: 200, step: 10},
                {key: 'min_profit', label: '最小利润(%)', type: 'number', min: 0.1, max: 2.0, step: 0.1}
            ],
            'breakout': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'breakout_threshold', label: '突破阈值(%)', type: 'number', min: 0.5, max: 3.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.1, max: 100, step: 0.1},
                {key: 'volume_threshold', label: '成交量倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'confirmation_periods', label: '确认周期', type: 'number', min: 1, max: 10, step: 1}
            ],
            'high_frequency': [
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 1000, step: 1},
                {key: 'min_profit', label: '最小利润(%)', type: 'number', min: 0.01, max: 0.1, step: 0.01},
                {key: 'volatility_threshold', label: '波动率阈值', type: 'number', min: 0.0001, max: 0.01, step: 0.0001},
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 5, max: 20, step: 1},
                {key: 'signal_interval', label: '信号间隔(秒)', type: 'number', min: 10, max: 60, step: 5}
            ],
            'trend_following': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 20, max: 100, step: 5},
                {key: 'trend_threshold', label: '趋势阈值(%)', type: 'number', min: 0.5, max: 3.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 1000, step: 1},
                {key: 'trend_strength_min', label: '最小趋势强度', type: 'number', min: 0.1, max: 1.0, step: 0.1}
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
                tbody.innerHTML = data.logs.map(log => `
                    <tr>
                        <td>${this.formatTime(log.timestamp)}</td>
                        <td><span class="badge bg-info">${log.optimization_type}</span></td>
                        <td><code>${JSON.stringify(log.old_parameters, null, 1)}</code></td>
                        <td><code>${JSON.stringify(log.new_parameters, null, 1)}</code></td>
                        <td>${log.trigger_reason}</td>
                        <td>${log.target_success_rate}%</td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无优化记录</td></tr>';
            }
            
        } catch (error) {
            console.error('加载优化记录失败:', error);
            document.getElementById('optimizationLogsTable').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">加载失败</td></tr>';
        }
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
            const response = await fetch(`/api/quantitative/balance-history?days=${days}`);
            const data = await response.json();
            
            if (data.success && data.data && data.data.length > 0) {
                this.balanceHistory = data.data;
                
                // 更新图表数据
                const labels = data.data.map(item => {
                    const date = new Date(item.timestamp);
                    return date.toLocaleDateString();
                });
                
                const balances = data.data.map(item => item.total_balance);
                
                this.balanceChart.data.labels = labels;
                this.balanceChart.data.datasets[0].data = balances;
                this.balanceChart.update();
                
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
                }
                
                // 显示里程碑提示
                const milestones = data.data.filter(item => item.milestone_note);
                if (milestones.length > 0) {
                    console.log('🎉 资产里程碑:', milestones.map(m => m.milestone_note).join(', '));
                }
                
            } else {
                console.warn('未获取到资产历史数据');
            }
            
        } catch (error) {
            console.error('加载资产历史失败:', error);
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
        return new Date(timestamp).toLocaleTimeString();
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
                tbody.innerHTML = data.data.slice(0, 10).map(signal => `
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
    
    console.log('量化交易系统初始化完成');
}); 