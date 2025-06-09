#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
성능 지표 관련 API 라우터
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from src.api_server.models.database import get_db
from src.api_server.models.models import Trade, PerformanceMetrics
from src.api_server.auth.auth import get_current_active_user
from src.analytics.performance_analyzer import PerformanceAnalyzer

router = APIRouter(
    prefix="/performance",
    tags=["performance"],
    dependencies=[Depends(get_current_active_user)],
    responses={401: {"description": "Unauthorized"}},
)

# DEAD CODE: @router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    timeframe: str = "all",
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    성능 지표 조회
    
    - **timeframe**: 기간 (all, day, week, month, year)
    - **strategy**: 전략 필터
    - **symbol**: 심볼 필터
    """
    # 날짜 범위 설정
    end_date = datetime.utcnow()
    if timeframe == "day":
        start_date = end_date - timedelta(days=1)
    elif timeframe == "week":
        start_date = end_date - timedelta(weeks=1)
    elif timeframe == "month":
        start_date = end_date - timedelta(days=30)
    elif timeframe == "year":
        start_date = end_date - timedelta(days=365)
    else:  # all
        start_date = datetime(2000, 1, 1)  # 충분히 과거
    
    # 거래 데이터 쿼리
    query = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.entry_time >= start_date,
        Trade.exit_time <= end_date
    )
    
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    trades = query.all()
    
    if not trades:
        return PerformanceMetrics(
            win_rate=0.0,
            profit_factor=0.0,
            sharpe=0.0,
            max_drawdown=0.0,
            total_trades=0,
            profit_percentage=0.0
        )
    
    # 성능 지표 계산
    analyzer = PerformanceAnalyzer(trades)
    
    win_rate = analyzer.calculate_win_rate()
    profit_factor = analyzer.calculate_profit_factor()
    sharpe = analyzer.calculate_sharpe_ratio()
    max_drawdown = analyzer.calculate_max_drawdown()
    total_trades = len(trades)
    profit_percentage = sum(trade.profit_percentage or 0 for trade in trades)
    
    return PerformanceMetrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
        total_trades=total_trades,
        profit_percentage=profit_percentage
    )

# DEAD CODE: @router.get("/equity-curve")
async def get_equity_curve(
    timeframe: str = "all",
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    자본 곡선 데이터 조회
    
    - **timeframe**: 기간 (all, day, week, month, year)
    - **strategy**: 전략 필터
    - **symbol**: 심볼 필터
    """
    # 날짜 범위 설정
    end_date = datetime.utcnow()
    if timeframe == "day":
        start_date = end_date - timedelta(days=1)
    elif timeframe == "week":
        start_date = end_date - timedelta(weeks=1)
    elif timeframe == "month":
        start_date = end_date - timedelta(days=30)
    elif timeframe == "year":
        start_date = end_date - timedelta(days=365)
    else:  # all
        start_date = datetime(2000, 1, 1)  # 충분히 과거
    
    # 거래 데이터 쿼리
    query = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.entry_time >= start_date,
        Trade.exit_time <= end_date
    ).order_by(Trade.exit_time)
    
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    trades = query.all()
    
    if not trades:
        return {"equity_curve": []}
    
    # 자본 곡선 계산
    analyzer = PerformanceAnalyzer(trades)
    equity_curve = analyzer.calculate_equity_curve()
    
    return {"equity_curve": equity_curve}

# DEAD CODE: @router.get("/drawdown")
async def get_drawdown(
    timeframe: str = "all",
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    낙폭 데이터 조회
    
    - **timeframe**: 기간 (all, day, week, month, year)
    - **strategy**: 전략 필터
    - **symbol**: 심볼 필터
    """
    # 날짜 범위 설정
    end_date = datetime.utcnow()
    if timeframe == "day":
        start_date = end_date - timedelta(days=1)
    elif timeframe == "week":
        start_date = end_date - timedelta(weeks=1)
    elif timeframe == "month":
        start_date = end_date - timedelta(days=30)
    elif timeframe == "year":
        start_date = end_date - timedelta(days=365)
    else:  # all
        start_date = datetime(2000, 1, 1)  # 충분히 과거
    
    # 거래 데이터 쿼리
    query = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.entry_time >= start_date,
        Trade.exit_time <= end_date
    ).order_by(Trade.exit_time)
    
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    trades = query.all()
    
    if not trades:
        return {"drawdown": []}
    
    # 낙폭 계산
    analyzer = PerformanceAnalyzer(trades)
    drawdown = analyzer.calculate_drawdown_series()
    
    return {"drawdown": drawdown}

# DEAD CODE: @router.get("/monthly-returns")
async def get_monthly_returns(
    year: Optional[int] = None,
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    월별 수익률 조회
    
    - **year**: 연도 필터 (기본값: 현재 연도)
    - **strategy**: 전략 필터
    """
    if not year:
        year = datetime.utcnow().year
    
    # 해당 연도의 거래 데이터 쿼리
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    
    query = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.exit_time >= start_date,
        Trade.exit_time <= end_date
    )
    
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    
    trades = query.all()
    
    if not trades:
        return {"monthly_returns": [0] * 12}
    
    # 월별 수익률 계산
    analyzer = PerformanceAnalyzer(trades)
    monthly_returns = analyzer.calculate_monthly_returns(year)
    
    return {"monthly_returns": monthly_returns}

# DEAD CODE: @router.get("/win-loss-distribution")
async def get_win_loss_distribution(
    timeframe: str = "all",
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    승패 분포 조회
    
    - **timeframe**: 기간 (all, day, week, month, year)
    - **strategy**: 전략 필터
    """
    # 날짜 범위 설정
    end_date = datetime.utcnow()
    if timeframe == "day":
        start_date = end_date - timedelta(days=1)
    elif timeframe == "week":
        start_date = end_date - timedelta(weeks=1)
    elif timeframe == "month":
        start_date = end_date - timedelta(days=30)
    elif timeframe == "year":
        start_date = end_date - timedelta(days=365)
    else:  # all
        start_date = datetime(2000, 1, 1)  # 충분히 과거
    
    # 거래 데이터 쿼리
    query = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.entry_time >= start_date,
        Trade.exit_time <= end_date
    )
    
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    
    trades = query.all()
    
    if not trades:
        return {
            "win_distribution": [],
            "loss_distribution": []
        }
    
    # 승패 분포 계산
    analyzer = PerformanceAnalyzer(trades)
    win_distribution, loss_distribution = analyzer.calculate_win_loss_distribution()
    
    return {
        "win_distribution": win_distribution,
        "loss_distribution": loss_distribution
    }
