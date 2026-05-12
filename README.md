# ORB Alpaca Trader

An automated day trading bot implementing the **Opening Range Breakout (ORB)** strategy, connected to [Alpaca Markets](https://alpaca.markets) via REST and WebSocket APIs.

## Strategy

The bot observes the first 15 minutes of price action after the 9:30 AM ET market open to define an *opening range* (high and low). If price breaks above the range high with above-average volume, it enters a long position with a broker-side bracket order (stop-loss + take-profit). All positions are force-closed at 3:55 PM ET.

- **Entry:** breakout above opening range high + volume > historical avg × 1.2
- **Stop-loss:** 0.5% below entry (submitted to Alpaca as a stop order)
- **Take-profit:** 1.0% above entry — 2:1 reward/risk ratio (submitted as a limit order)
- **Risk per trade:** ≤ 1.5% of account equity
- **No overnight holds** — hard close at 3:55 PM ET regardless of P&L

## Project Structure

```
├── main.py                  # Entry point
├── config.yaml              # Watchlist and strategy parameters
├── trader/
│   ├── alpaca_client.py     # REST order management (bracket orders)
│   ├── data_feed.py         # WebSocket real-time bar feed
│   ├── opening_range.py     # ORB high/low tracking
│   ├── position_manager.py  # Position sizing and stop/target levels
│   ├── strategy.py          # Entry/exit signal logic
│   └── session_manager.py   # Session lifecycle and scheduling
├── utils/
│   ├── logger.py            # Trade logging and daily summary
│   └── time_utils.py        # ET timezone helpers, market hours
└── tests/                   # 49 unit tests
```

## Setup

**1. Clone and install dependencies**
```bash
git clone https://github.com/WillHeadlee/ORB-Alpaca-Trader.git
cd ORB-Alpaca-Trader
pip install -r requirements.txt
```

**2. Configure API keys**

Create a free paper trading account at [alpaca.markets](https://alpaca.markets), generate an API key, then:
```bash
cp .env.example .env
# Edit .env and fill in ALPACA_API_KEY and ALPACA_SECRET_KEY
```

**3. Configure the watchlist and strategy (optional)**

Edit `config.yaml`:
```yaml
trading:
  watchlist: [SPY, QQQ, AAPL, TSLA, NVDA]

strategy:
  opening_range_minutes: 15   # observation window
  risk_per_trade_pct: 1.5     # max % of equity risked per trade
  stop_loss_pct: 0.5          # stop placed this % below entry
  reward_risk_ratio: 2.0      # take-profit = stop distance × ratio
  volume_multiplier: 1.2      # breakout bar volume must exceed avg × this
```

**4. Run**
```bash
python main.py
```

Started outside market hours, the bot sleeps until the next 9:30 AM ET open. Trade decisions are logged to `logs/trades.log` and a daily summary is printed at session end.

## Live Trading

Set `ALPACA_MODE=live` in `.env` (or `mode: live` in `config.yaml`). The bot requires explicit `yes` confirmation at startup before placing any live orders. **Run in paper mode for at least 2–4 weeks before going live.**

## Running Tests

```bash
python -m pytest tests/ -v
```

## Disclaimer

This project is for educational purposes. It is not financial advice. Past paper trading performance does not guarantee live results. Understand the code and the risk before enabling live mode.
