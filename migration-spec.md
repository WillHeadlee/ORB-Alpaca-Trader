# ORB Auto-Trader Homelab Migration Spec

## Environment
- **Target:** Proxmox LXC container (ID 100)
- **OS:** Ubuntu 22.04
- **Hostname:** orb-trader
- **Install path:** `/opt/orb-trader`
- **Secrets path:** `/etc/orb-trader/.env`
- **Python:** venv at `/opt/orb-trader/venv`

## File Structure (Post-Migration)
```
/opt/orb-trader/
├── venv/                    # Python virtual environment
├── main.py
├── config.yaml
├── trader/
│   ├── alpaca_client.py
│   ├── data_feed.py
│   ├── opening_range.py
│   ├── strategy.py
│   ├── position_manager.py
│   └── session_manager.py
├── utils/
│   ├── logger.py
│   └── time_utils.py
├── tests/
├── logs/
├── requirements.txt         # Generated from pip freeze
├── .gitignore              # Must exclude .env, logs/, __pycache__/
├── healthcheck.sh          # Monitoring script
└── metrics.db              # SQLite for performance tracking (new)

/etc/orb-trader/
└── .env                    # Secrets (chmod 600)

/etc/systemd/system/
└── orb-trader.service      # systemd service definition
```

## Code Changes Required

### 1. Environment File Path
**File:** Any file that loads `.env` (likely `main.py` or `alpaca_client.py`)

**Change:**
```python
# FROM:
load_dotenv()  # or load_dotenv('.env')

# TO:
load_dotenv('/etc/orb-trader/.env')
```

### 2. Logging Configuration
**File:** `utils/logger.py`

**Ensure logs write to:** `/opt/orb-trader/logs/`

**Add:** Log rotation (optional but recommended)
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/opt/orb-trader/logs/trader.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

### 3. Performance Metrics (NEW)
**Create:** `utils/metrics.py`

**Schema:**
```python
import sqlite3
from datetime import datetime

DB_PATH = '/opt/orb-trader/metrics.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,  -- 'BUY' or 'SELL'
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            pnl REAL,  -- NULL for buys, calculated for sells
            strategy TEXT DEFAULT 'ORB'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            total_pnl REAL,
            largest_win REAL,
            largest_loss REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_trade(symbol, action, quantity, price, pnl=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'INSERT INTO trades (timestamp, symbol, action, quantity, price, pnl) VALUES (?, ?, ?, ?, ?, ?)',
        (datetime.now().isoformat(), symbol, action, quantity, price, pnl)
    )
    conn.commit()
    conn.close()
```

**Integrate into:** `position_manager.py`
```python
from utils.metrics import log_trade, init_db

# In __init__ or setup:
init_db()

# When opening position:
log_trade(symbol, 'BUY', quantity, entry_price)

# When closing position:
pnl = (exit_price - entry_price) * quantity
log_trade(symbol, 'SELL', quantity, exit_price, pnl)
```

### 4. Timezone Awareness
**File:** `utils/time_utils.py`

**Ensure all datetime operations use:**
```python
import pytz
ET = pytz.timezone('America/New_York')

# Example:
now = datetime.now(ET)
market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
```

## systemd Service File
**Path:** `/etc/systemd/system/orb-trader.service`

```ini
[Unit]
Description=Alpaca ORB Auto-Trader
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orb-trader
Environment="PATH=/opt/orb-trader/venv/bin"
ExecStart=/opt/orb-trader/venv/bin/python /opt/orb-trader/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=orb-trader

[Install]
WantedBy=multi-user.target
```

## Healthcheck Script
**Path:** `/opt/orb-trader/healthcheck.sh`

```bash
#!/bin/bash
LOG_FILE="/opt/orb-trader/logs/healthcheck.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

if ! systemctl is-active --quiet orb-trader; then
    echo "[$TIMESTAMP] CRITICAL: orb-trader service is DOWN" >> "$LOG_FILE"
    
    # Optional: Send alert via Discord webhook
    # curl -X POST -H 'Content-Type: application/json' \
    #   -d '{"content":"🚨 ORB Trader is DOWN!"}' \
    #   YOUR_DISCORD_WEBHOOK_URL
    
    exit 1
else
    echo "[$TIMESTAMP] OK: orb-trader service is running" >> "$LOG_FILE"
    exit 0
fi
```

**Cron schedule:** `*/5 9-16 * * 1-5` (every 5 min, 9am-4pm ET, Mon-Fri)

## Dependencies (requirements.txt)
```
alpaca-py>=0.8.0
pyyaml>=6.0
python-dotenv>=1.0.0
pytz>=2023.3
```

## Git Configuration
**Create:** `.gitignore`
```
.env
logs/
*.log
__pycache__/
*.pyc
venv/
.venv/
metrics.db
*.db
.DS_Store
```

## Deployment Checklist
- [ ] LXC container created (ID 100, 2GB RAM, 2 cores)
- [ ] Python 3, pip, git installed
- [ ] Project directory created at `/opt/orb-trader`
- [ ] Virtual environment created and activated
- [ ] Code transferred to container
- [ ] `.env` moved to `/etc/orb-trader/` with chmod 600
- [ ] Code updated to use `/etc/orb-trader/.env`
- [ ] Dependencies installed from requirements.txt
- [ ] Metrics database initialized
- [ ] systemd service created and enabled
- [ ] Timezone set to America/New_York
- [ ] Healthcheck script created and cron configured
- [ ] Git initialized and pushed to GitHub
- [ ] Manual test run successful
- [ ] Service started and verified with journalctl
- [ ] Container rebooted to test auto-start

## Verification Commands
```bash
# Check service status
systemctl status orb-trader

# View live logs
journalctl -u orb-trader -f

# Check last 50 log entries
journalctl -u orb-trader -n 50

# Verify timezone
timedatectl

# Test metrics database
sqlite3 /opt/orb-trader/metrics.db "SELECT * FROM trades LIMIT 10;"

# Check if service survives reboot
reboot
# After reboot:
systemctl status orb-trader
```

## Performance Metrics Access
**Quick daily summary:**
```bash
sqlite3 /opt/orb-trader/metrics.db << EOF
SELECT 
    date(timestamp) as date,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(pnl), 2) as total_pnl
FROM trades 
WHERE pnl IS NOT NULL 
GROUP BY date(timestamp)
ORDER BY date DESC
LIMIT 7;
EOF
```

## Notes for Claude Code
- Container must be created on Proxmox host before code transfer
- Use `pct enter 100` to access container, not SSH initially
- All Python code runs inside venv at `/opt/orb-trader/venv`
- Service runs as root (acceptable for homelab; production would use dedicated user)
- No firewall rules needed unless exposing a web dashboard later
- Metrics schema is minimal - expand as needed for more analytics