"""Entry and exit signal generation for the ORB strategy."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from trader.opening_range import OpeningRange
from trader.position_manager import PositionLevels


class Signal(Enum):
    NONE = auto()
    ENTER_LONG = auto()
    EXIT_STOP = auto()
    EXIT_TARGET = auto()
    EXIT_HARD_CLOSE = auto()
    SKIP_BREAKDOWN = auto()
    SKIP_DUPLICATE = auto()
    SKIP_NO_RANGE = auto()
    SKIP_LOW_VOLUME = auto()


@dataclass
class SignalResult:
    signal: Signal
    reason: str


def evaluate_entry(
    symbol: str,
    price: float,
    volume: int,
    opening_range: Optional[OpeningRange],
    already_entered: bool,
    volume_multiplier: float,
) -> SignalResult:
    if already_entered:
        return SignalResult(Signal.SKIP_DUPLICATE, "already entered today")

    if opening_range is None or not opening_range.is_set:
        return SignalResult(Signal.SKIP_NO_RANGE, "opening range not yet set")

    if opening_range.is_breakdown(price):
        return SignalResult(
            Signal.SKIP_BREAKDOWN,
            f"price {price:.2f} < range_low {opening_range.range_low:.2f}, no short",
        )

    if opening_range.is_breakout_up(price, volume, volume_multiplier):
        return SignalResult(
            Signal.ENTER_LONG,
            f"breakout above {opening_range.range_high:.2f} with volume {volume} "
            f"(avg={opening_range.avg_bar_volume:.0f}, mult={volume_multiplier})",
        )

    if volume < opening_range.avg_bar_volume * volume_multiplier and price > opening_range.range_high:
        return SignalResult(
            Signal.SKIP_LOW_VOLUME,
            f"price above range high but volume {volume} below threshold "
            f"{opening_range.avg_bar_volume * volume_multiplier:.0f}",
        )

    return SignalResult(Signal.NONE, "no signal")


def evaluate_exit(
    price: float,
    levels: PositionLevels,
    hard_close: bool = False,
) -> SignalResult:
    if hard_close:
        return SignalResult(Signal.EXIT_HARD_CLOSE, "hard close time reached")

    if price <= levels.stop_loss:
        return SignalResult(
            Signal.EXIT_STOP,
            f"stop-loss hit: price {price:.2f} <= stop {levels.stop_loss:.2f}",
        )

    if price >= levels.take_profit:
        return SignalResult(
            Signal.EXIT_TARGET,
            f"take-profit hit: price {price:.2f} >= target {levels.take_profit:.2f}",
        )

    return SignalResult(Signal.NONE, "holding")
