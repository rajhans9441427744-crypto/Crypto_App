import numpy as np

def compute_advanced_smc(df):
    if df is None or len(df) < 30:
        return {}

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values
    times = df["time"].values

    order_blocks = {"bullish": [], "bearish": []}
    fvg = []

    # Fair Value Gaps (FVG)
    for i in range(2, len(df)):
        if lows[i] > highs[i - 2]:  # Bullish FVG
            fvg.append({"type": "BULLISH", "bottom": round(float(highs[i - 2]), 2), "top": round(float(lows[i]), 2)})
        elif highs[i] < lows[i - 2]:  # Bearish FVG
            fvg.append({"type": "BEARISH", "top": round(float(lows[i - 2]), 2), "bottom": round(float(highs[i]), 2)})

    # Order Blocks with 3-candle displacement
    for i in range(len(df) - 4):
        move = (closes[i + 3] - closes[i]) / closes[i]
        if closes[i] < opens[i] and move > 0.012:
            order_blocks["bullish"].append({"price": round(float(highs[i]), 2), "time": int(times[i])})
        elif closes[i] > opens[i] and move < -0.012:
            order_blocks["bearish"].append({"price": round(float(lows[i]), 2), "time": int(times[i])})

    # Break of Structure (BOS) / Change of Character (CHoCH)
    recent_high = np.max(highs[-20:-1])
    recent_low = np.min(lows[-20:-1])
    last_close = closes[-1]
    
    structure = "CONSOLIDATION"
    if last_close > recent_high:
        structure = "BOS: BULLISH EXPANSION"
    elif last_close < recent_low:
        structure = "BOS: BEARISH EXPANSION"

    return {
        "structure": structure,
        "fvg": fvg[-4:],
        "bullish_ob": order_blocks["bullish"][-3:],
        "bearish_ob": order_blocks["bearish"][-3:]
    }