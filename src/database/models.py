"""
데이터베이스 모델 모듈

이 모듈은 거래 데이터를 저장하기 위한 데이터베이스 모델을 정의합니다.
주문, 거래, 체결, 오류 로그 및 지표 스냅샷을 위한 테이블이 포함됩니다.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.database.connection import Base

logger = logging.getLogger(__name__)

class OrderStatus(str, Enum):
    """주문 상태 열거형"""
    PENDING = 'pending'           # 주문 생성됨
    OPEN = 'open'                 # 주문 제출됨
    PARTIALLY_FILLED = 'partially_filled'  # 부분 체결
    FILLED = 'filled'             # 완전 체결
    CANCELED = 'canceled'         # 취소됨
    REJECTED = 'rejected'         # 거부됨
    EXPIRED = 'expired'           # 만료됨
    FALLBACK = 'fallback'         # 폴백 진행 중
    ERROR = 'error'               # 오류 발생

class OrderType(str, Enum):
    """주문 유형 열거형"""
    LIMIT = 'limit'               # 지정가 주문
    MARKET = 'market'             # 시장가 주문
    STOP_LOSS = 'stop_loss'       # 손절매 주문
    TAKE_PROFIT = 'take_profit'   # 이익 실현 주문

class OrderSide(str, Enum):
    """주문 방향 열거형"""
    BUY = 'buy'                   # 매수
    SELL = 'sell'                 # 매도

class TimeFrame(str, Enum):
    """시간 프레임 열거형"""
    M1 = '1m'                     # 1분
    M5 = '5m'                     # 5분
    M15 = '15m'                   # 15분
    M30 = '30m'                   # 30분
    H1 = '1h'                     # 1시간
    H4 = '4h'                     # 4시간
    D1 = '1d'                     # 1일

class Order(Base):
    """주문 모델"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, nullable=False, index=True)
    client_order_id = Column(String(64), index=True)
    exchange_order_id = Column(String(64), index=True)
    
    # 주문 기본 정보
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    type = Column(SQLEnum(OrderType), nullable=False)
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    
    # 주문 수량 및 가격
    quantity = Column(Float, nullable=False)
    price = Column(Float)
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float)
    average_price = Column(Float)
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    exchange_timestamp = Column(DateTime)
    
    # 전략 및 지표 정보
    strategy = Column(String(50))
    timeframe = Column(SQLEnum(TimeFrame))
    indicators = Column(JSONB)
    
    # 추가 정보
    is_dry_run = Column(Boolean, default=False)
    is_fallback = Column(Boolean, default=False)
    parent_order_id = Column(String(64), ForeignKey('orders.order_id'), nullable=True)
    
    # 관계
    fills = relationship("Fill", back_populates="order", cascade="all, delete-orphan")
    errors = relationship("OrderError", back_populates="order", cascade="all, delete-orphan")
    child_orders = relationship("Order", backref=relationship("parent", remote_side=[order_id]))
    
    # 인덱스
    __table_args__ = (
        Index('idx_orders_symbol_status', 'symbol', 'status'),
        Index('idx_orders_created_at', 'created_at'),
        Index('idx_orders_strategy_timeframe', 'strategy', 'timeframe'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        주문 정보를 딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 주문 정보 딕셔너리
        """
        return {
            'id': self.id,
            'order_id': self.order_id,
            'client_order_id': self.client_order_id,
            'exchange_order_id': self.exchange_order_id,
            'symbol': self.symbol,
            'side': self.side.value if self.side else None,
            'type': self.type.value if self.type else None,
            'status': self.status.value if self.status else None,
            'quantity': self.quantity,
            'price': self.price,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.remaining_quantity,
            'average_price': self.average_price,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'exchange_timestamp': self.exchange_timestamp.isoformat() if self.exchange_timestamp else None,
            'strategy': self.strategy,
            'timeframe': self.timeframe.value if self.timeframe else None,
            'indicators': self.indicators,
            'is_dry_run': self.is_dry_run,
            'is_fallback': self.is_fallback,
            'parent_order_id': self.parent_order_id,
            'fills': [fill.to_dict() for fill in self.fills] if self.fills else [],
            'errors': [error.to_dict() for error in self.errors] if self.errors else []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """
        딕셔너리에서 주문 객체 생성
        
        Args:
            data: 주문 정보 딕셔너리
            
        Returns:
            Order: 주문 객체
        """
        # 기본 필드 설정
        order = cls(
            order_id=data['order_id'],
            client_order_id=data.get('client_order_id'),
            exchange_order_id=data.get('exchange_order_id'),
            symbol=data['symbol'],
            side=OrderSide(data['side']) if data.get('side') else None,
            type=OrderType(data['type']) if data.get('type') else None,
            status=OrderStatus(data['status']) if data.get('status') else OrderStatus.PENDING,
            quantity=data['quantity'],
            price=data.get('price'),
            filled_quantity=data.get('filled_quantity', 0.0),
            remaining_quantity=data.get('remaining_quantity'),
            average_price=data.get('average_price'),
            strategy=data.get('strategy'),
            timeframe=TimeFrame(data['timeframe']) if data.get('timeframe') else None,
            indicators=data.get('indicators'),
            is_dry_run=data.get('is_dry_run', False),
            is_fallback=data.get('is_fallback', False),
            parent_order_id=data.get('parent_order_id')
        )
        
        # 시간 정보 설정
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                order.created_at = datetime.fromisoformat(data['created_at'])
            else:
                order.created_at = data['created_at']
        
        if 'updated_at' in data and data['updated_at']:
            if isinstance(data['updated_at'], str):
                order.updated_at = datetime.fromisoformat(data['updated_at'])
            else:
                order.updated_at = data['updated_at']
        
        if 'exchange_timestamp' in data and data['exchange_timestamp']:
            if isinstance(data['exchange_timestamp'], str):
                order.exchange_timestamp = datetime.fromisoformat(data['exchange_timestamp'])
            else:
                order.exchange_timestamp = data['exchange_timestamp']
        
        return order


class Fill(Base):
    """체결 모델"""
    __tablename__ = 'fills'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), ForeignKey('orders.order_id'), nullable=False)
    fill_id = Column(String(64), unique=True)
    
    # 체결 정보
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    fee = Column(Float)
    fee_asset = Column(String(10))
    
    # 시간 정보
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 추가 정보
    is_maker = Column(Boolean, default=False)
    
    # 관계
    order = relationship("Order", back_populates="fills")
    
    # 인덱스
    __table_args__ = (
        Index('idx_fills_order_id', 'order_id'),
        Index('idx_fills_timestamp', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        체결 정보를 딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 체결 정보 딕셔너리
        """
        return {
            'id': self.id,
            'order_id': self.order_id,
            'fill_id': self.fill_id,
            'price': self.price,
            'quantity': self.quantity,
            'fee': self.fee,
            'fee_asset': self.fee_asset,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_maker': self.is_maker
        }


class OrderError(Base):
    """주문 오류 모델"""
    __tablename__ = 'order_errors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), ForeignKey('orders.order_id'), nullable=False)
    
    # 오류 정보
    error_code = Column(String(50))
    error_message = Column(Text, nullable=False)
    error_details = Column(JSONB)
    
    # 시간 정보
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 관계
    order = relationship("Order", back_populates="errors")
    
    # 인덱스
    __table_args__ = (
        Index('idx_order_errors_order_id', 'order_id'),
        Index('idx_order_errors_timestamp', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        오류 정보를 딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 오류 정보 딕셔너리
        """
        return {
            'id': self.id,
            'order_id': self.order_id,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class IndicatorSnapshot(Base):
    """지표 스냅샷 모델"""
    __tablename__ = 'indicator_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 기본 정보
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(SQLEnum(TimeFrame), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # 지표 값
    rsi = Column(Float)
    ewo = Column(Float)
    ema_short = Column(Float)
    ema_medium = Column(Float)
    ema_long = Column(Float)
    sma_short = Column(Float)
    sma_medium = Column(Float)
    sma_long = Column(Float)
    
    # 추가 지표 (JSON 형식으로 저장)
    additional_indicators = Column(JSONB)
    
    # 캔들 데이터
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    # 생성 시간
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 인덱스
    __table_args__ = (
        Index('idx_indicator_snapshots_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        지표 스냅샷 정보를 딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 지표 스냅샷 정보 딕셔너리
        """
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timeframe': self.timeframe.value if self.timeframe else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'rsi': self.rsi,
            'ewo': self.ewo,
            'ema_short': self.ema_short,
            'ema_medium': self.ema_medium,
            'ema_long': self.ema_long,
            'sma_short': self.sma_short,
            'sma_medium': self.sma_medium,
            'sma_long': self.sma_long,
            'additional_indicators': self.additional_indicators,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TradeSession(Base):
    """거래 세션 모델"""
    __tablename__ = 'trade_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False)
    
    # 세션 정보
    strategy = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    # 세션 설정
    config = Column(JSONB)
    
    # 세션 결과
    total_trades = Column(Integer, default=0)
    profitable_trades = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    total_profit_percent = Column(Float, default=0.0)
    
    # 상태
    is_active = Column(Boolean, default=True)
    is_dry_run = Column(Boolean, default=False)
    
    # 인덱스
    __table_args__ = (
        Index('idx_trade_sessions_strategy', 'strategy'),
        Index('idx_trade_sessions_start_time', 'start_time'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        거래 세션 정보를 딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 거래 세션 정보 딕셔너리
        """
        return {
            'id': self.id,
            'session_id': self.session_id,
            'strategy': self.strategy,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'config': self.config,
            'total_trades': self.total_trades,
            'profitable_trades': self.profitable_trades,
            'total_profit': self.total_profit,
            'total_profit_percent': self.total_profit_percent,
            'is_active': self.is_active,
            'is_dry_run': self.is_dry_run
        }
