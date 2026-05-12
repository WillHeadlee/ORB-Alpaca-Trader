-- Trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(4) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10, 4),
    exit_price DECIMAL(10, 4),
    pnl DECIMAL(10, 4),
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('paper', 'live')),
    stop_loss DECIMAL(10, 4),
    take_profit DECIMAL(10, 4),
    exit_reason VARCHAR(100)
);

CREATE INDEX idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX idx_trades_symbol ON trades(symbol);

-- Active positions
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10, 4) NOT NULL,
    current_price DECIMAL(10, 4),
    unrealized_pnl DECIMAL(10, 4),
    entry_time TIMESTAMPTZ NOT NULL,
    stop_loss DECIMAL(10, 4),
    take_profit DECIMAL(10, 4)
);

-- Daily summaries
CREATE TABLE daily_summary (
    date DATE PRIMARY KEY,
    mode VARCHAR(10) NOT NULL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    total_pnl DECIMAL(10, 4),
    largest_win DECIMAL(10, 4),
    largest_loss DECIMAL(10, 4),
    symbols_traded TEXT[]
);

-- Screener results
CREATE TABLE screener_results (
    id SERIAL PRIMARY KEY,
    scan_timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(10, 4),
    avg_volume BIGINT,
    volatility DECIMAL(5, 2),
    score DECIMAL(5, 2)
);

CREATE INDEX idx_screener_timestamp ON screener_results(scan_timestamp DESC);

-- Dashboard users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System logs
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(50)
);

CREATE INDEX idx_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX idx_logs_level ON system_logs(level);
