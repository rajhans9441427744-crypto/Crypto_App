# app.py
from flask import Flask, render_template, jsonify, request
from cache import db
from engine import start_engine, SYMBOLS

app = Flask(__name__)

# Start all background workers inside the Flask process
start_engine()

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/markets")
def markets():
    return jsonify(SYMBOLS)

@app.route("/api/dashboard")
def get_dashboard():
    symbol = request.args.get("symbol", "BTCUSDT").upper()
    data = db.get_dashboard(symbol)
    if not data:
        # Fallback if engine is still filling the initial cache
        live = db.get_live(symbol)
        return jsonify({
            "status": "warming_up",
            "symbol": symbol,
            "price": live.get("price", 0),
            "change": live.get("change", 0)
        }), 200
    return jsonify(data)

@app.route("/api/chart")
def get_chart():
    symbol = request.args.get("symbol", "BTCUSDT").upper()
    interval = request.args.get("interval", "15m")
    df = db.get_candles(symbol, interval)
    if df is None or df.empty:
        return jsonify([])

    records = []
    for _, row in df.tail(300).iterrows():
        # Ensure timestamp is an integer in seconds
        t = int(row["time"])
        if t > 1000000000000:
            t = int(t / 1000)
            
        records.append({
            "time": t,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"])
        })
    return jsonify(records)

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "live_cache": len(db.live),
        "scanner_cache": len(db.scanner),
        "dashboard_cache": len(db.dashboard)
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
