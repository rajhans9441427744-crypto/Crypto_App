# engine.py
import time
import json
import requests
import threading
import pandas as pd
import numpy as np
import websocket
from concurrent.futures import ThreadPoolExecutor

from cache import db
from indicators.technicals import compute_technicals
from indicators.smc import detect_smc
# IMPORTANT: Importing the new Tri-Model function
from strategy.ai_engine import generate_trade_setups

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

def fetch_single_candle(symbol, interval, limit=1000):
    # Use the official Binance Vision API which allows cloud server IPs
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    
    try:
        res = requests.get(url, timeout=10).json()
        
        # If Binance still blocks it, it returns a dictionary error instead of a list of candles
        if not isinstance(res, list):
            print(f"API Blocked or Error for {symbol}: {res}")
            return None
            
        df = pd.DataFrame(res, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades", "tb_base", "tb_quote", "ignore"
        ])
        
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
            
        df["time"] = df["time"].astype(int)
        return compute_technicals(df)
        
    except Exception as e:
        print(f"Kline fetch error for {symbol}:", e)
        return None

def fetch_derivatives_intel(symbol):
    """Fetches funding rate and mark price from Binance Futures."""
    try:
        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
        r = requests.get(url, timeout=3).json()
        rate = float(r.get("lastFundingRate", 0)) * 100
        mark_price = float(r.get("markPrice", 0))
        return {
            "funding_rate": f"{rate:.4f}%",
            "annualized_funding": f"{(rate * 3 * 365):.2f}%",
            "mark_price": mark_price,
            "next_funding_time": int(r.get("nextFundingTime", 0))
        }
    except Exception:
        return {
            "funding_rate": "+0.0100%",
            "annualized_funding": "+10.95%",
            "mark_price": 0.0,
            "next_funding_time": 0
        }

def sync_symbol_data(sym):
    scanner_summary = {}
    primary_df = None
    derivatives = fetch_derivatives_intel(sym) # Fetch early for the AI Engine

    for tf in TIMEFRAMES:
        df = fetch_single_candle(sym, tf, limit=1000)
        if df is not None and not df.empty:
            db.set_candles(sym, tf, df)
            db.set_analysis(sym, tf, df)
            
            last = df.iloc[-1].to_dict()
            smc = detect_smc(df)

            # Scanner needs a basic signal, we'll use the PA model from the new engine
            tf_setup = generate_trade_setups(last, smc, derivatives)["pa"]

            scanner_summary[tf] = {
                "price": round(float(last["close"]), 2),
                "rsi": round(float(last.get("RSI", 50)), 1),
                "adx": round(float(last.get("ADX", 20)), 1),
                "trend": "Bullish" if last.get("EMA20", 0) > last.get("EMA50", 0) else "Bearish",
                "strength": f"{tf_setup['probability']}%",
                "signal": tf_setup["signal"]
            }
            if tf == "15m":
                primary_df = df

    if primary_df is not None:
        db.set_scanner(sym, scanner_summary)
        live_info = db.get_live(sym)
        last_15m = primary_df.iloc[-1].to_dict()
        smc_15m = detect_smc(primary_df)
        
        # Call the new Tri-Model setup
        trade_setups = generate_trade_setups(last_15m, smc_15m, derivatives)

        # Volatility & Bollinger Band Width
        std20 = primary_df["close"].rolling(20).std().iloc[-1]
        bb_width = ((std20 * 4) / (last_15m.get("EMA20", 1) + 1e-9)) * 100

        # Premium vs Discount equilibrium
        range_high = primary_df["high"].tail(50).max()
        range_low = primary_df["low"].tail(50).min()
        equilibrium = (range_high + range_low) / 2.0
        current_close = live_info.get("price", last_15m["close"])
        pricing_zone = "DISCOUNT (Favorable Long)" if current_close < equilibrium else "PREMIUM (Favorable Short)"

        dashboard_payload = {
            "success": True,
            "status": "ready",
            "symbol": sym,
            "price": current_close,
            "change": live_info.get("change", 0.0),
            "high": live_info.get("high", last_15m["high"]),
            "low": live_info.get("low", last_15m["low"]),
            "volume": live_info.get("volume", last_15m["volume"]),
            "derivatives": derivatives,
            "pricing_zone": pricing_zone,
            "equilibrium": round(equilibrium, 2),
            "bb_width": f"{bb_width:.2f}%",
            "scanner": scanner_summary,
            "setups": trade_setups,  # Now passing all 3 models to the frontend
            "smc": smc_15m,
            "indicators": {
                "EMA_Trend": "Bullish" if last_15m.get("EMA20", 0) > last_15m.get("EMA50", 0) else "Bearish",
                "MACD": "Bullish" if last_15m.get("MACD", 0) > last_15m.get("MACD_SIGNAL", 0) else "Bearish",
                "RSI": round(float(last_15m.get("RSI", 50)), 1),
                "ADX": round(float(last_15m.get("ADX", 25)), 1),
                "ATR": round(float(last_15m.get("ATR", 0)), 2),
                "VWAP": "Above" if current_close > last_15m.get("VWAP", 0) else "Below",
                "Supertrend": "BUY" if last_15m.get("ST_DIRECTION", False) else "SELL"
            }
        }
        db.set_dashboard(sym, dashboard_payload)

def engine_sync_loop():
    print("⏳ Starting initial candle sync across all symbols...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(sync_symbol_data, SYMBOLS)
    print("✅ Initial data populated into cache.")

    while True:
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(sync_symbol_data, SYMBOLS)
            time.sleep(6)
        except Exception as e:
            print("Sync Loop Error:", e)
            time.sleep(3)

def websocket_worker():
    streams = "/".join([f"{s.lower()}@ticker" for s in SYMBOLS])
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    def on_message(ws, message):
        try:
            payload = json.loads(message).get("data", {})
            sym = payload.get("s")
            if sym:
                db.set_live(sym, {
                    "price": float(payload.get("c", 0)),
                    "change": float(payload.get("P", 0)),
                    "high": float(payload.get("h", 0)),
                    "low": float(payload.get("l", 0)),
                    "volume": float(payload.get("v", 0))
                })
        except Exception:
            pass

    while True:
        try:
            print("🚀 WebSocket stream starting...")
            ws = websocket.WebSocketApp(url, on_message=on_message)
            ws.run_forever()
        except Exception:
            pass
        time.sleep(2)

def start_engine():
    threading.Thread(target=websocket_worker, daemon=True).start()
    threading.Thread(target=engine_sync_loop, daemon=True).start()
