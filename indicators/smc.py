# indicators/smc.py
def detect_smc(df, lookback=100):
    if df is None or len(df) < 20:
        return {
            "order_blocks": {"bullish": [], "bearish": []},
            "fvg": [],
            "supports": [],
            "resistances": [],
            "market_structure": "Neutral"
        }

    df_recent = df.tail(lookback).copy().reset_index(drop=True)
    bullish_ob, bearish_ob = [], []
    fvg = []

    # 1. Order Blocks & FVGs
    for i in range(2, len(df_recent) - 2):
        c_open = df_recent.loc[i, "open"]
        c_close = df_recent.loc[i, "close"]
        c_high = df_recent.loc[i, "high"]
        c_low = df_recent.loc[i, "low"]

        # Bullish FVG: Low of candle i+1 is higher than High of candle i-1
        if df_recent.loc[i + 1, "low"] > df_recent.loc[i - 1, "high"]:
            fvg.append({
                "type": "Bullish",
                "top": round(float(df_recent.loc[i + 1, "low"]), 2),
                "bottom": round(float(df_recent.loc[i - 1, "high"]), 2)
            })

        # Bearish FVG: High of candle i+1 is lower than Low of candle i-1
        if df_recent.loc[i + 1, "high"] < df_recent.loc[i - 1, "low"]:
            fvg.append({
                "type": "Bearish",
                "top": round(float(df_recent.loc[i - 1, "low"]), 2),
                "bottom": round(float(df_recent.loc[i + 1, "high"]), 2)
            })

        # Order blocks (impulsive displacement > 1.2%)
        future_move = (df_recent.loc[i + 2, "close"] - c_close) / (c_close + 1e-9)
        if c_close < c_open and future_move > 0.012:
            bullish_ob.append({"high": round(float(c_high), 2), "low": round(float(c_low), 2)})
        elif c_close > c_open and future_move < -0.012:
            bearish_ob.append({"high": round(float(c_high), 2), "low": round(float(c_low), 2)})

    # 2. Support & Resistance
    window = 10
    supports, resistances = [], []
    for i in range(window, len(df_recent) - window):
        low_val = df_recent.loc[i, "low"]
        high_val = df_recent.loc[i, "high"]
        if low_val == df_recent.loc[i - window : i + window, "low"].min():
            supports.append(round(float(low_val), 2))
        if high_val == df_recent.loc[i - window : i + window, "high"].max():
            resistances.append(round(float(high_val), 2))

    # 3. Market Structure (HH, HL vs LH, LL)
    last_close = df_recent["close"].iloc[-1]
    prev_close = df_recent["close"].iloc[-10]
    structure = "Bullish (BOS)" if last_close > prev_close else "Bearish (BOS)"

    return {
        "order_blocks": {
            "bullish": bullish_ob[-3:],
            "bearish": bearish_ob[-3:]
        },
        "fvg": fvg[-4:],
        "supports": sorted(list(set(supports)))[-3:],
        "resistances": sorted(list(set(resistances)))[:3],
        "market_structure": structure
    }