"""Position sizing, stop-loss / take-profit calculation, and open-position tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from utils.time_utils import now_et


@dataclass
class PositionLevels:
    symbol: str
    entry_price: float
    shares: int
    stop_loss: float
    take_profit: float
    entry_time: datetime = field(default_factory=now_et)
    stop_order_id: Optional[str] = None  # bracket stop-loss child order ID
    breakeven_set: bool = False           # True once stop moved to entry price


def calculate_shares(
    equity: float,
    entry_price: float,
    stop_loss_pct: float,
    risk_per_trade_pct: float,
    max_position_pct: float = None,
) -> int:
    """
    Return shares sized so stop-loss costs at most risk_per_trade_pct % of equity.
    If max_position_pct is set, also caps total position cost to that % of equity.

    stop_loss_distance = entry_price * stop_loss_pct / 100
    max_dollar_risk    = equity * risk_per_trade_pct / 100
    shares             = floor(max_dollar_risk / stop_loss_distance)
    """
    if entry_price <= 0 or stop_loss_pct <= 0:
        return 0
    stop_distance = entry_price * stop_loss_pct / 100.0
    max_risk = equity * risk_per_trade_pct / 100.0
    shares = int(max_risk / stop_distance)
    if max_position_pct is not None:
        max_shares = int(equity * max_position_pct / 100.0 / entry_price)
        shares = min(shares, max_shares)
    return max(shares, 0)


def build_levels(
    symbol: str,
    entry_price: float,
    equity: float,
    stop_loss_pct: float,
    risk_per_trade_pct: float,
    reward_risk_ratio: float,
    max_position_pct: float = None,
) -> PositionLevels:
    shares = calculate_shares(equity, entry_price, stop_loss_pct, risk_per_trade_pct, max_position_pct)
    stop_distance = entry_price * stop_loss_pct / 100.0
    stop_loss = entry_price - stop_distance
    take_profit = entry_price + stop_distance * reward_risk_ratio
    return PositionLevels(
        symbol=symbol,
        entry_price=entry_price,
        shares=shares,
        stop_loss=round(stop_loss, 4),
        take_profit=round(take_profit, 4),
    )


class PositionTracker:
    """Tracks open positions and prevents duplicate entries."""

    def __init__(self) -> None:
        self._positions: dict[str, PositionLevels] = {}
        self._entered_today: set[str] = set()

    def has_entered(self, symbol: str) -> bool:
        return symbol in self._entered_today

    def open(self, levels: PositionLevels) -> None:
        self._positions[levels.symbol] = levels
        self._entered_today.add(levels.symbol)

    def close(self, symbol: str) -> Optional[PositionLevels]:
        return self._positions.pop(symbol, None)

    def get(self, symbol: str) -> Optional[PositionLevels]:
        return self._positions.get(symbol)

    def open_symbols(self) -> list[str]:
        return list(self._positions.keys())

    def is_open(self, symbol: str) -> bool:
        return symbol in self._positions
