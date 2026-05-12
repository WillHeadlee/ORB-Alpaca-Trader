from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    symbol = Column(String(10), nullable=False)
    action = Column(String(4), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(10, 4))
    exit_price = Column(Numeric(10, 4))
    pnl = Column(Numeric(10, 4))
    mode = Column(String(10), nullable=False)
    stop_loss = Column(Numeric(10, 4))
    take_profit = Column(Numeric(10, 4))
    exit_reason = Column(String(100))
    alpaca_order_id = Column(String(100), nullable=True)

class Position(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(10, 4), nullable=False)
    current_price = Column(Numeric(10, 4))
    unrealized_pnl = Column(Numeric(10, 4))
    entry_time = Column(DateTime(timezone=True), nullable=False)
    stop_loss = Column(Numeric(10, 4))
    take_profit = Column(Numeric(10, 4))

class DailySummary(Base):
    __tablename__ = 'daily_summary'

    date = Column(Date, primary_key=True)
    mode = Column(String(10), nullable=False)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    total_pnl = Column(Numeric(10, 4))
    largest_win = Column(Numeric(10, 4))
    largest_loss = Column(Numeric(10, 4))
    symbols_traded = Column(ARRAY(String))

class ScreenerResult(Base):
    __tablename__ = 'screener_results'

    id = Column(Integer, primary_key=True)
    scan_timestamp = Column(DateTime(timezone=True), nullable=False)
    symbol = Column(String(10), nullable=False)
    price = Column(Numeric(10, 4))
    avg_volume = Column(Integer)
    volatility = Column(Numeric(5, 2))
    score = Column(Numeric(5, 2))

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    level = Column(String(10), nullable=False)
    message = Column(String, nullable=False)
    source = Column(String(50))
