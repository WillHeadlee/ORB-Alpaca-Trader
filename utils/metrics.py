"""SQLite performance metrics — persists every trade and daily summary."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

_DB_ENV = os.getenv("ORB_METRICS_DB")
DB_PATH = Path(_DB_ENV) if _DB_ENV else Path(__file__).resolve().parent.parent / "metrics.db"


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                symbol    TEXT    NOT NULL,
                action    TEXT    NOT NULL,
                quantity  INTEGER NOT NULL,
                price     REAL    NOT NULL,
                pnl       REAL,
                strategy  TEXT    DEFAULT 'ORB'
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date           TEXT PRIMARY KEY,
                total_trades   INTEGER,
                winning_trades INTEGER,
                losing_trades  INTEGER,
                total_pnl      REAL,
                largest_win    REAL,
                largest_loss   REAL
            )
        """)


def log_trade(
    symbol: str,
    action: str,
    quantity: int,
    price: float,
    pnl: Optional[float] = None,
) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO trades (timestamp, symbol, action, quantity, price, pnl) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), symbol, action, quantity, price, pnl),
        )


def save_daily_summary(
    date: str,
    total_trades: int,
    winning_trades: int,
    losing_trades: int,
    total_pnl: float,
    largest_win: float,
    largest_loss: float,
) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO daily_summary
                (date, total_trades, winning_trades, losing_trades,
                 total_pnl, largest_win, largest_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_trades   = excluded.total_trades,
                winning_trades = excluded.winning_trades,
                losing_trades  = excluded.losing_trades,
                total_pnl      = excluded.total_pnl,
                largest_win    = excluded.largest_win,
                largest_loss   = excluded.largest_loss
            """,
            (date, total_trades, winning_trades, losing_trades,
             total_pnl, largest_win, largest_loss),
        )
