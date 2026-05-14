"""Alpaca API client — REST orders, account equity, historical bars."""

import os
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, GetOrdersRequest,
    TakeProfitRequest, StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from utils.logger import log


def _is_paper() -> bool:
    mode = os.getenv("ALPACA_MODE", "paper").lower()
    return mode != "live"


class AlpacaClient:
    def __init__(self) -> None:
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise EnvironmentError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")

        paper = _is_paper()
        self.paper = paper
        mode_label = "PAPER" if paper else "LIVE"
        log.info(f"Alpaca client initialised in {mode_label} mode")

        self._trading = TradingClient(api_key, secret_key, paper=paper)
        self._data = StockHistoricalDataClient(api_key, secret_key)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_equity(self) -> float:
        account = self._trading.get_account()
        return float(account.equity)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def submit_market_buy(self, symbol: str, qty: int) -> Optional[object]:
        """Plain market buy with no attached stops (use submit_bracket_buy instead)."""
        if qty < 1:
            log.warning(f"Skipping order for {symbol}: qty={qty} is invalid")
            return None
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        order = self._trading.submit_order(req)
        log.info(f"Order submitted: BUY {qty} {symbol} (id={order.id})")
        return order

    def submit_bracket_buy(
        self,
        symbol: str,
        qty: int,
        take_profit_price: float,
        stop_loss_price: float,
    ) -> Optional[object]:
        """Market buy with broker-side take-profit limit and stop-loss stop order."""
        if qty < 1:
            log.warning(f"Skipping bracket order for {symbol}: qty={qty} is invalid")
            return None
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
            stop_loss=StopLossRequest(stop_price=round(stop_loss_price, 2)),
        )
        order = self._trading.submit_order(req)
        log.info(
            f"Bracket order submitted: BUY {qty} {symbol} | "
            f"stop={stop_loss_price:.2f} target={take_profit_price:.2f} "
            f"(id={order.id})"
        )
        return order

    def submit_market_sell(self, symbol: str, qty: int) -> Optional[object]:
        if qty < 1:
            return None
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self._trading.submit_order(req)
        log.info(f"Order submitted: SELL {qty} {symbol} (id={order.id})")
        return order

    def close_all_positions(self) -> None:
        """Market-sell every open position (hard close)."""
        log.info("Closing all open positions (hard close)")
        self._trading.close_all_positions(cancel_orders=True)

    def get_open_positions(self) -> list:
        return self._trading.get_all_positions()

    def update_stop_loss(self, stop_order_id: str, new_stop_price: float) -> bool:
        """Move a bracket stop-loss leg to a new price via Alpaca order replace API."""
        from alpaca.trading.requests import ReplaceOrderRequest
        try:
            self._trading.replace_order_by_id(
                stop_order_id,
                ReplaceOrderRequest(stop_price=round(new_stop_price, 2)),
            )
            log.info(f"Stop order {stop_order_id} moved to {new_stop_price:.2f}")
            return True
        except Exception as exc:
            log.warning(f"Could not update stop loss: {exc}")
            return False

    def position_exists(self, symbol: str) -> bool:
        """Return True if a position for symbol is currently open on Alpaca.
        get_open_position raises APIError 40410000 when the position doesn't exist.
        Any other error (5xx, timeout) is re-raised so the caller can retry
        rather than silently treating an open position as closed.
        """
        from alpaca.common.exceptions import APIError
        try:
            self._trading.get_open_position(symbol)
            return True
        except APIError as e:
            if e.code == 40410000:
                return False
            raise

    # ------------------------------------------------------------------
    # Historical bars (used for average volume baseline)
    # ------------------------------------------------------------------

    def get_recent_bars(self, symbol: str, limit: int = 20):
        """Return up to `limit` daily bars for volume baseline.

        Uses daily timeframe (available on free IEX subscription).
        Each bar's volume is divided by 390 (market minutes per day)
        to give a per-minute average comparable to 1-min breakout bars.
        """
        from datetime import datetime, timedelta
        import pytz

        et = pytz.timezone("America/New_York")
        end = datetime.now(et)
        start = end - timedelta(days=limit * 2)  # enough trading days

        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            limit=limit,
        )
        bars = self._data.get_stock_bars(req)
        daily = bars.get(symbol, [])

        # Wrap each bar so .volume returns the per-minute equivalent
        class _ScaledBar:
            def __init__(self, b):
                self.volume = int(b.volume / 390)

        return [_ScaledBar(b) for b in daily]
