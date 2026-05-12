"""Session lifecycle — coordinates ORB phases, bar processing, and hard close."""

import asyncio
from datetime import datetime
from typing import Any

from alpaca.data.models import Bar as AlpacaBar

from trader.alpaca_client import AlpacaClient
from trader.opening_range import OpeningRangeTracker, Bar as ORBBar
from trader.position_manager import PositionTracker, build_levels
from trader.strategy import Signal, evaluate_entry, evaluate_exit
from trader.data_feed import DataFeed
from utils.logger import log, SessionStats, TradeRecord
from utils.metrics import init_db, log_trade, save_daily_summary
from utils.notifier import notify_daily_summary
from utils.time_utils import (
    now_et, opening_range_end, hard_close_dt, seconds_until,
    is_market_open, wait_until_market_open,
)


class SessionManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.cfg = config
        self.strategy = config["strategy"]
        self.watchlist: list[str] = config["trading"]["watchlist"]

        self.client = AlpacaClient()
        self.orb_tracker = OpeningRangeTracker(self.watchlist)
        self.pos_tracker = PositionTracker()
        self.stats = SessionStats()

        self._orb_done = False
        self._hard_closed = False
        self._feed: DataFeed | None = None
        self._volume_baselines: dict[str, float] = {}  # symbol → historical avg vol
        init_db()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(self) -> None:
        log.info(f"Session starting. Watchlist: {self.watchlist}")

        # Block here until 9:30 AM ET if we're outside market hours
        await wait_until_market_open()

        # Seed historical volume baseline for each symbol (uses prior-day bars)
        self._load_volume_baselines()

        # Compute timers *after* waking so dates are correct for today
        orb_end = opening_range_end(self.strategy["opening_range_minutes"])
        hard_close = hard_close_dt(self.strategy["hard_close_time"])
        log.info(f"ORB window ends at {orb_end.strftime('%H:%M:%S')} ET")
        log.info(f"Hard close at {hard_close.strftime('%H:%M:%S')} ET")

        self._feed = DataFeed(self.watchlist, self._on_bar)

        # Schedule hard close
        asyncio.create_task(self._schedule_hard_close(hard_close))
        # Schedule ORB finalisation
        asyncio.create_task(self._schedule_orb_finalise(orb_end))

        try:
            await self._feed.start()
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    # ------------------------------------------------------------------
    # Volume baseline (fetched once at session start from historical bars)
    # ------------------------------------------------------------------

    def _load_volume_baselines(self) -> None:
        for symbol in self.watchlist:
            try:
                bars = self.client.get_recent_bars(symbol, limit=20)
                if bars:
                    avg = sum(int(b.volume) for b in bars) / len(bars)
                    self._volume_baselines[symbol] = avg
                    log.info(f"{symbol}: historical avg volume = {avg:.0f}")
            except Exception as exc:
                log.warning(f"{symbol}: could not load volume baseline — {exc}")

    def _volume_multiplier_threshold(self, symbol: str) -> float:
        """Return the effective volume threshold for a breakout bar."""
        baseline = self._volume_baselines.get(symbol)
        if baseline:
            return baseline * self.strategy["volume_multiplier"]
        # Fall back to ORB bar average if no historical data
        orb = self.orb_tracker.get(symbol)
        return (orb.avg_bar_volume * self.strategy["volume_multiplier"]) if orb else 0.0

    # ------------------------------------------------------------------
    # Bar handler (called by DataFeed for every 1-min bar)
    # ------------------------------------------------------------------

    async def _on_bar(self, symbol: str, bar: AlpacaBar) -> None:
        if self._hard_closed:
            return

        orb_bar = ORBBar(
            timestamp=bar.timestamp,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=int(bar.volume),
        )

        # Accumulate ORB during observation window
        if not self._orb_done:
            self.orb_tracker.update(symbol, orb_bar)
            return

        price = float(bar.close)
        volume = int(bar.volume)

        # Exit checks for open positions
        if self.pos_tracker.is_open(symbol):
            await self._check_exit(symbol, price)
            return

        # Entry checks
        await self._check_entry(symbol, price, volume)

    # ------------------------------------------------------------------
    # Entry / exit logic
    # ------------------------------------------------------------------

    async def _check_entry(self, symbol: str, price: float, volume: int) -> None:
        orb = self.orb_tracker.get(symbol)
        # Use historical avg volume baseline; falls back to ORB-bar average
        vol_threshold = self._volume_multiplier_threshold(symbol)
        # evaluate_entry expects a multiplier, so express threshold as ratio to ORB avg
        orb_avg = orb.avg_bar_volume if (orb and orb.avg_bar_volume > 0) else 1.0
        effective_multiplier = vol_threshold / orb_avg if orb_avg else self.strategy["volume_multiplier"]

        result = evaluate_entry(
            symbol=symbol,
            price=price,
            volume=volume,
            opening_range=orb,
            already_entered=self.pos_tracker.has_entered(symbol),
            volume_multiplier=effective_multiplier,
        )

        if result.signal == Signal.ENTER_LONG:
            equity = self.client.get_equity()
            levels = build_levels(
                symbol=symbol,
                entry_price=price,
                equity=equity,
                stop_loss_pct=self.strategy["stop_loss_pct"],
                risk_per_trade_pct=self.strategy["risk_per_trade_pct"],
                reward_risk_ratio=self.strategy["reward_risk_ratio"],
            )
            if levels.shares < 1:
                log.warning(f"{symbol}: calculated 0 shares, skipping entry")
                return

            order = self.client.submit_bracket_buy(
                symbol, levels.shares, levels.take_profit, levels.stop_loss
            )
            if order:
                self.pos_tracker.open(levels)
                self.stats.record(TradeRecord(
                    symbol=symbol, action="ENTRY", price=price,
                    shares=levels.shares, reason=result.reason,
                ))
                log_trade(symbol, "BUY", levels.shares, price)
                log.info(
                    f"{symbol}: stop={levels.stop_loss:.2f}, "
                    f"target={levels.take_profit:.2f}"
                )
        elif result.signal not in (Signal.NONE, Signal.SKIP_DUPLICATE):
            self.stats.record(TradeRecord(
                symbol=symbol, action="SKIP", price=price,
                shares=0, reason=result.reason,
            ))

    async def _check_exit(self, symbol: str, price: float) -> None:
        levels = self.pos_tracker.get(symbol)
        if not levels:
            return
        result = evaluate_exit(price, levels)

        if result.signal in (Signal.EXIT_STOP, Signal.EXIT_TARGET, Signal.EXIT_HARD_CLOSE):
            pnl = (price - levels.entry_price) * levels.shares
            # Bracket legs may have already closed the position at Alpaca;
            # attempt the sell but swallow "position not found" errors.
            try:
                self.client.submit_market_sell(symbol, levels.shares)
            except Exception as exc:
                if "position" in str(exc).lower() or "order" in str(exc).lower():
                    log.info(f"{symbol}: position already closed by broker bracket fill")
                else:
                    log.error(f"{symbol}: sell error — {exc}")
            self.pos_tracker.close(symbol)
            self.stats.record(TradeRecord(
                symbol=symbol, action="EXIT", price=price,
                shares=levels.shares, reason=result.reason, pnl=pnl,
            ))
            log_trade(symbol, "SELL", levels.shares, price, pnl)

    # ------------------------------------------------------------------
    # Scheduled tasks
    # ------------------------------------------------------------------

    async def _schedule_orb_finalise(self, orb_end: datetime) -> None:
        secs = seconds_until(orb_end)
        log.info(f"ORB window closes in {secs:.0f}s")
        await asyncio.sleep(secs)
        self.orb_tracker.finalise_all()
        self._orb_done = True
        log.info("Opening range finalised — entry signals now active")

    async def _schedule_hard_close(self, close_time: datetime) -> None:
        secs = seconds_until(close_time)
        log.info(f"Hard close in {secs:.0f}s")
        await asyncio.sleep(secs)
        log.info("Hard close triggered — closing all positions")
        self._hard_closed = True

        # Log P&L for each tracked position using last known broker price
        try:
            broker_positions = {p.symbol: p for p in self.client.get_open_positions()}
        except Exception as exc:
            log.error(f"Could not fetch positions for P&L logging: {exc}")
            broker_positions = {}

        for symbol in list(self.pos_tracker.open_symbols()):
            levels = self.pos_tracker.get(symbol)
            bp = broker_positions.get(symbol)
            price = float(bp.current_price) if bp else (levels.entry_price if levels else 0.0)
            pnl = (price - levels.entry_price) * levels.shares if levels else 0.0
            self.pos_tracker.close(symbol)
            self.stats.record(TradeRecord(
                symbol=symbol, action="EXIT", price=price,
                shares=levels.shares if levels else 0,
                reason="hard close 3:55 ET", pnl=pnl,
            ))

        # Single call cancels all bracket legs and liquidates everything
        try:
            self.client.close_all_positions()
        except Exception as exc:
            log.error(f"close_all_positions error: {exc}")

        if self._feed:
            await self._feed.stop()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def _shutdown(self) -> None:
        self.stats.print_summary()
        self._persist_daily_summary()
        log.info("Session ended")

    def _persist_daily_summary(self) -> None:
        exits = [r for r in self.stats.records if r.action == "EXIT" and r.pnl is not None]
        entries = [r for r in self.stats.records if r.action == "ENTRY"]
        pnls = [r.pnl for r in exits]
        date = datetime.now().strftime("%Y-%m-%d")
        total   = len(entries)
        wins    = sum(1 for p in pnls if p > 0)
        losses  = sum(1 for p in pnls if p < 0)
        net_pnl = sum(pnls)
        l_win   = max((p for p in pnls if p > 0), default=0.0)
        l_loss  = min((p for p in pnls if p < 0), default=0.0)
        win_rate = (wins / len(exits) * 100) if exits else 0.0
        try:
            save_daily_summary(date, total, wins, losses, net_pnl, l_win, l_loss)
        except Exception as exc:
            log.error(f"Failed to save daily summary to metrics DB: {exc}")
        notify_daily_summary(date, total, win_rate, net_pnl, l_win, l_loss)
