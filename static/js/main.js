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
    
    // 设置API基础URL
    window.API_BASE_URL = 'http://47.236.39.134:8888';
    
    // 初始化系统状态
    updateSystemStatus();
    
    // 定时更新数据
    setInterval(updateAllData, 5000);
    
    // 初始化按钮事件
    initButtons();
    
    // 初始化余额隐私设置
    initPrivacySettings();
    
    // 首次加载数据
    updateAllData();
});

// 初始化按钮事件
function initButtons() {
    const toggleBtn = document.getElementById('toggle-btn');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const isRunning = toggleBtn.getAttribute('data-running') === 'true';
            
            const endpoint = isRunning ? '/api/stop' : '/api/start';
            
            // 在请求发送前禁用按钮,防止重复点击
            toggleBtn.disabled = true;
            
            fetch(window.API_BASE_URL + endpoint, { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})  // 发送空对象作为请求体
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const newStatus = !isRunning;
                        toggleBtn.setAttribute('data-running', newStatus);
                        
                        // 更新按钮文本和样式
                        if (newStatus) {
                            toggleBtn.textContent = '停止运行';
                            toggleBtn.classList.remove('btn-primary');
                            toggleBtn.classList.add('btn-danger');
                            addLogEntry('INFO', '系统已启动');
                        } else {
                            toggleBtn.textContent = '启动运行';
                            toggleBtn.classList.remove('btn-danger');
                            toggleBtn.classList.add('btn-primary');
                            addLogEntry('INFO', '系统已停止');
                        }
                        
                        updateSystemStatus();
                    } else {
                        addLogEntry('ERROR', (isRunning ? '停止' : '启动') + '失败: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error((isRunning ? '停止' : '启动') + '系统出错:', error);
                    addLogEntry('ERROR', '系统' + (isRunning ? '停止' : '启动') + '请求失败');
                })
                .finally(() => {
                    // 请求完成后重新启用按钮
                    toggleBtn.disabled = false;
                });
        });
    }
}

// 初始化余额隐私设置
function initPrivacySettings() {
    const togglePrivacyBtn = document.getElementById('toggle-privacy');
    if (togglePrivacyBtn) {
        // 默认开启隐私模式
        let isPrivate = true;
        document.body.classList.add('privacy-mode');
        
        togglePrivacyBtn.addEventListener('click', function() {
            isPrivate = !isPrivate;
            document.body.classList.toggle('privacy-mode');
            
            // 更新图标
            const icon = togglePrivacyBtn.querySelector('i');
            if (icon) {
                icon.className = isPrivate ? 'fas fa-eye-slash' : 'fas fa-eye';
            }
            
            // 更新按钮样式
            togglePrivacyBtn.classList.toggle('btn-outline-light');
            togglePrivacyBtn.classList.toggle('btn-light');
            
            // 更新所有余额显示
            updateBalanceDisplay(isPrivate);
        });
    }
}

// 更新余额显示
function updateBalanceDisplay(isPrivate) {
    const balanceElements = document.querySelectorAll('.balance-info h4, .table td:not(:first-child)');
    balanceElements.forEach(element => {
        if (element.dataset.value) {
            element.textContent = element.dataset.value;
            element.classList.toggle('privacy-blur', isPrivate);
        }
    });
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
    fetch(window.API_BASE_URL + '/api/prices')
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
    fetch(window.API_BASE_URL + '/api/diff')
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
    fetch(window.API_BASE_URL + '/api/balances')
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
    const isPrivate = document.body.classList.contains('privacy-mode');
    
    // 更新各交易所余额
    for (const exchange of EXCHANGES) {
        if (balances[exchange]) {
            // 更新总余额、可用余额和锁定余额
            const totalBalance = document.getElementById(`${exchange}-balance`);
            const availableBalance = document.getElementById(`${exchange}-available`);
            const lockedBalance = document.getElementById(`${exchange}-locked`);
            
            if (totalBalance) {
                totalBalance.dataset.value = balances[exchange].USDT || '-';
                totalBalance.textContent = totalBalance.dataset.value;
                totalBalance.classList.toggle('privacy-blur', isPrivate);
            }
            if (availableBalance) {
                availableBalance.dataset.value = balances[exchange].USDT_available || '-';
                availableBalance.textContent = availableBalance.dataset.value;
                availableBalance.classList.toggle('privacy-blur', isPrivate);
            }
            if (lockedBalance) {
                lockedBalance.dataset.value = balances[exchange].USDT_locked || '-';
                lockedBalance.textContent = lockedBalance.dataset.value;
                lockedBalance.classList.toggle('privacy-blur', isPrivate);
            }
            
            // 更新持仓情况
            const positionsTable = document.getElementById(`${exchange}-positions`);
            if (positionsTable) {
                positionsTable.innerHTML = '';
                
                const positions = balances[exchange].positions;
                if (positions && Object.keys(positions).length > 0) {
                    for (const [coin, position] of Object.entries(positions)) {
                        const row = document.createElement('tr');
                        
                        // 币种
                        const coinCell = document.createElement('td');
                        coinCell.textContent = coin;
                        row.appendChild(coinCell);
                        
                        // 总数量
                        const totalCell = document.createElement('td');
                        totalCell.dataset.value = position.amount || '-';
                        totalCell.textContent = totalCell.dataset.value;
                        totalCell.classList.toggle('privacy-blur', isPrivate);
                        row.appendChild(totalCell);
                        
                        // 可用
                        const availableCell = document.createElement('td');
                        availableCell.dataset.value = position.available || '-';
                        availableCell.textContent = availableCell.dataset.value;
                        availableCell.classList.toggle('privacy-blur', isPrivate);
                        row.appendChild(availableCell);
                        
                        // 锁定
                        const lockedCell = document.createElement('td');
                        lockedCell.dataset.value = position.locked || '-';
                        lockedCell.textContent = lockedCell.dataset.value;
                        lockedCell.classList.toggle('privacy-blur', isPrivate);
                        row.appendChild(lockedCell);
                        
                        // 价值
                        const valueCell = document.createElement('td');
                        valueCell.dataset.value = position.value || '-';
                        valueCell.textContent = valueCell.dataset.value;
                        valueCell.classList.toggle('privacy-blur', isPrivate);
                        row.appendChild(valueCell);
                        
                        positionsTable.appendChild(row);
                    }
                } else {
                    positionsTable.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无持仓数据</td></tr>';
                }
            }
        }
    }
}

// 更新系统状态
function updateSystemStatus() {
    fetch(window.API_BASE_URL + '/api/status')
        .then(response => response.json())
        .then(data => {
            // 更新状态标签
            const statusBadge = document.getElementById('status-badge');
            const modeBadge = document.getElementById('mode-badge');
            const arbitrageCountBadge = document.getElementById('arbitrage-count-badge');
            
            if (statusBadge) {
                statusBadge.textContent = data.running ? '运行中' : '已停止';
                statusBadge.className = 'badge ' + (data.running ? 'bg-success' : 'bg-secondary');
            }
            
            if (modeBadge) {
                modeBadge.textContent = data.mode === 'simulate' ? '模拟' : '实盘';
                modeBadge.className = 'badge ' + (data.mode === 'simulate' ? 'bg-warning' : 'bg-danger');
            }
            
            if (arbitrageCountBadge && data.arbitrage_count !== undefined) {
                arbitrageCountBadge.textContent = `套利:${data.arbitrage_count}`;
                arbitrageCountBadge.className = 'badge ' + (data.arbitrage_count > 0 ? 'bg-success' : 'bg-secondary');
            }

            // 更新按钮状态
            const toggleBtn = document.getElementById('toggle-btn');
            if (toggleBtn) {
                toggleBtn.setAttribute('data-running', data.running);
                if (data.running) {
                    toggleBtn.textContent = '停止运行';
                    toggleBtn.classList.remove('btn-primary');
                    toggleBtn.classList.add('btn-danger');
                } else {
                    toggleBtn.textContent = '启动运行';
                    toggleBtn.classList.remove('btn-danger');
                    toggleBtn.classList.add('btn-primary');
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

