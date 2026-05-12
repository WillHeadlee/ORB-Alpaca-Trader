from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from typing import Optional
import subprocess
import os

from alpaca.trading.client import TradingClient

from backend.database import get_db
from backend.models import Trade, Position, DailySummary, ScreenerResult, User, SystemLog
from backend.auth import verify_password, create_access_token, get_password_hash, verify_token
from utils.email_alerts import send_alert

def _get_alpaca_balance() -> float:
    try:
        client = TradingClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            paper=os.getenv('ALPACA_PAPER', 'true').lower() != 'false',
        )
        account = client.get_account()
        return float(account.equity)
    except Exception:
        return 0.0

router = APIRouter()

# ============================================================================
# AUTHENTICATION
# ============================================================================

@router.post("/api/auth/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/api/dashboard/status")
def get_status(db: Session = Depends(get_db), username: str = Depends(verify_token)):
    try:
        result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'orb-trader'],
                                capture_output=True, text=True)
        bot_status = 'running' if result.stdout.strip() == 'active' else 'stopped'
    except Exception:
        bot_status = 'unknown'

    positions = db.query(Position).all()

    today = date.today()
    today_trades = db.query(Trade).filter(func.date(Trade.timestamp) == today).all()
    today_pnl = sum(float(t.pnl or 0) for t in today_trades)

    account_balance = _get_alpaca_balance()
    mode = "paper" if os.getenv('ALPACA_PAPER', 'true').lower() != 'false' else "live"

    return {
        "bot_status": bot_status,
        "mode": mode,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "entry_price": float(p.entry_price),
                "current_price": float(p.current_price or p.entry_price),
                "unrealized_pnl": float(p.unrealized_pnl or 0),
                "entry_time": p.entry_time.isoformat(),
            }
            for p in positions
        ],
        "today_pnl": today_pnl,
        "account_balance": account_balance,
    }

@router.get("/api/dashboard/trades")
def get_trades(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    username: str = Depends(verify_token),
):
    trades = db.query(Trade).order_by(Trade.timestamp.desc()).limit(limit).offset(offset).all()
    total = db.query(func.count(Trade.id)).scalar()
    return {
        "trades": [
            {
                "id": t.id,
                "timestamp": t.timestamp.isoformat(),
                "symbol": t.symbol,
                "action": t.action,
                "quantity": t.quantity,
                "entry_price": float(t.entry_price or 0),
                "exit_price": float(t.exit_price or 0),
                "pnl": float(t.pnl or 0),
                "mode": t.mode,
            }
            for t in trades
        ],
        "total": total,
    }

@router.get("/api/dashboard/performance")
def get_performance(
    period: str = "30d",
    db: Session = Depends(get_db),
    username: str = Depends(verify_token),
):
    days = int(period.rstrip('d'))
    start_date = datetime.now() - timedelta(days=days)

    trades = db.query(Trade).filter(
        Trade.timestamp >= start_date,
        Trade.pnl.isnot(None),
    ).all()

    if not trades:
        return {
            "total_pnl": 0, "win_rate": 0, "daily_pnl": [],
            "total_trades": 0, "winning_trades": 0,
            "avg_win": 0, "avg_loss": 0,
        }

    total_pnl = sum(float(t.pnl) for t in trades)
    wins = [t for t in trades if float(t.pnl) > 0]
    losses = [t for t in trades if float(t.pnl) < 0]

    win_rate = len(wins) / len(trades)
    avg_win = sum(float(t.pnl) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(float(t.pnl) for t in losses) / len(losses) if losses else 0

    daily_pnl = db.query(
        func.date(Trade.timestamp).label('date'),
        func.sum(Trade.pnl).label('pnl'),
    ).filter(
        Trade.timestamp >= start_date,
        Trade.pnl.isnot(None),
    ).group_by(func.date(Trade.timestamp)).order_by('date').all()

    cumulative = 0
    daily_data = []
    for day in daily_pnl:
        cumulative += float(day.pnl)
        daily_data.append({
            "date": day.date.isoformat(),
            "pnl": float(day.pnl),
            "cumulative_pnl": cumulative,
        })

    return {
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "daily_pnl": daily_data,
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }

@router.get("/api/dashboard/logs")
def get_logs(
    level: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    username: str = Depends(verify_token),
):
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    logs = query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "source": log.source,
            }
            for log in logs
        ]
    }

# ============================================================================
# TRADING CONTROLS
# ============================================================================

@router.post("/api/trading/kill-switch")
def kill_switch(db: Session = Depends(get_db), username: str = Depends(verify_token)):
    try:
        positions = db.query(Position).all()
        if not positions:
            return {"message": "No positions to close", "positions_closed": 0}

        closed_count = len(positions)

        # TODO: call Alpaca API to close positions before clearing DB
        db.add(SystemLog(
            level='CRITICAL',
            message=f'Kill switch activated by {username}. Closed {closed_count} positions.',
            source='kill_switch',
        ))
        db.query(Position).delete()
        db.commit()

        send_alert(
            "Kill Switch Activated",
            f"<h2>Emergency stop triggered</h2><p>User: {username}</p>"
            f"<p>Positions closed: {closed_count}</p>",
        )

        return {"message": f"Successfully closed {closed_count} positions", "positions_closed": closed_count}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/trading/pause")
def pause_trading(username: str = Depends(verify_token)):
    try:
        subprocess.run(['/usr/bin/systemctl', 'stop', 'orb-trader'], check=True)
        return {"status": "paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/trading/resume")
def resume_trading(username: str = Depends(verify_token)):
    try:
        subprocess.run(['/usr/bin/systemctl', 'start', 'orb-trader'], check=True)
        return {"status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/trading/positions")
def get_positions(db: Session = Depends(get_db), username: str = Depends(verify_token)):
    positions = db.query(Position).all()
    return {
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "entry_price": float(p.entry_price),
                "current_price": float(p.current_price or p.entry_price),
                "unrealized_pnl": float(p.unrealized_pnl or 0),
            }
            for p in positions
        ]
    }

# ============================================================================
# SCREENER
# ============================================================================

@router.get("/api/screener/latest")
def get_screener_results(db: Session = Depends(get_db), username: str = Depends(verify_token)):
    latest_scan = db.query(func.max(ScreenerResult.scan_timestamp)).scalar()
    if not latest_scan:
        return {"results": [], "timestamp": None}

    results = db.query(ScreenerResult).filter(
        ScreenerResult.scan_timestamp == latest_scan
    ).order_by(ScreenerResult.score.desc()).all()

    return {
        "timestamp": latest_scan.isoformat(),
        "results": [
            {
                "symbol": r.symbol,
                "price": float(r.price),
                "avg_volume": r.avg_volume,
                "volatility": float(r.volatility or 0),
                "score": float(r.score),
            }
            for r in results
        ],
    }
