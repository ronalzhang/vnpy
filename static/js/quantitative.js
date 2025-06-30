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

// 🔥 全局状态管理器
class GlobalStatusManager {
    constructor() {
        this.status = {
            system: 'checking',
            websocket: 'connecting',
            exchange: 'checking',
            evolution: 'running'
        };
        this.indicators = {
            system: document.getElementById('globalStatusIndicator'),
            websocket: document.getElementById('websocketStatusIndicator'),
            exchange: document.getElementById('exchangeStatusIndicator'),
            evolution: document.getElementById('evolutionStatusIndicator')
        };
        this.statusTexts = {
            system: document.getElementById('globalSystemStatus'),
            websocket: document.getElementById('websocketStatus'),
            exchange: document.getElementById('exchangeStatus'),
            evolution: document.getElementById('evolutionStatus')
        };
        
        this.initializeWebSocket();
        this.startStatusPolling();
    }
    
    updateStatus(type, status, text) {
        this.status[type] = status;
        
        if (this.indicators[type] && this.statusTexts[type]) {
            const indicator = this.indicators[type].querySelector('.status-dot');
            const statusText = this.statusTexts[type];
            
            // 更新指示器颜色
            indicator.className = 'status-dot';
            switch(status) {
                case 'online':
                case 'connected':
                case 'running':
                    indicator.classList.add('bg-success');
                    break;
                case 'offline':
                case 'disconnected':
                case 'stopped':
                    indicator.classList.add('bg-danger');
                    break;
                case 'warning':
                case 'degraded':
                    indicator.classList.add('bg-warning');
                    break;
                case 'checking':
                case 'connecting':
                    indicator.classList.add('bg-info');
                    break;
                default:
                    indicator.classList.add('bg-secondary');
            }
            
            // 更新状态文本
            statusText.textContent = text;
        }
    }
    
    initializeWebSocket() {
        // 暂时禁用WebSocket连接，避免频繁错误
        console.log('🔄 WebSocket功能暂时禁用');
        this.updateStatus('websocket', 'disconnected', '已禁用');
        return;
    }
    

    
    handleWebSocketMessage(data) {
        // 处理实时数据更新
        if (data.type === 'strategy_update') {
            window.app?.updateStrategyData(data.data);
        } else if (data.type === 'system_status') {
            this.updateStatus('system', data.status, data.message);
        } else if (data.type === 'evolution_progress') {
            this.updateStatus('evolution', 'running', `第${data.generation}代第${data.individual}个`);
        }
    }
    
    async startStatusPolling() {
        // 每30秒检查一次系统状态
        setInterval(async () => {
            await this.checkSystemStatus();
            await this.checkExchangeStatus();
        }, 30000);
        
        // 立即执行一次
        await this.checkSystemStatus();
        await this.checkExchangeStatus();
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            console.log('🔍 系统状态检查结果:', data);
            
            if (data.success && data.data) {
                const status = data.data.overall_status;
                if (status === 'online') {
                    this.updateStatus('system', 'online', '系统在线');
                } else if (status === 'degraded') {
                    this.updateStatus('system', 'warning', '部分异常');
                } else {
                    this.updateStatus('system', 'offline', '系统离线');
                }
                
                // 检查交易所API状态
                const exchangeStatus = data.data.services?.exchange_api;
                if (exchangeStatus === 'online') {
                    this.updateStatus('exchange', 'online', 'API正常');
                } else if (exchangeStatus === 'degraded') {
                    this.updateStatus('exchange', 'warning', 'API异常');
                } else {
                    this.updateStatus('exchange', 'offline', 'API离线');
                }
            } else {
                this.updateStatus('system', 'offline', '检查失败');
                this.updateStatus('exchange', 'offline', '检查失败');
            }
        } catch (error) {
            console.error('系统状态检查失败:', error);
            this.updateStatus('system', 'offline', '检查失败');
            this.updateStatus('exchange', 'offline', '检查失败');
        }
    }
    
    async checkExchangeStatus() {
        try {
            const response = await fetch('/api/quantitative/exchange-status');
            const data = await response.json();
            
            if (data.success && data.status) {
                const connectedExchanges = Object.values(data.status).filter(s => s.connected).length;
                const totalExchanges = Object.keys(data.status).length;
                
                if (connectedExchanges === totalExchanges) {
                    this.updateStatus('exchange', 'online', `${connectedExchanges}/${totalExchanges} 正常`);
                } else if (connectedExchanges > 0) {
                    this.updateStatus('exchange', 'warning', `${connectedExchanges}/${totalExchanges} 连接`);
                } else {
                    this.updateStatus('exchange', 'offline', '全部离线');
                }
            }
        } catch (error) {
            console.error('交易所状态检查失败:', error);
            this.updateStatus('exchange', 'offline', '检查失败');
        }
    }
}

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
        
        // 🔥 使用统一的进化日志管理器，替换原有的分散逻辑
        this.evolutionLogManager = new UnifiedEvolutionLogManager();
        
        this.bindEvents();
        this.loadSystemStatus(); // 加载真实系统状态
        this.initEvolutionLog(); // 初始化进化日志
        this.loadManagementConfig(); // 加载管理配置
        this.bindManagementEvents(); // 🔥 确保事件绑定在DOM加载后执行
    }

    bindEvents() {
        // 模式选择
        document.getElementById('modeSelect')?.addEventListener('change', (e) => {
            this.changeMode(e.target.value);
        });
        
        // 初始化数据加载
        this.loadInitialData();
    }

    // 🔥 新增：初始化数据加载方法
    async loadInitialData() {
        try {
            // 加载系统状态
            await this.loadSystemStatus();
            
            // 🔧 新增：专门加载auto_trading状态
            await this.loadAutoTradingStatus();
            
            // 加载策略数据
            await this.loadStrategies();
            
            // 加载账户信息
            await this.loadAccountInfo();
            
            // 加载持仓信息
            await this.loadPositions();
            
            // 加载交易信号
            await this.loadSignals();
            
            console.log('✅ 初始数据加载完成');
        } catch (error) {
            console.error('❌ 初始数据加载失败:', error);
        }
    }

    // 🔧 新增：专门加载auto_trading状态
    async loadAutoTradingStatus() {
        try {
            const response = await fetch('/api/quantitative/auto-trading');
            const data = await response.json();
            
            if (data.success || data.data) {
                const autoTradingEnabled = data.data?.auto_trading_enabled || data.enabled || false;
                
                console.log('🔧 加载auto_trading状态:', {
                    API响应: data,
                    解析状态: autoTradingEnabled
                });
                
                // 更新全局状态
                window.autoTradingEnabled = autoTradingEnabled;
                
                // 更新实例状态
                if (!this.systemStatus) {
                    this.systemStatus = {};
                }
                this.systemStatus.auto_trading_enabled = autoTradingEnabled;
                
                // 更新界面显示
                this.updateAutoTradingStatus();
                
                console.log('✅ auto_trading状态加载成功:', autoTradingEnabled);
            } else {
                console.warn('⚠️ auto_trading状态获取失败，使用默认值false');
                window.autoTradingEnabled = false;
                if (this.systemStatus) {
                    this.systemStatus.auto_trading_enabled = false;
                }
                this.updateAutoTradingStatus();
            }
        } catch (error) {
            console.error('❌ 加载auto_trading状态失败:', error);
            window.autoTradingEnabled = false;
            if (this.systemStatus) {
                this.systemStatus.auto_trading_enabled = false;
            }
            this.updateAutoTradingStatus();
        }
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

    // 🔧 修复：真实交易开关 - 停止自动启动，由用户手动控制
    async toggleAutoTrading() {
        try {
            // 🔧 先获取当前状态，不要依赖全局变量
            const currentResponse = await fetch('/api/quantitative/auto-trading');
            const currentData = await currentResponse.json();
            
            const currentEnabled = currentData.data?.auto_trading_enabled || currentData.enabled || false;
            const newEnabled = !currentEnabled;
            
            console.log('🔧 真实交易开关:', {
                当前状态: currentEnabled,
                目标状态: newEnabled,
                API响应: currentData
            });
            
            const response = await fetch('/api/quantitative/auto-trading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: newEnabled })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 🔧 更新本地状态
                window.autoTradingEnabled = newEnabled;
                if (this.systemStatus) {
                    this.systemStatus.auto_trading_enabled = newEnabled;
                }
                
                this.updateAutoTradingStatus();
                this.showMessage(newEnabled ? '✅ 真实交易已启用' : '⚠️ 真实交易已禁用', 'success');
                
                // 重新加载策略以更新交易状态显示
                this.loadStrategies();
            } else {
                this.showMessage(data.message || '操作失败', 'error');
            }
        } catch (error) {
            console.error('真实交易控制失败:', error);
            this.showMessage('真实交易控制失败', 'error');
        }
    }

    // 更新系统状态显示
    updateSystemStatus() {
        const systemStatusEl = document.getElementById('systemStatus');
        const systemToggle = document.getElementById('systemToggle');
        
        // 检查状态值
        const isRunning = window.systemRunning || this.systemStatus?.running || false;
        
        console.log('🔄 更新系统状态显示:', {
            systemRunning: window.systemRunning,
            实例状态: this.systemStatus?.running,
            最终状态: isRunning,
            statusElement: !!systemStatusEl,
            toggleElement: !!systemToggle
        });
        
        if (isRunning) {
            // 系统控制台状态 - 运行中
            if (systemStatusEl) {
            systemStatusEl.innerHTML = '<span class="status-dot online"></span>在线';
            }
            if (systemToggle) {
            systemToggle.classList.add('active');
            }
            
            // 更新顶部导航栏状态
            const statusElement = document.getElementById('system-status-text');
            if (statusElement) {
                statusElement.textContent = '在线';
                statusElement.className = 'text-success';
            }
            
            console.log('✅ 系统状态已更新为在线');
        } else {
            // 系统控制台状态 - 离线
            if (systemStatusEl) {
            systemStatusEl.innerHTML = '<span class="status-dot offline"></span>离线';
            }
            if (systemToggle) {
            systemToggle.classList.remove('active');
            }
            
            // 更新顶部导航栏状态
            const statusElement = document.getElementById('system-status-text');
            if (statusElement) {
                statusElement.textContent = '离线';
                statusElement.className = 'text-muted';
            }
            
            console.log('⚠️ 系统状态已更新为离线');
        }
    }

    // 更新自动交易状态显示
    updateAutoTradingStatus() {
        const autoTradingToggle = document.getElementById('autoTradingToggle');
        
        const isAutoTradingEnabled = window.autoTradingEnabled || this.systemStatus?.auto_trading_enabled || false;
        
        console.log('🔄 更新自动交易状态:', {
            autoTradingEnabled: window.autoTradingEnabled,
            实例状态: this.systemStatus?.auto_trading_enabled,
            最终状态: isAutoTradingEnabled,
            toggleElement: !!autoTradingToggle
        });
        
        if (autoTradingToggle) {
            if (isAutoTradingEnabled) {
            autoTradingToggle.classList.add('active');
                console.log('✅ 自动交易状态已启用');
        } else {
            autoTradingToggle.classList.remove('active');
                console.log('⚠️ 自动交易状态已禁用');
            }
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
                        // 后端已返回百分比格式，直接使用
                        dailyReturnEl.textContent = `${dailyReturn >= 0 ? '+' : ''}${dailyReturn.toFixed(2)}%`;
                        dailyReturnEl.className = `metric-value ${dailyReturn >= 0 ? 'text-success' : 'text-danger'}`;
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
            
            // 检查API返回状态
            if (data.status === 'success' && data.data && Array.isArray(data.data)) {
                this.strategies = data.data;
                console.log(`✅ 成功加载 ${this.strategies.length} 个策略`);
                await this.renderStrategies();
            } else if (data.data && Array.isArray(data.data)) {
                // 兼容旧版本API结构
                this.strategies = data.data;
                console.log(`✅ 成功加载 ${this.strategies.length} 个策略`);
                await this.renderStrategies();
            } else {
                console.error('❌ 无效的策略数据结构:', data);
                console.log('API状态:', data.status, '数据类型:', typeof data.data, '是否数组:', Array.isArray(data.data));
                this.renderEmptyStrategies();
            }
        } catch (error) {
            console.error('❌ 加载策略失败:', error);
            console.log('网络或解析错误，渲染空策略状态');
            this.renderEmptyStrategies();
        }
    }

    // 渲染策略列表
    async renderStrategies() {
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

        // 🔥 修复：在渲染策略卡之前，确保进化状态已加载
        if (!this.evolutionState && this.evolutionLogManager) {
            console.log('⏳ 等待进化状态加载...');
            await this.evolutionLogManager.loadLogs();
            
            // 如果仍然没有进化状态，使用默认值
            if (!this.evolutionState) {
                this.evolutionState = {
                    current_generation: 1,
                    current_cycle: 10  // 根据日志显示的第10轮
                };
                console.log('⚠️ 使用默认进化状态: 第1代第10轮');
            }
        }

        // 按评分排序 - 使用正确的字段名
        const sortedStrategies = this.strategies.sort((a, b) => 
            (b.final_score || 0) - (a.final_score || 0)
        );

        console.log('排序后的策略:', sortedStrategies);

        container.innerHTML = sortedStrategies.map(strategy => {
            // 生成评分显示 - 使用正确的字段名
            const score = strategy.final_score || 0;
            // 🔥 后端已统一返回百分比格式，前端只需直接使用
            const winRate = strategy.win_rate || 0;
            const totalReturn = strategy.total_return || 0;
            const totalTrades = strategy.total_trades || 0;
            const strategyGeneration = strategy.generation || 1;
            const strategyCycle = strategy.cycle || 1;
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
            
            // 🔥 交易状态 - 策略始终运行验证交易，只有开启自动交易开关后才选择前几名进行真实交易
            let tradingStatus, tradingBadgeClass;
            
            // 策略理论上应该始终运行，进行验证交易
            const autoTradingEnabled = this.systemStatus?.auto_trading_enabled || false;
            let isRealTrading = false;
            if (autoTradingEnabled && score >= 65) {
                tradingStatus = '真实交易';
                tradingBadgeClass = 'bg-success';
                isRealTrading = true;
            } else {
                tradingStatus = '验证交易';  // 所有策略都进行验证交易
                tradingBadgeClass = 'bg-info';
            }
            
            // 🔥 修复：使用实时解析的进化状态，不硬编码
            const currentGeneration = this.evolutionState?.current_generation || strategy.generation || 1;
            const currentCycle = this.evolutionState?.current_cycle || strategy.cycle || 1;
            const evolutionDisplay = `第${currentGeneration}代第${currentCycle}轮`;
            
            // 🔥 修复：应用金色样式给真实交易策略
            const cardClass = `strategy-card ${strategy.enabled ? 'strategy-running' : 'strategy-stopped'} ${isRealTrading ? 'golden' : ''}`;
            
            return `
            <div class="col-md-4 mb-3">
                <div class="card ${cardClass}">
                    <div class="card-body">
                        <!-- 顶部：标题和状态 -->
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="card-title mb-0">
                                    <a href="javascript:void(0)" onclick="showStrategyConfig('${strategy.id}')" class="text-decoration-none">
                                        ${strategy.name}
                                    </a>
                                </h6>
                                <small class="text-muted">${strategy.symbol} • ${evolutionDisplay}</small>
                            </div>
                            <div class="text-end">
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
                                        <div class="text-success fw-bold">${winRate.toFixed(1)}%</div>
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
                                        <div class="text-warning fw-bold">${((strategy.daily_return || 0) * 100).toFixed(3)}%</div>
                                        <small class="text-muted">日收益</small>
                                    </div>
                                </div>
                            </div>

                        </div>
                        
                        <!-- 底部：操作按钮 -->
                        <div class="d-flex justify-content-center">
                            <button class="btn btn-sm btn-outline-info" 
                                    onclick="showStrategyLogs('${strategy.id}')"
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
        const strategy = this.strategies[strategyIndex];
        if (!strategy) return;
        
        this.showMessage('策略启动中...', 'info');
        
        try {
            // 根据策略分数和自动交易开关决定启动模式
            const score = strategy.final_score || 0;
            const autoTradingEnabled = this.systemStatus?.auto_trading_enabled || false;
            const mode = (autoTradingEnabled && score >= 65) ? 'real' : 'verification';
            const modeText = (autoTradingEnabled && score >= 65) ? '真实交易' : '验证交易';
            
            // 调用后端API启动策略
            const response = await fetch(`/api/quantitative/strategies/${strategy.id}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(`策略已启动 - ${modeText}模式`, 'success');
            } else {
                this.showMessage(data.message || '策略启动失败', 'error');
            }
            
            this.loadStrategies(); // 重新加载策略状态
        } catch (error) {
            console.error('策略启动失败:', error);
            this.showMessage('策略启动失败', 'error');
        }
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

    // 显示策略配置弹窗 - 🔥 修复：统一使用实时数据，确保策略卡和参数页数据同步
    async showStrategyConfig(strategyId) {
        try {
            // 🔥 获取最新的实时策略数据，确保和策略卡数据同步
            const response = await fetch(`/api/quantitative/strategies/${strategyId}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showMessage('获取策略信息失败', 'error');
                return;
            }
            
            const strategy = data.data;
            
            // 🔥 同时从策略卡中获取当前显示的数据，确保一致性
            const strategyFromCard = this.strategies.find(s => s.id === strategyId);
            
            // 填充基本信息
            document.getElementById('strategyId').value = strategy.id;
            document.getElementById('strategyName').value = strategy.name;
            document.getElementById('strategySymbol').value = strategy.symbol;
            document.getElementById('strategyType').value = strategy.type;
            document.getElementById('strategyEnabled').checked = strategy.enabled;
            
            // 生成参数表单
            this.generateParameterForm(strategy.type, strategy.parameters);
            
            // 🔥 修复数据同步：优先使用API实时数据，确保策略卡和参数页显示一致
            // 如果API数据和卡片数据不一致，使用最新的API数据并更新卡片
            const totalReturn = strategy.total_return || 0;
            const winRate = strategy.win_rate || 0;
            const totalTrades = strategy.total_trades || 0;
            const dailyReturn = strategy.daily_return || 0;
            const finalScore = strategy.final_score || 0;
            
            // 🔥 统一数据格式：确保参数页和策略卡使用相同的数据计算方式
            document.getElementById('strategyTotalReturn').textContent = `${(totalReturn * 100).toFixed(2)}%`;
            document.getElementById('strategyWinRate').textContent = `${winRate.toFixed(1)}%`;
            document.getElementById('strategyTotalTrades').textContent = totalTrades;
            document.getElementById('strategyDailyReturn').textContent = `${(dailyReturn * 100).toFixed(3)}%`;
            
            // 🔥 如果发现数据不同步，更新本地策略数据以保持一致性
            if (strategyFromCard) {
                strategyFromCard.total_return = totalReturn;
                strategyFromCard.win_rate = winRate;
                strategyFromCard.total_trades = totalTrades;
                strategyFromCard.daily_return = dailyReturn;
                strategyFromCard.final_score = finalScore;
                
                console.log(`✅ 已同步策略 ${strategyId} 的数据，确保卡片和参数页一致`);
            }
            
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
                {key: 'stop_loss_pct', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit_pct', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'max_position_risk', label: '最大仓位风险(%)', type: 'number', min: 1, max: 100, step: 1},
                {key: 'min_hold_time', label: '最小持仓时间(分钟)', type: 'number', min: 1, max: 1440, step: 1},
                {key: 'rsi_period', label: 'RSI周期', type: 'number', min: 10, max: 30, step: 1},
                {key: 'rsi_overbought', label: 'RSI超买线', type: 'number', min: 60, max: 90, step: 1},
                {key: 'rsi_oversold', label: 'RSI超卖线', type: 'number', min: 10, max: 40, step: 1},
                {key: 'macd_fast_period', label: 'MACD快线周期', type: 'number', min: 5, max: 50, step: 1},
                {key: 'macd_slow_period', label: 'MACD慢线周期', type: 'number', min: 20, max: 200, step: 1}
            ],
            'mean_reversion': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'std_multiplier', label: '标准差倍数', type: 'number', min: 1.0, max: 4.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.001, max: 1000, step: 0.001},
                {key: 'reversion_threshold', label: '回归阈值', type: 'number', min: 0.005, max: 0.05, step: 0.001},
                {key: 'min_deviation', label: '最小偏离度', type: 'number', min: 0.01, max: 0.1, step: 0.001},
                {key: 'stop_loss_pct', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit_pct', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'bb_period', label: 'BB周期', type: 'number', min: 10, max: 50, step: 1},
                {key: 'bb_std_dev', label: 'BB标准差', type: 'number', min: 1.5, max: 3.0, step: 0.1},
                {key: 'max_positions', label: '最大持仓数', type: 'number', min: 1, max: 10, step: 1},
                {key: 'entry_cooldown', label: '入场冷却时间', type: 'number', min: 1, max: 60, step: 1},
                {key: 'lookbook_period', label: '回看周期', type: 'number', min: 10, max: 100, step: 1}
            ],
            'grid_trading': [
                {key: 'grid_spacing', label: '网格间距(%)', type: 'number', min: 0.5, max: 5.0, step: 0.1},
                {key: 'grid_count', label: '网格数量', type: 'number', min: 5, max: 30, step: 1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 1, max: 10000, step: 1},
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 50, max: 200, step: 10},
                {key: 'min_profit', label: '最小利润(%)', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'emergency_stop_loss', label: '紧急止损', type: 'checkbox'},
                {key: 'grid_density', label: '网格密度', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'grid_pause_conditions', label: '网格暂停条件', type: 'checkbox'},
                {key: 'liquidity_threshold', label: '流动性阈值', type: 'number', min: 1000, max: 100000, step: 1000},
                {key: 'lower_price_limit', label: '价格下限', type: 'number', min: 0.001, max: 10, step: 0.001},
                {key: 'max_grid_exposure', label: '最大网格敞口', type: 'number', min: 10, max: 100, step: 5},
                {key: 'profit_taking_ratio', label: '获利比率', type: 'number', min: 0.1, max: 1.0, step: 0.1},
                {key: 'rebalance_threshold', label: '再平衡阈值', type: 'number', min: 0.1, max: 5.0, step: 0.1},
                {key: 'single_grid_risk', label: '单网格风险', type: 'number', min: 0.1, max: 5.0, step: 0.1},
                {key: 'trend_filter_enabled', label: '趋势过滤', type: 'checkbox'},
                {key: 'upper_price_limit', label: '价格上限', type: 'number', min: 1, max: 1000, step: 1},
                {key: 'volatility_adjustment', label: '波动率调整', type: 'checkbox'},
                {key: 'volume_weighted', label: '成交量权重', type: 'checkbox'}
            ],
            'breakout': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'breakout_threshold', label: '突破阈值(%)', type: 'number', min: 0.5, max: 3.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.1, max: 100, step: 0.1},
                {key: 'volume_threshold', label: '成交量倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'confirmation_periods', label: '确认周期', type: 'number', min: 1, max: 10, step: 1},
                {key: 'stop_loss_pct', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit_pct', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'atr_multiplier', label: 'ATR倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'atr_period', label: 'ATR周期', type: 'number', min: 10, max: 50, step: 1},
                {key: 'breakout_strength_min', label: '最小突破强度', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'false_breakout_filter', label: '假突破过滤', type: 'checkbox'},
                {key: 'max_holding_period', label: '最大持仓周期', type: 'number', min: 1, max: 1440, step: 1},
                {key: 'momentum_confirmation', label: '动量确认', type: 'checkbox'},
                {key: 'price_ma_period', label: '价格均线周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'pullback_tolerance', label: '回调容忍度', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'stop_loss_atr_multiple', label: '止损ATR倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'take_profit_atr_multiple', label: '止盈ATR倍数', type: 'number', min: 1.0, max: 10.0, step: 0.1},
                {key: 'trailing_stop_enabled', label: '跟踪止损', type: 'checkbox'},
                {key: 'volume_ma_period', label: '成交量均线周期', type: 'number', min: 10, max: 100, step: 1}
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
                {key: 'trailing_stop_pct', label: '跟踪止损(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'profit_lock_pct', label: '利润锁定(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'max_adverse_excursion', label: '最大不利偏移', type: 'number', min: 1, max: 10, step: 0.5},
                {key: 'ema_fast_period', label: '快速EMA周期', type: 'number', min: 5, max: 50, step: 1},
                {key: 'ema_slow_period', label: '慢速EMA周期', type: 'number', min: 20, max: 200, step: 1},
                {key: 'adx_threshold', label: 'ADX趋势阈值', type: 'number', min: 20, max: 50, step: 1},
                {key: 'adx_period', label: 'ADX计算周期', type: 'number', min: 10, max: 30, step: 1},
                {key: 'slope_threshold', label: '斜率阈值', type: 'number', min: 0.0001, max: 0.01, step: 0.0001},
                {key: 'trend_angle_min', label: '最小趋势角度', type: 'number', min: 5, max: 45, step: 1},
                {key: 'trend_duration_min', label: '最小趋势持续时间', type: 'number', min: 10, max: 120, step: 5},
                {key: 'max_drawdown_exit', label: '最大回撤退出(%)', type: 'number', min: 2, max: 15, step: 0.5},
                {key: 'volume_confirmation', label: '成交量确认', type: 'checkbox'},
                {key: 'multi_timeframe', label: '多时间框架', type: 'checkbox'},
                {key: 'trend_reversal_detection', label: '趋势反转检测', type: 'checkbox'}
            ],
            'breakout': [
                {key: 'lookback_period', label: '观察周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'breakout_threshold', label: '突破阈值(%)', type: 'number', min: 0.5, max: 3.0, step: 0.1},
                {key: 'quantity', label: '交易数量', type: 'number', min: 0.1, max: 100, step: 0.1},
                {key: 'volume_threshold', label: '成交量倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'confirmation_periods', label: '确认周期', type: 'number', min: 1, max: 10, step: 1},
                {key: 'stop_loss_pct', label: '止损百分比(%)', type: 'number', min: 0.5, max: 10.0, step: 0.1},
                {key: 'take_profit_pct', label: '止盈百分比(%)', type: 'number', min: 0.5, max: 20.0, step: 0.1},
                {key: 'atr_multiplier', label: 'ATR倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'atr_period', label: 'ATR周期', type: 'number', min: 10, max: 50, step: 1},
                {key: 'breakout_strength_min', label: '最小突破强度', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'false_breakout_filter', label: '假突破过滤', type: 'checkbox'},
                {key: 'max_holding_period', label: '最大持仓周期', type: 'number', min: 1, max: 1440, step: 1},
                {key: 'momentum_confirmation', label: '动量确认', type: 'checkbox'},
                {key: 'price_ma_period', label: '价格均线周期', type: 'number', min: 10, max: 100, step: 1},
                {key: 'pullback_tolerance', label: '回调容忍度', type: 'number', min: 0.1, max: 2.0, step: 0.1},
                {key: 'stop_loss_atr_multiple', label: '止损ATR倍数', type: 'number', min: 1.0, max: 5.0, step: 0.1},
                {key: 'take_profit_atr_multiple', label: '止盈ATR倍数', type: 'number', min: 1.0, max: 10.0, step: 0.1},
                {key: 'trailing_stop_enabled', label: '跟踪止损', type: 'checkbox'},
                {key: 'volume_ma_period', label: '成交量均线周期', type: 'number', min: 10, max: 100, step: 1}
            ]
        };
        
        const configs = parameterConfigs[strategyType] || [];
        
        // 🔥 修复参数键名映射问题：前端键 -> 后端键  
        const parameterMapping = {
            'stop_loss': 'stop_loss_pct',
            'take_profit': 'take_profit_pct',
            'max_position_size': 'position_sizing',
            'ma_short': 'ema_fast_period',
            'ma_long': 'ema_slow_period',
            'ema_short': 'ema_fast_period',
            'ema_long': 'ema_slow_period',
            'rsi_upper': 'rsi_overbought',
            'rsi_lower': 'rsi_oversold'
        };
        
        configs.forEach(config => {
            // 使用映射获取正确的参数值
            const backendKey = parameterMapping[config.key] || config.key;
            const value = parameters[backendKey] || parameters[config.key] || '';
            
            if (config.type === 'checkbox') {
                parametersHtml += `
                    <div class="row mb-2">
                        <div class="col-6">
                            <label class="form-label">${config.label}</label>
                        </div>
                        <div class="col-6">
                            <div class="form-check form-switch">
                                <input type="checkbox" 
                                       class="form-check-input" 
                                       name="${config.key}"
                                       id="${config.key}_switch"
                                       onchange="updateSwitchLabel('${config.key}_switch')"
                                       ${value ? 'checked' : ''}>
                                <label class="form-check-label" for="${config.key}_switch">
                                    <span id="${config.key}_label" class="${value ? 'text-success' : 'text-muted'}" style="font-size: 12px;">${value ? '启用' : '禁用'}</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `;
            } else {
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
            }
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
                if (input.type === 'checkbox') {
                    parameters[input.name] = input.checked;
                } else {
                    const numValue = parseFloat(input.value);
                    parameters[input.name] = isNaN(numValue) ? input.value : numValue;
                }
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

    // 🔥 重新设计：多标签页策略日志显示
    async showStrategyLogs(strategyId) {
        try {
            // 设置模态框标题
            document.getElementById('strategyLogsModalLabel').innerHTML = 
                `<i class="fas fa-history"></i> 策略日志 - ${this.getStrategyName(strategyId)}`;
            
            // 初始化标签页
            this.initLogTabs(strategyId);
            
            // 默认加载实盘日志
            await this.loadCategorizedLogs(strategyId, 'real_trading');
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('strategyLogsModal'));
            modal.show();
            
        } catch (error) {
            console.error('显示策略日志失败:', error);
            this.showMessage('显示策略日志失败', 'error');
        }
    }

    // 🔥 新增：初始化日志标签页
    initLogTabs(strategyId) {
        const tabContainer = document.getElementById('strategyLogTabs');
        if (!tabContainer) return;

        tabContainer.innerHTML = `
            <ul class="nav nav-pills nav-justified mb-3" id="logTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="real-trading-tab" data-bs-toggle="pill" 
                            data-bs-target="#real-trading" type="button" role="tab"
                            onclick="app.switchLogTab('${strategyId}', 'real_trading')">
                        <i class="fas fa-dollar-sign me-1"></i>实盘日志
                        <span class="badge bg-success ms-1" id="realTradingCount">0</span>
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="validation-tab" data-bs-toggle="pill" 
                            data-bs-target="#validation" type="button" role="tab"
                            onclick="app.switchLogTab('${strategyId}', 'validation')">
                        <i class="fas fa-vial me-1"></i>验证日志
                        <span class="badge bg-info ms-1" id="validationCount">0</span>
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="evolution-tab" data-bs-toggle="pill" 
                            data-bs-target="#evolution" type="button" role="tab"
                            onclick="app.switchLogTab('${strategyId}', 'evolution')">
                        <i class="fas fa-dna me-1"></i>进化日志
                        <span class="badge bg-warning ms-1" id="evolutionCount">0</span>
                    </button>
                </li>
            </ul>
            
            <div class="tab-content" id="logTabContent">
                <div class="tab-pane fade show active" id="real-trading" role="tabpanel">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead class="table-dark">
                                <tr>
                                    <th>时间</th>
                <th>交易对</th>
                                    <th>信号</th>
                                    <th>价格</th>
                <th>数量</th>
                                    <th>盈亏</th>
                                    <th>置信度</th>
                                    <th>状态</th>
            </tr>
                            </thead>
                            <tbody id="realTradingLogs">
                                <tr><td colspan="8" class="text-center">加载中...</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div id="realTradingPagination"></div>
                </div>
                
                <div class="tab-pane fade" id="validation" role="tabpanel">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead class="table-dark">
            <tr>
                <th>时间</th>
                                    <th>交易对</th>
                <th>信号</th>
                <th>价格</th>
                <th>数量</th>
                <th>盈亏</th>
                                    <th>置信度</th>
                                    <th>验证类型</th>
            </tr>
                            </thead>
                            <tbody id="validationLogs">
                                <tr><td colspan="8" class="text-center">点击标签页加载验证日志</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div id="validationPagination"></div>
                </div>
                
                <div class="tab-pane fade" id="evolution" role="tabpanel">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead class="table-dark">
                                <tr>
                                    <th>时间</th>
                                    <th>类型</th>
                                    <th>触发原因</th>
                                    <th>旧参数</th>
                                    <th>新参数</th>
                                    <th>目标胜率</th>
                                    <th>状态</th>
                </tr>
                            </thead>
                            <tbody id="evolutionLogs">
                                <tr><td colspan="7" class="text-center">点击标签页加载进化日志</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div id="evolutionPagination"></div>
                </div>
            </div>
        `;
    }

    // 🔥 新增：切换日志标签页
    async switchLogTab(strategyId, logType) {
        try {
            // 更新标签页状态
            document.querySelectorAll('#logTabs .nav-link').forEach(tab => {
                tab.classList.remove('active');
            });
            document.getElementById(`${logType.replace('_', '-')}-tab`).classList.add('active');
            
            // 加载对应类型的日志
            await this.loadCategorizedLogs(strategyId, logType);
            
        } catch (error) {
            console.error(`切换到${logType}标签页失败:`, error);
            this.showMessage(`切换标签页失败`, 'error');
        }
    }

    // 🔥 新增：加载分类日志
    async loadCategorizedLogs(strategyId, logType) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/logs-by-category?type=${logType}&limit=100`);
            const data = await response.json();
            
            if (data.success) {
                this.renderCategorizedLogs(logType, data.logs);
                // 🔥 修复：直接更新当前标签页的计数
                this.updateSingleLogTabCount(logType, data.logs?.length || 0);
            } else {
                this.showLogError(logType, data.message || '加载失败');
                this.updateSingleLogTabCount(logType, 0);
            }
            
        } catch (error) {
            console.error(`加载${logType}日志失败:`, error);
            this.showLogError(logType, '网络错误');
            this.updateSingleLogTabCount(logType, 0);
        }
    }

    // 🔥 新增：渲染分类日志
    renderCategorizedLogs(logType, logs) {
        const containerMap = {
            'real_trading': 'realTradingLogs',
            'validation': 'validationLogs', 
            'evolution': 'evolutionLogs'
        };
        
        const containerId = containerMap[logType];
        const container = document.getElementById(containerId);
        
        if (!container) return;
        
        if (!logs || logs.length === 0) {
            container.innerHTML = `<tr><td colspan="8" class="text-center text-muted">暂无${this.getLogTypeName(logType)}记录</td></tr>`;
            return;
        }
        
        if (logType === 'evolution') {
            // 渲染进化日志
            container.innerHTML = logs.map(log => `
                <tr>
                    <td>${this.formatTime(log.timestamp)}</td>
                    <td><span class="badge bg-info">${log.optimization_type || log.signal_type || '参数调整'}</span></td>
                    <td>${log.trigger_reason || '自动优化'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-secondary" onclick="app.showParameterDetails('${JSON.stringify(log.old_parameters || {}).replace(/'/g, "\\'")}', '旧参数')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="app.showParameterDetails('${JSON.stringify(log.new_parameters || {}).replace(/'/g, "\\'")}', '新参数')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                    <td>${log.target_success_rate || 0}%</td>
                    <td>
                        <span class="badge ${log.validation_passed ? 'bg-success' : 'bg-warning'}">
                            ${log.validation_passed ? '已应用' : '待验证'}
                        </span>
                    </td>
                </tr>
            `).join('');
        } else {
            // 渲染交易日志（实盘和验证）
            container.innerHTML = logs.map(log => `
                <tr class="${logType === 'validation' ? 'table-info' : ''}">
                    <td>${this.formatTime(log.timestamp)}</td>
                    <td>${log.symbol || 'N/A'}</td>
                    <td>
                        <span class="badge ${log.signal_type === 'buy' ? 'bg-success' : 'bg-danger'}">
                            ${(log.signal_type || '').toUpperCase()}
                        </span>
                    </td>
                    <td>${log.price ? log.price.toFixed(6) : '0'}</td>
                    <td>${log.quantity ? log.quantity.toFixed(6) : '0'}</td>
                    <td class="${log.pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${log.pnl >= 0 ? '+' : ''}${(log.pnl || 0).toFixed(6)}U
                    </td>
                    <td>${log.confidence ? (log.confidence * 100).toFixed(1) : '0'}%</td>
                    <td>
                        <span class="badge ${log.executed ? 'bg-success' : 'bg-secondary'}">
                            ${log.executed ? '已执行' : '待执行'}
                        </span>
                        ${logType === 'validation' ? '<br><small class="text-muted">验证交易</small>' : ''}
                    </td>
                </tr>
            `).join('');
        }
    }

    // 🔥 修复：更新单个标签页计数
    updateSingleLogTabCount(logType, count) {
        const countMap = {
            'real_trading': 'realTradingCount',
            'validation': 'validationCount',
            'evolution': 'evolutionCount'
        };
        
        const elementId = countMap[logType];
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = count;
            console.log(`✅ 已更新 ${logType} 日志计数: ${count}`);
        }
    }

    // 🔥 保留：更新所有标签页计数（如需批量更新时使用）
    updateLogTabCounts(categorized) {
        const countMap = {
            'real_trading': 'realTradingCount',
            'validation': 'validationCount',
            'evolution': 'evolutionCount'
        };
        
        Object.entries(countMap).forEach(([logType, elementId]) => {
            const element = document.getElementById(elementId);
            if (element) {
                const count = categorized[logType] ? categorized[logType].length : 0;
                element.textContent = count;
            }
        });
    }

    // 🔥 新增：显示日志错误
    showLogError(logType, message) {
        const containerMap = {
            'real_trading': 'realTradingLogs',
            'validation': 'validationLogs',
            'evolution': 'evolutionLogs'
        };
        
        const containerId = containerMap[logType];
        const container = document.getElementById(containerId);
        
        if (container) {
            container.innerHTML = `<tr><td colspan="8" class="text-center text-danger">加载失败: ${message}</td></tr>`;
        }
    }

    // 🔥 新增：获取日志类型名称
    getLogTypeName(logType) {
        const nameMap = {
            'real_trading': '实盘交易',
            'validation': '验证交易',
            'evolution': '策略进化'
        };
        return nameMap[logType] || logType;
    }

    // 🔥 新增：显示参数详情
    showParameterDetails(parametersJson, title) {
        try {
            const parameters = typeof parametersJson === 'string' ? JSON.parse(parametersJson) : parametersJson;
            
            let content = '<div class="row">';
            Object.entries(parameters).forEach(([key, value]) => {
                content += `
                    <div class="col-md-6 mb-2">
                        <strong>${key}:</strong> 
                        <span class="text-primary">${JSON.stringify(value)}</span>
                    </div>
                `;
            });
            content += '</div>';
            
            // 显示在模态框中
            const modalHtml = `
                <div class="modal fade" id="parameterModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${content}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 移除旧模态框
            const oldModal = document.getElementById('parameterModal');
            if (oldModal) oldModal.remove();
            
            // 添加新模态框
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('parameterModal'));
            modal.show();
            
        } catch (error) {
            console.error('显示参数详情失败:', error);
            this.showMessage('参数解析失败', 'error');
        }
    }

    // 🔥 删除旧的loadTradeLogs和loadOptimizationLogs方法，统一使用新的分类方法

    // 加载系统状态 - 使用统一状态端点
    async loadSystemStatus() {
        try {
            console.log('🔄 开始加载系统状态...');
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            console.log('📊 系统状态API响应:', data);
            
            if (data.success && data.data) {
                // 根据统一状态端点更新状态
                const isOnline = data.data.overall_status === 'online';
                const isDegraded = data.data.overall_status === 'degraded';
                
                // 更新全局状态变量
                window.systemRunning = isOnline || isDegraded;
                // 🔧 修复：不要将strategy_engine状态映射到auto_trading_enabled
                // auto_trading_enabled应该从专门的API获取，不是strategy_engine状态
                
                // 保存到实例变量
                this.systemStatus = {
                    running: isOnline || isDegraded,
                    overall_status: data.data.overall_status,
                    services: data.data.services,
                    details: data.data.details,
                    timestamp: data.data.timestamp
                };
                
                // 更新界面显示
                this.updateSystemStatus();
                this.updateAutoTradingStatus();
                
                console.log('✅ 系统状态加载成功:', {
                    overall_status: data.data.overall_status,
                    running: window.systemRunning,
                    autoTrading: window.autoTradingEnabled,
                    services: data.data.services
                });
            } else {
                console.error('❌ 获取系统状态失败:', data.error);
                // 默认设置为离线状态
                window.systemRunning = false;
                window.autoTradingEnabled = false;
                this.systemStatus = { running: false, auto_trading_enabled: false, overall_status: 'offline' };
                this.updateSystemStatus();
                this.updateAutoTradingStatus();
            }
        } catch (error) {
            console.error('❌ 加载系统状态失败:', error);
            // 网络错误时设置为离线状态
            window.systemRunning = false;
            window.autoTradingEnabled = false;
            this.systemStatus = { running: false, auto_trading_enabled: false, overall_status: 'offline' };
            this.updateSystemStatus();
            this.updateAutoTradingStatus();
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
            
            if ((data.success || data.status === 'success') && data.data && data.data.length > 0) {
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
        if (managementConfig) {
            // 🔧 修复：安全设置传统配置元素，避免null错误（删除evolutionInterval）
            this.safeSetValue('maxStrategies', managementConfig.maxStrategies || 20);
            this.safeSetValue('realTradingScore', managementConfig.realTradingScore || 65);
            this.safeSetValue('realTradingCount', managementConfig.realTradingCount || 2);
            this.safeSetValue('validationAmount', managementConfig.validationAmount || 50);
            this.safeSetValue('realTradingAmount', managementConfig.realTradingAmount || 100);
            this.safeSetValue('minTrades', managementConfig.minTrades || 10);
            this.safeSetValue('minWinRate', managementConfig.minWinRate || 65);
            this.safeSetValue('minProfit', managementConfig.minProfit || 0);
            this.safeSetValue('maxDrawdown', managementConfig.maxDrawdown || 10);
            this.safeSetValue('minSharpeRatio', managementConfig.minSharpeRatio || 1.0);
            this.safeSetValue('maxPositionSize', managementConfig.maxPositionSize || 100);
            this.safeSetValue('stopLossPercent', managementConfig.stopLossPercent || 5);
            this.safeSetValue('takeProfitPercent', managementConfig.takeProfitPercent || 4);
            this.safeSetValue('maxHoldingMinutes', managementConfig.maxHoldingMinutes || 30);
            this.safeSetValue('minProfitForTimeStop', managementConfig.minProfitForTimeStop || 1);
            this.safeSetValue('eliminationDays', managementConfig.eliminationDays || 7);
            this.safeSetValue('minScore', managementConfig.minScore || 50);
            
            // 🔧 新增：参数验证配置
            this.safeSetValue('paramValidationTrades', managementConfig.paramValidationTrades || 20);
            
            // 🔧 新增：设置实盘交易控制参数
            this.safeSetValue('real_trading_enabled', managementConfig.real_trading_enabled || false);
            this.safeSetValue('min_simulation_days', managementConfig.min_simulation_days || 7);
            this.safeSetValue('min_sim_win_rate', managementConfig.min_sim_win_rate || 65);
            this.safeSetValue('min_sim_total_pnl', managementConfig.min_sim_total_pnl || 5);
        }
    }

    // 🔥 新增：安全设置元素值的辅助方法
    safeSetValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.value = value;
        } else {
            console.debug(`元素 ${elementId} 不存在，跳过设置`);
        }
    }

    // 🔧 新增：安全设置复选框状态的辅助方法
    safeSetCheckbox(elementId, checked) {
        const element = document.getElementById(elementId);
        if (element) {
            element.checked = checked;
        } else {
            console.debug(`复选框元素 ${elementId} 不存在，跳过设置`);
        }
    }

    // 驼峰转连字符
    camelToKebab(str) {
        return str.replace(/([A-Z])/g, '-$1').toLowerCase();
    }

    // 保存管理配置
    async saveManagementConfig() {
        try {
            const updatedConfig = {
                maxStrategies: parseInt(document.getElementById('maxStrategies')?.value) || 20,
                realTradingScore: parseFloat(document.getElementById('realTradingScore')?.value) || 65,
                realTradingCount: parseInt(document.getElementById('realTradingCount')?.value) || 2,
                validationAmount: parseFloat(document.getElementById('validationAmount')?.value) || 50,
                realTradingAmount: parseFloat(document.getElementById('realTradingAmount')?.value) || 100,
                minTrades: parseInt(document.getElementById('minTrades')?.value) || 10,
                minWinRate: parseFloat(document.getElementById('minWinRate')?.value) || 65,
                minProfit: parseFloat(document.getElementById('minProfit')?.value) || 0,
                maxDrawdown: parseFloat(document.getElementById('maxDrawdown')?.value) || 10,
                minSharpeRatio: parseFloat(document.getElementById('minSharpeRatio')?.value) || 1.0,
                maxPositionSize: parseFloat(document.getElementById('maxPositionSize')?.value) || 100,
                stopLossPercent: parseFloat(document.getElementById('stopLossPercent')?.value) || 5,
                takeProfitPercent: parseFloat(document.getElementById('takeProfitPercent')?.value) || 4,
                maxHoldingMinutes: parseInt(document.getElementById('maxHoldingMinutes')?.value) || 30,
                minProfitForTimeStop: parseFloat(document.getElementById('minProfitForTimeStop')?.value) || 1,
                eliminationDays: parseInt(document.getElementById('eliminationDays')?.value) || 7,
                minScore: parseFloat(document.getElementById('minScore')?.value) || 50,
                // 🔧 新增：参数验证配置
                paramValidationTrades: parseInt(document.getElementById('paramValidationTrades')?.value) || 20,
                // 🔧 新增：实盘交易控制参数
                real_trading_enabled: document.getElementById('real_trading_enabled')?.value === 'true',
                min_simulation_days: parseInt(document.getElementById('min_simulation_days')?.value) || 7,
                min_sim_win_rate: parseFloat(document.getElementById('min_sim_win_rate')?.value) || 65,
                min_sim_total_pnl: parseFloat(document.getElementById('min_sim_total_pnl')?.value) || 5
            };

            const response = await fetch('/api/quantitative/management-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: updatedConfig })
            });

            const data = await response.json();
            console.log('服务器响应:', data);
            
            if (data.success) {
                // 🔥 立即更新本地配置
                Object.assign(managementConfig, updatedConfig);
                console.log('本地配置已更新:', managementConfig);
                
                this.showMessage('配置保存成功并同步到后端', 'success');
                
                // 不关闭弹窗，让用户看到配置已保存
                // const modal = bootstrap.Modal.getInstance(document.getElementById('strategyManagementModal'));
                // if (modal) modal.hide();
            } else {
                this.showMessage(data.message || '保存失败', 'error');
            }
        } catch (error) {
            console.error('保存配置失败:', error);
            this.showMessage('保存配置失败: ' + error.message, 'error');
        }
    }

    // 重置管理配置
    resetManagementConfig() {
        const defaultConfig = {
            maxStrategies: 20,
            realTradingScore: 65,
            realTradingCount: 2,
            validationAmount: 50,
            realTradingAmount: 100,
            minTrades: 10,
            minWinRate: 65,
            minProfit: 0,
            maxDrawdown: 10,
            minSharpeRatio: 1.0,
            maxPositionSize: 100,
            stopLossPercent: 5,
            takeProfitPercent: 4,
            maxHoldingMinutes: 30,
            minProfitForTimeStop: 1,
            eliminationDays: 7,
            minScore: 50,
            // 🔧 新增：参数验证配置默认值
            paramValidationTrades: 20,
            // 🔧 新增：实盘交易控制参数默认值
            real_trading_enabled: false,
            min_simulation_days: 7,
            min_sim_win_rate: 65,
            min_sim_total_pnl: 5
        };

        Object.assign(managementConfig, defaultConfig);
        this.updateManagementForm();
        this.showMessage('已恢复默认配置', 'info');
    }

    // 切换全自动策略管理
    async toggleAutoStrategyManagement(enabled) {
        try {
            const response = await fetch('/api/quantitative/auto-strategy-management', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: enabled })
            });

            const data = await response.json();
            
            if (data.success) {
                // 更新界面状态
                const statusElement = document.getElementById('autoManagementStatus');
                const configElement = document.getElementById('autoManagementConfig');
                
                if (enabled) {
                    statusElement.textContent = '启用';
                    statusElement.className = 'text-success';
                    configElement.style.display = 'block';
                } else {
                    statusElement.textContent = '禁用';
                    statusElement.className = 'text-muted';
                    configElement.style.display = 'none';
                }
                
                this.showMessage(data.message, 'success');
                
                // 刷新状态
                this.loadAutoManagementStatus();
            } else {
                this.showMessage(data.message || '操作失败', 'error');
                // 恢复开关状态
                document.getElementById('autoManagementEnabled').checked = !enabled;
            }
        } catch (error) {
            console.error('切换全自动策略管理失败:', error);
            this.showMessage('切换全自动策略管理失败', 'error');
            // 恢复开关状态
            document.getElementById('autoManagementEnabled').checked = !enabled;
        }
    }

    // 加载全自动策略管理状态
    async loadAutoManagementStatus() {
        try {
            const response = await fetch('/api/quantitative/auto-strategy-management/status');
            const data = await response.json();
            
            if (data.success && data.data) {
                const status = data.data;
                
                // 更新开关状态
                const switchElement = document.getElementById('autoManagementEnabled');
                if (switchElement) {
                    switchElement.checked = status.enabled || false;
                }
                
                // 更新状态文本
                const statusElement = document.getElementById('autoManagementStatus');
                const configElement = document.getElementById('autoManagementConfig');
                
                if (statusElement) {
                    if (status.enabled) {
                        statusElement.textContent = '启用';
                        statusElement.className = 'text-success';
                        if (configElement) configElement.style.display = 'block';
                    } else {
                        statusElement.textContent = '禁用';
                        statusElement.className = 'text-muted';
                        if (configElement) configElement.style.display = 'none';
                    }
                }
                
                // 🔥 修复：更新状态统计，确保整数不显示小数点
                document.getElementById('currentActiveStrategies').textContent = Math.floor(status.current_active_strategies || 0).toString();
                document.getElementById('realTradingStrategiesCount').textContent = Math.floor(status.real_trading_strategies || 0).toString();
                document.getElementById('validationStrategiesCount').textContent = Math.floor(status.validation_strategies || 0).toString();
                document.getElementById('totalStrategiesCount').textContent = Math.floor(status.total_strategies || 0).toString();
                
                // 更新配置值
                if (status.min_active_strategies) {
                    const minElement = document.getElementById('minActiveStrategies');
                    if (minElement) minElement.value = status.min_active_strategies;
                }
                if (status.max_active_strategies) {
                    const maxElement = document.getElementById('maxActiveStrategies');
                    if (maxElement) maxElement.value = status.max_active_strategies;
                }
                if (status.auto_enable_threshold) {
                    const thresholdElement = document.getElementById('autoEnableThreshold');
                    if (thresholdElement) thresholdElement.value = status.auto_enable_threshold;
                }
                if (status.auto_select_interval) {
                    const intervalElement = document.getElementById('autoSelectionInterval');
                    if (intervalElement) intervalElement.value = status.auto_select_interval / 60; // 转换为分钟
                }
                if (status.strategy_rotation_enabled !== undefined) {
                    const rotationElement = document.getElementById('strategyRotationEnabled');
                    if (rotationElement) rotationElement.checked = status.strategy_rotation_enabled;
                }
                
            } else {
                console.warn('获取全自动策略管理状态失败:', data.message);
            }
        } catch (error) {
            console.error('❌ 获取全自动策略管理状态失败:', error.message || error);
            
            // 设置默认值以防止界面错误
            this.safeSetText('currentActiveStrategies', '0');
            this.safeSetText('realTradingStrategiesCount', '0');
            this.safeSetText('validationStrategiesCount', '0');
            this.safeSetText('totalStrategiesCount', '0');
            
            // 显示用户友好的错误信息
            const statusElement = document.getElementById('autoManagementStatus');
            if (statusElement) {
                statusElement.textContent = '连接失败';
                statusElement.className = 'text-danger';
            }
        }
    }

    // ==================== 策略进化日志功能 ====================
    
    // 🔥 使用统一的进化日志管理器初始化
    initEvolutionLog() {
        console.log('🔄 初始化进化日志系统...');
        this.evolutionLogManager.startPolling();
    }

    // 🔥 简化：移除重复的进化日志轮询方法，统一使用管理器
    startEvolutionLogPolling() {
        this.evolutionLogManager.startPolling();
    }

    stopEvolutionLogPolling() {
        this.evolutionLogManager.stopPolling();
    }

    // 🔥 简化：进化日志加载现在由管理器处理
    async loadEvolutionLog() {
        this.evolutionLogManager.refresh();
    }

    // 🔥 移除重复的渲染方法，统一由管理器处理
    renderEvolutionLog(logs) {
        // 兼容性保持：保存到全局变量
        this.allEvolutionLogs = logs || [];
        // 实际渲染由统一管理器处理
        if (this.evolutionLogManager) {
            this.evolutionLogManager.logs = this.allEvolutionLogs;
            this.evolutionLogManager.renderAllViews();
        }
    }

    // 🔥 新增：渲染策略管理标题右侧的横向滚动日志
    renderStrategyManagementEvolutionLog(logs) {
        const ticker = document.getElementById('strategyManagementEvolutionTicker');
        if (!ticker) return;

        if (!logs || logs.length === 0) {
            ticker.innerHTML = '<div class="log-item"><span class="text-muted">暂无进化日志</span></div>';
            return;
        }

        // 取最近10条日志用于横向滚动显示
        const recentLogs = logs.slice(-10);
        
        const logItems = recentLogs.map(log => {
            const time = new Date(log.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            let actionText = '';
            let colorClass = 'text-muted';
            
            switch(log.action) {
                case 'created':
                    actionText = '创建策略';
                    colorClass = 'text-success';
                    break;
                case 'optimized':
                    actionText = '优化策略';
                    colorClass = 'text-info';
                    break;
                case 'promoted':
                    actionText = '提升策略';
                    colorClass = 'text-warning';
                    break;
                case 'protected':
                    actionText = '保护策略';
                    colorClass = 'text-secondary';
                    break;
                case 'evolved':
                    actionText = '进化策略';
                    colorClass = 'text-primary';
                    break;
                case 'eliminated':
                    actionText = '淘汰策略';
                    colorClass = 'text-danger';
                    break;
                default:
                    // 🔥 修复：使用完整的details字段，确保显示完整信息
                    actionText = log.details || log.action || '系统活动';
                    colorClass = 'text-muted';
            }

            return `
                <div class="log-item">
                    <span class="${colorClass}">[${time}] ${actionText}</span>
                    ${log.strategy_name ? `<small class="text-muted"> - ${log.strategy_name}</small>` : ''}
                </div>
            `;
        }).join('');

        ticker.innerHTML = logItems;
    }
    
    // 🔥 新增：更新策略数据方法（供WebSocket调用）
    async updateStrategyData(data) {
        if (data && data.strategy_id) {
            // 更新对应策略的数据
            const strategyIndex = this.strategies.findIndex(s => s.id === data.strategy_id);
            if (strategyIndex !== -1) {
                this.strategies[strategyIndex] = { ...this.strategies[strategyIndex], ...data };
                await this.renderStrategies(); // 重新渲染策略列表
            }
        }
    }

    // 🔥 新增：格式化数字方法
    formatNumber(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return '-';
        }
        
        const num = parseFloat(value);
        
        // 对于小数，保留合适的精度
        if (Math.abs(num) < 1) {
            return num.toFixed(6);
        } else if (Math.abs(num) < 100) {
            return num.toFixed(4);
        } else {
            return num.toFixed(2);
        }
    }

    // 🔥 新增：格式化时间方法
    formatTime(timestamp) {
        if (!timestamp) return '-';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return '-';
            
            return date.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            console.error('时间格式化错误:', error);
            return '-';
        }
    }

    // 🔥 新增：显示消息方法
    showMessage(message, type = 'info') {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        messageEl.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        messageEl.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // 添加到页面
        document.body.appendChild(messageEl);
        
        // 3秒后自动消失
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 3000);
    }

    // 🔥 新增：策略管理配置显示
    showStrategyManagement() {
        try {
            // 加载管理配置
            this.loadManagementConfig();
            
            // 🔥 新增：初始化四层配置管理器
            if (!window.fourTierConfigManager) {
                window.fourTierConfigManager = new FourTierConfigManager();
            }
            window.fourTierConfigManager.init();
            
            // 显示策略管理模态框
            const modal = new bootstrap.Modal(document.getElementById('strategyManagementModal'));
        modal.show();
        } catch (error) {
            console.error('显示策略管理失败:', error);
            this.showMessage('显示策略管理失败', 'error');
        }
    }

    // 🔥 新增：余额图表切换
    toggleBalanceChart(period) {
        try {
            console.log(`切换余额图表周期: ${period}天`);
            
            // 更新按钮状态
            document.querySelectorAll('.btn-outline-primary').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // 查找对应的按钮并设置为激活状态
            const buttons = document.querySelectorAll('.btn-outline-primary');
            buttons.forEach(btn => {
                if (btn.textContent.includes(period)) {
                    btn.classList.add('active');
                }
            });
            
            // 这里可以添加实际的图表切换逻辑
            // 例如调用图表库的API来更新数据
            this.loadBalanceChart(period);
            
        } catch (error) {
            console.error('切换余额图表失败:', error);
            this.showMessage('切换图表失败', 'error');
        }
    }

    // 🔥 新增：加载余额图表数据
    async loadBalanceChart(period) {
        try {
            console.log(`加载${period}天的余额数据...`);
            
            // 发送请求获取余额历史数据
            const response = await fetch(`/api/quantitative/balance-history?period=${period}`);
            const data = await response.json();
            
            if (data.success) {
                // 这里可以集成图表库来渲染数据
                console.log(`成功加载${period}天的余额数据:`, data.data);
                this.showMessage(`已切换到${period}天视图`, 'success');
        } else {
                console.warn(`加载${period}天余额数据失败:`, data.message);
                this.showMessage('暂无历史数据', 'warning');
            }
            
        } catch (error) {
            console.error('加载余额图表数据失败:', error);
            // 不显示错误消息，避免过多提示
        }
    }

    // 🔥 新增：获取策略名称
    getStrategyName(strategyId) {
        // 从策略列表中查找对应的策略名称
        if (this.strategies) {
            const strategy = this.strategies.find(s => s.id === strategyId);
            return strategy ? strategy.name : `策略 ${strategyId}`;
        }
        return `策略 ${strategyId}`;
    }

    // 🔥 新增：查看全部日志
    showAllLogs() {
        try {
            console.log('查看全部日志');
            
            // 可以显示一个包含所有策略日志的模态框
            // 或者跳转到专门的日志页面
            const content = '<div class="text-center"><p>暂无日志数据</p><p class="text-muted">日志功能正在开发中...</p></div>';
            
            this.showGenericModal('系统日志', content);
            
        } catch (error) {
            console.error('显示全部日志失败:', error);
            this.showMessage('显示日志失败', 'error');
        }
    }

    // 🔥 新增：显示通用模态框
    showGenericModal(title, content) {
        const modalHtml = `
            <div class="modal fade" id="genericModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 移除旧模态框
        const oldModal = document.getElementById('genericModal');
        if (oldModal) oldModal.remove();
        
        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('genericModal'));
        modal.show();
    }

    // 🔥 修复：更新管理配置显示，去掉不必要的小数点，添加参数名称
    updateManagementConfigDisplay(config) {
        // 格式化整数显示，去掉小数点
        const formatInteger = (value) => {
            return Number.isInteger(value) ? value.toString() : value.toFixed(2);
        };
        
        // 🔥 修复：更新当前状态数值，确保整数不显示小数点
        const updateElement = (id, value, isInteger = false) => {
            const element = document.getElementById(id);
            if (element) {
                if (isInteger || Number.isInteger(Number(value))) {
                    element.textContent = Math.floor(Number(value)).toString(); // 强制整数显示，不显示小数点
                } else {
                    element.textContent = Number(value).toFixed(2);
                }
            }
        };
        
        // 🔥 更新四个关键指标（修复格式）
        updateElement('currentActiveStrategies', Math.floor(config.currentActiveStrategies || 0), true);
        updateElement('realTradingStrategiesCount', Math.floor(config.realTradingStrategiesCount || 0), true);
        updateElement('validationStrategiesCount', Math.floor(config.validationStrategiesCount || 0), true);
        updateElement('totalStrategiesCount', Math.floor(config.totalStrategiesCount || 0), true);
        
        // 更新配置参数到表单
        const configMapping = {
            'evolutionInterval': config.evolutionInterval || 10,
            'maxStrategies': config.maxStrategies || 20,
            'realTradingScore': config.realTradingScore || 65,
            'realTradingCount': config.realTradingCount || 2,
            'validationAmount': config.validationAmount || 50,
            'minTrades': config.minTrades || 10,
            'minWinRate': config.minWinRate || 65,
            'realTradingAmount': config.realTradingAmount || 100,
            'minProfit': config.minProfit || 0,
            'maxDrawdown': config.maxDrawdown || 10,
            'minSharpeRatio': config.minSharpeRatio || 1.0,
            'maxPositionSize': config.maxPositionSize || 100,
            'stopLossPercent': config.stopLossPercent || 5,
            'takeProfitPercent': config.takeProfitPercent || 4,
            'maxHoldingMinutes': config.maxHoldingMinutes || 30,
            'minProfitForTimeStop': config.minProfitForTimeStop || 1,
            'eliminationDays': config.eliminationDays || 7,
            'minScore': config.minScore || 50
        };
        
        Object.entries(configMapping).forEach(([key, value]) => {
            const element = document.getElementById(key);
            if (element) {
                element.value = value;
            }
        });
        
        console.log('✅ 管理配置显示已更新');
    }

    // 绑定管理配置事件
    bindManagementEvents() {
        // 保存配置按钮
        const saveBtn = document.getElementById('saveManagementConfig');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                console.log('保存配置按钮被点击');
                this.saveManagementConfig();
            });
        }

        // 重置配置按钮
        const resetBtn = document.getElementById('resetManagementConfig');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                console.log('重置配置按钮被点击');
                this.resetManagementConfig();
            });
        }

        // 全自动策略管理开关
        const autoMgmtSwitch = document.getElementById('autoManagementEnabled');
        if (autoMgmtSwitch) {
            autoMgmtSwitch.addEventListener('change', () => {
                this.toggleAutoStrategyManagement(autoMgmtSwitch.checked);
            });
        }
        
        // 加载全自动策略管理状态
        this.loadAutoManagementStatus();

        // 🔥 添加实时保存功能 - 当输入框失去焦点时自动保存
        const form = document.getElementById('strategyManagementForm');
        if (form) {
            ['evolutionInterval', 'maxStrategies', 'realTradingScore', 'realTradingCount', 'validationAmount', 'realTradingAmount',
             'minTrades', 'minWinRate', 'minProfit', 'maxDrawdown', 'minSharpeRatio', 'maxPositionSize', 
             'stopLossPercent', 'takeProfitPercent', 'maxHoldingMinutes', 'minProfitForTimeStop',
             'eliminationDays', 'minScore'].forEach(key => {
                const input = form.querySelector(`#${key}`);
                if (input) {
                    input.addEventListener('blur', () => {
                        console.log(`${key} 输入框失去焦点，自动保存配置`);
                        this.saveManagementConfig();
                    });
                    input.addEventListener('change', () => {
                        console.log(`${key} 输入框值变化，自动保存配置`);
                        this.saveManagementConfig();
                    });
                }
            });
        }
    }
}

// 🔥 统一的进化日志滚动管理器
class UnifiedEvolutionLogManager {
    constructor() {
        this.logs = [];
        this.isLoading = false;
        this.refreshInterval = 30000; // 🔧 修复：30秒刷新一次，避免动画重置
        this.refreshTimer = null;
        this.lastLogCount = 0; // 追踪日志数量变化
        
        // 滚动配置
        this.verticalConfig = {
            containerId: 'evolutionTicker',
            maxLogs: 30,
            scrollType: 'vertical',
            animationDuration: 60000 // 60秒完整滚动
        };
        
        this.horizontalConfig = {
            containerId: 'strategyManagementEvolutionTicker', 
            maxLogs: 30,  // 🔥 修复：改为30条日志
            scrollType: 'horizontal',
            animationDuration: 40000 // 40秒完整滚动
        };
    }
    
    // 开始日志轮询
    startPolling() {
        // 立即加载一次
        this.loadLogs();
        
        // 定时刷新
        this.refreshTimer = setInterval(() => {
            this.loadLogs();
        }, this.refreshInterval);
        
        console.log('✅ 进化日志轮询已启动');
    }
    
    // 停止日志轮询
    stopPolling() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        console.log('⏹️ 进化日志轮询已停止');
    }
    
    // 加载日志数据
    async loadLogs() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        try {
            const response = await fetch('/api/quantitative/evolution-log');
            const data = await response.json();
            
            if (data.success && data.logs) {
                // 🔧 修复：只有在日志数量变化时才重新渲染，避免动画重置
                const hasNewLogs = data.logs.length !== this.lastLogCount;
                this.logs = data.logs;
                this.lastLogCount = data.logs.length;
                
                if (hasNewLogs) {
                    console.log(`📝 检测到新的进化日志，重新渲染 (${data.logs.length}条)`);
                    this.renderAllViews();
                } else {
                    console.log(`📊 日志数量无变化，跳过重新渲染 (${data.logs.length}条)`);
                    this.updateLogCount(); // 只更新计数
                }
                
                                    // 🔥 修复：从最新的进化日志中解析当前世代信息
                    if (this.logs.length > 0) {
                        const latestLog = this.logs[0]; // 最新的日志
                        const evolutionPattern = /第(\d+)代第(\d+)轮/;
                        
                        if (latestLog.details && evolutionPattern.test(latestLog.details)) {
                            const match = latestLog.details.match(evolutionPattern);
                            if (match && window.app) {
                                const newGeneration = parseInt(match[1]);
                                const newCycle = parseInt(match[2]);
                                
                                // 检查是否有变化，如果有变化则触发策略卡重新渲染
                                const oldState = window.app.evolutionState;
                                const hasChanged = !oldState || 
                                    oldState.current_generation !== newGeneration || 
                                    oldState.current_cycle !== newCycle;
                                
                                window.app.evolutionState = {
                                    current_generation: newGeneration,
                                    current_cycle: newCycle
                                };
                                console.log(`✅ 从进化日志解析世代信息: 第${newGeneration}代第${newCycle}轮`);
                                
                                // 🔥 如果世代信息发生变化，重新渲染策略卡以更新代数轮数显示
                                if (hasChanged && window.app.strategies && window.app.strategies.length > 0) {
                                    console.log('🔄 世代信息已更新，重新渲染策略卡...');
                                    window.app.renderStrategies();
                                }
                            }
                        }
                        
                        // 如果没有从日志解析出来，使用默认值
                        if (window.app && !window.app.evolutionState) {
                            window.app.evolutionState = {
                                current_generation: 1,
                                current_cycle: 1
                            };
                            console.log('⚠️ 使用默认世代信息: 第1代第1轮');
                        }
                    }
                
                // 保存到全局变量供其他功能使用
                if (window.app) {
                    window.app.allEvolutionLogs = this.logs;
                }
            }
        } catch (error) {
            console.error('❌ 加载进化日志失败:', error);
            // 设置默认值
            if (window.app) {
                window.app.evolutionState = {
                    current_generation: 1,
                    current_cycle: 8
                };
            }
        } finally {
            this.isLoading = false;
        }
    }
    
    // 渲染所有视图
    renderAllViews() {
        this.renderVerticalView();
        this.renderHorizontalView();
        this.updateLogCount();
    }
    
    // 渲染垂直滚动视图（策略进化实时监控区域）
    renderVerticalView() {
        const container = document.getElementById(this.verticalConfig.containerId);
        if (!container) return;
        
        if (!this.logs || this.logs.length === 0) {
            container.innerHTML = '<div class="ticker-item"><span class="text-muted">暂无进化日志...</span></div>';
            return;
        }
        
        // 🔥 修复：取最新的30条日志，确保显示最新数据
        const recentLogs = [...this.logs]
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, this.verticalConfig.maxLogs);
        
        const tickerContent = recentLogs.map(log => {
            const time = new Date(log.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            let actionClass = 'created';
            let actionText = '新增';
            let actionIcon = '🆕';
            
            switch(log.action) {
                case 'created':
                    actionClass = 'created';
                    actionText = '新增';
                    actionIcon = '🆕';
                    break;
                case 'eliminated':
                    actionClass = 'eliminated';
                    actionText = '淘汰';
                    actionIcon = '❌';
                    break;
                case 'optimized':
                    actionClass = 'optimized';
                    actionText = '优化';
                    actionIcon = '⚡';
                    break;
                case 'validated':
                    actionClass = 'validated';
                    actionText = '验证';
                    actionIcon = '✅';
                    break;
                case 'promoted':
                    actionClass = 'promoted';
                    actionText = '晋级';
                    actionIcon = '🔝';
                    break;
                case 'protected':
                    actionClass = 'protected';
                    actionText = '保护';
                    actionIcon = '🛡️';
                    break;
                case 'evolved':
                    actionClass = 'evolved';
                    actionText = '进化';
                    actionIcon = '🧬';
                    break;
                default:
                    actionIcon = '📊';
                    actionText = log.action || '系统活动';
            }

            // 🔥 使用完整的details信息，确保显示完整内容
            const message = log.details || log.message || '策略进化中...';

            return `
                <div class="ticker-item">
                    <span class="time">${time}</span>
                    <span class="action ${actionClass}">${actionIcon} ${actionText}</span>
                    <span class="message">${message}</span>
                    ${log.strategy_id ? `<span class="strategy-id" data-id="${log.strategy_id}">ID: ${log.strategy_id.substring(0, 8)}</span>` : ''}
                </div>
            `;
        }).join('');

        // 平滑更新内容
        container.style.opacity = '0.7';
        setTimeout(() => {
            container.innerHTML = tickerContent;
            container.style.opacity = '1';
        }, 200);
    }
    
    // 渲染水平滚动视图（策略管理标题右侧）
    renderHorizontalView() {
        const container = document.getElementById(this.horizontalConfig.containerId);
        if (!container) return;
        
        if (!this.logs || this.logs.length === 0) {
            container.innerHTML = '<div class="log-item"><span class="text-muted">暂无进化日志</span></div>';
            return;
        }
        
        // 🔥 修复：取最新的30条日志用于横向滚动，确保显示最新且完整的信息
        const recentLogs = [...this.logs]
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, this.horizontalConfig.maxLogs);
        
        const logItems = recentLogs.map(log => {
            const time = new Date(log.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            let actionText = '';
            let colorClass = 'text-muted';
            
            switch(log.action) {
                case 'created':
                    actionText = '创建策略';
                    colorClass = 'text-success';
                    break;
                case 'optimized':
                    actionText = '优化策略';
                    colorClass = 'text-info';
                    break;
                case 'promoted':
                    actionText = '提升策略';
                    colorClass = 'text-warning';
                    break;
                case 'protected':
                    actionText = '保护策略';
                    colorClass = 'text-secondary';
                    break;
                case 'evolved':
                    actionText = '进化策略';
                    colorClass = 'text-primary';
                    break;
                case 'eliminated':
                    actionText = '淘汰策略';
                    colorClass = 'text-danger';
                    break;
                default:
                    // 🔥 修复：使用完整的details字段，确保显示完整信息
                    actionText = log.details || log.action || '系统活动';
                    colorClass = 'text-muted';
            }

            return `
                <div class="log-item">
                    <span class="${colorClass}">[${time}] ${actionText}</span>
                    ${log.strategy_name ? `<small class="text-muted"> - ${log.strategy_name}</small>` : ''}
                </div>
            `;
        }).join('');

        container.innerHTML = logItems;
    }
    
    // 更新日志计数
    updateLogCount() {
        const countElement = document.getElementById('evolutionLogCount');
        if (countElement && this.logs) {
            countElement.textContent = `${this.logs.length} 条记录`;
        }
    }
    
    // 手动刷新
    refresh() {
        this.loadLogs();
    }
}

// 🔥 移除重复的全局函数定义，这些函数已在HTML模板中定义，避免冲突 

// 四层进化配置管理类
class FourTierConfigManager {
    constructor() {
        this.config = {};
        this.init();
    }

    async init() {
        await this.loadConfig();
        this.setupEventListeners();
        this.startStatusUpdater();
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/quantitative/management-config');
            const data = await response.json();
            
            if (data.success) {
                this.config = data.config;
                const fourTierConfig = data.four_tier_config || {};
                
                // 填充传统配置字段
                this.populateTraditionalConfig(this.config);
                
                // 填充四层进化配置字段
                this.populateFourTierConfig(fourTierConfig);
                
                console.log('✅ 四层进化配置加载成功:', fourTierConfig);
            } else {
                console.error('❌ 加载配置失败:', data.message);
            }
        } catch (error) {
            console.error('❌ 配置加载异常:', error);
        }
    }

    populateTraditionalConfig(config) {
        // 填充传统配置字段
        const fields = [
            'maxStrategies', 'realTradingScore', 'realTradingCount',
            'validationAmount', 'realTradingAmount', 'minTrades', 'minWinRate', 
            'minProfit', 'maxDrawdown', 'minSharpeRatio'
        ];

        fields.forEach(field => {
            const element = document.getElementById(field);
            if (element && config[field] !== undefined) {
                element.value = config[field];
            }
        });
    }

    populateFourTierConfig(fourTierConfig) {
        // 填充四层进化配置字段
        Object.keys(fourTierConfig).forEach(key => {
            const element = document.getElementById(key);
            if (element && fourTierConfig[key]) {
                const value = fourTierConfig[key].value || fourTierConfig[key];
                if (element.tagName === 'SELECT') {
                    element.value = value.toString();
                } else {
                    element.value = value;
                }
            }
        });
        
        // 🔧 新增：填充实盘交易控制参数
        const realTradingFields = ['real_trading_enabled', 'min_simulation_days', 'min_sim_win_rate', 'min_sim_total_pnl'];
        realTradingFields.forEach(field => {
            const element = document.getElementById(field);
            if (element && fourTierConfig[field]) {
                const value = fourTierConfig[field].value || fourTierConfig[field];
                if (element.tagName === 'SELECT') {
                    element.value = value.toString();
                } else {
                    element.value = value;
                }
            }
        });
    }

    setupEventListeners() {
        // 保存配置按钮
        const saveBtn = document.getElementById('saveConfigBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveConfig());
        }

        // 实时配置更新监听
        const configInputs = document.querySelectorAll('#management-config input[type="number"]');
        configInputs.forEach(input => {
            input.addEventListener('change', () => this.onConfigChange(input));
        });
    }

    onConfigChange(input) {
        const key = input.id;
        const value = parseFloat(input.value) || 0;
        
        // 实时更新本地配置
        if (this.isFourTierConfig(key)) {
            // 四层配置更新
            console.log(`🔧 四层配置更新: ${key} = ${value}`);
        } else {
            // 传统配置更新
            this.config[key] = value;
            console.log(`🔧 传统配置更新: ${key} = ${value}`);
        }

        // 实时更新统计显示
        this.updateTierStats();
    }

    isFourTierConfig(key) {
        const fourTierKeys = [
            'high_freq_pool_size', 'display_strategies_count', 'real_trading_count',
            'low_freq_interval_hours', 'high_freq_interval_minutes', 'display_interval_minutes',
            'low_freq_validation_count', 'high_freq_validation_count', 'display_validation_count',
            'validation_amount', 'real_trading_amount', 'real_trading_score_threshold'
        ];
        return fourTierKeys.includes(key);
    }

    async saveConfig() {
        try {
            // 🔧 收集传统配置（删除evolutionInterval，已统一到四层配置）
            const traditionalConfig = {};
            const traditionalFields = [
                'maxStrategies', 'realTradingScore', 'realTradingCount',
                'validationAmount', 'realTradingAmount', 'minTrades', 'minWinRate',
                'minProfit', 'maxDrawdown', 'minSharpeRatio'
            ];

            traditionalFields.forEach(field => {
                const element = document.getElementById(field);
                if (element) {
                    traditionalConfig[field] = parseFloat(element.value) || 0;
                }
            });

            // 收集四层进化配置（包含实盘交易控制参数）
            const fourTierConfig = {};
            const fourTierFields = [
                'high_freq_pool_size', 'display_strategies_count', 'real_trading_count',
                'low_freq_interval_hours', 'high_freq_interval_minutes', 'display_interval_minutes',
                'low_freq_validation_count', 'high_freq_validation_count', 'display_validation_count',
                'validation_amount', 'real_trading_amount', 'real_trading_score_threshold',
                // 🔧 新增：实盘交易控制参数
                'real_trading_enabled', 'min_simulation_days', 'min_sim_win_rate', 'min_sim_total_pnl'
            ];

            fourTierFields.forEach(field => {
                const element = document.getElementById(field);
                if (element) {
                    if (element.tagName === 'SELECT') {
                        fourTierConfig[field] = element.value === 'true';
                    } else {
                        fourTierConfig[field] = parseFloat(element.value) || 0;
                    }
                }
            });

            // 发送保存请求
            const response = await fetch('/api/quantitative/management-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config: traditionalConfig,
                    four_tier_config: fourTierConfig
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('✅ 四层进化配置保存成功！重启进化调度器后生效', 'success');
                
                // 更新本地配置
                this.config = { ...this.config, ...traditionalConfig };
                
                // 立即更新统计显示
                this.updateTierStats();
                
                console.log('✅ 配置保存成功:', result.message);
            } else {
                this.showNotification('❌ 配置保存失败: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('❌ 保存配置异常:', error);
            this.showNotification('❌ 配置保存异常: ' + error.message, 'error');
        }
    }

    async updateTierStats() {
        try {
            // 获取四层系统统计
            const response = await fetch('/api/quantitative/management-config');
            const data = await response.json();
            
            if (data.success && data.four_tier_config) {
                const config = data.four_tier_config;
                
                // 计算理论进化次数
                const poolSize = parseInt(config.high_freq_pool_size?.value || 2000);
                const displayCount = parseInt(config.display_strategies_count?.value || 21);
                const realTradingCount = parseInt(config.real_trading_count?.value || 3);
                const realTradingThreshold = parseFloat(config.real_trading_score_threshold?.value || 65);
                
                const lowFreqHours = parseInt(config.low_freq_interval_hours?.value || 24);
                const highFreqMinutes = parseInt(config.high_freq_interval_minutes?.value || 60);
                const displayMinutes = parseInt(config.display_interval_minutes?.value || 3);
                
                // 计算每小时理论进化次数
                const tier1Evolutions = Math.floor(16337 / lowFreqHours); // 假设总策略数16337
                const tier2Evolutions = Math.floor(poolSize * (60 / highFreqMinutes));
                const tier3Evolutions = Math.floor(displayCount * (60 / displayMinutes));
                
                // 更新显示
                this.updateTierDisplay('tier1_count', '16,337');
                this.updateTierDisplay('tier1_evolutions', tier1Evolutions.toLocaleString());
                
                this.updateTierDisplay('tier2_count', poolSize.toLocaleString());
                this.updateTierDisplay('tier2_evolutions', tier2Evolutions.toLocaleString());
                
                this.updateTierDisplay('tier3_count', displayCount.toString());
                this.updateTierDisplay('tier3_evolutions', tier3Evolutions.toLocaleString());
                
                this.updateTierDisplay('tier4_count', realTradingCount.toString());
                this.updateTierDisplay('tier4_threshold', realTradingThreshold.toString());
                
                console.log('📊 四层系统统计已更新');
            }
        } catch (error) {
            console.error('❌ 更新统计失败:', error);
        }
    }

    updateTierDisplay(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    startStatusUpdater() {
        // 立即更新一次
        this.updateTierStats();
        
        // 每30秒更新一次统计
        setInterval(() => {
            this.updateTierStats();
        }, 30000);
    }

    showNotification(message, type = 'info') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
}

// 在量化系统初始化时启动四层配置管理器
document.addEventListener('DOMContentLoaded', function() {
    // 等待量化系统初始化完成后启动
    setTimeout(() => {
        if (typeof window.fourTierConfigManager === 'undefined') {
            window.fourTierConfigManager = new FourTierConfigManager();
            console.log('🚀 四层进化配置管理器已启动');
        }
    }, 1000);
});