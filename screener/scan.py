#!/usr/bin/env python3
"""
Daily stock screener — runs at 9:15 AM ET Mon-Fri.

Uses Alpaca snapshots for bulk price/volume pre-filtering, then fetches
20-day bars only for the candidates that pass. Saves top 100 to DB.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockSnapshotRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from backend.database import SessionLocal
from backend.models import ScreenerResult

PRICE_MIN = 50
PRICE_MAX = 500
VOLUME_MIN = 150_000         # pre-filter: IEX feed ~3% of real volume (150K ≈ 5M real)
AVG_VOLUME_MIN = 300_000     # final filter: 20-day avg (300K ≈ 10M real)
BATCH_SIZE = 1000
TOP_N = 100


def scan_top_100():
    print(f"Starting screener scan at {datetime.now()}")

    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')

    trading_client = TradingClient(api_key, secret_key, paper=True)
    data_client = StockHistoricalDataClient(api_key, secret_key)

    # Step 1: get all tradable assets
    assets = trading_client.get_all_assets()
    symbols = [
        a.symbol for a in assets
        if a.tradable and a.status == 'active'
        and a.exchange in ('NASDAQ', 'NYSE', 'ARCA')
        and '/' not in a.symbol  # exclude crypto-style symbols
    ]
    print(f"Found {len(symbols)} tradable assets — fetching snapshots in batches...")

    # Step 2: batch snapshot requests to pre-filter by price and rough volume
    candidates = []
    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        try:
            snaps = data_client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=batch))
            for symbol, snap in snaps.items():
                # Use prev_daily_bar for volume (complete); latest_trade for price
                bar = snap.previous_daily_bar or snap.daily_bar
                if bar is None:
                    continue
                price = float(snap.latest_trade.price) if snap.latest_trade else float(bar.close)
                volume = int(bar.volume)
                if PRICE_MIN <= price <= PRICE_MAX and volume >= VOLUME_MIN:
                    candidates.append(symbol)
        except Exception as e:
            print(f"Snapshot batch {i//BATCH_SIZE + 1} error: {e}")
        print(f"  Snapshot batch {i//BATCH_SIZE + 1}/{-(-len(symbols)//BATCH_SIZE)} — {len(candidates)} candidates so far")

    print(f"Pre-filter complete: {len(candidates)} candidates pass price/volume screen")

    # Step 3: fetch 20-day bars for candidates to calculate proper avg volume + volatility
    results = []
    scan_timestamp = datetime.now()

    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i:i + BATCH_SIZE]
        try:
            bars_resp = data_client.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=30),
                end=datetime.now(),
            ))

            for symbol in batch:
                if symbol not in bars_resp.data:
                    continue
                symbol_bars = bars_resp.data[symbol]
                if len(symbol_bars) < 20:
                    continue

                volumes = [bar.volume for bar in symbol_bars[-20:]]
                closes = [bar.close for bar in symbol_bars[-20:]]
                avg_volume = sum(volumes) / len(volumes)
                current_price = float(closes[-1])

                if avg_volume < AVG_VOLUME_MIN:
                    continue
                if not (PRICE_MIN <= current_price <= PRICE_MAX):
                    continue

                highs = [bar.high for bar in symbol_bars[-14:]]
                lows = [bar.low for bar in symbol_bars[-14:]]
                atr = sum(h - l for h, l in zip(highs, lows)) / 14
                volatility = (atr / current_price) * 100

                score = (avg_volume / 1_000_000) * 0.6 + volatility * 0.4

                results.append({
                    'symbol': symbol,
                    'price': round(current_price, 4),
                    'avg_volume': int(avg_volume),
                    'volatility': round(volatility, 2),
                    'score': round(score, 2),
                })
        except Exception as e:
            print(f"Bars batch error: {e}")

    results.sort(key=lambda x: x['score'], reverse=True)
    top = results[:TOP_N]
    print(f"Qualified: {len(results)} symbols — saving top {len(top)}")
    print("Top 10:", [r['symbol'] for r in top[:10]])

    db = SessionLocal()
    try:
        for r in top:
            db.add(ScreenerResult(
                scan_timestamp=scan_timestamp,
                symbol=r['symbol'],
                price=r['price'],
                avg_volume=r['avg_volume'],
                volatility=r['volatility'],
                score=r['score'],
            ))
        db.commit()
        print(f"Saved {len(top)} screener results to database")
    except Exception as e:
        db.rollback()
        print(f"Error saving to database: {e}")
    finally:
        db.close()


if __name__ == '__main__':
    scan_top_100()
