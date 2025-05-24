"""Initial database schema

Revision ID: initial_schema
Revises: 
Create Date: 2023-05-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 주문 테이블
    op.create_table('orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.String(length=50), nullable=False),
        sa.Column('exchange', sa.String(length=20), nullable=False),
        sa.Column('pair', sa.String(length=20), nullable=False),
        sa.Column('order_type', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_order_id'), 'orders', ['order_id'], unique=True)
    op.create_index(op.f('ix_orders_pair'), 'orders', ['pair'], unique=False)
    op.create_index(op.f('ix_orders_created_at'), 'orders', ['created_at'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    
    # 체결 테이블
    op.create_table('fills',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.String(length=50), nullable=False),
        sa.Column('fill_id', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), nullable=True),
        sa.Column('fee_currency', sa.String(length=10), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fills_order_id'), 'fills', ['order_id'], unique=False)
    op.create_index(op.f('ix_fills_timestamp'), 'fills', ['timestamp'], unique=False)
    
    # 주문 오류 테이블
    op.create_table('order_errors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.String(length=50), nullable=True),
        sa.Column('exchange', sa.String(length=20), nullable=False),
        sa.Column('pair', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.String(length=500), nullable=False),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('request_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_errors_timestamp'), 'order_errors', ['timestamp'], unique=False)
    
    # 지표 스냅샷 테이블
    op.create_table('indicator_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pair', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('indicators', sa.JSON(), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_indicator_snapshots_pair'), 'indicator_snapshots', ['pair'], unique=False)
    op.create_index(op.f('ix_indicator_snapshots_timestamp'), 'indicator_snapshots', ['timestamp'], unique=False)
    
    # 거래 세션 테이블
    op.create_table('trade_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('initial_balance', sa.Float(), nullable=False),
        sa.Column('final_balance', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_pct', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trade_sessions_session_id'), 'trade_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_trade_sessions_start_time'), 'trade_sessions', ['start_time'], unique=False)
    
    # 거래 테이블
    op.create_table('trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_id', sa.String(length=50), nullable=False),
        sa.Column('session_id', sa.String(length=50), nullable=True),
        sa.Column('pair', sa.String(length=20), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('entry_order_id', sa.String(length=50), nullable=True),
        sa.Column('exit_order_id', sa.String(length=50), nullable=True),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_pct', sa.Float(), nullable=True),
        sa.Column('open_time', sa.DateTime(), nullable=False),
        sa.Column('close_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('risk_reward_ratio', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_trade_id'), 'trades', ['trade_id'], unique=True)
    op.create_index(op.f('ix_trades_pair'), 'trades', ['pair'], unique=False)
    op.create_index(op.f('ix_trades_open_time'), 'trades', ['open_time'], unique=False)
    op.create_index(op.f('ix_trades_close_time'), 'trades', ['close_time'], unique=False)
    op.create_index(op.f('ix_trades_status'), 'trades', ['status'], unique=False)
    
    # 자산 곡선 테이블
    op.create_table('equity_curve',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('balance_usdt', sa.Float(), nullable=False),
        sa.Column('balance_btc', sa.Float(), nullable=True),
        sa.Column('open_positions_value', sa.Float(), nullable=True),
        sa.Column('total_value', sa.Float(), nullable=False),
        sa.Column('drawdown_pct', sa.Float(), nullable=True),
        sa.Column('session_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_equity_curve_ts'), 'equity_curve', ['ts'], unique=False)
    
    # 파라미터 세트 테이블
    op.create_table('param_set',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('params', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('backtest_result', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_param_set_strategy'), 'param_set', ['strategy'], unique=False)
    
    # 일일 통계 테이블
    op.create_table('stats_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('pair', sa.String(length=20), nullable=True),
        sa.Column('trades_count', sa.Integer(), nullable=False),
        sa.Column('win_count', sa.Integer(), nullable=False),
        sa.Column('loss_count', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=False),
        sa.Column('total_pnl_pct', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('avg_trade_duration', sa.Float(), nullable=True),
        sa.Column('avg_profit_trade', sa.Float(), nullable=True),
        sa.Column('avg_loss_trade', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stats_daily_date'), 'stats_daily', ['date'], unique=False)
    op.create_index(op.f('ix_stats_daily_strategy'), 'stats_daily', ['strategy'], unique=False)
    op.create_index(op.f('ix_stats_daily_pair'), 'stats_daily', ['pair'], unique=False)


def downgrade() -> None:
    # 테이블 삭제 (생성의 역순)
    op.drop_table('stats_daily')
    op.drop_table('param_set')
    op.drop_table('equity_curve')
    op.drop_table('trades')
    op.drop_table('trade_sessions')
    op.drop_table('indicator_snapshots')
    op.drop_table('order_errors')
    op.drop_table('fills')
    op.drop_table('orders')
