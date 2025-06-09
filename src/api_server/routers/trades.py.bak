#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
거래 데이터 및 기록 관련 API 라우터
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.api_server.models.database import get_db
from src.api_server.models.models import Trade, TradeResponse, TradeCreate, TradeUpdate
from src.api_server.auth.auth import get_current_active_user

router = APIRouter(
    prefix="/trades",
    tags=["trades"],
    dependencies=[Depends(get_current_active_user)],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/", response_model=List[TradeResponse])
async def get_trades(
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    거래 기록 조회
    
    - **symbol**: 심볼 필터 (예: BTC/USDT)
    - **strategy**: 전략 필터
    - **status**: 상태 필터 (open, closed, cancelled)
    - **start_date**: 시작 날짜 필터
    - **end_date**: 종료 날짜 필터
    - **limit**: 최대 결과 수 (기본값: 100, 최대: 1000)
    - **offset**: 결과 오프셋
    """
    query = db.query(Trade)
    
    # 필터 적용
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if strategy:
        query = query.filter(Trade.strategy == strategy)
    if status:
        query = query.filter(Trade.status == status)
    if start_date:
        query = query.filter(Trade.entry_time >= start_date)
    if end_date:
        query = query.filter(Trade.entry_time <= end_date)
    
    # 정렬 및 페이징
    query = query.order_by(Trade.entry_time.desc()).offset(offset).limit(limit)
    
    return query.all()

@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """
    특정 거래 조회
    
    - **trade_id**: 조회할 거래 ID
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found"
        )
    
    return trade

@router.post("/", response_model=TradeResponse)
async def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    """
    새 거래 생성
    """
    db_trade = Trade(**trade.dict())
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    return db_trade

@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_update: TradeUpdate,
    db: Session = Depends(get_db)
):
    """
    거래 업데이트
    
    - **trade_id**: 업데이트할 거래 ID
    """
    db_trade = db.query(Trade).filter(Trade.id == trade_id).first()
    
    if not db_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found"
        )
    
    # 업데이트할 필드만 업데이트
    for key, value in trade_update.dict(exclude_unset=True).items():
        setattr(db_trade, key, value)
    
    # 이익 계산 (exit_price가 있는 경우)
    if trade_update.exit_price and db_trade.entry_price:
        if db_trade.trade_type == "buy":
            db_trade.profit = (trade_update.exit_price - db_trade.entry_price) * db_trade.amount
            db_trade.profit_percentage = (trade_update.exit_price / db_trade.entry_price - 1) * 100
        else:  # sell
            db_trade.profit = (db_trade.entry_price - trade_update.exit_price) * db_trade.amount
            db_trade.profit_percentage = (db_trade.entry_price / trade_update.exit_price - 1) * 100
    
    db.commit()
    db.refresh(db_trade)
    
    return db_trade

@router.delete("/{trade_id}")
async def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """
    거래 삭제
    
    - **trade_id**: 삭제할 거래 ID
    """
    db_trade = db.query(Trade).filter(Trade.id == trade_id).first()
    
    if not db_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found"
        )
    
    db.delete(db_trade)
    db.commit()
    
    return {"status": "success", "message": f"Trade with ID {trade_id} deleted"}

@router.get("/summary/daily", response_model=List[dict])
async def get_daily_trade_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    일별 거래 요약 조회
    
    - **start_date**: 시작 날짜 필터
    - **end_date**: 종료 날짜 필터
    """
    # 기본 날짜 범위 설정 (최근 30일)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # 일별 거래 요약 쿼리 (SQL 함수 사용)
    result = db.execute("""
        SELECT 
            DATE(entry_time) as date,
            COUNT(*) as total_trades,
            SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losing_trades,
            SUM(profit) as total_profit,
            AVG(profit_percentage) as avg_profit_percentage
        FROM trades
        WHERE entry_time BETWEEN :start_date AND :end_date
        AND status = 'closed'
        GROUP BY DATE(entry_time)
        ORDER BY date
    """, {"start_date": start_date, "end_date": end_date})
    
    summary = []
    for row in result:
        summary.append({
            "date": row.date,
            "total_trades": row.total_trades,
            "winning_trades": row.winning_trades,
            "losing_trades": row.losing_trades,
            "win_rate": row.winning_trades / row.total_trades if row.total_trades > 0 else 0,
            "total_profit": row.total_profit,
            "avg_profit_percentage": row.avg_profit_percentage
        })
    
    return summary

@router.get("/summary/symbols", response_model=List[dict])
async def get_symbol_trade_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    심볼별 거래 요약 조회
    
    - **start_date**: 시작 날짜 필터
    - **end_date**: 종료 날짜 필터
    """
    # 기본 날짜 범위 설정 (최근 30일)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # 심볼별 거래 요약 쿼리
    result = db.execute("""
        SELECT 
            symbol,
            COUNT(*) as total_trades,
            SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losing_trades,
            SUM(profit) as total_profit,
            AVG(profit_percentage) as avg_profit_percentage
        FROM trades
        WHERE entry_time BETWEEN :start_date AND :end_date
        AND status = 'closed'
        GROUP BY symbol
        ORDER BY total_profit DESC
    """, {"start_date": start_date, "end_date": end_date})
    
    summary = []
    for row in result:
        summary.append({
            "symbol": row.symbol,
            "total_trades": row.total_trades,
            "winning_trades": row.winning_trades,
            "losing_trades": row.losing_trades,
            "win_rate": row.winning_trades / row.total_trades if row.total_trades > 0 else 0,
            "total_profit": row.total_profit,
            "avg_profit_percentage": row.avg_profit_percentage
        })
    
    return summary
