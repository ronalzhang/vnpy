// 常量定义
const SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "SHIB/USDT"];
const EXCHANGES = ["binance", "okx", "bitget"];
const EXCHANGE_FEES = {
    "binance": 0.1,
    "okx": 0.1,
    "bitget": 0.1
};

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log("页面加载完成，初始化系统...");
    
    // 初始化系统状态
    updateSystemStatus();
    
    // 定时更新数据
    setInterval(updateAllData, 5000);
    
    // 初始化按钮事件
    initButtons();
    
    // 首次加载数据
    updateAllData();
});

// 初始化按钮事件
function initButtons() {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    if (startBtn) {
        startBtn.addEventListener('click', function() {
            fetch('/api/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        addLogEntry('INFO', '系统已启动');
                        updateSystemStatus();
                    } else {
                        addLogEntry('ERROR', '系统启动失败: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('启动系统出错:', error);
                    addLogEntry('ERROR', '系统启动请求失败');
                });
        });
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', function() {
            fetch('/api/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        addLogEntry('INFO', '系统已停止');
                        updateSystemStatus();
                    } else {
                        addLogEntry('ERROR', '系统停止失败: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('停止系统出错:', error);
                    addLogEntry('ERROR', '系统停止请求失败');
                });
        });
    }
}

// 更新所有数据
function updateAllData() {
    updateMarketData();
    updateArbitrageData();
    updateBalanceData();
    updateSystemStatus();
    updateServerTime();
}

// 更新市场数据
function updateMarketData() {
    fetch('/api/prices')
        .then(response => response.json())
        .then(data => {
            if (data) {
                renderPriceTable(data);
            } else {
                console.error('获取到的市场数据格式不正确:', data);
            }
        })
        .catch(error => {
            console.error('获取市场数据出错:', error);
        });
}

// 渲染价格表格
function renderPriceTable(pricesData) {
    const tableBody = document.getElementById('price-data');
    if (!tableBody) return;
    
    // 清空表格
    tableBody.innerHTML = '';
    
    // 遍历所有交易对
    for (const symbol of SYMBOLS) {
        const row = document.createElement('tr');
        
        // 添加币种列
        const symbolCell = document.createElement('td');
        symbolCell.className = 'text-center';
        symbolCell.textContent = symbol.replace('/USDT', '');
        row.appendChild(symbolCell);
        
        // 添加各交易所价格列
        for (const exchange of EXCHANGES) {
            const priceCell = document.createElement('td');
            priceCell.className = 'text-center';
            
            if (pricesData[exchange] && pricesData[exchange][symbol]) {
                const buyPrice = pricesData[exchange][symbol].buy;
                const sellPrice = pricesData[exchange][symbol].sell;
                
                if (buyPrice && sellPrice) {
                    priceCell.innerHTML = `${buyPrice.toFixed(2)}/${sellPrice.toFixed(2)}`;
                } else {
                    priceCell.innerHTML = '<span class="text-muted">暂无数据</span>';
                }
            } else {
                priceCell.innerHTML = '<span class="text-muted">暂无数据</span>';
            }
            
            row.appendChild(priceCell);
        }
        
        // 计算并添加差价列
        const diffCell = document.createElement('td');
        diffCell.className = 'text-center';
        
        // 找出所有交易所中的最低卖价（买入价）和最高买价（卖出价）
        let minAskPrice = Infinity;  // 最低卖价（我们的买入价）
        let maxBidPrice = 0;         // 最高买价（我们的卖出价）
        let validPrices = false;
        
        for (const exchange of EXCHANGES) {
            if (pricesData[exchange] && pricesData[exchange][symbol]) {
                const askPrice = pricesData[exchange][symbol].sell;  // 交易所的卖价（我们的买入价）
                const bidPrice = pricesData[exchange][symbol].buy;   // 交易所的买价（我们的卖出价）
                
                if (askPrice && bidPrice) {
                    minAskPrice = Math.min(minAskPrice, askPrice);
                    maxBidPrice = Math.max(maxBidPrice, bidPrice);
                    validPrices = true;
                }
            }
        }
        
        // 计算差价百分比
        if (validPrices && minAskPrice !== Infinity && maxBidPrice > 0) {
            const diffPct = ((maxBidPrice - minAskPrice) / minAskPrice) * 100;
            if (diffPct > 0) {
                let colorClass = '';
                if (diffPct >= 1) {
                    colorClass = 'text-warning';  // 金色，表示高套利机会
                } else if (diffPct >= 0.5) {
                    colorClass = 'text-muted';    // 灰色，表示有套利机会
                }
                diffCell.innerHTML = `<span class="${colorClass}">${diffPct.toFixed(2)}%</span>`;
            } else {
                diffCell.innerHTML = `<span>${diffPct.toFixed(2)}%</span>`;
            }
        } else {
            diffCell.innerHTML = '<span class="text-muted">-</span>';
        }
        
        row.appendChild(diffCell);
        
        // 添加行到表格
        tableBody.appendChild(row);
    }
}

// 更新套利数据
function updateArbitrageData() {
    fetch('/api/diff')
        .then(response => response.json())
        .then(data => {
            if (data) {
                renderArbitrageTable(data);
                
                // 更新套利机会数量
                const arbitrageCount = document.getElementById('arbitrage-count');
                if (arbitrageCount) {
                    arbitrageCount.textContent = data.length;
                }
            }
        })
        .catch(error => {
            console.error('获取套利数据出错:', error);
        });
}

// 渲染套利表格
function renderArbitrageTable(opportunities) {
    const tableBody = document.getElementById('arbitrage-data');
    if (!tableBody) return;
    
    // 清空表格
    tableBody.innerHTML = '';
    
    if (opportunities.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 9;
        cell.className = 'text-center text-muted';
        cell.textContent = '暂无套利机会';
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
    }
    
    // 添加套利机会
    for (const opp of opportunities) {
        const row = document.createElement('tr');
        
        // 交易对
        const symbolCell = document.createElement('td');
        symbolCell.textContent = opp.symbol;
        row.appendChild(symbolCell);
        
        // 买入所
        const buyExchangeCell = document.createElement('td');
        buyExchangeCell.textContent = opp.buyExchange;
        row.appendChild(buyExchangeCell);
        
        // 卖出所
        const sellExchangeCell = document.createElement('td');
        sellExchangeCell.textContent = opp.sellExchange;
        row.appendChild(sellExchangeCell);
        
        // 买入价
        const buyPriceCell = document.createElement('td');
        buyPriceCell.textContent = opp.buyPrice.toFixed(2);
        row.appendChild(buyPriceCell);
        
        // 卖出价
        const sellPriceCell = document.createElement('td');
        sellPriceCell.textContent = opp.sellPrice.toFixed(2);
        row.appendChild(sellPriceCell);
        
        // 深度
        const depthCell = document.createElement('td');
        depthCell.textContent = opp.depth ? opp.depth.toFixed(4) : '-';
        row.appendChild(depthCell);
        
        // 差价
        const diffCell = document.createElement('td');
        diffCell.textContent = opp.priceDiff.toFixed(2);
        row.appendChild(diffCell);
        
        // 差价百分比
        const diffPctCell = document.createElement('td');
        diffPctCell.className = 'text-success';
        diffPctCell.textContent = opp.priceDiffPct.toFixed(2) + '%';
        row.appendChild(diffPctCell);
        
        // 可执行
        const executableCell = document.createElement('td');
        executableCell.className = 'text-center';
        if (opp.executable) {
            executableCell.innerHTML = '<span class="badge bg-success">是</span>';
        } else {
            executableCell.innerHTML = '<span class="badge bg-secondary">否</span>';
        }
        row.appendChild(executableCell);
        
        tableBody.appendChild(row);
    }
}

// 更新账户余额数据
function updateBalanceData() {
    fetch('/api/balances')
        .then(response => response.json())
        .then(data => {
            if (data) {
                console.log('API返回的余额数据:', data);  // 添加日志
                renderBalanceData(data);
            }
        })
        .catch(error => {
            console.error('获取账户余额数据出错:', error);
        });
}

// 渲染账户余额数据
function renderBalanceData(balances) {
    // 更新各交易所余额
    for (const exchange of EXCHANGES) {
        if (balances[exchange]) {
            // 更新总余额、可用余额和锁定余额
            const totalBalance = document.getElementById(`${exchange}-balance`);
            const availableBalance = document.getElementById(`${exchange}-available`);
            const lockedBalance = document.getElementById(`${exchange}-locked`);
            
            if (totalBalance) totalBalance.textContent = balances[exchange].total || '-';
            if (availableBalance) availableBalance.textContent = balances[exchange].available || '-';
            if (lockedBalance) lockedBalance.textContent = balances[exchange].locked || '-';
            
            // 更新持仓情况
            const positionsTable = document.getElementById(`${exchange}-positions`);
            if (positionsTable) {
                positionsTable.innerHTML = '';
                
                // 检查positions是否为数组且有数据
                const positions = balances[exchange].positions;
                if (Array.isArray(positions) && positions.length > 0) {
                    for (const position of positions) {
                        const row = document.createElement('tr');
                        
                        // 币种
                        const coinCell = document.createElement('td');
                        coinCell.textContent = position.coin || '-';
                        row.appendChild(coinCell);
                        
                        // 总数量
                        const totalCell = document.createElement('td');
                        totalCell.textContent = position.total || '-';
                        row.appendChild(totalCell);
                        
                        // 可用
                        const availableCell = document.createElement('td');
                        availableCell.textContent = position.available || '-';
                        row.appendChild(availableCell);
                        
                        // 锁定
                        const lockedCell = document.createElement('td');
                        lockedCell.textContent = position.locked || '-';
                        row.appendChild(lockedCell);
                        
                        // 价值
                        const valueCell = document.createElement('td');
                        valueCell.textContent = position.value || '-';
                        row.appendChild(valueCell);
                        
                        positionsTable.appendChild(row);
                    }
                } else {
                    // 如果没有持仓数据或positions不是数组，显示空状态
                    positionsTable.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无持仓数据</td></tr>';
                }
            }
        }
    }
}

// 更新系统状态
function updateSystemStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data) {
                // 更新状态指示器
                const statusIndicator = document.getElementById('status-indicator');
                if (statusIndicator) {
                    statusIndicator.textContent = data.running ? '运行中' : '已停止';
                    statusIndicator.className = data.running ? 'badge bg-success' : 'badge bg-danger';
                }
                
                // 更新模式指示器
                const modeIndicator = document.getElementById('mode-indicator');
                if (modeIndicator) {
                    modeIndicator.textContent = data.mode === 'simulate' ? '模拟模式' : '实盘模式';
                    modeIndicator.className = data.mode === 'simulate' ? 'badge bg-info' : 'badge bg-warning';
                }
                
                // 更新最后更新时间
                const lastUpdate = document.getElementById('last-update');
                if (lastUpdate && data.last_update) {
                    lastUpdate.textContent = data.last_update;
                }
            }
        })
        .catch(error => {
            console.error('获取系统状态出错:', error);
        });
}

// 更新服务器时间
function updateServerTime() {
    const serverTime = document.getElementById('server-time');
    if (serverTime) {
        const now = new Date();
        serverTime.textContent = now.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }
}

// 添加日志条目
function addLogEntry(level, message) {
    const logsList = document.getElementById('operation-logs');
    if (!logsList) return;
    
    const now = new Date();
    const timeStr = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    
    const li = document.createElement('li');
    li.className = 'list-group-item';
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'text-muted';
    timeSpan.textContent = `[${timeStr}]`;
    
    const levelBadge = document.createElement('span');
    levelBadge.className = `badge ${getBadgeClass(level)} ms-2`;
    levelBadge.textContent = level;
    
    li.appendChild(timeSpan);
    li.appendChild(levelBadge);
    li.appendChild(document.createTextNode(' ' + message));
    
    // 添加到列表顶部
    logsList.insertBefore(li, logsList.firstChild);
    
    // 限制日志条目数量
    if (logsList.children.length > 100) {
        logsList.removeChild(logsList.lastChild);
    }
}

// 获取日志级别对应的徽章类
function getBadgeClass(level) {
    switch (level.toUpperCase()) {
        case 'INFO': return 'bg-info';
        case 'WARNING': return 'bg-warning';
        case 'ERROR': return 'bg-danger';
        case 'SUCCESS': return 'bg-success';
        case 'ARBITRAGE': return 'bg-success';
        default: return 'bg-secondary';
    }
}

// 套利机会查找函数
function findArbitrageOpportunities(pricesData) {
    let opportunities = [];
    
    // 检查价格数据是否有效
    if (!pricesData) {
        console.error("价格数据无效");
        return opportunities;
    }
    
    // 遍历所有交易对
    for (const symbol of SYMBOLS) {
        // 遍历所有交易所组合
        for (const buyExchange of EXCHANGES) {
            // 检查买入交易所数据是否存在
            if (!pricesData[buyExchange] || !pricesData[buyExchange][symbol]) {
                continue;
            }
            
            // 获取买入交易所的卖1价格(我们要花这个价格买入)
            const buyPrice = pricesData[buyExchange][symbol].sell;
            if (!buyPrice || isNaN(parseFloat(buyPrice))) {
                console.log(`${buyExchange} ${symbol} 卖价无效: ${buyPrice}`);
                continue;
            }
            
            for (const sellExchange of EXCHANGES) {
                if (buyExchange === sellExchange) continue;
                
                // 检查卖出交易所数据是否存在
                if (!pricesData[sellExchange] || !pricesData[sellExchange][symbol]) {
                    continue;
                }
                
                // 获取卖出交易所的买1价格(我们能以这个价格卖出)
                const sellPrice = pricesData[sellExchange][symbol].buy;
                if (!sellPrice || isNaN(parseFloat(sellPrice))) {
                    console.log(`${sellExchange} ${symbol} 买价无效: ${sellPrice}`);
                    continue;
                }
                
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

