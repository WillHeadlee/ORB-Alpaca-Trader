"""Unit tests for entry/exit signal generation."""

import pytest
from trader.opening_range import OpeningRange
from trader.position_manager import PositionLevels
from trader.strategy import Signal, evaluate_entry, evaluate_exit


def make_orb(high=450.0, low=445.0, avg_vol=1000, finalised=True) -> OpeningRange:
    orb = OpeningRange("SPY")
    orb.range_high = high
    orb.range_low = low
    orb.total_volume = avg_vol
    orb.bar_count = 1
    if finalised:
        orb.finalise()
    return orb


def make_levels(entry=450.0, stop=447.75, tp=454.50) -> PositionLevels:
    return PositionLevels(
        symbol="SPY", entry_price=entry,
        shares=10, stop_loss=stop, take_profit=tp,
    )


class TestEvaluateEntry:
    def test_enter_on_valid_breakout(self):
        orb = make_orb(high=450.0, avg_vol=1000)
        result = evaluate_entry("SPY", price=451.0, volume=1200,
                                opening_range=orb, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.ENTER_LONG

    def test_skip_duplicate_entry(self):
        orb = make_orb()
        result = evaluate_entry("SPY", price=451.0, volume=2000,
                                opening_range=orb, already_entered=True,
                                volume_multiplier=1.2)
        assert result.signal == Signal.SKIP_DUPLICATE

    def test_skip_no_range(self):
        result = evaluate_entry("SPY", price=451.0, volume=2000,
                                opening_range=None, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.SKIP_NO_RANGE

    def test_skip_range_not_finalised(self):
        orb = make_orb(finalised=False)
        result = evaluate_entry("SPY", price=451.0, volume=2000,
                                opening_range=orb, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.SKIP_NO_RANGE

    def test_skip_breakdown(self):
        orb = make_orb(low=445.0)
        result = evaluate_entry("SPY", price=444.0, volume=2000,
                                opening_range=orb, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.SKIP_BREAKDOWN

    def test_skip_low_volume_breakout(self):
        orb = make_orb(high=450.0, avg_vol=1000)
        result = evaluate_entry("SPY", price=451.0, volume=500,
                                opening_range=orb, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.SKIP_LOW_VOLUME

    def test_no_signal_inside_range(self):
        orb = make_orb(high=450.0, low=445.0, avg_vol=1000)
        result = evaluate_entry("SPY", price=447.0, volume=2000,
                                opening_range=orb, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.NONE

    def test_exact_high_not_breakout(self):
        orb = make_orb(high=450.0, avg_vol=1000)
        result = evaluate_entry("SPY", price=450.0, volume=2000,
                                opening_range=orb, already_entered=False,
                                volume_multiplier=1.2)
        assert result.signal == Signal.NONE


class TestEvaluateExit:
    def test_stop_loss_hit(self):
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=447.0, levels=levels)
        assert result.signal == Signal.EXIT_STOP

    def test_exact_stop_loss(self):
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=447.75, levels=levels)
        assert result.signal == Signal.EXIT_STOP

    def test_take_profit_hit(self):
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=455.0, levels=levels)
        assert result.signal == Signal.EXIT_TARGET

    def test_exact_take_profit(self):
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=454.50, levels=levels)
        assert result.signal == Signal.EXIT_TARGET

    def test_holding_between_levels(self):
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=452.0, levels=levels)
        assert result.signal == Signal.NONE

    def test_hard_close_overrides_all(self):
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=452.0, levels=levels, hard_close=True)
        assert result.signal == Signal.EXIT_HARD_CLOSE

    def test_hard_close_at_stop_loss(self):
        """Hard close flag takes priority even when price is at stop."""
        levels = make_levels(entry=450.0, stop=447.75, tp=454.50)
        result = evaluate_exit(price=447.0, levels=levels, hard_close=True)
        assert result.signal == Signal.EXIT_HARD_CLOSE
