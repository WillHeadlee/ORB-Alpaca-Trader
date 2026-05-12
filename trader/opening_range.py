"""Opening Range Breakout detection — tracks high/low during the observation window."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class OpeningRange:
    symbol: str
    range_high: float = float("-inf")
    range_low: float = float("inf")
    total_volume: int = 0
    bar_count: int = 0
    is_set: bool = False

    def update(self, bar: Bar) -> None:
        if bar.high > self.range_high:
            self.range_high = bar.high
        if bar.low < self.range_low:
            self.range_low = bar.low
        self.total_volume += bar.volume
        self.bar_count += 1

    def finalise(self) -> None:
        self.is_set = True

    @property
    def avg_bar_volume(self) -> float:
        return self.total_volume / self.bar_count if self.bar_count else 0.0

    def is_breakout_up(self, price: float, volume: int, volume_multiplier: float) -> bool:
        """True when price exceeds range high AND volume is above average."""
        if not self.is_set:
            return False
        return (
            price > self.range_high
            and volume >= self.avg_bar_volume * volume_multiplier
        )

    def is_breakdown(self, price: float) -> bool:
        return self.is_set and price < self.range_low


class OpeningRangeTracker:
    """Manages OpeningRange objects for a list of symbols."""

    def __init__(self, symbols: list[str]) -> None:
        self._ranges: dict[str, OpeningRange] = {s: OpeningRange(s) for s in symbols}

    def update(self, symbol: str, bar: Bar) -> None:
        if symbol in self._ranges and not self._ranges[symbol].is_set:
            self._ranges[symbol].update(bar)

    def finalise(self, symbol: str) -> None:
        if symbol in self._ranges:
            self._ranges[symbol].finalise()

    def finalise_all(self) -> None:
        for r in self._ranges.values():
            r.finalise()

    def get(self, symbol: str) -> Optional[OpeningRange]:
        return self._ranges.get(symbol)

    def all_set(self) -> bool:
        return all(r.is_set for r in self._ranges.values())
