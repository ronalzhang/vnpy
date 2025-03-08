// 全局变量
let currentSymbol = 'BTC/USDT';
let isMonitoring = true;
let isSimulateMode = true;
let refreshInterval = null;
let lastPrices = {};

// DOM 元素
const statusIndicator = document.getElementById('status-indicator');
const modeIndicator = document.getElementById('mode-indicator');
const lastUpdateEl = document.getElementById('last-update');
const serverTimeEl = document.getElementById('server-time');
const startButton = document.getElementById('start-btn');
const stopButton = document.getElementById('stop-btn');
const symbolSelect = document.getElementById('symbol-select');
const priceDataTable = document.getElementById('price-data');
const arbitrageDataTable = document.getElementById('arbitrage-data');
const operationLogs = document.getElementById('operation-logs');

// 初始化函数
function init() {
    // 注册事件监听器
    startButton.addEventListener('click', startMonitoring);
    stopButton.addEventListener('click', stopMonitoring);
    symbolSelect.addEventListener('change', handleSymbolChange);
    
    // 启动数据刷新
    startDataRefresh();
    
    // 更新服务器时间
    updateServerTime();
    
    // 初始状态设置
    updateStatus();
}

// 开始监控
function startMonitoring() {
    if (!isMonitoring) {
        isMonitoring = true;
        updateStatus();
        startDataRefresh();
        
        // 通过API启动监控
        fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                simulate: isSimulateMode
            })
        })
        .then(response => response.json())
        .then(data => {
            addLog('INFO', '监控已启动');
        })
        .catch(error => {
            addLog('ERROR', '启动监控失败: ' + error);
        });
    }
}

// 停止监控
function stopMonitoring() {
    if (isMonitoring) {
        isMonitoring = false;
        updateStatus();
        stopDataRefresh();
        
        // 通过API停止监控
        fetch('/api/stop', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            addLog('INFO', '监控已停止');
        })
        .catch(error => {
            addLog('ERROR', '停止监控失败: ' + error);
        });
    }
}

// 切换交易对
function handleSymbolChange(event) {
    currentSymbol = event.target.value;
    fetchPriceData();
    addLog('INFO', `已切换到 ${currentSymbol}`);
}

// 开始数据刷新
function startDataRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    fetchPriceData();
    refreshInterval = setInterval(() => {
        fetchPriceData();
        updateServerTime();
    }, 5000); // 每5秒刷新一次
}

// 停止数据刷新
function stopDataRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// 更新系统状态显示
function updateStatus() {
    if (isMonitoring) {
        statusIndicator.textContent = '运行中';
        statusIndicator.className = 'badge bg-success';
        startButton.disabled = true;
        stopButton.disabled = false;
    } else {
        statusIndicator.textContent = '已停止';
        statusIndicator.className = 'badge bg-secondary';
        startButton.disabled = false;
        stopButton.disabled = true;
    }
    
    modeIndicator.textContent = isSimulateMode ? '模拟模式' : '真实模式';
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
    });
    serverTimeEl.textContent = timeString;
    lastUpdateEl.textContent = timeString;
}

// 获取价格数据
function fetchPriceData() {
    if (!isMonitoring) return;
    
    fetch('/api/prices')
        .then(response => response.json())
        .then(data => {
            updatePriceTable(data);
            calculateArbitrage(data);
            updateLastPrices(data);
        })
        .catch(error => {
            addLog('ERROR', '获取价格数据失败: ' + error);
        });
}

// 更新价格表格
function updatePriceTable(data) {
    if (!data) return;
    
    const exchanges = Object.keys(data);
    priceDataTable.innerHTML = '';
    
    exchanges.forEach(exchange => {
        const symbolData = data[exchange][currentSymbol];
        if (!symbolData) return;
        
        const row = document.createElement('tr');
        
        // 生成随机买卖价和交易量 (实际项目中会使用真实数据)
        const bid = typeof symbolData === 'object' ? symbolData.bid : symbolData * 0.9995;
        const ask = typeof symbolData === 'object' ? symbolData.ask : symbolData * 1.0005;
        const volume = Math.round(Math.random() * 5000 + 1000) / 10;
        const depth = {
            bid: (Math.random() * 10 + 5).toFixed(1),
            ask: (Math.random() * 8 + 3).toFixed(1)
        };
        
        // 检查价格变化，添加上涨/下跌颜色
        let bidClass = '';
        let askClass = '';
        if (lastPrices[exchange] && lastPrices[exchange][currentSymbol]) {
            const lastBid = lastPrices[exchange][currentSymbol].bid || 0;
            const lastAsk = lastPrices[exchange][currentSymbol].ask || 0;
            
            bidClass = bid > lastBid ? 'price-up' : bid < lastBid ? 'price-down' : '';
            askClass = ask > lastAsk ? 'price-up' : ask < lastAsk ? 'price-down' : '';
        }
        
        row.innerHTML = `
            <td>${exchange}</td>
            <td class="${bidClass}">${formatNumber(bid)}</td>
            <td class="${askClass}">${formatNumber(ask)}</td>
            <td>${volume} ${currentSymbol.split('/')[0]}</td>
            <td>${depth.bid} / ${depth.ask} ${currentSymbol.split('/')[0]}</td>
        `;
        
        priceDataTable.appendChild(row);
    });
}

// 计算套利机会
function calculateArbitrage(data) {
    if (!data) return;
    
    const exchanges = Object.keys(data);
    const arbitrageOpportunities = [];
    
    // 计算所有可能的交易所对
    for (let i = 0; i < exchanges.length; i++) {
        for (let j = 0; j < exchanges.length; j++) {
            if (i === j) continue;
            
            const buyExchange = exchanges[i];
            const sellExchange = exchanges[j];
            
            const buyPrice = typeof data[buyExchange][currentSymbol] === 'object' 
                ? data[buyExchange][currentSymbol].ask 
                : data[buyExchange][currentSymbol] * 1.0005;
                
            const sellPrice = typeof data[sellExchange][currentSymbol] === 'object' 
                ? data[sellExchange][currentSymbol].bid 
                : data[sellExchange][currentSymbol] * 0.9995;
            
            if (sellPrice > buyPrice) {
                const priceDiff = sellPrice - buyPrice;
                const priceDiffPct = (priceDiff / buyPrice) * 100;
                
                // 只显示价差大于0.1%的机会
                if (priceDiffPct > 0.1) {
                    arbitrageOpportunities.push({
                        buyExchange,
                        sellExchange,
                        buyPrice,
                        sellPrice,
                        priceDiff,
                        priceDiffPct,
                        isExecutable: priceDiffPct > 0.2 // 假设差价大于0.2%才可执行
                    });
                }
            }
        }
    }
    
    // 按价差百分比降序排序
    arbitrageOpportunities.sort((a, b) => b.priceDiffPct - a.priceDiffPct);
    
    // 更新UI
    updateArbitrageTable(arbitrageOpportunities);
    
    // 记录新的套利机会
    const significantOpportunities = arbitrageOpportunities.filter(opp => opp.priceDiffPct > 0.2);
    if (significantOpportunities.length > 0) {
        const topOpp = significantOpportunities[0];
        addLog('ARBITRAGE', `发现套利机会: ${currentSymbol} ${topOpp.buyExchange}(${formatNumber(topOpp.buyPrice)}) → ${topOpp.sellExchange}(${formatNumber(topOpp.sellPrice)}), 差价: ${formatNumber(topOpp.priceDiff)} (${topOpp.priceDiffPct.toFixed(2)}%)`);
    }
}

// 更新套利表格
function updateArbitrageTable(opportunities) {
    arbitrageDataTable.innerHTML = '';
    
    if (opportunities.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="7" class="text-center">当前没有套利机会</td>`;
        arbitrageDataTable.appendChild(row);
        return;
    }
    
    // 显示前3个最佳机会
    const displayOpps = opportunities.slice(0, 3);
    
    displayOpps.forEach(opp => {
        const row = document.createElement('tr');
        if (opp.isExecutable) {
            row.classList.add('table-success');
        } else if (opp.priceDiffPct < 0.15) {
            row.classList.add('text-muted');
        }
        
        row.innerHTML = `
            <td>${opp.buyExchange}</td>
            <td>${opp.sellExchange}</td>
            <td>${formatNumber(opp.buyPrice)}</td>
            <td>${formatNumber(opp.sellPrice)}</td>
            <td>${formatNumber(opp.priceDiff)}</td>
            <td>${opp.priceDiffPct.toFixed(2)}%</td>
            <td>${opp.isExecutable 
                ? '<i class="fas fa-check-circle text-success"></i>' 
                : '<i class="fas fa-times-circle text-danger"></i>'}</td>
        `;
        
        arbitrageDataTable.appendChild(row);
    });
}

// 更新历史价格记录
function updateLastPrices(data) {
    // 深拷贝当前价格数据
    lastPrices = JSON.parse(JSON.stringify(data));
}

// 添加日志
function addLog(level, message) {
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    
    let badgeClass = 'bg-info';
    switch (level) {
        case 'ERROR':
            badgeClass = 'bg-danger';
            break;
        case 'WARNING':
            badgeClass = 'bg-warning';
            break;
        case 'ARBITRAGE':
            badgeClass = 'bg-success';
            break;
        case 'SUCCESS':
            badgeClass = 'bg-success';
            break;
    }
    
    const logItem = document.createElement('li');
    logItem.className = 'list-group-item';
    logItem.innerHTML = `
        <span class="text-muted">[${timeString}]</span> 
        <span class="badge ${badgeClass}">${level}</span> 
        ${message}
    `;
    
    operationLogs.prepend(logItem);
    
    // 限制日志条数
    if (operationLogs.children.length > 50) {
        operationLogs.removeChild(operationLogs.lastChild);
    }
}

// 格式化数字
function formatNumber(num) {
    return num.toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', init);
