"""Trade and summary persistence — writes to PostgreSQL so the dashboard sees live data."""

import os
from datetime import datetime
from typing import Optional


def _get_mode() -> str:
    return 'paper' if os.getenv('ALPACA_PAPER', 'true').lower() != 'false' else 'live'


def init_db() -> None:
    """No-op: PostgreSQL schema is managed by scripts/init_db.sql."""
    pass


def log_trade(
    symbol: str,
    action: str,
    quantity: int,
    price: float,
    pnl: Optional[float] = None,
    order_id: Optional[str] = None,
    stop_leg_id: Optional[str] = None,
    tp_leg_id: Optional[str] = None,
) -> None:
    try:
        from backend.database import SessionLocal
        from backend.models import Trade
        db = SessionLocal()
        try:
            trade = Trade(
                timestamp=datetime.now().astimezone(),
                symbol=symbol,
                action=action,
                quantity=quantity,
                entry_price=price if action == 'BUY' else None,
                exit_price=price if action == 'SELL' else None,
                pnl=pnl,
                mode=_get_mode(),
                alpaca_order_id=order_id,
                bracket_stop_leg_id=stop_leg_id,
                bracket_tp_leg_id=tp_leg_id,
            )
            db.add(trade)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        print(f"[metrics] Failed to log trade to PostgreSQL: {exc}")


def save_daily_summary(
    date: str,
    total_trades: int,
    winning_trades: int,
    losing_trades: int,
    total_pnl: float,
    largest_win: float,
    largest_loss: float,
) -> None:
    try:
        from backend.database import SessionLocal
        from backend.models import DailySummary
        from sqlalchemy.dialects.postgresql import insert
        db = SessionLocal()
        try:
            stmt = insert(DailySummary).values(
                date=datetime.strptime(date, '%Y-%m-%d').date(),
                mode=_get_mode(),
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                total_pnl=total_pnl,
                largest_win=largest_win,
                largest_loss=largest_loss,
                symbols_traded=[],
            ).on_conflict_do_update(
                index_elements=['date'],
                set_=dict(
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    total_pnl=total_pnl,
                    largest_win=largest_win,
                    largest_loss=largest_loss,
                )
            )
            db.execute(stmt)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        print(f"[metrics] Failed to save daily summary to PostgreSQL: {exc}")
