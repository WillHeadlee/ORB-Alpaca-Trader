"""Unit tests for position sizing and PositionTracker."""

import pytest
from trader.position_manager import (
    calculate_shares, build_levels, PositionTracker, PositionLevels
)


class TestCalculateShares:
    def test_basic_sizing(self):
        # equity=10000, entry=100, stop=0.5%, risk=1.5%, no cap
        # stop_distance=0.50, max_risk=150, shares=300
        shares = calculate_shares(
            equity=10_000, entry_price=100.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
            max_position_pct=100,
        )
        assert shares == 300

    def test_smaller_account(self):
        shares = calculate_shares(
            equity=1_000, entry_price=50.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
            max_position_pct=100,
        )
        assert shares == 60

    def test_expensive_stock(self):
        shares = calculate_shares(
            equity=10_000, entry_price=500.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
            max_position_pct=100,
        )
        assert shares == 60

    def test_max_position_cap_applied(self):
        # equity=100000, entry=25, stop=0.5%, risk=1.5%, cap=20%
        # risk-based: stop=0.125, max_risk=1500, shares=12000
        # cap: 100000*20%/25 = 800 shares → cap wins
        shares = calculate_shares(
            equity=100_000, entry_price=25.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
            max_position_pct=20,
        )
        assert shares == 800

    def test_max_position_cap_not_binding(self):
        # equity=100000, entry=500, stop=0.5%, risk=1.5%, cap=20%
        # risk-based: stop=2.50, max_risk=1500, shares=600
        # cap: 100000*20%/500 = 40 → cap wins (600 > 40)
        shares = calculate_shares(
            equity=100_000, entry_price=500.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
            max_position_pct=20,
        )
        assert shares == 40

    def test_zero_entry_price_returns_zero(self):
        shares = calculate_shares(10_000, 0.0, 0.5, 1.5)
        assert shares == 0

    def test_zero_stop_loss_pct_returns_zero(self):
        shares = calculate_shares(10_000, 100.0, 0.0, 1.5)
        assert shares == 0

    def test_shares_are_whole_numbers(self):
        shares = calculate_shares(10_000, 137.50, 0.5, 1.5, max_position_pct=100)
        assert isinstance(shares, int)

    def test_risk_scales_linearly(self):
        shares_low = calculate_shares(10_000, 100.0, 0.5, 1.0, max_position_pct=100)
        shares_high = calculate_shares(10_000, 100.0, 0.5, 2.0, max_position_pct=100)
        assert shares_high == shares_low * 2


class TestBuildLevels:
    def _levels(self, **kwargs):
        defaults = dict(
            symbol="SPY",
            entry_price=450.0,
            equity=10_000.0,
            stop_loss_pct=0.5,
            risk_per_trade_pct=1.5,
            reward_risk_ratio=2.0,
            max_position_pct=100,  # disable cap for these unit tests
        )
        defaults.update(kwargs)
        return build_levels(**defaults)

    def test_stop_loss_below_entry(self):
        lvl = self._levels()
        assert lvl.stop_loss < lvl.entry_price

    def test_take_profit_above_entry(self):
        lvl = self._levels()
        assert lvl.take_profit > lvl.entry_price

    def test_reward_risk_ratio(self):
        lvl = self._levels(reward_risk_ratio=2.0)
        stop_dist = lvl.entry_price - lvl.stop_loss
        tp_dist = lvl.take_profit - lvl.entry_price
        assert abs(tp_dist / stop_dist - 2.0) < 1e-6

    def test_stop_loss_correct_distance(self):
        lvl = self._levels(entry_price=100.0, stop_loss_pct=0.5)
        assert abs(lvl.stop_loss - 99.50) < 0.001

    def test_take_profit_correct_distance(self):
        lvl = self._levels(entry_price=100.0, stop_loss_pct=0.5, reward_risk_ratio=2.0)
        assert abs(lvl.take_profit - 101.00) < 0.001


class TestPositionTracker:
    def _levels(self, symbol="SPY"):
        return PositionLevels(
            symbol=symbol, entry_price=450.0, shares=10,
            stop_loss=447.75, take_profit=454.50,
        )

    def test_open_and_is_open(self):
        tracker = PositionTracker()
        tracker.open(self._levels("SPY"))
        assert tracker.is_open("SPY")

    def test_not_open_before_entry(self):
        tracker = PositionTracker()
        assert not tracker.is_open("SPY")

    def test_has_entered_after_open(self):
        tracker = PositionTracker()
        tracker.open(self._levels("SPY"))
        assert tracker.has_entered("SPY")

    def test_close_removes_position(self):
        tracker = PositionTracker()
        tracker.open(self._levels("SPY"))
        tracker.close("SPY")
        assert not tracker.is_open("SPY")

    def test_has_entered_persists_after_close(self):
        tracker = PositionTracker()
        tracker.open(self._levels("SPY"))
        tracker.close("SPY")
        assert tracker.has_entered("SPY")

    def test_open_symbols(self):
        tracker = PositionTracker()
        tracker.open(self._levels("SPY"))
        tracker.open(self._levels("QQQ"))
        assert set(tracker.open_symbols()) == {"SPY", "QQQ"}

    def test_multiple_symbols_independent(self):
        tracker = PositionTracker()
        tracker.open(self._levels("SPY"))
        tracker.open(self._levels("AAPL"))
        tracker.close("SPY")
        assert not tracker.is_open("SPY")
        assert tracker.is_open("AAPL")
