#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from backend.database import SessionLocal
from backend.models import ScreenerResult

def scan_top_100():
    """
    Run at 9:15 AM daily to find high-liquidity ORB candidates.

    Criteria: tradable, active, avg 20-day volume > 10M, price $20-$500.
    Score: volume (60%) + volatility (40%).
    """
    print(f"Starting screener scan at {datetime.now()}")

    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')

    trading_client = TradingClient(api_key, secret_key, paper=True)
    data_client = StockHistoricalDataClient(api_key, secret_key)

    assets = trading_client.get_all_assets()
    tradable = [
        a for a in assets
        if a.tradable and a.status == 'active' and a.exchange in ('NASDAQ', 'NYSE', 'ARCA')
    ]
    print(f"Found {len(tradable)} tradable assets")

    results = []
    scan_timestamp = datetime.now()

    for i, asset in enumerate(tradable):
        try:
            bars_request = StockBarsRequest(
                symbol_or_symbols=asset.symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=30),
                end=datetime.now(),
            )
            bars = data_client.get_stock_bars(bars_request)

            if asset.symbol not in bars.data:
                continue

            symbol_bars = bars.data[asset.symbol]
            if len(symbol_bars) < 20:
                continue

            volumes = [bar.volume for bar in symbol_bars]
            closes = [bar.close for bar in symbol_bars]
            avg_volume = sum(volumes[-20:]) / 20
            current_price = closes[-1]

            if avg_volume < 10_000_000:
                continue
            if not (20 <= current_price <= 500):
                continue

            highs = [bar.high for bar in symbol_bars[-14:]]
            lows = [bar.low for bar in symbol_bars[-14:]]
            atr = sum(h - l for h, l in zip(highs, lows)) / 14
            volatility = (atr / current_price) * 100

            score = (avg_volume / 1_000_000) * 0.6 + volatility * 0.4

            results.append({
                'symbol': asset.symbol,
                'price': float(current_price),
                'avg_volume': int(avg_volume),
                'volatility': round(volatility, 2),
                'score': round(score, 2),
            })

            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(tradable)} assets")

        except Exception:
            continue

    results.sort(key=lambda x: x['score'], reverse=True)
    top_100 = results[:100]
    print(f"Found {len(results)} qualifying symbols, saving top 100")

    db = SessionLocal()
    try:
        for r in top_100:
            db.add(ScreenerResult(
                scan_timestamp=scan_timestamp,
                symbol=r['symbol'],
                price=r['price'],
                avg_volume=r['avg_volume'],
                volatility=r['volatility'],
                score=r['score'],
            ))
        db.commit()
        print(f"Saved {len(top_100)} screener results")
    except Exception as e:
        db.rollback()
        print(f"Error saving to database: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    scan_top_100()
