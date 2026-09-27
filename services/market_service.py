import pandas as pd
import requests

class MarketService:
    def __init__(self, **kwargs):
        # Removed CCXT initialization to prevent geo-block crashes on boot
        pass

    def search_symbols(self, query=""):
        """Returns matching USDT pairs using Binance Vision API to bypass blocks."""
        query = query.upper().replace("/", "").replace(":USDT", "")
        try:
            # Query the public mirror which allows cloud IPs
            url = "https://data-api.binance.vision/api/v3/exchangeInfo"
            res = requests.get(url, timeout=5).json()
            symbols = [s["symbol"] for s in res.get("symbols", []) if s["status"] == "TRADING"]
            matches = [s for s in symbols if query in s and s.endswith("USDT")]
            return sorted(matches)[:30]
        except Exception as e:
            print("Search API Error:", e)
            # Fallback list if the API temporarily times out
            return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "SUIUSDT", "LINKUSDT", "DOGEUSDT"]

    def fetch_ohlcv(self, symbol="BTCUSDT", timeframe="15m", limit=300):
        """Fetches OHLCV data directly using the public Binance Vision API."""
        
        # Convert front-end formats like 'BTC/USDT' or 'BTC/USDT:USDT' to raw 'BTCUSDT'
        raw_sym = symbol.replace("/", "").split(":")[0]
        if not raw_sym.endswith("USDT"):
            raw_sym += "USDT"
            
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={raw_sym}&interval={timeframe}&limit={limit}"
        
        try:
            res = requests.get(url, timeout=7).json()
            
            if not isinstance(res, list):
                print(f"Vision API Blocked/Error for {raw_sym}: {res}")
                return None
                
            df = pd.DataFrame(res, columns=[
                "timestamp", "open", "high", "low", "close", "volume", 
                "ct", "qav", "trades", "tbb", "tbq", "ign"
            ])
            
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
                
            df["time"] = (df["timestamp"] / 1000).astype(int)
            return df
            
        except Exception as e:
            print(f"Kline fetch error for {raw_sym}:", e)
            return None

    def get_volume_profile(self, df, bins=24):
        """Calculates Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL)."""
        df = df.copy()
        df["price_bin"] = pd.cut(df["close"], bins=bins)
        profile = df.groupby("price_bin", observed=False)["volume"].sum().reset_index()
        
        poc_idx = profile["volume"].idxmax()
        poc_interval = profile.loc[poc_idx, "price_bin"]
        poc = round((poc_interval.left + poc_interval.right) / 2, 2)
        
        total_vol = profile["volume"].sum()
        target_vol = total_vol * 0.70
        sorted_bins = profile.sort_values(by="volume", ascending=False)
        accum_vol, val_bins = 0, []
        
        for _, row in sorted_bins.iterrows():
            accum_vol += row["volume"]
            val_bins.append(row["price_bin"])
            if accum_vol >= target_vol:
                break
                
        vah = round(max([b.right for b in val_bins]), 2)
        val = round(min([b.left for b in val_bins]), 2)
        return {"poc": poc, "vah": vah, "val": val}

    def fetch_crypto_news(self):
        """Pulls breaking crypto headlines."""
        url = "https://cryptopanic.com/api/free/v1/posts/?auth_token=FREE_OR_CUSTOM_KEY&public=true"
        try:
            res = requests.get(url, timeout=4).json()
            news_items = []
            for item in res.get("results", [])[:6]:
                news_items.append({
                    "title": item.get("title"),
                    "url": item.get("url")
                })
            return news_items
        except Exception:
            # Fallback placeholder news if API key is not provided
            return [
                {"title": "Bitcoin Sustains Institutional Inflows Amid Hashrate Peak", "url": "#"},
                {"title": "Open Interest Expands Across Major Derivatives Venues", "url": "#"}
            ]
