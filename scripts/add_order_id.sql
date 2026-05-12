ALTER TABLE trades ADD COLUMN IF NOT EXISTS alpaca_order_id VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades(alpaca_order_id);
