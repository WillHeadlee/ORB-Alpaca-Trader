# ORB Alpaca Trader

An automated day trading bot implementing the **Opening Range Breakout (ORB)** strategy, connected to [Alpaca Markets](https://alpaca.markets). Includes a live web dashboard, stock screener, PostgreSQL trade history, and Google Drive backups.

---

## Strategy

The bot observes the first 15 minutes after the 9:30 AM ET open to define an *opening range* (high and low). If price breaks above the range high with above-average volume, it enters a long position with a bracket order (stop-loss + take-profit). All positions are force-closed at 3:55 PM ET.

| Parameter | Default | Description |
|---|---|---|
| Opening range | 15 min | Observation window after open |
| Risk per trade | 1.5% | Max % of equity risked |
| Stop-loss | 0.5% below entry | Submitted as broker stop order |
| Take-profit | 2:1 reward/risk | Submitted as broker limit order |
| Hard close | 3:55 PM ET | Force-closes all positions |
| Volume filter | 1.2× avg | Breakout bar must exceed this |

Watchlist is populated daily from the stock screener (top 20 by volume × volatility score). Falls back to `config.yaml` if no screener data exists.

---

## Architecture

```
├── main.py                      # Entry point
├── config.yaml                  # Strategy parameters and fallback watchlist
├── trader/
│   ├── alpaca_client.py         # REST order management (bracket orders)
│   ├── data_feed.py             # WebSocket real-time bar feed
│   ├── opening_range.py         # ORB high/low tracking
│   ├── position_manager.py      # Position sizing and stop/target levels
│   ├── strategy.py              # Entry/exit signal logic
│   └── session_manager.py       # Session lifecycle and scheduling
├── backend/
│   ├── app.py                   # FastAPI application
│   ├── auth.py                  # JWT authentication
│   ├── database.py              # SQLAlchemy / PostgreSQL connection
│   ├── models.py                # ORM models
│   └── routes.py                # REST API endpoints
├── frontend/                    # React + Vite + Tailwind dashboard
├── screener/
│   └── scan.py                  # Daily stock screener (Alpaca snapshots)
├── scripts/
│   ├── init_db.sql              # PostgreSQL schema
│   ├── create_user.py           # Dashboard user creation
│   ├── backup.sh                # Restic + rclone backup to Google Drive
│   └── migrate_from_sqlite.py   # One-time migration from old SQLite DB
└── utils/
    ├── logger.py                # Trade logging and session stats
    ├── metrics.py               # PostgreSQL trade persistence
    ├── email_alerts.py          # Gmail SMTP alerts
    └── time_utils.py            # ET timezone helpers
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
# Alpaca (paper trading)
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret

# Set to 'false' for live trading
ALPACA_PAPER=true

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
npm install
npm run build
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

Copy `Caddyfile` to `/etc/caddy/Caddyfile` and reload:
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

The web dashboard shows live bot status, account equity, today's P&L, open positions, 30-day performance chart, trade log, and screener results. It polls every 5 seconds.

Access at `http://<server-ip>` (port 80 via Caddy) or `http://<tailscale-ip>:8000` directly.

---

## Daily Flow

| Time (ET) | Event |
|---|---|
| 9:15 AM | Screener scans top stocks, saves to DB |
| 9:30 AM | Bot wakes, loads screener watchlist |
| 9:45 AM | Opening range established, entries active |
| 3:55 PM | Hard close — all positions liquidated |
| 6:00 PM | Backup runs to Google Drive |

---

## Live Trading

Change `ALPACA_PAPER=false` in `/etc/orb-trader/.env` and swap in your live API keys. The bot requires explicit `yes` confirmation at startup.

**Run in paper mode for at least 2–4 weeks before going live.**

---

## Tests

```bash
python -m pytest tests/ -v
```

---

## Disclaimer

This project is for educational purposes only. It is not financial advice. Past paper trading performance does not guarantee live results. You are solely responsible for any trading decisions made using this software.
