"""Unit tests for OpeningRange detection logic."""

import pytest
from datetime import datetime
from trader.opening_range import Bar, OpeningRange, OpeningRangeTracker


def make_bar(high: float, low: float, volume: int, close: float | None = None) -> Bar:
    return Bar(
        timestamp=datetime(2024, 1, 2, 9, 31),
        open=(high + low) / 2,
        high=high,
        low=low,
        close=close if close is not None else (high + low) / 2,
        volume=volume,
    )


class TestOpeningRange:
    def test_update_expands_high(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.update(make_bar(high=452.0, low=446.0, volume=1200))
        assert orb.range_high == 452.0

    def test_update_contracts_low(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.update(make_bar(high=448.0, low=443.0, volume=1100))
        assert orb.range_low == 443.0

    def test_avg_bar_volume(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.update(make_bar(high=451.0, low=446.0, volume=2000))
        assert orb.avg_bar_volume == 1500.0

    def test_not_set_before_finalise(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        assert not orb.is_set

    def test_set_after_finalise(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.finalise()
        assert orb.is_set

    def test_breakout_up_requires_finalise(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        # Not finalised yet
        assert not orb.is_breakout_up(451.0, 2000, 1.2)

    def test_breakout_up_price_and_volume(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.finalise()
        # Price above high, volume above avg * 1.2
        assert orb.is_breakout_up(451.0, 1200, 1.2)

    def test_breakout_up_low_volume_fails(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.finalise()
        # Price above high but volume too low
        assert not orb.is_breakout_up(451.0, 500, 1.2)

    def test_breakout_up_price_not_above_high(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.finalise()
        assert not orb.is_breakout_up(449.0, 2000, 1.2)

    def test_breakdown_below_low(self):
        orb = OpeningRange("SPY")
        orb.update(make_bar(high=450.0, low=445.0, volume=1000))
        orb.finalise()
        assert orb.is_breakdown(444.0)
        assert not orb.is_breakdown(446.0)

    def test_single_bar_range(self):
        orb = OpeningRange("AAPL")
        orb.update(make_bar(high=180.0, low=175.0, volume=5000))
        orb.finalise()
        assert orb.range_high == 180.0
        assert orb.range_low == 175.0
        assert orb.bar_count == 1


class TestOpeningRangeTracker:
    def test_multi_symbol_update(self):
        tracker = OpeningRangeTracker(["SPY", "QQQ"])
        tracker.update("SPY", make_bar(450.0, 445.0, 1000))
        tracker.update("QQQ", make_bar(380.0, 375.0, 800))
        assert tracker.get("SPY").range_high == 450.0
        assert tracker.get("QQQ").range_low == 375.0

    def test_finalise_all(self):
        tracker = OpeningRangeTracker(["SPY", "QQQ"])
        tracker.update("SPY", make_bar(450.0, 445.0, 1000))
        tracker.update("QQQ", make_bar(380.0, 375.0, 800))
        tracker.finalise_all()
        assert tracker.all_set()

    def test_no_update_after_finalise(self):
        tracker = OpeningRangeTracker(["SPY"])
        tracker.update("SPY", make_bar(450.0, 445.0, 1000))
        tracker.finalise("SPY")
        tracker.update("SPY", make_bar(500.0, 400.0, 9999))  # should be ignored
        assert tracker.get("SPY").range_high == 450.0

    def test_unknown_symbol_ignored(self):
        tracker = OpeningRangeTracker(["SPY"])
        tracker.update("NVDA", make_bar(700.0, 690.0, 1000))  # not in watchlist
        assert tracker.get("NVDA") is None
