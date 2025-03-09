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
    
    // 计算套利机会
    const arbitrageOpps = findArbitrageOpportunities(pricesData);
    window.currentArbitrageOpps = arbitrageOpps; // 保存当前套利机会供其他函数使用

    // 更新套利机会表格
    updateArbitrageTable(arbitrageOpps);
    
    // 遍历所有交易对
    for (const symbol of SYMBOLS) {
        // 提取币种名称（移除/USDT部分）
        const coin = symbol.split('/')[0];
        
        // 检查是否有数据
        const binancePrice = pricesData.binance && pricesData.binance[symbol];
        const okxPrice = pricesData.okx && pricesData.okx[symbol];
        const bitgetPrice = pricesData.bitget && pricesData.bitget[symbol];
        
        // 查找当前交易对的最高净利润
        let maxNetProfitPct = 0;
        for (const opp of arbitrageOpps) {
            if (opp.symbol === symbol && opp.netProfitPct > maxNetProfitPct) {
                maxNetProfitPct = opp.netProfitPct;
            }
        }
        
        // 创建表格行
        const tr = document.createElement('tr');
        
        // 高亮当前选中交易对
        if (symbol === currentSymbol) {
            tr.classList.add('table-primary');
        }
        
        // 添加套利机会警告样式
        if (maxNetProfitPct > 0) {
            tr.classList.add('table-success');
        }
        
        tr.innerHTML = `
            <td class="text-center"><strong>${coin}</strong></td>
            <td class="text-end">${binancePrice ? formatPrice(binancePrice.buy) : '-'}</td>
            <td class="text-end">${okxPrice ? formatPrice(okxPrice.buy) : '-'}</td>
            <td class="text-end">${bitgetPrice ? formatPrice(bitgetPrice.buy) : '-'}</td>
            <td class="text-end">${maxNetProfitPct > 0 ? formatPercentage(maxNetProfitPct) : '-'}</td>
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
        
        // 更新系统状态中的套利机会数量
        updateArbitrageStatus(0);
        return;
    }
    
    // 添加前5个最佳机会
    const topOpportunities = opportunities.slice(0, 5);
    
    for (const opp of topOpportunities) {
        // 提取币种名称（移除/USDT部分）
        const coin = opp.symbol.split('/')[0];
        
        // 创建行
        const row = document.createElement('tr');
        
        // 添加净利润警告样式
        if (opp.netProfitPct >= 0.1) { // 大于0.1%的净利润显示为绿色
            row.classList.add('table-success');
        }
        
        // 格式化买入/卖出交易所名称（缩短显示）
        const buyExchange = formatExchangeName(opp.buyExchange);
        const sellExchange = formatExchangeName(opp.sellExchange);
        
        row.innerHTML = `
            <td class="text-center">${coin}</td>
            <td class="text-center">${buyExchange}</td>
            <td class="text-center">${sellExchange}</td>
            <td class="text-end">${formatPrice(opp.buyPrice)}</td>
            <td class="text-end">${formatPrice(opp.sellPrice)}</td>
            <td class="text-end">${formatDepth(opp.depth)}</td>
            <td class="text-end">${formatPrice(opp.priceDiff)}</td>
            <td class="text-end">${formatPercentage(opp.netProfitPct)}</td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-primary execute-arbitrage" 
                    data-symbol="${opp.symbol}" 
                    data-buy-exchange="${opp.buyExchange}" 
                    data-sell-exchange="${opp.sellExchange}">
                    执行
                </button>
            </td>
        `;
        
        arbitrageTable.appendChild(row);
    }
    
    // 绑定执行按钮事件
    document.querySelectorAll('.execute-arbitrage').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            const buyExchange = this.getAttribute('data-buy-exchange');
            const sellExchange = this.getAttribute('data-sell-exchange');
            executeArbitrage(symbol, buyExchange, sellExchange);
        });
    });
    
    // 更新系统状态中的套利机会数量
    updateArbitrageStatus(opportunities.length);
    
    // 如果有高利润的套利机会，添加日志提醒
    if (opportunities.length > 0 && opportunities[0].netProfitPct >= 0.2) {
        const opp = opportunities[0];
        addLog('ARBITRAGE', `高利润套利机会: ${opp.symbol} 从${formatExchangeName(opp.buyExchange)}买入(${formatPrice(opp.buyPrice)})，在${formatExchangeName(opp.sellExchange)}卖出(${formatPrice(opp.sellPrice)})，净利润: ${formatPercentage(opp.netProfitPct)}`);
    }
}

// 更新套利状态信息
function updateArbitrageStatus(count) {
    const statusIndicator = document.getElementById('arbitrage-count');
    if (statusIndicator) {
        statusIndicator.textContent = count;
        
        if (count > 0) {
            statusIndicator.classList.remove('bg-secondary');
            statusIndicator.classList.add('bg-success');
        } else {
            statusIndicator.classList.remove('bg-success');
            statusIndicator.classList.add('bg-secondary');
        }
    }
}

// 获取套利数据 - 不再单独请求套利数据，而是从价格数据中计算
function fetchArbitrageData() {
    // 这个函数现在留空，套利计算在updatePriceTable中进行
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
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    
    let badge;
    switch(level.toUpperCase()) {
        case 'INFO': badge = '<span class="badge bg-info">INFO</span>'; break;
        case 'WARNING': badge = '<span class="badge bg-warning">警告</span>'; break;
        case 'ERROR': badge = '<span class="badge bg-danger">错误</span>'; break;
        case 'SUCCESS': badge = '<span class="badge bg-success">成功</span>'; break;
        case 'ARBITRAGE': badge = '<span class="badge bg-primary">套利</span>'; break;
        default: badge = `<span class="badge bg-secondary">${level}</span>`;
    }
    
    const logItem = document.createElement('li');
    logItem.className = 'list-group-item';
    logItem.innerHTML = `
        <span class="text-muted">[${timeString}]</span> 
        ${badge} 
        ${message}
    `;
    
    const logContainer = document.getElementById('operation-logs');
    if (logContainer) {
        logContainer.prepend(logItem);
        
        // 限制日志数量，保持性能
        const maxLogs = 50;
        while (logContainer.children.length > maxLogs) {
            logContainer.removeChild(logContainer.lastChild);
        }
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

// 交易所列表
const EXCHANGES = ["binance", "okx", "bitget"];

// 交易所手续费率 (百分比)
const EXCHANGE_FEES = {
    "binance": 0.1,
    "okx": 0.1,
    "bitget": 0.1
};

// 识别套利机会
function findArbitrageOpportunities(pricesData) {
    let opportunities = [];
    
    // 遍历所有交易对
    for (const symbol of SYMBOLS) {
        // 遍历所有交易所组合
        for (const buyExchange of EXCHANGES) {
            if (!pricesData[buyExchange] || !pricesData[buyExchange][symbol]) continue;
            
            // 获取买入交易所的卖1价格(我们要花这个价格买入)
            const buyPrice = pricesData[buyExchange][symbol].sell;
            if (!buyPrice) continue;
            
            for (const sellExchange of EXCHANGES) {
                if (buyExchange === sellExchange) continue;
                if (!pricesData[sellExchange] || !pricesData[sellExchange][symbol]) continue;
                
                // 获取卖出交易所的买1价格(我们能以这个价格卖出)
                const sellPrice = pricesData[sellExchange][symbol].buy;
                if (!sellPrice) continue;
                
                // 只有当卖出价高于买入价时才存在套利机会
                if (sellPrice > buyPrice) {
                    const priceDiff = sellPrice - buyPrice;
                    const priceDiffPct = (priceDiff / buyPrice) * 100;
                    
                    // 计算净利润(扣除费用)
                    const buyFee = buyPrice * (EXCHANGE_FEES[buyExchange] / 100); // 买入手续费
                    const sellFee = sellPrice * (EXCHANGE_FEES[sellExchange] / 100); // 卖出手续费
                    const netProfit = priceDiff - buyFee - sellFee;
                    const netProfitPct = (netProfit / buyPrice) * 100;
                    
                    // 计算深度 (取两个交易所中较小的深度)
                    let depth = 0;
                    if (pricesData[buyExchange][symbol].depth && pricesData[sellExchange][symbol].depth) {
                        const buyDepth = pricesData[buyExchange][symbol].depth.ask || 0;
                        const sellDepth = pricesData[sellExchange][symbol].depth.bid || 0;
                        depth = Math.min(buyDepth, sellDepth);
                    }
                    
                    // 只保留净利润为正的套利机会
                    if (netProfit > 0) {
                        opportunities.push({
                            symbol,
                            buyExchange,
                            sellExchange,
                            buyPrice,
                            sellPrice,
                            priceDiff,
                            priceDiffPct,
                            netProfit,
                            netProfitPct,
                            depth,
                            executable: true,
                            timestamp: new Date().toISOString()
                        });
                    }
                }
            }
        }
    }
    
    // 按净利润百分比排序 (从高到低)
    opportunities.sort((a, b) => b.netProfitPct - a.netProfitPct);
    
    return opportunities;
}

// 执行套利操作
function executeArbitrage(symbol, buyExchange, sellExchange) {
    // 查找匹配的套利机会
    const opportunity = window.currentArbitrageOpps.find(opp => 
        opp.symbol === symbol && 
        opp.buyExchange === buyExchange && 
        opp.sellExchange === sellExchange
    );
    
    if (!opportunity) {
        addLog('ERROR', `未找到套利机会: ${symbol} ${buyExchange} → ${sellExchange}`);
        return;
    }
    
    // 检查资金分布情况
    checkFundDistribution(opportunity, showArbitrageModal);
}

// 检查资金分布情况
function checkFundDistribution(opportunity, callback) {
    const { symbol, buyExchange, buyPrice } = opportunity;
    const baseCurrency = symbol.split('/')[0]; // 基础货币 (如BTC)
    const quoteCurrency = symbol.split('/')[1]; // 计价货币 (如USDT)
    
    // 获取买入交易所的余额
    const buyExchangeBalance = balances_data[buyExchange];
    
    if (!buyExchangeBalance) {
        addLog('ERROR', `无法获取${formatExchangeName(buyExchange)}的余额信息`);
        return;
    }
    
    // 检查买入交易所是否有足够的USDT
    const availableUSDT = buyExchangeBalance.USDT_available || 0;
    
    // 假设需要交易的金额是1000USDT
    const requiredUSDT = 1000;
    
    // 如果买入交易所有足够资金，可以直接执行
    if (availableUSDT >= requiredUSDT) {
        addLog('INFO', `${formatExchangeName(buyExchange)}有足够资金(${formatNumber(availableUSDT)} USDT)，可直接执行套利`);
        
        if (callback) callback(opportunity, {
            sufficient: true,
            availableUSDT: availableUSDT,
            requiredUSDT: requiredUSDT
        });
    } else {
        // 否则，需要提示用户转移资金
        addLog('WARNING', `${formatExchangeName(buyExchange)}资金不足，需要转移${formatNumber(requiredUSDT - availableUSDT)} USDT`);
        
        // 找出有足够资金的交易所
        const sourcesWithFunds = [];
        for (const exchange of EXCHANGES) {
            if (exchange === buyExchange) continue;
            
            const exchangeBalance = balances_data[exchange];
            if (exchangeBalance && exchangeBalance.USDT_available >= requiredUSDT - availableUSDT) {
                sourcesWithFunds.push({
                    exchange,
                    availableUSDT: exchangeBalance.USDT_available
                });
            }
        }
        
        if (callback) callback(opportunity, {
            sufficient: false,
            availableUSDT: availableUSDT,
            requiredUSDT: requiredUSDT,
            sourcesWithFunds: sourcesWithFunds
        });
    }
}

// 显示套利执行模态框
function showArbitrageModal(opportunity, fundInfo) {
    // 创建模态框HTML
    const modalHTML = createArbitrageModalHTML(opportunity, fundInfo);
    
    // 添加到页面
    if (!document.getElementById('arbitrageModal')) {
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer.firstChild);
    } else {
        document.getElementById('arbitrageModalContent').innerHTML = createArbitrageModalContent(opportunity, fundInfo);
    }
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('arbitrageModal'));
    modal.show();
    
    // 绑定事件
    setupArbitrageModalEvents(opportunity, fundInfo);
}

// 创建套利模态框HTML
function createArbitrageModalHTML(opportunity, fundInfo) {
    return `
    <div class="modal fade" id="arbitrageModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">套利执行 - ${opportunity.symbol}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body" id="arbitrageModalContent">
                    ${createArbitrageModalContent(opportunity, fundInfo)}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="button" class="btn btn-primary" id="executeArbitrageBtn">执行套利</button>
                </div>
            </div>
        </div>
    </div>
    `;
}

// 创建套利模态框内容
function createArbitrageModalContent(opportunity, fundInfo) {
    const { symbol, buyExchange, sellExchange, buyPrice, sellPrice, priceDiff, netProfitPct, depth } = opportunity;
    const coin = symbol.split('/')[0];
    
    // 计算可以购买的数量
    const maxAmount = Math.min(
        fundInfo.availableUSDT / buyPrice, 
        depth || (fundInfo.availableUSDT / buyPrice)
    );
    
    // 预估利润
    const estimatedProfit = maxAmount * priceDiff;
    
    let fundTransferHTML = '';
    
    if (!fundInfo.sufficient) {
        fundTransferHTML = `
        <div class="alert alert-warning">
            <strong>资金不足!</strong> ${formatExchangeName(buyExchange)}中的可用资金(${formatNumber(fundInfo.availableUSDT)} USDT)
            不足以执行此套利。您需要转移至少${formatNumber(fundInfo.requiredUSDT - fundInfo.availableUSDT)} USDT到此交易所。
            
            <div class="mt-2">
                <h6>可选的资金来源:</h6>
                <ul>
        `;
        
        if (fundInfo.sourcesWithFunds && fundInfo.sourcesWithFunds.length > 0) {
            fundInfo.sourcesWithFunds.forEach(source => {
                fundTransferHTML += `
                <li>${formatExchangeName(source.exchange)} - 可用: ${formatNumber(source.availableUSDT)} USDT 
                    <button class="btn btn-sm btn-outline-primary ms-2 transfer-fund-btn" 
                        data-source="${source.exchange}" 
                        data-target="${buyExchange}" 
                        data-amount="${fundInfo.requiredUSDT - fundInfo.availableUSDT}">
                        转移资金
                    </button>
                </li>
                `;
            });
        } else {
            fundTransferHTML += `<li>没有其他交易所有足够的资金</li>`;
        }
        
        fundTransferHTML += `
                </ul>
            </div>
        </div>
        `;
    }
    
    return `
    <div class="arbitrage-details">
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">套利路径</div>
                    <div class="card-body">
                        <p class="lead">
                            <strong>${coin}/USDT</strong>: 
                            在<strong>${formatExchangeName(buyExchange)}</strong>买入 → 
                            在<strong>${formatExchangeName(sellExchange)}</strong>卖出
                        </p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">价格信息</div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">买入价: <strong>${formatPrice(buyPrice)}</strong></div>
                            <div class="col-6">卖出价: <strong>${formatPrice(sellPrice)}</strong></div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-6">价差: <strong>${formatPrice(priceDiff)}</strong></div>
                            <div class="col-6">净利润: <strong class="text-success">${formatPercentage(netProfitPct)}</strong></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        ${fundTransferHTML}
        
        <div class="card mb-3">
            <div class="card-header">交易设置</div>
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-4">
                        <label for="tradeAmount">交易数量 (${coin}):</label>
                        <input type="number" class="form-control" id="tradeAmount" 
                            value="${(maxAmount * 0.9).toFixed(4)}" 
                            max="${maxAmount.toFixed(4)}" 
                            step="0.0001">
                        <small class="text-muted">最大可交易: ${maxAmount.toFixed(4)} ${coin}</small>
                    </div>
                    <div class="col-md-4">
                        <label for="estimatedCost">估计花费 (USDT):</label>
                        <input type="text" class="form-control" id="estimatedCost" readonly>
                    </div>
                    <div class="col-md-4">
                        <label for="estimatedProfit">估计利润 (USDT):</label>
                        <input type="text" class="form-control bg-light text-success" id="estimatedProfit" 
                            value="${formatNumber(estimatedProfit)}" readonly>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">执行步骤</div>
            <div class="card-body">
                <div class="step-container">
                    <div class="step active" id="step1">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <h6>准备资金</h6>
                            <p>确保买入交易所有足够的USDT</p>
                        </div>
                        <div class="step-status"><i class="fas fa-check-circle text-success"></i></div>
                    </div>
                    <div class="step" id="step2">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <h6>买入 ${coin}</h6>
                            <p>在${formatExchangeName(buyExchange)}以${formatPrice(buyPrice)}买入${coin}</p>
                        </div>
                        <div class="step-status"><i class="fas fa-circle text-muted"></i></div>
                    </div>
                    <div class="step" id="step3">
                        <div class="step-number">3</div>
                        <div class="step-content">
                            <h6>卖出 ${coin}</h6>
                            <p>在${formatExchangeName(sellExchange)}以${formatPrice(sellPrice)}卖出${coin}</p>
                        </div>
                        <div class="step-status"><i class="fas fa-circle text-muted"></i></div>
                    </div>
                    <div class="step" id="step4">
                        <div class="step-number">4</div>
                        <div class="step-content">
                            <h6>完成</h6>
                            <p>计算实际利润并记录</p>
                        </div>
                        <div class="step-status"><i class="fas fa-circle text-muted"></i></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `;
}

// 设置套利模态框事件
function setupArbitrageModalEvents(opportunity, fundInfo) {
    // 绑定交易数量变化事件
    const tradeAmountInput = document.getElementById('tradeAmount');
    const estimatedCostInput = document.getElementById('estimatedCost');
    const estimatedProfitInput = document.getElementById('estimatedProfit');
    
    if (tradeAmountInput) {
        tradeAmountInput.addEventListener('input', function() {
            const amount = parseFloat(this.value) || 0;
            const cost = amount * opportunity.buyPrice;
            const profit = amount * opportunity.priceDiff;
            
            estimatedCostInput.value = formatNumber(cost);
            estimatedProfitInput.value = formatNumber(profit);
        });
        
        // 触发一次input事件来初始化显示
        tradeAmountInput.dispatchEvent(new Event('input'));
    }
    
    // 绑定资金转移按钮事件
    document.querySelectorAll('.transfer-fund-btn').forEach(button => {
        button.addEventListener('click', function() {
            const source = this.getAttribute('data-source');
            const target = this.getAttribute('data-target');
            const amount = parseFloat(this.getAttribute('data-amount'));
            
            transferFunds(source, target, amount);
        });
    });
    
    // 绑定执行套利按钮事件
    const executeButton = document.getElementById('executeArbitrageBtn');
    if (executeButton) {
        executeButton.addEventListener('click', function() {
            startArbitrageExecution(opportunity);
        });
    }
}

// 转移资金
function transferFunds(sourceExchange, targetExchange, amount) {
    addLog('INFO', `正在从${formatExchangeName(sourceExchange)}转移${formatNumber(amount)} USDT到${formatExchangeName(targetExchange)}...`);
    
    // 模拟API调用
    setTimeout(() => {
        addLog('SUCCESS', `成功从${formatExchangeName(sourceExchange)}转移${formatNumber(amount)} USDT到${formatExchangeName(targetExchange)}`);
        
        // 更新本地余额数据 (实际应用中应从服务器获取最新数据)
        if (balances_data[sourceExchange]) {
            balances_data[sourceExchange].USDT = (balances_data[sourceExchange].USDT || 0) - amount;
            balances_data[sourceExchange].USDT_available = (balances_data[sourceExchange].USDT_available || 0) - amount;
        }
        
        if (balances_data[targetExchange]) {
            balances_data[targetExchange].USDT = (balances_data[targetExchange].USDT || 0) + amount;
            balances_data[targetExchange].USDT_available = (balances_data[targetExchange].USDT_available || 0) + amount;
        }
        
        // 更新余额显示
        updateExchangeBalance(sourceExchange, balances_data[sourceExchange]);
        updateExchangeBalance(targetExchange, balances_data[targetExchange]);
        
        // 更新模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('arbitrageModal'));
        modal.hide();
        
        // 重新检查资金并显示模态框
        checkFundDistribution(currentArbitrageOpportunity, showArbitrageModal);
    }, 2000);
}

// 开始执行套利
function startArbitrageExecution(opportunity) {
    const tradeAmount = parseFloat(document.getElementById('tradeAmount').value);
    if (!tradeAmount || tradeAmount <= 0) {
        addLog('ERROR', '交易数量必须大于0');
        return;
    }
    
    // 保存当前正在执行的套利机会
    window.currentArbitrageOpportunity = opportunity;
    
    // 更新步骤状态
    updateArbitrageStep(1, 'complete');
    updateArbitrageStep(2, 'active');
    
    // 执行买入操作
    executeArbitrageBuy(opportunity, tradeAmount);
}

// 执行套利买入
function executeArbitrageBuy(opportunity, amount) {
    const { symbol, buyExchange, buyPrice } = opportunity;
    
    addLog('INFO', `正在${formatExchangeName(buyExchange)}买入${amount} ${symbol.split('/')[0]}，价格：${formatPrice(buyPrice)}...`);
    
    // 模拟API调用
    setTimeout(() => {
        addLog('SUCCESS', `成功在${formatExchangeName(buyExchange)}买入${amount} ${symbol.split('/')[0]}`);
        
        // 更新步骤状态
        updateArbitrageStep(2, 'complete');
        updateArbitrageStep(3, 'active');
        
        // 执行卖出操作
        executeArbitrageSell(opportunity, amount);
    }, 2000);
}

// 执行套利卖出
function executeArbitrageSell(opportunity, amount) {
    const { symbol, sellExchange, sellPrice } = opportunity;
    
    addLog('INFO', `正在${formatExchangeName(sellExchange)}卖出${amount} ${symbol.split('/')[0]}，价格：${formatPrice(sellPrice)}...`);
    
    // 模拟API调用
    setTimeout(() => {
        addLog('SUCCESS', `成功在${formatExchangeName(sellExchange)}卖出${amount} ${symbol.split('/')[0]}`);
        
        // 更新步骤状态
        updateArbitrageStep(3, 'complete');
        updateArbitrageStep(4, 'active');
        
        // 完成套利
        completeArbitrage(opportunity, amount);
    }, 2000);
}

// 完成套利
function completeArbitrage(opportunity, amount) {
    const { priceDiff, netProfitPct } = opportunity;
    const profit = amount * priceDiff;
    
    addLog('SUCCESS', `套利完成! 净利润: ${formatNumber(profit)} USDT (${formatPercentage(netProfitPct)})`);
    
    // 更新步骤状态
    updateArbitrageStep(4, 'complete');
    
    // 关闭模态框
    setTimeout(() => {
        const modal = bootstrap.Modal.getInstance(document.getElementById('arbitrageModal'));
        if (modal) modal.hide();
        
        // 添加历史记录
        addArbitrageHistory(opportunity, amount, profit);
    }, 2000);
}

// 更新套利步骤状态
function updateArbitrageStep(stepNumber, status) {
    const step = document.getElementById(`step${stepNumber}`);
    if (!step) return;
    
    // 移除所有状态类
    step.classList.remove('active', 'complete');
    
    // 添加新状态类
    if (status === 'active') {
        step.classList.add('active');
        step.querySelector('.step-status').innerHTML = '<i class="fas fa-spinner fa-spin text-primary"></i>';
    } else if (status === 'complete') {
        step.classList.add('complete');
        step.querySelector('.step-status').innerHTML = '<i class="fas fa-check-circle text-success"></i>';
    } else {
        step.querySelector('.step-status').innerHTML = '<i class="fas fa-circle text-muted"></i>';
    }
}

// 添加套利历史记录
function addArbitrageHistory(opportunity, amount, profit) {
    // 在实际应用中，这里应该将历史记录保存到服务器
    const historyItem = {
        ...opportunity,
        amount,
        profit,
        timestamp: new Date().toISOString()
    };
    
    console.log('套利历史记录:', historyItem);
    
    // 更新界面显示
    fetchArbitrageData();
    fetchBalanceData();
}

