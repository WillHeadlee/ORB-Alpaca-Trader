#!/usr/bin/env python3

import sys
import os
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Trade, DailySummary

def migrate():
    sqlite_path = '/opt/orb-trader/metrics.db'

    if not os.path.exists(sqlite_path):
        print("No SQLite database found — nothing to migrate")
        return

    print(f"Migrating from {sqlite_path} to PostgreSQL...")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()
    pg_db = SessionLocal()

    try:
        sqlite_cursor.execute("SELECT * FROM trades")
        trades = sqlite_cursor.fetchall()
        print(f"Migrating {len(trades)} trades...")

        for row in trades:
            trade = Trade(
                timestamp=datetime.fromisoformat(row[1]),
                symbol=row[2],
                action=row[3],
                quantity=row[4],
                entry_price=row[5] if row[3] == 'BUY' else None,
                exit_price=row[5] if row[3] == 'SELL' else None,
                pnl=row[6],
                mode='paper',
                stop_loss=None,
                take_profit=None,
                exit_reason=None,
            )
            pg_db.add(trade)

        sqlite_cursor.execute("SELECT * FROM daily_summary")
        summaries = sqlite_cursor.fetchall()
        print(f"Migrating {len(summaries)} daily summaries...")

        for row in summaries:
            summary = DailySummary(
                date=datetime.strptime(row[0], '%Y-%m-%d').date(),
                mode='paper',
                total_trades=row[1],
                winning_trades=row[2],
                losing_trades=row[3],
                total_pnl=row[4],
                largest_win=row[5],
                largest_loss=row[6],
                symbols_traded=[],
            )
            pg_db.add(summary)

        pg_db.commit()
        print("Migration completed successfully!")

    except Exception as e:
        pg_db.rollback()
        print(f"Migration failed: {e}")
    finally:
        sqlite_conn.close()
        pg_db.close()

if __name__ == '__main__':
    migrate()
