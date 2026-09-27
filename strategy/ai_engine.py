# strategy/ai_engine.py

def generate_trade_setups(last, smc_data, derivatives):
    close = float(last.get("close", 0))
    atr = float(last.get("ATR", close * 0.015))
    
    # -----------------------------------------
    # 1. SMC MODEL (Smart Money Concepts)
    # -----------------------------------------
    smc_score = 50
    smc_reasons = []
    structure = smc_data.get("market_structure", "Neutral")
    
    if "Bullish" in structure:
        smc_score += 25
        smc_reasons.append("BOS: Bullish Market Structure")
    elif "Bearish" in structure:
        smc_score -= 25
        smc_reasons.append("BOS: Bearish Market Structure")

    bull_obs = smc_data.get("order_blocks", {}).get("bullish", [])
    bear_obs = smc_data.get("order_blocks", {}).get("bearish", [])
    
    if bull_obs and abs(close - bull_obs[-1]["high"]) / close < 0.01:
        smc_score += 20
        smc_reasons.append("Mitigating Bullish Order Block")
    if bear_obs and abs(close - bear_obs[-1]["low"]) / close < 0.01:
        smc_score -= 20
        smc_reasons.append("Rejecting Bearish Order Block")
        
    smc_setup = format_setup(smc_score, close, atr, smc_reasons)

    # -----------------------------------------
    # 2. PRICE ACTION MODEL (Technicals)
    # -----------------------------------------
    pa_score = 50
    pa_reasons = []
    
    if float(last.get("EMA20", 0)) > float(last.get("EMA50", 0)):
        pa_score += 15
        pa_reasons.append("EMA 20 > EMA 50 (Golden Cross Setup)")
    else:
        pa_score -= 15
        pa_reasons.append("EMA 20 < EMA 50 (Death Cross Setup)")
        
    rsi = float(last.get("RSI", 50))
    if 40 <= rsi <= 60:
        pa_score += 15
        pa_reasons.append(f"RSI ({rsi:.1f}) showing healthy momentum")
    elif rsi > 70:
        pa_score -= 20
        pa_reasons.append(f"RSI Overbought ({rsi:.1f}) - Pullback risk")
    elif rsi < 30:
        pa_score += 20
        pa_reasons.append(f"RSI Oversold ({rsi:.1f}) - Reversal probable")
        
    if float(last.get("ADX", 0)) > 25:
        pa_score += 10 if pa_score > 50 else -10
        pa_reasons.append("Strong ADX Trend Velocity")

    pa_setup = format_setup(pa_score, close, atr, pa_reasons)

    # -----------------------------------------
    # 3. NEWS & SENTIMENT MODEL
    # -----------------------------------------
    news_score = 50
    news_reasons = []
    
    funding = derivatives.get("funding_rate", "0%")
    funding_val = float(funding.replace("%", "")) if isinstance(funding, str) else 0.0
    
    if funding_val > 0.02:
        news_score -= 20
        news_reasons.append(f"High Long Funding ({funding}) - Long Squeeze Risk")
    elif funding_val < -0.01:
        news_score += 20
        news_reasons.append(f"Negative Funding ({funding}) - Short Squeeze Fuel")
    else:
        news_reasons.append("Funding rates neutral (Spot driven market)")
        
    news_score += 10 # Simulated base bullish sentiment for crypto baseline
    news_reasons.append("Global Crypto Sentiment: Cautiously Optimistic")
    
    news_setup = format_setup(news_score, close, atr, news_reasons)

    return {
        "smc": smc_setup,
        "pa": pa_setup,
        "news": news_setup
    }

def format_setup(score, close, atr, reasons):
    prob = int(max(5, min(95, score)))
    
    if prob >= 70:
        signal, bias = "LONG EXECUTION", "LONG"
    elif prob <= 30:
        signal, bias = "SHORT EXECUTION", "SHORT"
    else:
        signal, bias = "WAIT FOR CONFIRMATION", "NEUTRAL"
        
    if bias == "LONG":
        entry = f"${(close * 0.998):.2f} - ${close:.2f}"
        sl = round(close - (1.5 * atr), 2)
        tp1 = round(close + (2.0 * atr), 2)
    elif bias == "SHORT":
        entry = f"${close:.2f} - ${(close * 1.002):.2f}"
        sl = round(close + (1.5 * atr), 2)
        tp1 = round(close - (2.0 * atr), 2)
    else:
        entry, sl, tp1 = "--", 0, 0
        
    rr = round(abs(tp1 - close) / (abs(close - sl) + 1e-9), 2) if sl != 0 else 0.0

    return {
        "probability": prob,
        "signal": signal,
        "bias": bias,
        "entry": entry,
        "sl": f"${sl:.2f}" if sl else "--",
        "tp1": f"${tp1:.2f}" if tp1 else "--",
        "rr": f"1 : {rr}" if rr else "--",
        "reasons": reasons if reasons else ["Awaiting data..."]
    }