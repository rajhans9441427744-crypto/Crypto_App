# indicators/technicals.py
import pandas as pd
import numpy as np

def compute_technicals(df):
    if df is None or len(df) < 50:
        return df

    df = df.copy()

    # 1. EMAs
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["EMA_20"] = df["EMA20"]  # Alias for backward compatibility

    # 2. MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]

    # 3. RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # 4. ATR & ADX
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(window=14).mean()

    plus_dm = df["high"].diff()
    minus_dm = -df["low"].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / (df["ATR"] + 1e-9))
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / (df["ATR"] + 1e-9))
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)) * 100
    df["ADX"] = dx.rolling(window=14).mean()
    df["+DI"] = plus_di
    df["-DI"] = minus_di

    # 5. VWAP
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    vol_cum = df["volume"].cumsum()
    df["VWAP"] = (typical * df["volume"]).cumsum() / (vol_cum + 1e-9)

    # 6. Supertrend (10, 3)
    hl2 = (df["high"] + df["low"]) / 2.0
    upperband = hl2 + 3.0 * df["ATR"]
    lowerband = hl2 - 3.0 * df["ATR"]
    supertrend = [np.nan] * len(df)
    direction = [True] * len(df)

    for i in range(1, len(df)):
        if df["close"].iloc[i] > upperband.iloc[i - 1]:
            direction[i] = True
        elif df["close"].iloc[i] < lowerband.iloc[i - 1]:
            direction[i] = False
        else:
            direction[i] = direction[i - 1]
            if direction[i]:
                lowerband.iloc[i] = max(lowerband.iloc[i], lowerband.iloc[i - 1])
            else:
                upperband.iloc[i] = min(upperband.iloc[i], upperband.iloc[i - 1])
        supertrend[i] = lowerband.iloc[i] if direction[i] else upperband.iloc[i]

    df["SUPERTREND"] = supertrend
    df["ST_DIRECTION"] = direction

    return df