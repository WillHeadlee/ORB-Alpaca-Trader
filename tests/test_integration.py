"""Integration tests: SessionManager strategy pipeline with synthetic bar replay.

Tests _on_bar() directly — bypasses WebSocket and market-hours scheduling
while exercising the full ORB formation → entry signal → order submission →
exit signal pipeline.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import patch

from trader.session_manager import SessionManager


# ── Synthetic bar ──────────────────────────────────────────────────────────────

@dataclass
class FakeBar:
    symbol: str
    close: float
    volume: int
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.high == 0.0:
            self.high = self.close + 0.10
        if self.low == 0.0:
            self.low = self.close - 0.10


# ── Fake Alpaca order ──────────────────────────────────────────────────────────

@dataclass
class FakeOrder:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ── Mock Alpaca client ─────────────────────────────────────────────────────────

class MockAlpacaClient:
    def __init__(self):
        self.bracket_buys: list[dict] = []
        self.market_sells: list[dict] = []

    def get_equity(self) -> float:
        return 100_000.0

    def get_recent_bars(self, symbol: str, limit: int = 20):
        return []

    def submit_bracket_buy(self, symbol, qty, take_profit, stop_loss):
        order = FakeOrder()
        self.bracket_buys.append({
            "symbol": symbol, "qty": qty,
            "take_profit": take_profit, "stop_loss": stop_loss,
            "order_id": order.id,
        })
        return order

    def submit_market_sell(self, symbol, qty):
        order = FakeOrder()
        self.market_sells.append({"symbol": symbol, "qty": qty, "order_id": order.id})
        return order

    def get_open_positions(self):
        return []

    def close_all_positions(self):
        pass


# ── Config ─────────────────────────────────────────────────────────────────────

TEST_CONFIG = {
    "trading": {"mode": "paper", "watchlist": ["SPY"], "screener_top_n": 20},
    "strategy": {
        "opening_range_minutes": 15,
        "risk_per_trade_pct": 1.5,
        "stop_loss_pct": 0.5,
        "reward_risk_ratio": 2.0,
        "hard_close_time": "15:55",
        "volume_multiplier": 1.2,
        "max_position_pct": 20.0,
    },
}

# ORB parameters used across tests
ORB_HIGH = 450.0
ORB_LOW = 445.0
ORB_BASE_VOL = 1_000    # avg volume per ORB bar
ENTRY_PRICE = 451.0     # breakout close price
STOP_LOSS = ENTRY_PRICE * (1 - 0.005)    # ~448.75
TAKE_PROFIT = ENTRY_PRICE + (ENTRY_PRICE - STOP_LOSS) * 2.0  # ~455.50


import pytest

@pytest.fixture
def session():
    """SessionManager with MockAlpacaClient; patches active for the whole test."""
    mock_client = MockAlpacaClient()
    with patch('trader.session_manager.AlpacaClient', return_value=mock_client), \
         patch('trader.session_manager._load_screener_watchlist', return_value=[]), \
         patch('trader.session_manager.log_trade'), \
         patch('trader.session_manager.save_daily_summary'):
        manager = SessionManager(TEST_CONFIG)
        yield manager, mock_client


def run(coro):
    return asyncio.run(coro)


def feed_orb_bars(manager: "SessionManager", n: int = 15) -> None:
    """Feed n ORB-window bars building range_high=450, range_low=445."""
    for _ in range(n):
        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=447.0, volume=ORB_BASE_VOL,
            high=ORB_HIGH, low=ORB_LOW,
        )))


def finalise_orb(manager: "SessionManager") -> None:
    manager.orb_tracker.finalise_all()
    manager._orb_done = True


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestSessionManagerIntegration:

    def test_orb_range_builds_correctly(self, session):
        manager, _ = session
        run(manager._on_bar("SPY", FakeBar("SPY", close=447.0, volume=1000, high=450.0, low=445.0)))
        run(manager._on_bar("SPY", FakeBar("SPY", close=448.0, volume=1000, high=449.0, low=445.5)))
        run(manager._on_bar("SPY", FakeBar("SPY", close=446.0, volume=1000, high=448.0, low=444.0)))

        orb = manager.orb_tracker.get("SPY")
        assert orb.range_high == 450.0
        assert orb.range_low == 444.0
        assert manager._orb_done is False

    def test_no_entry_before_orb_done(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        assert len(mock.bracket_buys) == 0

    def test_no_entry_inside_range(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        finalise_orb(manager)
        for _ in range(5):
            run(manager._on_bar("SPY", FakeBar("SPY", close=447.5, volume=ORB_BASE_VOL * 2)))
        assert len(mock.bracket_buys) == 0

    def test_breakout_triggers_entry(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        finalise_orb(manager)

        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=ENTRY_PRICE, volume=int(ORB_BASE_VOL * 1.5),
            high=452.0, low=450.5,
        )))

        assert len(mock.bracket_buys) == 1
        order = mock.bracket_buys[0]
        assert order["symbol"] == "SPY"
        assert order["qty"] >= 1
        assert order["stop_loss"] < ENTRY_PRICE
        assert order["take_profit"] > ENTRY_PRICE

    def test_low_volume_breakout_skipped(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        finalise_orb(manager)

        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=ENTRY_PRICE, volume=500,
            high=452.0, low=450.5,
        )))

        assert len(mock.bracket_buys) == 0

    def test_stop_loss_triggers_exit(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        finalise_orb(manager)

        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=ENTRY_PRICE, volume=int(ORB_BASE_VOL * 1.5),
            high=452.0, low=450.5,
        )))
        assert len(mock.bracket_buys) == 1

        below_stop = STOP_LOSS - 0.50
        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=below_stop, volume=500,
            high=below_stop + 0.1, low=below_stop - 0.5,
        )))

        assert len(mock.market_sells) == 1
        assert not manager.pos_tracker.is_open("SPY")

    def test_take_profit_triggers_exit(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        finalise_orb(manager)

        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=ENTRY_PRICE, volume=int(ORB_BASE_VOL * 1.5),
            high=452.0, low=450.5,
        )))
        assert len(mock.bracket_buys) == 1

        above_tp = TAKE_PROFIT + 0.50
        run(manager._on_bar("SPY", FakeBar(
            "SPY", close=above_tp, volume=500,
            high=above_tp + 0.1, low=above_tp - 0.1,
        )))

        assert len(mock.market_sells) == 1
        assert not manager.pos_tracker.is_open("SPY")

    def test_no_duplicate_entry(self, session):
        manager, mock = session
        feed_orb_bars(manager)
        finalise_orb(manager)

        breakout = FakeBar(
            "SPY", close=ENTRY_PRICE, volume=int(ORB_BASE_VOL * 1.5),
            high=452.0, low=450.5,
        )
        run(manager._on_bar("SPY", breakout))
        run(manager._on_bar("SPY", breakout))

        assert len(mock.bracket_buys) == 1
