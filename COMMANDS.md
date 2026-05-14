# SSH Command Reference

All commands run from the server as `admin0@orb-trader`.

---

## Services

```bash
# Status
sudo systemctl status orb-trader orb-api

# Restart both
sudo systemctl restart orb-trader orb-api

# Restart API only (after backend changes)
sudo systemctl restart orb-api

# Restart bot only
sudo systemctl restart orb-trader
```

---

## Deploy

```bash
# Pull latest code
sudo git -C /opt/orb-trader pull

# Pull + rebuild frontend + restart API
sudo git -C /opt/orb-trader pull && \
  cd /opt/orb-trader/frontend && sudo npm run build && \
  sudo systemctl restart orb-api

# Pull + restart bot (backend/config changes)
sudo git -C /opt/orb-trader pull && sudo systemctl restart orb-trader orb-api
```

---

## Logs

```bash
# Bot — last 50 lines
sudo journalctl -u orb-trader -n 50

# Bot — follow live
sudo journalctl -u orb-trader -f

# Bot — full session (replace dates)
sudo journalctl -u orb-trader --since "2026-05-13 09:00:00" --until "2026-05-13 16:10:00" --no-pager

# API — last 20 lines
sudo journalctl -u orb-api -n 20

# API — follow live
sudo journalctl -u orb-api -f
```

---

## Screener

```bash
# Run screener now (outside market hours is fine)
sudo bash -c 'set -a && source /etc/orb-trader/.env && set +a && \
  cd /opt/orb-trader && /opt/orb-trader/venv/bin/python screener/scan.py'
```

---

## Tests

```bash
cd /opt/orb-trader
ORB_LOG_DIR=/tmp /opt/orb-trader/venv/bin/pytest tests/ -v
```

---

## Database

```bash
# Open psql
sudo -u postgres psql orb_trader

# Recent trades
sudo -u postgres psql orb_trader -c \
  "SELECT timestamp, symbol, action, quantity, entry_price, exit_price, pnl FROM trades ORDER BY timestamp DESC LIMIT 20;"

# Today's trades
sudo -u postgres psql orb_trader -c \
  "SELECT * FROM trades WHERE timestamp::date = CURRENT_DATE ORDER BY timestamp;"

# Slippage report — how much market orders cost vs signal price
sudo -u postgres psql orb_trader -c \
  "SELECT symbol, signal_price, entry_price AS fill_price, slippage_bps \
   FROM trades WHERE action = 'BUY' AND slippage_bps IS NOT NULL \
   ORDER BY timestamp DESC LIMIT 30;"

# Average slippage (if consistently > 10-15 bps, switch to limit orders)
sudo -u postgres psql orb_trader -c \
  "SELECT ROUND(AVG(slippage_bps), 2) AS avg_slippage_bps, \
          ROUND(MAX(slippage_bps), 2) AS max_slippage_bps, \
          COUNT(*) AS trades \
   FROM trades WHERE action = 'BUY' AND slippage_bps IS NOT NULL;"

# Run a migration script
sudo -u postgres psql orb_trader < /opt/orb-trader/scripts/add_order_id.sql
```

---

## Backup

```bash
# Run backup manually
sudo /opt/orb-trader/scripts/backup.sh

# Check snapshots in Google Drive
sudo RESTIC_REPOSITORY="rclone:gdrive:orb-trader-backups" \
     RESTIC_PASSWORD_FILE="/etc/orb-trader/restic.password" \
     restic snapshots
```

---

## Health Check

```bash
curl http://localhost:8000/health
```

---

## Misc

```bash
# Create a new dashboard user
sudo /opt/orb-trader/venv/bin/python /opt/orb-trader/scripts/create_user.py

# Run a test trade (paper — places real bracket order)
sudo bash -c 'set -a && source /etc/orb-trader/.env && set +a && \
  cd /opt/orb-trader && DATABASE_URL=postgresql://postgres:postgres@localhost/orb_trader \
  /opt/orb-trader/venv/bin/python scripts/test_trade.py'

# Check Tailscale IP
tailscale ip -4
```
