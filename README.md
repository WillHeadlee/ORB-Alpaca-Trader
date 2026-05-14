# ORB Alpaca Trader

An automated day trading bot implementing the **Opening Range Breakout (ORB)** strategy, connected to [Alpaca Markets](https://alpaca.markets). Includes a live web dashboard, daily stock screener, PostgreSQL trade history, Google Drive backups, and remote access via Tailscale.

---

## Strategy

The bot observes the first 15 minutes after the 9:30 AM ET open to define an *opening range* (high and low). If price breaks above the range high with sufficient volume and passes all filters, it enters a long position with a broker-side bracket order. All positions are force-closed at 3:55 PM ET.

### Entry parameters

| Parameter | Default | Description |
|---|---|---|
| Opening range | 15 min | Observation window after open |
| Risk per trade | 1.5% | Max % of equity risked per trade |
| Max position size | 20% | Cap on total position cost as % of equity |
| Max concurrent | 3 | Max simultaneous open positions |
| Stop-loss | 0.75% below entry | Submitted as broker stop order |
| Take-profit | 2:1 reward/risk | Submitted as broker limit order |
| Volume filter | 1.2× avg | Breakout bar must exceed this |
| Price floor | $50 | Screener minimum — excludes thin-book stocks |
| ORB range cap | 2% | Skip if opening range > 2% wide (chaotic open) |

### Entry filters (applied in order)

| Filter | Logic |
|---|---|
| VWAP | Price must be above session VWAP |
| SPY index | SPY must be above its 9:30 open price |
| Relative strength | Stock % change from open must exceed SPY % change |
| Daily resistance | Skip if previous day's high is within 1R of entry |
| Leveraged ETFs | Excluded from screener universe entirely |

### Exit logic

| Exit | Trigger |
|---|---|
| Stop-loss | Bracket order fires at -0.75% |
| Take-profit | Bracket order fires at +1.5% (2:1 R:R) |
| Breakeven stop | When position reaches 1:1 R:R, stop moved to entry price |
| Stale exit | Close if open > 45 min and profit < 0.5R |
| Hard close | All positions liquidated at 3:55 PM ET |
| Last entry | No new entries after 11:30 AM ET |

The watchlist is populated each morning from the stock screener (top 20 symbols by volume × volatility score, $50+ price, no leveraged ETFs). Falls back to the `config.yaml` watchlist if no screener data exists.

With a 2:1 reward/risk ratio, the strategy needs a win rate above ~35% to be profitable.

---

## Architecture

```
├── main.py                      # Entry point
├── config.yaml                  # Strategy parameters and fallback watchlist
├── trader/
│   ├── alpaca_client.py         # REST order management (bracket orders)
│   ├── data_feed.py             # WebSocket real-time bar feed (auto-reconnect)
│   ├── opening_range.py         # ORB high/low tracking
│   ├── position_manager.py      # Position sizing with risk + equity cap
│   ├── strategy.py              # Entry/exit signal logic
│   └── session_manager.py       # Session lifecycle, screener watchlist loading
├── backend/
│   ├── app.py                   # FastAPI application
│   ├── auth.py                  # JWT authentication (bcrypt passwords)
│   ├── database.py              # SQLAlchemy / PostgreSQL connection
│   ├── models.py                # ORM models (trades, positions, screener, logs)
│   └── routes.py                # REST API — dashboard, trading controls, fill sync
├── frontend/                    # React + Vite + Tailwind dashboard
│   └── src/
│       ├── Dashboard.jsx        # Main trading dashboard
│       ├── KillSwitch.jsx       # Emergency close + test-run controls
│       └── PerformanceChart.jsx # 30-day cumulative P&L chart
├── screener/
│   └── scan.py                  # Daily screener — batch Alpaca snapshots, top 100
├── scripts/
│   ├── init_db.sql              # PostgreSQL schema
│   ├── create_user.py           # Dashboard user creation
│   ├── backup.sh                # Restic + rclone backup to Google Drive
│   ├── test_trade.py            # End-to-end paper trade verification
│   └── migrate_from_sqlite.py   # One-time migration from old SQLite DB
└── utils/
    ├── logger.py                # Rotating file + console logger, session stats
    ├── metrics.py               # PostgreSQL trade persistence
    ├── email_alerts.py          # Gmail SMTP alerts (kill switch, errors)
    └── time_utils.py            # ET timezone helpers, market hours
```

---

## Deployment (Homelab / VPS)

### Prerequisites

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib nodejs npm restic rclone caddy
```

### 1. Clone and set up Python environment

```bash
git clone https://github.com/WillHeadlee/ORB-Alpaca-Trader.git /opt/orb-trader
cd /opt/orb-trader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. PostgreSQL

```bash
sudo -u postgres createdb orb_trader
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"
sudo -u postgres psql orb_trader < scripts/init_db.sql
```

### 3. Environment variables

Create `/etc/orb-trader/.env`:

```bash
# Alpaca API
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true            # set to false for live trading

# Database
DATABASE_URL=postgresql://postgres:yourpassword@localhost/orb_trader

# JWT secret for dashboard (generate: openssl rand -hex 32)
JWT_SECRET=your_random_secret

# Email alerts (optional)
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
ALERT_EMAIL=you@gmail.com
```

### 4. Dashboard user

```bash
/opt/orb-trader/venv/bin/python scripts/create_user.py
```

### 5. Build the frontend

```bash
cd /opt/orb-trader/frontend
npm install && npm run build
```

### 6. Systemd services

**`/etc/systemd/system/orb-api.service`** — FastAPI dashboard backend:
```ini
[Unit]
Description=ORB Trader API
After=network-online.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orb-trader
Environment="PATH=/opt/orb-trader/venv/bin"
EnvironmentFile=/etc/orb-trader/.env
ExecStart=/opt/orb-trader/venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/orb-trader.service`** — Trading bot:
```ini
[Unit]
Description=Alpaca ORB Auto-Trader
After=network-online.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orb-trader
Environment="PATH=/opt/orb-trader/venv/bin"
EnvironmentFile=/etc/orb-trader/.env
ExecStart=/opt/orb-trader/venv/bin/python /opt/orb-trader/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now orb-api orb-trader caddy
```

### 7. Reverse proxy (Caddy)

```bash
sudo cp /opt/orb-trader/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### 8. Cron jobs

```bash
sudo crontab -e
```

```
# Screener — 9:15 AM ET Mon-Fri
15 9 * * 1-5 cd /opt/orb-trader && set -a && . /etc/orb-trader/.env && set +a && /opt/orb-trader/venv/bin/python screener/scan.py >> /opt/orb-trader/logs/screener.log 2>&1

# Backup — 6:00 PM ET Mon-Fri
0 18 * * 1-5 /opt/orb-trader/scripts/backup.sh >> /opt/orb-trader/logs/backup.log 2>&1
```

### 9. Remote access (Tailscale)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4   # access dashboard at http://<this-ip>
```

---

## Dashboard

Access at `http://<tailscale-ip>` (port 80 via Caddy). Features:

- Live bot status, trading mode, account equity
- Real-time clock (ET)
- Today's P&L, 30-day P&L, win rate
- Open positions pulled live from Alpaca
- 30-day cumulative P&L chart
- Trade log with auto-synced Alpaca fills
- Stock screener results (top 20)
- **TEST RUN** — triggers the strategy right now on the top screener symbol
- **CLOSE ALL** — emergency kill switch with confirmation

---

## Daily Flow

| Time (ET) | Event |
|---|---|
| 9:15 AM | Screener scans ~11,000 stocks, saves top 100 to DB |
| 9:30 AM | Bot wakes, loads top 20 screener symbols as watchlist |
| 9:30–9:45 AM | Opening range established (bot observes, does not trade) |
| 9:45 AM+ | Entry signals active — bracket orders submitted on breakouts |
| 3:55 PM | Hard close — all positions liquidated |
| 6:00 PM | Backup runs to Google Drive |

---

## Tests

```bash
/opt/orb-trader/venv/bin/pytest tests/ -v
# 51 passed
```

Covers: opening range logic, position sizing (with and without equity cap), entry/exit signal generation, position tracker.

---

## Live Trading

Change `ALPACA_PAPER=false` in `/etc/orb-trader/.env` and swap in live API keys. The bot requires explicit `yes` confirmation at startup. **Run paper for at least 2–4 weeks first.**

---

## Disclaimer

Educational purposes only. Not financial advice. Past paper performance does not guarantee live results. You are solely responsible for any trading decisions made using this software.
