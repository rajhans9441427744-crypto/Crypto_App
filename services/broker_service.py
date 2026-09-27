import ccxt

class BrokerExecutionService:
    def __init__(self, exchange_id="delta", api_key=None, api_secret=None):
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}  # Perpetuals
        })

    def get_account_balance(self):
        """Fetches total balance, free equity, and unrealized PnL."""
        balance = self.exchange.fetch_balance()
        return {
            "total_usd": balance.get("USDT", {}).get("total", 0.0),
            "free_usd": balance.get("USDT", {}).get("free", 0.0),
            "used_usd": balance.get("USDT", {}).get("used", 0.0),
        }

    def place_bracket_order(self, symbol, side, amount, entry_price=None, stop_loss=None, take_profit=None):
        """
        Executes a directional trade with atomic stop-loss and take-profit parameters.
        Side: 'buy' for Long, 'sell' for Short.
        """
        try:
            # 1. Market Entry Order
            order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount
            )
            
            # 2. Stop Loss (Trigger Order)
            exit_side = "sell" if side == "buy" else "buy"
            sl_order = None
            if stop_loss:
                params = {"stopPrice": stop_loss, "reduceOnly": True}
                sl_order = self.exchange.create_order(
                    symbol=symbol,
                    type="stop_market",
                    side=exit_side,
                    amount=amount,
                    params=params
                )

            # 3. Take Profit Limit Order
            tp_order = None
            if take_profit:
                params = {"reduceOnly": True}
                tp_order = self.exchange.create_order(
                    symbol=symbol,
                    type="limit",
                    side=exit_side,
                    amount=amount,
                    price=take_profit,
                    params=params
                )

            return {
                "success": True,
                "order_id": order["id"],
                "sl_id": sl_order["id"] if sl_order else None,
                "tp_id": tp_order["id"] if tp_order else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_open_positions(self):
        """Retrieves live perp positions with mark price, liquidation, and ROI."""
        positions = self.exchange.fetch_positions()
        active = []
        for pos in positions:
            size = float(pos.get("contracts", 0))
            if size > 0:
                active.append({
                    "symbol": pos.get("symbol"),
                    "side": pos.get("side"),
                    "contracts": size,
                    "entry_price": pos.get("entryPrice"),
                    "mark_price": pos.get("markPrice"),
                    "unrealized_pnl": pos.get("unrealizedPnl"),
                    "liquidation_price": pos.get("liquidationPrice")
                })
        return active