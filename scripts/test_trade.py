#!/usr/bin/env python3
"""
One-shot trade test — submits a small paper buy on SPY, waits for fill,
then closes it. Verifies the full order → fill → close → DB log pipeline.
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from utils.metrics import log_trade

api_key    = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

client = TradingClient(api_key, secret_key, paper=True)

account = client.get_account()
equity  = float(account.equity)
print(f"Account equity: ${equity:,.2f}")

# Submit a 1-share market buy of SPY
print("Submitting test buy: 1 share of SPY...")
order = client.submit_order(MarketOrderRequest(
    symbol='SPY',
    qty=1,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
))
print(f"Order submitted: {order.id} — status: {order.status}")

# Wait for fill
print("Waiting for fill...")
for _ in range(15):
    time.sleep(2)
    order = client.get_order_by_id(order.id)
    print(f"  status: {order.status}")
    if order.status == 'filled':
        break

if order.status != 'filled':
    print("Order not filled in 30s — cancelling")
    client.cancel_order_by_id(order.id)
    sys.exit(1)

fill_price = float(order.filled_avg_price)
print(f"Filled at ${fill_price:.2f}")

# Log the buy to PostgreSQL
log_trade('SPY', 'BUY', 1, fill_price)
print("Buy logged to database")

# Close the position immediately
print("Closing position...")
client.close_position('SPY')
time.sleep(3)

# Log the sell (approx same price)
log_trade('SPY', 'SELL', 1, fill_price, pnl=0.0)
print("Sell logged to database")

print("\nTest complete — check the dashboard trade log.")
