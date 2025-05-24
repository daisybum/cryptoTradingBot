#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
백테스트 결과 관련 API 라우터
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import json
import os

from src.api_server.models.database import get_db
from src.api_server.models.models import BacktestResult, BacktestResultResponse, BacktestResultCreate
from src.api_server.auth.auth import get_current_active_user
from src.strategy_engine.backtesting import BacktestingFramework

router = APIRouter(
    prefix="/backtest",
    tags=["backtest"],
    dependencies=[Depends(get_current_active_user)],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/results", response_model=List[BacktestResultResponse])
async def get_backtest_results(
    strategy: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    백테스트 결과 목록 조회
    
    - **strategy**: 전략 필터
    - **start_date**: 시작 날짜 필터
    - **end_date**: 종료 날짜 필터
    - **limit**: 최대 결과 수 (기본값: 100, 최대: 1000)
    - **offset**: 결과 오프셋
    """
    query = db.query(BacktestResult)
    
    # 필터 적용
    if strategy:
        query = query.filter(BacktestResult.strategy == strategy)
    if start_date:
        query = query.filter(BacktestResult.start_date >= start_date)
    if end_date:
        query = query.filter(BacktestResult.end_date <= end_date)
    
    # 정렬 및 페이징
    query = query.order_by(BacktestResult.created_at.desc()).offset(offset).limit(limit)
    
    return query.all()

@router.get("/results/{result_id}", response_model=BacktestResultResponse)
async def get_backtest_result(result_id: int, db: Session = Depends(get_db)):
    """
    특정 백테스트 결과 조회
    
    - **result_id**: 조회할 백테스트 결과 ID
    """
    result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest result with ID {result_id} not found"
        )
    
    return result

@router.post("/results", response_model=BacktestResultResponse)
async def create_backtest_result(
    result: BacktestResultCreate,
    db: Session = Depends(get_db)
):
    """
    새 백테스트 결과 생성
    """
    db_result = BacktestResult(**result.dict())
    
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    
    return db_result

@router.delete("/results/{result_id}")
async def delete_backtest_result(result_id: int, db: Session = Depends(get_db)):
    """
    백테스트 결과 삭제
    
    - **result_id**: 삭제할 백테스트 결과 ID
    """
    db_result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
    
    if not db_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest result with ID {result_id} not found"
        )
    
    db.delete(db_result)
    db.commit()
    
    return {"status": "success", "message": f"Backtest result with ID {result_id} deleted"}

@router.post("/run")
async def run_backtest(
    strategy: str,
    timeframe: str = "5m",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    pairs: List[str] = None,
    parameters: Dict[str, str] = None
):
    """
    백테스트 실행
    
    - **strategy**: 전략 이름
    - **timeframe**: 타임프레임 (기본값: 5m)
    - **start_date**: 시작 날짜 (YYYYMMDD 형식)
    - **end_date**: 종료 날짜 (YYYYMMDD 형식)
    - **pairs**: 거래 쌍 목록
    - **parameters**: 전략 파라미터 (키-값 쌍)
    """
    try:
        # 백테스팅 프레임워크 인스턴스 생성
        backtesting = BacktestingFramework()
        
        # 타임레인지 설정
        timerange = None
        if start_date and end_date:
            timerange = f"{start_date}-{end_date}"
        elif start_date:
            timerange = f"{start_date}-"
        elif end_date:
            timerange = f"-{end_date}"
        
        # 백테스트 실행
        result = backtesting.run_backtest(
            strategy=strategy,
            timeframe=timeframe,
            timerange=timerange,
            pairs=pairs,
            parameters=parameters
        )
        
        return {"status": "success", "result": result}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run backtest: {str(e)}"
        )

@router.post("/upload-result")
async def upload_backtest_result(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    백테스트 결과 파일 업로드
    
    - **file**: 백테스트 결과 JSON 파일
    """
    try:
        # 파일 내용 읽기
        contents = await file.read()
        backtest_data = json.loads(contents)
        
        # 필수 필드 확인
        required_fields = ["strategy", "start_date", "end_date", "total_trades", "win_rate", 
                          "profit_factor", "sharpe_ratio", "max_drawdown", "profit_percentage"]
        
        for field in required_fields:
            if field not in backtest_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # 날짜 형식 변환
        backtest_data["start_date"] = datetime.fromisoformat(backtest_data["start_date"])
        backtest_data["end_date"] = datetime.fromisoformat(backtest_data["end_date"])
        
        # 파라미터를 JSON 문자열로 변환
        if "parameters" in backtest_data and not isinstance(backtest_data["parameters"], str):
            backtest_data["parameters"] = json.dumps(backtest_data["parameters"])
        
        # 백테스트 결과 생성
        db_result = BacktestResult(**backtest_data)
        
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        
        return {"status": "success", "message": "Backtest result uploaded successfully", "id": db_result.id}
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload backtest result: {str(e)}"
        )

@router.get("/compare")
async def compare_backtest_results(
    result_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    백테스트 결과 비교
    
    - **result_ids**: 비교할 백테스트 결과 ID 목록
    """
    if len(result_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 backtest results are required for comparison"
        )
    
    results = []
    for result_id in result_ids:
        result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest result with ID {result_id} not found"
            )
        results.append(result)
    
    # 결과 비교 데이터 생성
    comparison = []
    for result in results:
        comparison.append({
            "id": result.id,
            "strategy": result.strategy,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "profit_percentage": result.profit_percentage,
            "created_at": result.created_at,
            "parameters": json.loads(result.parameters) if result.parameters else {}
        })
    
    return {"comparison": comparison}
