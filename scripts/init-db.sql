-- PostgreSQL 초기화 스크립트
-- NASOSv5_mod3 Bot 데이터베이스 스키마 생성

-- 트레이드 테이블
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    open_time TIMESTAMP WITH TIME ZONE NOT NULL,
    close_time TIMESTAMP WITH TIME ZONE,
    open_price NUMERIC(18, 8) NOT NULL,
    close_price NUMERIC(18, 8),
    quantity NUMERIC(18, 8) NOT NULL,
    side VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    pnl_pct NUMERIC(10, 2),
    pnl_usdt NUMERIC(18, 8),
    fee NUMERIC(18, 8),
    strategy VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 캔들 데이터 테이블 (5분)
CREATE TABLE IF NOT EXISTS candle_5m (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open NUMERIC(18, 8) NOT NULL,
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume NUMERIC(18, 8) NOT NULL,
    UNIQUE (pair, timestamp)
);

-- 자산 밸런스 테이블
CREATE TABLE IF NOT EXISTS balances (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    asset VARCHAR(20) NOT NULL,
    free NUMERIC(18, 8) NOT NULL,
    locked NUMERIC(18, 8) NOT NULL,
    total NUMERIC(18, 8) NOT NULL,
    usdt_value NUMERIC(18, 8) NOT NULL,
    UNIQUE (timestamp, asset)
);

-- 자산 가치 곡선 테이블
CREATE TABLE IF NOT EXISTS equity_curve (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    balance_usdt NUMERIC(18, 8) NOT NULL,
    UNIQUE (timestamp)
);

-- 일일 통계 테이블
CREATE TABLE IF NOT EXISTS stats_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    trades_count INTEGER NOT NULL,
    win_count INTEGER NOT NULL,
    loss_count INTEGER NOT NULL,
    win_rate NUMERIC(5, 2),
    profit_factor NUMERIC(10, 2),
    total_pnl_usdt NUMERIC(18, 8) NOT NULL,
    total_pnl_pct NUMERIC(10, 2) NOT NULL,
    max_drawdown NUMERIC(10, 2),
    sharpe_ratio NUMERIC(10, 2),
    calmar_ratio NUMERIC(10, 2),
    exposure_pct NUMERIC(5, 2),
    UNIQUE (date)
);

-- 전략 파라미터 세트 테이블
CREATE TABLE IF NOT EXISTS param_sets (
    id SERIAL PRIMARY KEY,
    strategy VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    params JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (strategy, version)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair);
CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
CREATE INDEX IF NOT EXISTS idx_candle_5m_pair_timestamp ON candle_5m(pair, timestamp);
CREATE INDEX IF NOT EXISTS idx_equity_curve_timestamp ON equity_curve(timestamp);
CREATE INDEX IF NOT EXISTS idx_stats_daily_date ON stats_daily(date);

-- 권한 설정
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nasos_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nasos_user;
