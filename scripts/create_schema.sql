-- 거래 테이블
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(50) NOT NULL UNIQUE,
    pair VARCHAR(20) NOT NULL,
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    entry_price FLOAT,
    exit_price FLOAT,
    quantity FLOAT NOT NULL,
    side VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    pnl FLOAT,
    pnl_pct FLOAT,
    fee FLOAT,
    strategy VARCHAR(50),
    timeframe VARCHAR(10),
    reason VARCHAR(50),
    tags JSONB,
    risk_reward_ratio FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    session_id VARCHAR(50),
    entry_order_id VARCHAR(50),
    exit_order_id VARCHAR(50)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_trades_trade_id ON trades(trade_id);
CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair);
CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time);
CREATE INDEX IF NOT EXISTS idx_trades_close_time ON trades(close_time);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_strategy_pair ON trades(strategy, pair);
CREATE INDEX IF NOT EXISTS idx_trades_open_close_time ON trades(open_time, close_time);

-- 자산 곡선 테이블
CREATE TABLE IF NOT EXISTS equity_curve (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP NOT NULL,
    balance_usdt FLOAT NOT NULL,
    balance_btc FLOAT,
    open_positions_value FLOAT,
    total_value FLOAT NOT NULL,
    drawdown_pct FLOAT,
    session_id VARCHAR(50)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_equity_curve_ts ON equity_curve(ts);
CREATE INDEX IF NOT EXISTS idx_equity_curve_balance ON equity_curve(balance_usdt);

-- 파라미터 세트 테이블
CREATE TABLE IF NOT EXISTS param_set (
    id SERIAL PRIMARY KEY,
    strategy VARCHAR(50) NOT NULL,
    params JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    description VARCHAR(200),
    backtest_result JSONB
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_param_set_strategy ON param_set(strategy);
CREATE INDEX IF NOT EXISTS idx_param_set_is_active ON param_set(is_active);

-- 일일 통계 테이블
CREATE TABLE IF NOT EXISTS stats_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    strategy VARCHAR(50),
    pair VARCHAR(20),
    trades_count INTEGER NOT NULL DEFAULT 0,
    win_count INTEGER NOT NULL DEFAULT 0,
    loss_count INTEGER NOT NULL DEFAULT 0,
    win_rate FLOAT,
    profit_factor FLOAT,
    total_pnl FLOAT NOT NULL DEFAULT 0,
    total_pnl_pct FLOAT,
    max_drawdown FLOAT,
    avg_trade_duration FLOAT,
    avg_profit_trade FLOAT,
    avg_loss_trade FLOAT
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_stats_daily_date ON stats_daily(date);
CREATE INDEX IF NOT EXISTS idx_stats_daily_strategy ON stats_daily(strategy);
CREATE INDEX IF NOT EXISTS idx_stats_daily_pair ON stats_daily(pair);
CREATE INDEX IF NOT EXISTS idx_stats_daily_date_strategy ON stats_daily(date, strategy);
CREATE INDEX IF NOT EXISTS idx_stats_daily_win_rate ON stats_daily(win_rate);
CREATE INDEX IF NOT EXISTS idx_stats_daily_profit_factor ON stats_daily(profit_factor);

-- 주문 테이블 (이미 존재하는 경우 생성하지 않음)
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL UNIQUE,
    client_order_id VARCHAR(64),
    exchange_order_id VARCHAR(64),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    quantity FLOAT NOT NULL,
    price FLOAT,
    filled_quantity FLOAT DEFAULT 0.0,
    remaining_quantity FLOAT,
    average_price FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    exchange_timestamp TIMESTAMP,
    strategy VARCHAR(50),
    timeframe VARCHAR(10),
    indicators JSONB,
    is_dry_run BOOLEAN DEFAULT FALSE,
    is_fallback BOOLEAN DEFAULT FALSE,
    parent_order_id VARCHAR(64)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON orders(symbol, status);
CREATE INDEX IF NOT EXISTS idx_orders_strategy_timeframe ON orders(strategy, timeframe);
CREATE INDEX IF NOT EXISTS idx_orders_created_at_status ON orders(created_at, status);

-- 체결 테이블
CREATE TABLE IF NOT EXISTS fills (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,
    fill_id VARCHAR(64) UNIQUE,
    price FLOAT NOT NULL,
    quantity FLOAT NOT NULL,
    fee FLOAT,
    fee_asset VARCHAR(10),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_maker BOOLEAN DEFAULT FALSE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills(order_id);
CREATE INDEX IF NOT EXISTS idx_fills_timestamp ON fills(timestamp);

-- 주문 오류 테이블
CREATE TABLE IF NOT EXISTS order_errors (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(64),
    error_code VARCHAR(50),
    error_message TEXT NOT NULL,
    error_details JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_order_errors_order_id ON order_errors(order_id);
CREATE INDEX IF NOT EXISTS idx_order_errors_timestamp ON order_errors(timestamp);

-- 지표 스냅샷 테이블
CREATE TABLE IF NOT EXISTS indicator_snapshots (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    rsi FLOAT,
    ewo FLOAT,
    ema_short FLOAT,
    ema_medium FLOAT,
    ema_long FLOAT,
    sma_short FLOAT,
    sma_medium FLOAT,
    sma_long FLOAT,
    additional_indicators JSONB,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    volume FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_indicator_snapshots_symbol ON indicator_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_indicator_snapshots_timestamp ON indicator_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_indicator_snapshots_symbol_timeframe_timestamp ON indicator_snapshots(symbol, timeframe, timestamp);

-- 거래 세션 테이블
CREATE TABLE IF NOT EXISTS trade_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    strategy VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    config JSONB,
    total_trades INTEGER DEFAULT 0,
    profitable_trades INTEGER DEFAULT 0,
    total_profit FLOAT DEFAULT 0.0,
    total_profit_percent FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    is_dry_run BOOLEAN DEFAULT FALSE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_trade_sessions_strategy ON trade_sessions(strategy);
CREATE INDEX IF NOT EXISTS idx_trade_sessions_start_time ON trade_sessions(start_time);

-- Alembic 버전 테이블 (마이그레이션 추적용)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- 초기 버전 설정
INSERT INTO alembic_version (version_num) VALUES ('initial_schema') ON CONFLICT DO NOTHING;
