#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 서버를 위한 데이터베이스 모델 정의
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel

Base = declarative_base()

# SQLAlchemy 모델
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    strategy = Column(String, index=True)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    amount = Column(Float)
    fee = Column(Float)
    profit = Column(Float, nullable=True)
    profit_percentage = Column(Float, nullable=True)
    status = Column(String)  # open, closed, cancelled
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trade_type = Column(String)  # buy, sell
    exchange = Column(String)
    order_id = Column(String, nullable=True)

class BotStatus(Base):
    __tablename__ = "bot_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String)  # running, stopped, paused
    mode = Column(String)  # live, paper, backtest
    uptime = Column(Integer)  # seconds
    last_update = Column(DateTime, default=datetime.utcnow)
    active_trades = Column(Integer, default=0)
    balance = Column(Float)
    equity = Column(Float)
    strategy = Column(String)
    exchange = Column(String)

class Parameter(Base):
    __tablename__ = "parameters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    value = Column(String)
    description = Column(String, nullable=True)
    strategy = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy = Column(String, index=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    total_trades = Column(Integer)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    profit_percentage = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    parameters = Column(String)  # JSON string of parameters used

# Pydantic 모델 (API 요청/응답 스키마)
class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

class TradeBase(BaseModel):
    symbol: str
    strategy: str
    entry_price: float
    amount: float
    fee: float
    status: str
    trade_type: str
    exchange: str

class TradeCreate(TradeBase):
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_id: Optional[str] = None

class TradeUpdate(BaseModel):
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    profit: Optional[float] = None
    profit_percentage: Optional[float] = None
    status: Optional[str] = None
    order_id: Optional[str] = None

class TradeResponse(TradeBase):
    id: int
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    profit: Optional[float] = None
    profit_percentage: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_id: Optional[str] = None

    class Config:
        orm_mode = True

class BotStatusBase(BaseModel):
    status: str
    mode: str
    uptime: int
    active_trades: int
    balance: float
    equity: float
    strategy: str
    exchange: str

class BotStatusCreate(BotStatusBase):
    pass

class BotStatusUpdate(BaseModel):
    status: Optional[str] = None
    mode: Optional[str] = None
    uptime: Optional[int] = None
    active_trades: Optional[int] = None
    balance: Optional[float] = None
    equity: Optional[float] = None

class BotStatusResponse(BotStatusBase):
    id: int
    last_update: datetime

    class Config:
        orm_mode = True

class ParameterBase(BaseModel):
    name: str
    value: str
    strategy: str
    description: Optional[str] = None

class ParameterCreate(ParameterBase):
    pass

class ParameterUpdate(BaseModel):
    value: str
    description: Optional[str] = None

class ParameterResponse(ParameterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class BacktestResultBase(BaseModel):
    strategy: str
    start_date: datetime
    end_date: datetime
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    profit_percentage: float
    parameters: str

class BacktestResultCreate(BacktestResultBase):
    pass

class BacktestResultResponse(BacktestResultBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class PerformanceMetrics(BaseModel):
    win_rate: float
    profit_factor: float
    sharpe: float
    max_drawdown: float
    total_trades: int
    profit_percentage: float
