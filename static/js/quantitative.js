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
        // 🔧 暂时禁用WebSocket连接，避免频繁错误日志
        // 等WebSocket服务启动后再启用
        this.updateStatus('websocket', 'disconnected', '服务未启动');
        console.log('💡 WebSocket服务暂未启动，已禁用连接尝试');
        
        // 可以通过调用 this.enableWebSocket() 来启用WebSocket
        return;
        
        /* 原WebSocket连接代码 - 暂时注释
        try {
            // 尝试连接实时监控WebSocket
            this.websocket = new WebSocket('ws://47.236.39.134:8765');
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket连接成功');
                this.updateStatus('websocket', 'connected', '已连接');
                this.reconnectAttempts = 0; // 重置重连计数
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket消息解析错误:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 WebSocket连接断开');
                this.updateStatus('websocket', 'disconnected', '连接断开');
                
                // 限制重连次数，避免无限重连
                if (this.reconnectAttempts < 3) {
                    this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
                    console.log(`尝试第${this.reconnectAttempts}次重连...`);
                    setTimeout(() => this.initializeWebSocket(), 10000); // 10秒后重连
                } else {
                    console.log('WebSocket重连次数已达上限，停止重连');
                    this.updateStatus('websocket', 'disconnected', '服务不可用');
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket连接错误:', error);
                this.updateStatus('websocket', 'disconnected', '连接失败');
            };
            
        } catch (error) {
            console.error('WebSocket初始化失败:', error);
            this.updateStatus('websocket', 'disconnected', '不可用');
        }
        */
    }
    
    // 🔥 新增：手动启用WebSocket的方法
    enableWebSocket() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            console.log('WebSocket已连接');
            return;
        }
        
        this.reconnectAttempts = 0;
        try {
            console.log('🔄 启用WebSocket连接...');
            this.websocket = new WebSocket('ws://47.236.39.134:8765');
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket连接成功');
                this.updateStatus('websocket', 'connected', '已连接');
                this.reconnectAttempts = 0;
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket消息解析错误:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 WebSocket连接断开');
                this.updateStatus('websocket', 'disconnected', '连接断开');
                
                if (this.reconnectAttempts < 3) {
                    this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
                    console.log(`尝试第${this.reconnectAttempts}次重连...`);
                    setTimeout(() => this.enableWebSocket(), 10000);
                } else {
                    console.log('WebSocket重连次数已达上限');
                    this.updateStatus('websocket', 'disconnected', '服务不可用');
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket连接错误:', error);
                this.updateStatus('websocket', 'disconnected', '连接失败');
            };
            
        } catch (error) {
            console.error('WebSocket启用失败:', error);
            this.updateStatus('websocket', 'disconnected', '不可用');
        }
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
            
            if (data.overall_status === 'online') {
                this.updateStatus('system', 'online', '运行正常');
            } else if (data.overall_status === 'degraded') {
                this.updateStatus('system', 'warning', '部分异常');
            } else {
                this.updateStatus('system', 'offline', '系统离线');
            }
        } catch (error) {
            console.error('系统状态检查失败:', error);
            this.updateStatus('system', 'offline', '检查失败');
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

// 🔥 增强的进化日志渲染
class EnhancedEvolutionRenderer {
    constructor() {
        this.logCount = 0;
        this.maxDisplayLogs = 50;
    }
    
    renderEvolutionLog(logs) {
        const ticker = document.getElementById('evolutionTicker');
        const logCountElement = document.getElementById('evolutionLogCount');
        
        if (!ticker) return;

        // 更新日志计数
        this.logCount = logs.length;
        if (logCountElement) {
            logCountElement.textContent = `${this.logCount} 条记录`;
        }

        // 🔧 优化排序和显示
        const sortedLogs = [...logs].sort((a, b) => {
            const timeA = new Date(a.timestamp || '1970-01-01').getTime();
            const timeB = new Date(b.timestamp || '1970-01-01').getTime();
            return timeB - timeA; // 最新在前
        });
        
        const recentLogs = sortedLogs.slice(0, this.maxDisplayLogs);
        
        // 生成增强的HTML内容
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
                default:
                    actionIcon = '📊';
            }

            return `
                <div class="ticker-item">
                    <span class="time">${time}</span>
                    <span class="action ${actionClass}">${actionIcon} ${actionText}</span>
                    <span class="message">${log.message || log.details || '策略进化中...'}</span>
                    ${log.strategy_id ? `<span class="strategy-id" data-id="${log.strategy_id}">ID: ${log.strategy_id.substring(0, 8)}</span>` : ''}
                </div>
            `;
        }).join('');

        // 平滑更新内容
        ticker.style.opacity = '0.7';
        setTimeout(() => {
            ticker.innerHTML = tickerContent || '<div class="ticker-item"><span class="text-muted">暂无进化日志...</span></div>';
            ticker.style.opacity = '1';
        }, 200);

        // 添加点击事件监听器
        ticker.querySelectorAll('.strategy-id').forEach(element => {
            element.addEventListener('click', (e) => {
                const strategyId = e.target.dataset.id;
                if (strategyId && window.app) {
                    window.app.viewStrategyDetails(strategyId);
                }
            });
        });

        console.log(`✅ 进化日志已更新: ${recentLogs.length}条最新日志`);
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
        
        // 🔥 新增：全局状态管理和增强功能
        this.globalStatusManager = new GlobalStatusManager();
        this.evolutionRenderer = new EnhancedEvolutionRenderer();
        
        this.bindEvents();
        this.initChart();
        this.loadSystemStatus(); // 加载真实系统状态
        this.startAutoRefresh();
        this.initEvolutionLog(); // 初始化进化日志
        this.loadManagementConfig(); // 加载管理配置
        this.bindManagementEvents(); // 🔥 确保事件绑定在DOM加载后执行
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
            
            const response = await fetch('/api/quantitative/auto-trading', {
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
                systemStatusEl.innerHTML = '<span class="status-indicator status-running"></span>在线';
            }
            if (systemToggle) {
                systemToggle.classList.add('active');
            }
            
            // 更新顶部导航栏状态
            const statusElements = document.querySelectorAll('[data-status-text]');
            statusElements.forEach(el => {
                el.textContent = '在线';
                el.className = 'text-success';
            });
            
            console.log('✅ 系统状态已更新为在线');
        } else {
            // 系统控制台状态 - 离线
            if (systemStatusEl) {
                systemStatusEl.innerHTML = '<span class="status-indicator status-offline"></span>离线';
            }
            if (systemToggle) {
                systemToggle.classList.remove('active');
            }
            
            // 更新顶部导航栏状态
            const statusElements = document.querySelectorAll('[data-status-text]');
            statusElements.forEach(el => {
                el.textContent = '离线';
                el.className = 'text-muted';
            });
            
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
                this.renderStrategies();
            } else if (data.data && Array.isArray(data.data)) {
                // 兼容旧版本API结构
                this.strategies = data.data;
                console.log(`✅ 成功加载 ${this.strategies.length} 个策略`);
                this.renderStrategies();
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
            // 🔥 后端已统一返回百分比格式，前端只需直接使用
            const winRate = strategy.win_rate || 0;
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
            
            // 🔥 交易状态 - 策略始终运行验证交易，只有开启自动交易开关后才选择前几名进行真实交易
            let tradingStatus, tradingBadgeClass;
            
            // 策略理论上应该始终运行，进行验证交易
            const autoTradingEnabled = this.systemStatus?.auto_trading_enabled || false;
            if (autoTradingEnabled && score >= 65) {
                tradingStatus = '真实交易';
                tradingBadgeClass = 'bg-success';
            } else {
                tradingStatus = '验证交易';  // 所有策略都进行验证交易
                tradingBadgeClass = 'bg-info';
            }
            
            return `
            <div class="col-md-4 mb-3">
                <div class="card strategy-card ${strategy.enabled ? 'strategy-running' : 'strategy-stopped'}">
                    <div class="card-body">
                        <!-- 顶部：标题和状态 -->
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="card-title mb-0">
                                    <a href="javascript:void(0)" onclick="window.app.showStrategyConfig('${strategy.id}')" class="text-decoration-none">
                                        ${strategy.name}
                                    </a>
                                </h6>
                                <small class="text-muted">${strategy.symbol} • ${strategy.evolution_display || `第${generation}代第${round}轮`}</small>
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
                                    onclick="window.app.showStrategyLogs('${strategy.id}')"
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

    // 🔥 重新设计：加载交易周期日志 - 支持交易周期和传统单笔交易两种显示模式
    async loadTradeLogs(strategyId) {
        try {
            const response = await fetch(`/api/quantitative/strategies/${strategyId}/trade-logs`);
            const data = await response.json();
            
            const tbody = document.getElementById('tradeLogsTable');
            
            if (data.success && data.logs && data.logs.length > 0) {
                this.tradeLogs = data.logs;
                this.displayMode = data.display_mode || 'legacy_trades';
                this.currentTradeLogPage = 1;
                this.tradeLogsPerPage = 15;
                
                // 根据显示模式渲染不同的表格结构
                if (this.displayMode === 'trade_cycles') {
                    this.renderTradeCyclesPage();
                } else {
                    this.renderTradeLogsPage();
                }
                this.renderTradeLogPagination();
                
            } else {
                const colSpan = this.displayMode === 'trade_cycles' ? '9' : '7';
                tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-muted">暂无交易记录</td></tr>`;
                document.getElementById('tradeLogPaginationContainer').innerHTML = '';
            }
            
        } catch (error) {
            console.error('加载交易日志失败:', error);
            const tbody = document.getElementById('tradeLogsTable');
            if (tbody) {
                const colSpan = this.displayMode === 'trade_cycles' ? '9' : '7';
                tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-danger">加载失败</td></tr>`;
            }
            const container = document.getElementById('tradeLogPaginationContainer');
            if (container) {
                container.innerHTML = '';
            }
        }
    }

    // 🔥 新增：渲染交易周期页面 - 显示完整的买入卖出周期
    renderTradeCyclesPage() {
        const tbody = document.getElementById('tradeLogsTable');
        const startIndex = (this.currentTradeLogPage - 1) * this.tradeLogsPerPage;
        const endIndex = startIndex + this.tradeLogsPerPage;
        const currentCycles = this.tradeLogs.slice(startIndex, endIndex);
        
        // 更新表头为交易周期格式
        const thead = document.querySelector('#tradeLogsTable').closest('table').querySelector('thead');
        thead.innerHTML = `
            <tr>
                <th>周期ID</th>
                <th>买入时间</th>
                <th>卖出时间</th>
                <th>交易对</th>
                <th>买入价格</th>
                <th>卖出价格</th>
                <th>数量</th>
                <th>持有时长</th>
                <th>周期盈亏</th>
                <th>交易类型</th>
                <th>执行状态</th>
            </tr>
        `;
        
        // 分类统计
        const realCycles = currentCycles.filter(cycle => cycle.trade_type === 'real_trading');
        const validationCycles = currentCycles.filter(cycle => cycle.trade_type === 'verification');
        const initialCycles = currentCycles.filter(cycle => cycle.trade_type === 'initial_validation');
        
        tbody.innerHTML = [
            // 显示真实交易周期
            ...realCycles.map(cycle => `
                <tr class="real-trade-row">
                    <td><span class="badge bg-primary">${cycle.cycle_id}</span></td>
                    <td>${this.formatTime(cycle.buy_timestamp)}</td>
                    <td>${this.formatTime(cycle.sell_timestamp)}</td>
                    <td>${cycle.symbol}</td>
                    <td>${cycle.buy_price.toFixed(6)}</td>
                    <td>${cycle.sell_price.toFixed(6)}</td>
                    <td>${cycle.quantity.toFixed(6)}</td>
                    <td>${cycle.holding_minutes}分钟</td>
                    <td class="${cycle.cycle_pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${cycle.cycle_pnl >= 0 ? '+' : ''}${cycle.cycle_pnl.toFixed(6)}U
                        <br><small>(${cycle.return_percentage >= 0 ? '+' : ''}${cycle.return_percentage.toFixed(2)}%)</small>
                    </td>
                    <td><span class="badge bg-success">${cycle.trade_mode}</span></td>
                    <td><span class="badge bg-success">${cycle.execution_status}</span></td>
                </tr>
            `),
            // 显示验证交易周期
            ...validationCycles.map(cycle => `
                <tr class="validation-trade-row" style="background-color: #f8f9fa;">
                    <td><span class="badge bg-secondary">${cycle.cycle_id}</span></td>
                    <td>${this.formatTime(cycle.buy_timestamp)}</td>
                    <td>${this.formatTime(cycle.sell_timestamp)}</td>
                    <td>${cycle.symbol}</td>
                    <td>${cycle.buy_price.toFixed(6)}</td>
                    <td>${cycle.sell_price.toFixed(6)}</td>
                    <td>${cycle.quantity.toFixed(6)}</td>
                    <td>${cycle.holding_minutes}分钟</td>
                    <td class="${cycle.cycle_pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${cycle.cycle_pnl >= 0 ? '+' : ''}${cycle.cycle_pnl.toFixed(6)}U
                        <br><small>(${cycle.return_percentage >= 0 ? '+' : ''}${cycle.return_percentage.toFixed(2)}%)</small>
                    </td>
                    <td><span class="badge bg-info">${cycle.trade_mode}</span></td>
                    <td><span class="badge bg-secondary">${cycle.execution_status}</span></td>
                </tr>
            `),
            // 显示初始验证周期
            ...initialCycles.map(cycle => `
                <tr class="initial-validation-row" style="background-color: #fff3cd;">
                    <td><span class="badge bg-warning">${cycle.cycle_id}</span></td>
                    <td>${this.formatTime(cycle.buy_timestamp)}</td>
                    <td>${this.formatTime(cycle.sell_timestamp)}</td>
                    <td>${cycle.symbol}</td>
                    <td>${cycle.buy_price.toFixed(6)}</td>
                    <td>${cycle.sell_price.toFixed(6)}</td>
                    <td>${cycle.quantity.toFixed(6)}</td>
                    <td>${cycle.holding_minutes}分钟</td>
                    <td class="${cycle.cycle_pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${cycle.cycle_pnl >= 0 ? '+' : ''}${cycle.cycle_pnl.toFixed(6)}U
                        <br><small>(${cycle.return_percentage >= 0 ? '+' : ''}${cycle.return_percentage.toFixed(2)}%)</small>
                    </td>
                    <td><span class="badge bg-warning">${cycle.trade_mode}</span></td>
                    <td><span class="badge bg-warning">${cycle.execution_status}</span></td>
                </tr>
            `)
        ].join('');
        
        // 添加统计信息
        const totalReal = this.tradeLogs.filter(cycle => cycle.trade_type === 'real_trading').length;
        const totalValidation = this.tradeLogs.filter(cycle => cycle.trade_type === 'verification').length;
        const totalInitial = this.tradeLogs.filter(cycle => cycle.trade_type === 'initial_validation').length;
        
        const statsRow = `
            <tr class="table-info">
                <td colspan="11" class="text-center">
                    <strong>当前页：真实交易 ${realCycles.length} 个周期，验证交易 ${validationCycles.length} 个周期，初始验证 ${initialCycles.length} 个周期</strong>
                    <br><small>总计：真实 ${totalReal} 个，验证 ${totalValidation} 个，初始验证 ${totalInitial} 个</small>
                </td>
            </tr>
        `;
        tbody.innerHTML = statsRow + tbody.innerHTML;
    }

    // 🔥 修复：渲染传统单笔交易日志页面
    renderTradeLogsPage() {
        const tbody = document.getElementById('tradeLogsTable');
        const startIndex = (this.currentTradeLogPage - 1) * this.tradeLogsPerPage;
        const endIndex = startIndex + this.tradeLogsPerPage;
        const currentLogs = this.tradeLogs.slice(startIndex, endIndex);
        
        // 确保表头为单笔交易格式
        const thead = document.querySelector('#tradeLogsTable').closest('table').querySelector('thead');
        thead.innerHTML = `
            <tr>
                <th>时间</th>
                <th>信号</th>
                <th>价格</th>
                <th>数量</th>
                <th>置信度</th>
                <th>交易类型</th>
                <th>执行状态</th>
                <th>盈亏</th>
            </tr>
        `;
        
        // 分类统计
        const realTrades = currentLogs.filter(log => log.trade_type === 'real_trading');
        const validationTrades = currentLogs.filter(log => log.trade_type === 'verification');
        const initialTrades = currentLogs.filter(log => log.trade_type === 'initial_validation');
        
        tbody.innerHTML = [
            // 显示真实交易
            ...realTrades.map(log => `
                <tr class="real-trade-row">
                    <td>${this.formatTime(log.timestamp)}</td>
                    <td><span class="badge ${log.signal_type === 'buy' ? 'bg-success' : 'bg-danger'}">${log.signal_type.toUpperCase()}</span></td>
                    <td>${log.price.toFixed(6)}</td>
                    <td>${log.quantity.toFixed(6)}</td>
                    <td>${(log.confidence * 100).toFixed(1)}%</td>
                    <td><span class="badge bg-success">${log.trade_mode}</span></td>
                    <td><span class="badge bg-success">${log.execution_status}</span></td>
                    <td class="${log.pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${log.pnl >= 0 ? '+' : ''}${log.pnl.toFixed(6)}U
                    </td>
                </tr>
            `),
            // 显示验证交易
            ...validationTrades.map(log => `
                <tr class="validation-trade-row" style="background-color: #f8f9fa;">
                    <td>${this.formatTime(log.timestamp)}</td>
                    <td><span class="badge ${log.signal_type === 'buy' ? 'bg-success' : 'bg-danger'}">${log.signal_type.toUpperCase()}</span></td>
                    <td>${log.price.toFixed(6)}</td>
                    <td>${log.quantity.toFixed(6)}</td>
                    <td>${(log.confidence * 100).toFixed(1)}%</td>
                    <td><span class="badge bg-info">${log.trade_mode}</span></td>
                    <td><span class="badge bg-secondary">${log.execution_status}</span></td>
                    <td class="${log.pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${log.pnl >= 0 ? '+' : ''}${log.pnl.toFixed(6)}U
                    </td>
                </tr>
            `),
            // 显示初始验证交易
            ...initialTrades.map(log => `
                <tr class="initial-validation-row" style="background-color: #fff3cd;">
                    <td>${this.formatTime(log.timestamp)}</td>
                    <td><span class="badge ${log.signal_type === 'buy' ? 'bg-success' : 'bg-danger'}">${log.signal_type.toUpperCase()}</span></td>
                    <td>${log.price.toFixed(6)}</td>
                    <td>${log.quantity.toFixed(6)}</td>
                    <td>${(log.confidence * 100).toFixed(1)}%</td>
                    <td><span class="badge bg-warning">${log.trade_mode}</span></td>
                    <td><span class="badge bg-warning">${log.execution_status}</span></td>
                    <td class="${log.pnl >= 0 ? 'text-success' : 'text-danger'}">
                        ${log.pnl >= 0 ? '+' : ''}${log.pnl.toFixed(6)}U
                    </td>
                </tr>
            `)
        ].join('');
        
        // 添加统计信息
        const totalReal = this.tradeLogs.filter(log => log.trade_type === 'real_trading').length;
        const totalValidation = this.tradeLogs.filter(log => log.trade_type === 'verification').length;
        const totalInitial = this.tradeLogs.filter(log => log.trade_type === 'initial_validation').length;
        
        const statsRow = `
            <tr class="table-info">
                <td colspan="8" class="text-center">
                    <strong>当前页：真实交易 ${realTrades.length} 条，验证交易 ${validationTrades.length} 条，初始验证 ${initialTrades.length} 条</strong>
                    <br><small>总计：真实 ${totalReal} 条，验证 ${totalValidation} 条，初始验证 ${totalInitial} 条</small>
                </td>
            </tr>
        `;
        tbody.innerHTML = statsRow + tbody.innerHTML;
    }

    // 🔥 新增：渲染交易日志分页控件
    renderTradeLogPagination() {
        const container = document.getElementById('tradeLogPaginationContainer');
        if (!container) return;
        
        const totalPages = Math.ceil(this.tradeLogs.length / this.tradeLogsPerPage);
        
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let paginationHtml = `
            <nav aria-label="交易日志分页">
                <ul class="pagination pagination-sm justify-content-center">
                    <li class="page-item ${this.currentTradeLogPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="javascript:void(0)" onclick="app.changeTradeLogPage(${this.currentTradeLogPage - 1})">上一页</a>
                    </li>
        `;
        
        // 显示页码
        for (let i = 1; i <= totalPages; i++) {
            paginationHtml += `
                <li class="page-item ${i === this.currentTradeLogPage ? 'active' : ''}">
                    <a class="page-link" href="javascript:void(0)" onclick="app.changeTradeLogPage(${i})">${i}</a>
                </li>
            `;
        }
        
        paginationHtml += `
                    <li class="page-item ${this.currentTradeLogPage === totalPages ? 'disabled' : ''}">
                        <a class="page-link" href="javascript:void(0)" onclick="app.changeTradeLogPage(${this.currentTradeLogPage + 1})">下一页</a>
                    </li>
                </ul>
            </nav>
        `;
        
        container.innerHTML = paginationHtml;
    }

    // 🔥 新增：切换交易日志页面
    changeTradeLogPage(page) {
        if (page < 1 || page > Math.ceil(this.tradeLogs.length / this.tradeLogsPerPage)) {
            return;
        }
        
        this.currentTradeLogPage = page;
        this.renderTradeLogsPage();
        this.renderTradeLogPagination();
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
                this.logsPerPage = 20;  // 🔥 修复：增加每页显示日志数量到20条，支持更多记录查看
                
                this.renderOptimizationLogs();
                this.renderLogPagination();
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无优化记录</td></tr>';
                document.getElementById('logPaginationContainer').innerHTML = '';
            }
            
        } catch (error) {
            console.error('加载优化记录失败:', error);
            const tbody = document.getElementById('optimizationLogsTable');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">加载失败</td></tr>';
            }
            const container = document.getElementById('logPaginationContainer');
            if (container) {
                container.innerHTML = '';
            }
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
                <td><code style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block;">${JSON.stringify(log.old_parameters || {}, null, 1)}</code></td>
                <td><code style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block;">${JSON.stringify(log.new_parameters || {}, null, 1)}</code></td>
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

        // 🔥 只显示基于真实数据的收益曲线，不生成任何模拟数据
        performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '账户价值',
                    data: [],
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

        // 加载真实的收益历史数据
        this.loadRealPerformanceData();
    }

    // 加载真实收益数据
    async loadRealPerformanceData() {
        try {
            const response = await fetch('/api/quantitative/performance-history');
            const data = await response.json();
            
            if (data.success && data.data && data.data.length > 0) {
                const labels = data.data.map(item => {
                    const date = new Date(item.timestamp);
                    return date.toLocaleDateString();
                });
                
                const values = data.data.map(item => item.account_value);
                
                if (performanceChart) {
                    performanceChart.data.labels = labels;
                    performanceChart.data.datasets[0].data = values;
                    performanceChart.update();
                }
            } else {
                // 如果没有真实数据，显示空图表
                console.log('暂无真实收益数据，显示空图表');
            }
        } catch (error) {
            console.error('加载真实收益数据失败:', error);
            // 显示空图表而不是错误
            if (performanceChart) {
                performanceChart.data.labels = [];
                performanceChart.data.datasets[0].data = [];
                performanceChart.update();
            }
        }
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
                    const date = new Date(item.date || item.timestamp);
                    return date.toLocaleDateString();
                });
                
                const balances = data.data.map(item => item.balance || item.total_balance);
                
                if (this.balanceChart) {
                    this.balanceChart.data.labels = labels;
                    this.balanceChart.data.datasets[0].data = balances;
                    this.balanceChart.update();
                    console.log('资产图表已更新');
                } else {
                    console.warn('资产图表未初始化');
                }
                
                // 更新当前资产显示
                const currentBalance = data.data[data.data.length - 1].balance || data.data[data.data.length - 1].total_balance;
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
                    // 🔥 不再显示任何模拟数据，只显示真实数据或空状态
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
                window.autoTradingEnabled = data.data.services?.strategy_engine === 'online';
                
                // 保存到实例变量
                this.systemStatus = {
                    running: isOnline || isDegraded,
                    auto_trading_enabled: data.data.services?.strategy_engine === 'online',
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
            document.getElementById('evolutionInterval').value = managementConfig.evolutionInterval || 10;
            document.getElementById('maxStrategies').value = managementConfig.maxStrategies || 20;
            document.getElementById('realTradingScore').value = managementConfig.realTradingScore || 65;
            document.getElementById('realTradingCount').value = managementConfig.realTradingCount || 2;
            document.getElementById('validationAmount').value = managementConfig.validationAmount || 50;
            document.getElementById('realTradingAmount').value = managementConfig.realTradingAmount || 100;
            document.getElementById('minTrades').value = managementConfig.minTrades || 10;
            document.getElementById('minWinRate').value = managementConfig.minWinRate || 65;
            document.getElementById('minProfit').value = managementConfig.minProfit || 0;
            document.getElementById('maxDrawdown').value = managementConfig.maxDrawdown || 10;
            document.getElementById('minSharpeRatio').value = managementConfig.minSharpeRatio || 1.0;
            document.getElementById('maxPositionSize').value = managementConfig.maxPositionSize || 100;
            document.getElementById('stopLossPercent').value = managementConfig.stopLossPercent || 5;
            document.getElementById('takeProfitPercent').value = managementConfig.takeProfitPercent || 4;
            document.getElementById('maxHoldingMinutes').value = managementConfig.maxHoldingMinutes || 30;
            document.getElementById('minProfitForTimeStop').value = managementConfig.minProfitForTimeStop || 1;
            document.getElementById('eliminationDays').value = managementConfig.eliminationDays || 7;
            document.getElementById('minScore').value = managementConfig.minScore || 50;
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
                evolutionInterval: parseInt(document.getElementById('evolutionInterval').value) || 10,
                maxStrategies: parseInt(document.getElementById('maxStrategies').value) || 20,
                realTradingScore: parseFloat(document.getElementById('realTradingScore').value) || 65,
                realTradingCount: parseInt(document.getElementById('realTradingCount').value) || 2,
                validationAmount: parseFloat(document.getElementById('validationAmount').value) || 50,
                realTradingAmount: parseFloat(document.getElementById('realTradingAmount').value) || 100,
                minTrades: parseInt(document.getElementById('minTrades').value) || 10,
                minWinRate: parseFloat(document.getElementById('minWinRate').value) || 65,
                minProfit: parseFloat(document.getElementById('minProfit').value) || 0,
                maxDrawdown: parseFloat(document.getElementById('maxDrawdown').value) || 10,
                minSharpeRatio: parseFloat(document.getElementById('minSharpeRatio').value) || 1.0,
                maxPositionSize: parseFloat(document.getElementById('maxPositionSize').value) || 100,
                stopLossPercent: parseFloat(document.getElementById('stopLossPercent').value) || 5,
                takeProfitPercent: parseFloat(document.getElementById('takeProfitPercent').value) || 4,
                maxHoldingMinutes: parseInt(document.getElementById('maxHoldingMinutes').value) || 30,
                minProfitForTimeStop: parseFloat(document.getElementById('minProfitForTimeStop').value) || 1,
                eliminationDays: parseInt(document.getElementById('eliminationDays').value) || 7,
                minScore: parseFloat(document.getElementById('minScore').value) || 50
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
            evolutionInterval: 10,
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
            minScore: 50
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
                
                // 更新状态统计（增加null检查）
                this.safeSetText('currentActiveStrategies', status.current_active_strategies || 0);
                this.safeSetText('realTradingStrategiesCount', status.real_trading_strategies || 0);
                this.safeSetText('validationStrategiesCount', status.validation_strategies || 0);
                this.safeSetText('totalStrategiesCount', status.total_strategies || 0);
                
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
    
    // 初始化进化日志
    initEvolutionLog() {
        this.startEvolutionLogPolling();
        
        // 绑定管理配置事件
        this.bindManagementEvents();
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

    // 渲染进化日志 - 使用增强渲染器
    renderEvolutionLog(logs) {
        // 保存所有日志到全局变量供全部日志页面使用
        this.allEvolutionLogs = logs || [];
        
        // 🔥 使用新的增强渲染器
        if (this.evolutionRenderer) {
            this.evolutionRenderer.renderEvolutionLog(logs);
        } else {
            // 降级处理
            const ticker = document.getElementById('evolutionTicker');
            if (ticker) {
                ticker.innerHTML = '<div class="ticker-item"><span class="text-muted">加载中...</span></div>';
            }
        }
    }
    
    // 🔥 新增：更新策略数据方法（供WebSocket调用）
    updateStrategyData(data) {
        if (data && data.strategy_id) {
            // 更新对应策略的数据
            const strategyIndex = this.strategies.findIndex(s => s.id === data.strategy_id);
            if (strategyIndex !== -1) {
                this.strategies[strategyIndex] = { ...this.strategies[strategyIndex], ...data };
                this.renderStrategies(); // 重新渲染策略列表
            }
        }
    }
}

// 🔥 移除重复的全局函数定义，这些函数已在HTML模板中定义，避免冲突 