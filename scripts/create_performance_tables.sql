-- 성능 지표 테이블
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    strategy VARCHAR(50),
    pair VARCHAR(20),
    total_trades INTEGER NOT NULL,
    win_rate FLOAT NOT NULL,
    profit_factor FLOAT,
    average_profit FLOAT,
    average_profit_percent FLOAT,
    average_duration FLOAT,
    sharpe_ratio FLOAT,
    sortino_ratio FLOAT,
    calmar_ratio FLOAT,
    max_drawdown FLOAT,
    max_drawdown_duration INTEGER,
    volatility FLOAT,
    expectancy FLOAT,
    recovery_factor FLOAT,
    profit_to_drawdown FLOAT,
    average_winning_trade FLOAT,
    average_losing_trade FLOAT,
    largest_winning_trade FLOAT,
    largest_losing_trade FLOAT,
    max_consecutive_wins INTEGER,
    max_consecutive_losses INTEGER,
    profit_per_day FLOAT,
    annual_return FLOAT
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy ON performance_metrics(strategy);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_pair ON performance_metrics(pair);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_date_range ON performance_metrics(start_date, end_date);

-- 보고서 테이블
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    report_type VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    strategy VARCHAR(50),
    file_path VARCHAR(500) NOT NULL,
    metrics_id INTEGER REFERENCES performance_metrics(id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON reports(timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_report_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_strategy ON reports(strategy);
CREATE INDEX IF NOT EXISTS idx_reports_date_range ON reports(start_date, end_date);
