# Alpaca ORB Auto-Trader — Project Spec

## Background

This project builds an automated day trading bot using the **Opening Range Breakout (ORB)** strategy, connected to [Alpaca Markets](https://alpaca.markets) via their REST API and WebSocket data feed.

**Trader profile:**
- Goal: Maximize short-term gains
- Style: Day trading (all positions open and close within the same market day)
- Capital: $1,000 – $10,000
- Risk tolerance: Moderate (balanced risk/reward)
- Starting mode: Paper trading (simulated, no real money at risk)

**Strategy overview:**
The ORB strategy observes price action in the first 15–30 minutes after market open (9:30–9:45/10:00 AM ET) to define an "opening range" (high and low). A breakout above the range high triggers a buy; a breakdown below the range low triggers a short or skip. All positions are closed before market close (3:55 PM ET).

**Key constraints:**
- SEC Pattern Day Trader (PDT) rule: accounts under $25,000 on margin are limited to 3 day trades per rolling 5-business-day window. Start in paper mode to avoid this restriction.
- Risk per trade: No more than 1–2% of total account balance.
- No overnight holds: all positions must be flat by end of day.

---

## Claude Code Prompt

Use the following prompt to initialize the project with Claude Code:

```
Build a Python-based automated day trading bot using the Opening Range Breakout (ORB) strategy, connected to the Alpaca Markets API.

Project requirements:

1. **Alpaca connection**
   - Use the `alpaca-trade-api` Python library (or `alpaca-py` if preferred)
   - Support both paper trading and live trading modes via environment variable (ALPACA_MODE=paper|live)
   - Load API keys from a .env file (ALPACA_API_KEY, ALPACA_SECRET_KEY)

2. **Watchlist**
   - Trade a configurable list of liquid stocks (default: SPY, QQQ, AAPL, TSLA, NVDA)
   - Allow the watchlist to be set in config.yaml

3. **Opening Range logic**
   - Observe the first 15 minutes of price action after 9:30 AM ET (configurable: 15 or 30 min)
   - Record the high and low of that opening range for each symbol

4. **Entry logic**
   - If price breaks above the opening range high with above-average volume, submit a market buy order
   - If price breaks below the opening range low, skip (no shorting for now)
   - Only enter one position per symbol per day

5. **Position sizing**
   - Risk no more than 1.5% of total account equity per trade
   - Calculate share quantity based on entry price and stop-loss distance

6. **Exit logic**
   - Stop-loss: placed 0.5% below entry (configurable)
   - Take-profit: 2x the stop-loss distance (1% above entry) — a 2:1 reward/risk ratio
   - Hard close: close all open positions at 3:55 PM ET regardless of P&L

7. **Logging**
   - Log every trade decision (entry, exit, skip) with timestamp, symbol, price, reason, and P&L
   - Write logs to logs/trades.log
   - Print a daily summary at end of session: total trades, win rate, net P&L

8. **Structure**
   - Follow the project structure in spec.md
   - Use async where appropriate for real-time data handling
   - Write unit tests for the ORB detection logic and position sizing functions

Start by scaffolding the full project structure, then implement each module one at a time. Ask me before placing any live orders.
```

---

## Recommended Project Structure

```
orb-trader/
│
├── .env                        # API keys (never commit this)
├── .env.example                # Template for .env
├── .gitignore
├── config.yaml                 # Watchlist, strategy params, risk settings
├── requirements.txt
├── README.md
├── spec.md                     # This file
│
├── main.py                     # Entry point — starts the trading session
│
├── trader/
│   ├── __init__.py
│   ├── alpaca_client.py        # Alpaca API connection and order management
│   ├── data_feed.py            # Real-time price and volume data (WebSocket)
│   ├── opening_range.py        # ORB detection logic (high/low calculation)
│   ├── strategy.py             # Entry/exit signal generation
│   ├── position_manager.py     # Position sizing, stop-loss, take-profit
│   └── session_manager.py      # Market hours, hard close at 3:55 PM ET
│
├── utils/
│   ├── __init__.py
│   ├── logger.py               # Trade logging and daily summary
│   └── time_utils.py           # ET timezone helpers, market hour checks
│
├── tests/
│   ├── test_opening_range.py   # Unit tests for ORB detection
│   ├── test_position_sizing.py # Unit tests for risk/sizing calculations
│   └── test_strategy.py        # Unit tests for entry/exit logic
│
└── logs/
    └── trades.log              # Auto-generated trade log
```

---

## Configuration Reference (`config.yaml`)

```yaml
trading:
  mode: paper                   # paper | live
  watchlist:
    - SPY
    - QQQ
    - AAPL
    - TSLA
    - NVDA

strategy:
  opening_range_minutes: 15     # How long to observe before trading (15 or 30)
  risk_per_trade_pct: 1.5       # % of account to risk per trade
  stop_loss_pct: 0.5            # % below entry for stop-loss
  reward_risk_ratio: 2.0        # Take-profit = stop_loss * this value
  hard_close_time: "15:55"      # ET time to force-close all positions
  volume_multiplier: 1.2        # Breakout must have volume > avg * this value
```

---

## Getting Started Checklist

- [ ] Create Alpaca paper trading account at alpaca.markets
- [ ] Generate API key and secret from the Alpaca dashboard
- [ ] Copy `.env.example` to `.env` and fill in your keys
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run in paper mode: `python main.py`
- [ ] Review `logs/trades.log` after first session
- [ ] Run for 2–4 weeks in paper mode before considering live trading

---

## Important Notes

**PDT Rule:** If your Alpaca account is a margin account under $25,000, you are limited to 3 day trades per 5 rolling business days. Paper trading has no such restriction. Consider a cash account to avoid this limit, though settlement times (T+1) will restrict same-day reuse of capital.

**This is not financial advice.** Past performance of a strategy in paper trading does not guarantee live trading results. Always understand the code and the risk before enabling live mode.
