// 全局变量
let currentSymbol = "BTC/USDT";
let isMonitoring = false;
let updateInterval = null;
let lastUpdateTime = null;

// DOM 元素
const statusIndicator = document.getElementById('status-indicator');
const modeIndicator = document.getElementById('mode-indicator');
const lastUpdateEl = document.getElementById('last-update');
const serverTimeEl = document.getElementById('server-time');
const startButton = document.getElementById('start-btn');
const stopButton = document.getElementById('stop-btn');
const priceDataTable = document.getElementById('price-data');
const arbitrageDataTable = document.getElementById('arbitrage-data');
const operationLogs = document.getElementById('operation-logs');

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化界面
    setupEventListeners();
    updateServerTime();
    
    // 初始化下拉框默认值
    // 交易对选择功能已移除
    
    // 启动自动监控
    startMonitoring();
});

// 设置事件监听器
function setupEventListeners() {
// 交易对选择功能已移除
    
    // 开始/停止监控按钮
    document.getElementById('start-btn').addEventListener('click', startMonitoring);
    document.getElementById('stop-btn').addEventListener('click', stopMonitoring);
}

// 开始监控
function startMonitoring() {
    if (isMonitoring) return;
    
    isMonitoring = true;
    document.getElementById('status-indicator').classList.remove('bg-warning');
    document.getElementById('status-indicator').classList.add('bg-success');
    document.getElementById('status-indicator').textContent = '运行中';
    
    // 立即获取数据
    fetchPriceData();
    fetchArbitrageData();
    fetchBalanceData();
    
    // 设置定时刷新（每5秒）
    updateInterval = setInterval(function() {
        fetchPriceData();
        fetchArbitrageData();
        updateServerTime();
        
        // 每分钟更新余额数据
        if (new Date().getSeconds() < 5) {
            fetchBalanceData();
        }
    }, 5000);
    
    // 添加日志
    addLog('INFO', '开始监控市场数据');
}

// 停止监控
function stopMonitoring() {
    if (!isMonitoring) return;
    
    isMonitoring = false;
    clearInterval(updateInterval);
    document.getElementById('status-indicator').classList.remove('bg-success');
    document.getElementById('status-indicator').classList.add('bg-warning');
    document.getElementById('status-indicator').textContent = '已停止';
    
    // 添加日志
    addLog('INFO', '停止监控市场数据');
}

// 获取价格数据
function fetchPriceData() {
    // 获取状态信息
    fetch('/api/status')
        .then(response => response.json())
        .then(statusData => {
            lastUpdateTime = statusData.last_update;
            document.getElementById('last-update').textContent = lastUpdateTime;
            
            // 检查模式
            const modeIndicator = document.getElementById('mode-indicator');
            if (statusData.mode === 'simulate') {
                modeIndicator.textContent = '模拟模式';
                modeIndicator.classList.remove('bg-primary');
                modeIndicator.classList.add('bg-info');
            } else {
                modeIndicator.textContent = '实盘模式';
                modeIndicator.classList.remove('bg-info');
                modeIndicator.classList.add('bg-primary');
            }
            
            // 获取价格数据
            fetch('/api/prices')
                .then(response => response.json())
                .then(pricesData => {
                    // 更新价格表格
                    updatePriceTable(pricesData);
                })
                .catch(error => {
                    console.error('获取价格数据失败:', error);
                    addLog('ERROR', '获取价格数据失败: ' + error.message);
                });
        })
        .catch(error => {
            console.error('获取状态数据失败:', error);
            addLog('ERROR', '获取状态数据失败: ' + error.message);
        });
}

// 更新价格表格
function updatePriceTable(pricesData) {
    const tbody = document.getElementById('price-data');
    tbody.innerHTML = '';
    
    // 遍历所有交易对
    for (const symbol of SYMBOLS) {
        // 提取币种名称（移除/USDT部分）
        const coin = symbol.split('/')[0];
        
        // 检查是否有数据
        const binancePrice = pricesData.binance && pricesData.binance[symbol];
        const okxPrice = pricesData.okx && pricesData.okx[symbol];
        const bitgetPrice = pricesData.bitget && pricesData.bitget[symbol];
        
        // 即使没有数据也显示行
        
        // 计算最大差价
        let maxDiffPct = 0;
        if (binancePrice && okxPrice) {
            const diff1 = Math.abs(binancePrice.sell / okxPrice.buy - 1) * 100;
            const diff2 = Math.abs(okxPrice.sell / binancePrice.buy - 1) * 100;
            maxDiffPct = Math.max(maxDiffPct, diff1, diff2);
        }
        if (binancePrice && bitgetPrice) {
            const diff1 = Math.abs(binancePrice.sell / bitgetPrice.buy - 1) * 100;
            const diff2 = Math.abs(bitgetPrice.sell / binancePrice.buy - 1) * 100;
            maxDiffPct = Math.max(maxDiffPct, diff1, diff2);
        }
        if (okxPrice && bitgetPrice) {
            const diff1 = Math.abs(okxPrice.sell / bitgetPrice.buy - 1) * 100;
            const diff2 = Math.abs(bitgetPrice.sell / okxPrice.buy - 1) * 100;
            maxDiffPct = Math.max(maxDiffPct, diff1, diff2);
        }
        
        // 计算最大深度 (深度数据移动到套利机会表中显示)
        let maxDepth = 0;
        if (binancePrice && binancePrice.depth) {
            const bidDepth = binancePrice.depth.bid || 0;
            const askDepth = binancePrice.depth.ask || 0;
            maxDepth = Math.max(maxDepth, bidDepth + askDepth);
        }
        if (okxPrice && okxPrice.depth) {
            const bidDepth = okxPrice.depth.bid || 0;
            const askDepth = okxPrice.depth.ask || 0;
            maxDepth = Math.max(maxDepth, bidDepth + askDepth);
        }
        if (bitgetPrice && bitgetPrice.depth) {
            const bidDepth = bitgetPrice.depth.bid || 0;
            const askDepth = bitgetPrice.depth.ask || 0;
            maxDepth = Math.max(maxDepth, bidDepth + askDepth);
        }
        
        // 创建表格行
        const tr = document.createElement('tr');
        
        // 高亮当前选中交易对
        if (symbol === currentSymbol) {
            tr.classList.add('table-primary');
        }
        
        // 添加差价警告样式 (增加差价阈值到0.5%)
        if (maxDiffPct > 0.5) {
            tr.classList.add('table-success');
        }
        
        tr.innerHTML = `
            <td class="text-center"><strong>${coin}</strong></td>
            <td class="text-end">${binancePrice ? formatPrice(binancePrice.buy) : '-'}</td>
            <td class="text-end">${okxPrice ? formatPrice(okxPrice.buy) : '-'}</td>
            <td class="text-end">${bitgetPrice ? formatPrice(bitgetPrice.buy) : '-'}</td>
            <td class="text-end">${maxDiffPct > 0 ? formatPercentage(maxDiffPct) : '-'}</td>
        `;
        
        tbody.appendChild(tr);
    }
}

// 更新套利表格
function updateArbitrageTable(opportunities) {
    const arbitrageTable = document.getElementById('arbitrage-data');
    arbitrageTable.innerHTML = '';
    
    if (!opportunities || opportunities.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="9" class="text-center">当前无套利机会</td>';
        arbitrageTable.appendChild(row);
        return;
    }
    
    // 添加前5个最佳机会
    const topOpportunities = opportunities.slice(0, 5);
    
    for (const opp of topOpportunities) {
        // 提取币种名称（移除/USDT部分）
        const coin = opp.symbol.split('/')[0];
        
        // 计算深度
        let depth = 0;
        // 尝试获取买入交易所的深度
        if (opp.buy_depth) {
            depth = opp.buy_depth;
        } else {
            // 后端可能没有直接提供深度数据，使用默认值
            depth = 0;
        }
        
        // 创建行
        const row = document.createElement('tr');
        
        // 添加价差警告样式
        if (opp.price_diff_pct >= 0.01) {
            row.classList.add('table-success');
        }
        
        // 格式化买入/卖出交易所名称（缩短显示）
        const buyExchange = formatExchangeName(opp.buy_exchange);
        const sellExchange = formatExchangeName(opp.sell_exchange);
        
        row.innerHTML = `
            <td class="text-center">${coin}</td>
            <td class="text-center">${buyExchange}</td>
            <td class="text-center">${sellExchange}</td>
            <td class="text-end">${formatPrice(opp.buy_price)}</td>
            <td class="text-end">${formatPrice(opp.sell_price)}</td>
            <td class="text-end">${formatDepth(depth)}</td>
            <td class="text-end">${formatPrice(opp.price_diff)}</td>
            <td class="text-end">${formatPercentage(opp.price_diff_pct)}</td>
            <td class="text-center">${opp.is_executable ? '<span class="badge bg-success">可执行</span>' : '<span class="badge bg-secondary">不可执行</span>'}</td>
        `;
        
        arbitrageTable.appendChild(row);
    }
}

// 获取套利数据
function fetchArbitrageData() {
    fetch('/api/diff')
        .then(response => response.json())
        .then(data => {
            updateArbitrageTable(data);
        })
        .catch(error => {
            console.error('获取套利数据失败:', error);
        });
}

// 获取余额数据
function fetchBalanceData() {
    fetch('/api/balances')
        .then(response => response.json())
        .then(data => {
            // 更新Binance余额
            updateExchangeBalance('binance', data.binance);
            // 更新OKX余额
            updateExchangeBalance('okx', data.okx);
            // 更新Bitget余额
            updateExchangeBalance('bitget', data.bitget);
        })
        .catch(error => {
            console.error('获取余额数据失败:', error);
        });
}

// 更新交易所余额信息
function updateExchangeBalance(exchange, balanceData) {
    // 获取相关元素
    const balanceEl = document.getElementById(`${exchange}-balance`);
    const availableEl = document.getElementById(`${exchange}-available`);
    const lockedEl = document.getElementById(`${exchange}-locked`);
    const positionsTable = document.getElementById(`${exchange}-positions`);
    
    if (!balanceData) {
        return;
    }
    
    // 更新USDT余额数据
    if (balanceEl) balanceEl.textContent = formatNumber(balanceData.USDT || 0);
    if (availableEl) availableEl.textContent = formatNumber(balanceData.USDT_available || 0);
    if (lockedEl) lockedEl.textContent = formatNumber(balanceData.USDT_locked || 0);
    
    // 更新持仓数据
    if (positionsTable) {
        positionsTable.innerHTML = '';
        
        // 检查是否有持仓
        if (!balanceData.positions || Object.keys(balanceData.positions).length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="5" class="text-center">无持仓</td>';
            positionsTable.appendChild(tr);
            return;
        }
        
        // 添加持仓数据
        for (const [coin, position] of Object.entries(balanceData.positions)) {
            if (position.amount > 0) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${coin}</td>
                    <td>${formatNumber(position.amount, 2)}</td>
                    <td>${formatNumber(position.available, 2)}</td>
                    <td>${formatNumber(position.locked, 2)}</td>
                    <td>${formatNumber(position.value, 2)}</td>
                `;
                positionsTable.appendChild(tr);
            }
        }
    }
}

// 更新服务器时间
function updateServerTime() {
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }).replace(/\//g, '-');
    
    document.getElementById('server-time').textContent = timeString;
}

// 添加操作日志
function addLog(level, message) {
    const logs = document.getElementById('operation-logs');
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }).replace(/\//g, '-');
    
    const li = document.createElement('li');
    li.className = 'list-group-item';
    
    let badgeClass = 'bg-info';
    if (level === 'ERROR') badgeClass = 'bg-danger';
    else if (level === 'WARNING') badgeClass = 'bg-warning';
    else if (level === 'SUCCESS') badgeClass = 'bg-success';
    else if (level === 'ARBITRAGE') badgeClass = 'bg-primary';
    
    li.innerHTML = `
        <span class="text-muted">[${timeString}]</span> 
        <span class="badge ${badgeClass}">${level}</span> 
        ${message}
    `;
    
    // 添加到顶部
    logs.insertBefore(li, logs.firstChild);
    
    // 限制日志条数
    if (logs.children.length > 50) {
        logs.removeChild(logs.lastChild);
    }
}

// 格式化交易所名称
function formatExchangeName(exchange) {
    const names = {
        'binance': 'Binance',
        'okex': 'OKX',
        'okx': 'OKX',
        'bitget': 'Bitget'
    };
    return names[exchange] || exchange;
}

// 格式化价格数字
function formatPrice(price) {
    if (price === undefined || price === null) return '-';
    
    // 根据价格大小调整精度
    let precision = 2;
    if (price < 0.01) precision = 6;
    else if (price < 1) precision = 4;
    else if (price < 10) precision = 3;
    else if (price >= 10000) precision = 0;
    
    return price.toLocaleString('en-US', {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision
    });
}

// 格式化百分比
function formatPercentage(value) {
    if (value === undefined || value === null) return '-';
    return value.toFixed(3) + '%';
}

// 格式化深度
function formatDepth(depth) {
    if (depth === undefined || depth === null) return '-';
    return depth.toFixed(2);
}

// 格式化普通数字
function formatNumber(num, precision = 2) {
    if (num === undefined || num === null) return '-';
    return num.toLocaleString('en-US', {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision
    });
}

// 交易对列表
const SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
    "ADA/USDT", "DOT/USDT", "AVAX/USDT", "SHIB/USDT"
];

