# cache.py
from threading import Lock

class CacheStore:
    def __init__(self):
        self._lock = Lock()
        self.live = {}         # { symbol: { price, change, high, low, volume } }
        self.candles = {}      # { symbol: { interval: DataFrame } }
        self.analysis = {}     # { symbol: { interval: DataFrame } }
        self.scanner = {}      # { symbol: { interval: { probability, signal, ... } } }
        self.dashboard = {}    # { symbol: final_payload }
        self.sentiment = {}    # { symbol: { fear_greed, open_interest, funding } }

    def set_live(self, symbol, data):
        with self._lock:
            self.live[symbol.upper()] = data

    def get_live(self, symbol):
        with self._lock:
            return self.live.get(symbol.upper(), {})

    def set_candles(self, symbol, interval, df):
        with self._lock:
            sym = symbol.upper()
            if sym not in self.candles:
                self.candles[sym] = {}
            self.candles[sym][interval] = df

    def get_candles(self, symbol, interval):
        with self._lock:
            return self.candles.get(symbol.upper(), {}).get(interval)

    def set_analysis(self, symbol, interval, df):
        with self._lock:
            sym = symbol.upper()
            if sym not in self.analysis:
                self.analysis[sym] = {}
            self.analysis[sym][interval] = df

    def get_analysis(self, symbol, interval):
        with self._lock:
            return self.analysis.get(symbol.upper(), {}).get(interval)

    def set_scanner(self, symbol, data):
        with self._lock:
            self.scanner[symbol.upper()] = data

    def get_scanner(self, symbol):
        with self._lock:
            return self.scanner.get(symbol.upper(), {})

    def set_dashboard(self, symbol, data):
        with self._lock:
            self.dashboard[symbol.upper()] = data

    def get_dashboard(self, symbol):
        with self._lock:
            return self.dashboard.get(symbol.upper())

    def set_sentiment(self, symbol, data):
        with self._lock:
            self.sentiment[symbol.upper()] = data

    def get_sentiment(self, symbol):
        with self._lock:
            return self.sentiment.get(symbol.upper(), {})

# Global singleton
db = CacheStore()