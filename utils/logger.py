"""Trade logger — rotating file + console, plus end-of-session daily summary."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Production path takes priority; falls back to repo-local logs/
_LOG_DIR_ENV = os.getenv("ORB_LOG_DIR")
LOG_DIR = Path(_LOG_DIR_ENV) if _LOG_DIR_ENV else Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trades.log"


def _setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("orb_trader")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = _setup_logger()


@dataclass
class TradeRecord:
    symbol: str
    action: str           # ENTRY | EXIT | SKIP
    price: float
    shares: int
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    pnl: Optional[float] = None


class SessionStats:
    def __init__(self) -> None:
        self.records: list[TradeRecord] = []

    def record(self, rec: TradeRecord) -> None:
        self.records.append(rec)
        pnl_str = f" | P&L={rec.pnl:+.2f}" if rec.pnl is not None else ""
        log.info(
            f"{rec.action:<5} | {rec.symbol:<6} | price={rec.price:.2f} "
            f"| shares={rec.shares}{pnl_str} | {rec.reason}"
        )

    def print_summary(self) -> None:
        entries = [r for r in self.records if r.action == "ENTRY"]
        exits = [r for r in self.records if r.action == "EXIT" and r.pnl is not None]

        total_trades = len(entries)
        wins = sum(1 for r in exits if (r.pnl or 0) > 0)
        net_pnl = sum(r.pnl for r in exits if r.pnl is not None)
        win_rate = (wins / len(exits) * 100) if exits else 0.0

        summary = (
            "\n" + "=" * 55 + "\n"
            f"  DAILY SUMMARY  {datetime.now().strftime('%Y-%m-%d')}\n"
            + "=" * 55 + "\n"
            f"  Total trades : {total_trades}\n"
            f"  Closed trades: {len(exits)}\n"
            f"  Win rate     : {win_rate:.1f}%\n"
            f"  Net P&L      : ${net_pnl:+.2f}\n"
            + "=" * 55
        )
        log.info(summary)
        print(summary)
