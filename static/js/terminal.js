let currentSymbol = "BTCUSDT";
let currentInterval = "15m";
let chart, candleSeries;

let currentAITab = "smc";
let latestSetups = null; // Store latest AI payloads

function initChart() {
    const container = document.getElementById("chart");
    chart = LightweightCharts.createChart(container, {
        layout: { background: { color: "transparent" }, textColor: "#64748b" },
        grid: { vertLines: { color: "rgba(255,255,255,0.02)" }, horzLines: { color: "rgba(255,255,255,0.02)" } },
        timeScale: { borderColor: "rgba(255,255,255,0.08)", timeVisible: true },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal }
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: "#10b981", downColor: "#f43f5e",
        borderUpColor: "#10b981", borderDownColor: "#f43f5e",
        wickUpColor: "#10b981", wickDownColor: "#f43f5e"
    });

    window.addEventListener("resize", () => {
        chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    });
}

async function loadCandles() {
    try {
        const res = await fetch(`/api/chart?symbol=${currentSymbol}&interval=${currentInterval}`);
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
            candleSeries.setData(data);
        }
    } catch (e) {
        console.error("Candle load error:", e);
    }
}

function switchAITab(tabName) {
    currentAITab = tabName;
    document.getElementById("tab-smc").classList.remove("active");
    document.getElementById("tab-pa").classList.remove("active");
    document.getElementById("tab-news").classList.remove("active");
    document.getElementById(`tab-${tabName}`).classList.add("active");
    
    const labels = { smc: "SMC CONFIDENCE", pa: "PRICE ACTION CONFIDENCE", news: "SENTIMENT CONFIDENCE" };
    document.getElementById("aiModelLabel").innerText = labels[tabName];
    
    renderAITab();
}

function renderAITab() {
    if (!latestSetups || !latestSetups[currentAITab]) return;
    const data = latestSetups[currentAITab];

    const sigElem = document.getElementById("aiSignal");
    sigElem.innerText = data.signal;
    sigElem.className = `signal-badge ${data.bias === "LONG" ? "bullish" : data.bias === "SHORT" ? "bearish" : "cyan"}`;

    const scoreElem = document.getElementById("aiScore");
    scoreElem.innerText = `${data.probability}%`;
    scoreElem.className = `mono score-number ${data.bias === "LONG" ? "bullish" : data.bias === "SHORT" ? "bearish" : ""}`;

    document.getElementById("aiEntry").innerText = data.entry;
    document.getElementById("aiSL").innerText = data.sl;
    document.getElementById("aiTP1").innerText = data.tp1;
    document.getElementById("aiRR").innerText = data.rr;

    const listElem = document.getElementById("aiReasons");
    listElem.innerHTML = "";
    (data.reasons || []).forEach(r => {
        const li = document.createElement("li");
        li.innerText = r;
        listElem.appendChild(li);
    });
}

async function updateTerminal() {
    try {
        const res = await fetch(`/api/dashboard?symbol=${currentSymbol}`);
        const data = await res.json();

        // 1. Live Header Metrics
        if (data.price !== undefined) {
            document.getElementById("navPrice").innerText = `$${Number(data.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
            const changeElem = document.getElementById("navChange");
            changeElem.innerText = `${data.change >= 0 ? "+" : ""}${Number(data.change).toFixed(2)}%`;
            changeElem.className = `m-value mono ${data.change >= 0 ? "bullish" : "bearish"}`;
        }

        if (data.derivatives) {
            document.getElementById("navFunding").innerText = `${data.derivatives.funding_rate} / ${data.derivatives.annualized_funding}`;
        }

        if (data.pricing_zone) {
            const zoneElem = document.getElementById("navZone");
            zoneElem.innerText = data.pricing_zone;
            zoneElem.className = `m-value mono ${data.pricing_zone.includes("DISCOUNT") ? "bullish" : "bearish"}`;
        }

        // 2. Smart Money Concepts
        if (data.smc) {
            const structureElem = document.getElementById("smcStructure");
            structureElem.innerText = data.smc.market_structure;
            structureElem.className = data.smc.market_structure.includes("Bullish") ? "bullish font-bold" : "bearish font-bold";

            document.getElementById("smcEquilibrium").innerText = `$${data.equilibrium}`;

            const fvgs = data.smc.fvg || [];
            const topFvg = fvgs.filter(f => f.type === "Bearish").map(f => `$${f.top}-$${f.bottom}`).join(", ");
            const botFvg = fvgs.filter(f => f.type === "Bullish").map(f => `$${f.bottom}-$${f.top}`).join(", ");
            document.getElementById("smcFVGTop").innerText = topFvg || "Clean Liquidity (None)";
            document.getElementById("smcFVGBottom").innerText = botFvg || "Clean Liquidity (None)";

            const obTotal = (data.smc.order_blocks?.bullish?.length || 0) + (data.smc.order_blocks?.bearish?.length || 0);
            document.getElementById("smcOB").innerText = `${obTotal} Zones Detected`;
        }

        // 3. Multi-Timeframe Heatmap
        if (data.scanner) {
            let heatmapHtml = "";
            for (const [tf, info] of Object.entries(data.scanner)) {
                const isBull = info.signal.includes("BUY") || info.signal.includes("LONG");
                const isBear = info.signal.includes("SELL") || info.signal.includes("SHORT");
                const cellClass = isBull ? "heatmap-cell bullish-cell" : isBear ? "heatmap-cell bearish-cell" : "heatmap-cell";
                heatmapHtml += `
                    <div class="${cellClass}">
                        <div class="font-bold">${tf}</div>
                        <div class="${isBull ? 'bullish' : isBear ? 'bearish' : 'cyan'}">${info.signal}</div>
                        <div class="m-label">RSI: ${info.rsi}</div>
                    </div>
                `;
            }
            document.getElementById("tfHeatmap").innerHTML = heatmapHtml;
        }

        // 4. Tri-Model AI Setup Tabs
        if (data.setups) {
            latestSetups = data.setups;
            renderAITab(); 
        }

        // 5. Core Indicators Snapshot (Restored)
        if (data.indicators) {
            let indHtml = "";
            for (const [name, val] of Object.entries(data.indicators)) {
                indHtml += `
                    <div class="ind-box">
                        <span class="m-label">${name}</span>
                        <div class="font-bold">${val}</div>
                    </div>
                `;
            }
            document.getElementById("indicatorMatrix").innerHTML = indHtml;
        }

        // Update Watchlist dynamic prices
        const wtElem = document.getElementById(`wt_price_${currentSymbol}`);
        if (wtElem && data.price) {
            wtElem.innerText = `$${Number(data.price).toLocaleString()}`;
        }

    } catch (e) {
        console.error("Terminal refresh error:", e);
    }
}

async function loadWatchlist() {
    try {
        const res = await fetch("/api/markets");
        const symbols = await res.json();
        const container = document.getElementById("watchlist");
        container.innerHTML = "";

        symbols.forEach(sym => {
            const div = document.createElement("div");
            div.className = "watch-item mono";
            div.innerHTML = `
                <span class="font-bold">${sym}</span>
                <span id="wt_price_${sym}" class="cyan">--</span>
            `;
            div.onclick = () => switchSymbol(sym);
            container.appendChild(div);
        });
    } catch (e) {
        console.error("Watchlist load error:", e);
    }
}

function switchSymbol(sym) {
    currentSymbol = sym;
    document.getElementById("symbolSelect").value = sym;
    loadCandles();
    updateTerminal();
}

function switchInterval(interval) {
    currentInterval = interval;
    document.querySelectorAll(".tf-btn").forEach(btn => {
        btn.classList.toggle("active", btn.innerText.toLowerCase() === interval.toLowerCase());
    });
    loadCandles();
}

window.onload = () => {
    initChart();
    loadWatchlist();
    loadCandles();
    updateTerminal();
    setInterval(updateTerminal, 2000);
};