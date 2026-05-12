"""Unit tests for position sizing and PositionTracker."""

import pytest
from trader.position_manager import (
    calculate_shares, build_levels, PositionTracker, PositionLevels
)


class TestCalculateShares:
    def test_basic_sizing(self):
        # equity=10000, entry=100, stop_loss_pct=0.5, risk=1.5%
        # stop_distance = 100 * 0.005 = 0.50
        # max_risk = 10000 * 0.015 = 150
        # shares = floor(150 / 0.50) = 300
        shares = calculate_shares(
            equity=10_000, entry_price=100.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
        )
        assert shares == 300

    def test_smaller_account(self):
        # equity=1000, entry=50, stop_loss_pct=0.5, risk=1.5%
        # stop_distance = 50 * 0.005 = 0.25
        # max_risk = 1000 * 0.015 = 15
        # shares = floor(15 / 0.25) = 60
        shares = calculate_shares(
            equity=1_000, entry_price=50.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
        )
        assert shares == 60

    def test_expensive_stock(self):
        # equity=10000, entry=500, stop_loss_pct=0.5, risk=1.5%
        # stop_distance = 500 * 0.005 = 2.50
        # max_risk = 150
        # shares = floor(150 / 2.50) = 60
        shares = calculate_shares(
            equity=10_000, entry_price=500.0,
            stop_loss_pct=0.5, risk_per_trade_pct=1.5,
        )
        assert shares == 60

    def test_zero_entry_price_returns_zero(self):
        shares = calculate_shares(10_000, 0.0, 0.5, 1.5)
        assert shares == 0

    def test_zero_stop_loss_pct_returns_zero(self):
        shares = calculate_shares(10_000, 100.0, 0.0, 1.5)
        assert shares == 0

    def test_shares_are_whole_numbers(self):
        # result must always be int
        shares = calculate_shares(10_000, 137.50, 0.5, 1.5)
        assert isinstance(shares, int)

    def test_risk_scales_linearly(self):
        shares_low = calculate_shares(10_000, 100.0, 0.5, 1.0)
        shares_high = calculate_shares(10_000, 100.0, 0.5, 2.0)
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
