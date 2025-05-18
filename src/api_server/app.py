#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
역사적 데이터 REST API 서버

이 모듈은 FastAPI를 사용하여 역사적 OHLCV 데이터를 제공하는 REST API를 구현합니다.
"""

import os
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data_collection.data_collector import DataCollector
from src.data_collection.historical_data_fetcher import HistoricalDataFetcher
from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

# FastAPI 앱 생성
app = FastAPI(
    title="Trading Bot Historical Data API",
    description="역사적 OHLCV 데이터를 제공하는 REST API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 모델 정의
class OHLCVData(BaseModel):
    timestamp: int = Field(..., description="캔들 시간 (밀리초 타임스탬프)")
    open: float = Field(..., description="시가")
    high: float = Field(..., description="고가")
    low: float = Field(..., description="저가")
    close: float = Field(..., description="종가")
    volume: float = Field(..., description="거래량")

class OHLCVResponse(BaseModel):
    symbol: str = Field(..., description="심볼 (예: BTC/USDT)")
    timeframe: str = Field(..., description="타임프레임 (예: 5m)")
    data: List[OHLCVData] = Field(..., description="OHLCV 데이터 목록")

# 의존성 주입을 위한 함수
async def get_data_collector():
    """
    DataCollector 인스턴스를 생성하고 반환합니다.
    """
    collector = DataCollector()
    # 필요한 초기화 수행
    try:
        yield collector
    finally:
        # 리소스 정리
        pass

async def get_historical_fetcher():
    """
    HistoricalDataFetcher 인스턴스를 생성하고 반환합니다.
    """
    fetcher = HistoricalDataFetcher()
    try:
        yield fetcher
    finally:
        await fetcher.close()

# 루트 엔드포인트
@app.get("/")
async def root():
    """
    API 서버 상태 확인
    """
    return {"status": "online", "message": "Historical Data API is running"}

# 사용 가능한 심볼 목록 조회
@app.get("/symbols", response_model=List[str])
async def get_symbols(collector: DataCollector = Depends(get_data_collector)):
    """
    사용 가능한 심볼 목록을 반환합니다.
    """
    try:
        # 지원되는 심볼 목록 반환
        return collector.symbols
    except Exception as e:
        logger.error(f"심볼 목록 조회 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 사용 가능한 타임프레임 목록 조회
@app.get("/timeframes", response_model=List[str])
async def get_timeframes(collector: DataCollector = Depends(get_data_collector)):
    """
    사용 가능한 타임프레임 목록을 반환합니다.
    """
    try:
        # 지원되는 타임프레임 목록 반환
        return collector.timeframes
    except Exception as e:
        logger.error(f"타임프레임 목록 조회 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 역사적 OHLCV 데이터 조회
@app.get("/historical/{symbol}/{timeframe}", response_model=OHLCVResponse)
async def get_historical_data(
    symbol: str,
    timeframe: str,
    start: Optional[int] = Query(None, description="시작 시간 (밀리초 타임스탬프)"),
    end: Optional[int] = Query(None, description="종료 시간 (밀리초 타임스탬프)"),
    limit: int = Query(1000, description="최대 캔들 수", ge=1, le=5000),
    fetcher: HistoricalDataFetcher = Depends(get_historical_fetcher)
):
    """
    특정 심볼과 타임프레임에 대한 역사적 OHLCV 데이터를 반환합니다.
    
    - **symbol**: 심볼 (예: BTC/USDT)
    - **timeframe**: 타임프레임 (예: 5m)
    - **start**: 시작 시간 (밀리초 타임스탬프)
    - **end**: 종료 시간 (밀리초 타임스탬프)
    - **limit**: 최대 캔들 수 (기본값: 1000, 최대: 5000)
    """
    try:
        # 심볼 형식 검증 및 변환
        symbol = symbol.upper().replace('_', '/')
        
        # 시작 시간이 없는 경우 기본값 설정 (30일 전)
        if start is None:
            start = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        
        # 종료 시간이 없는 경우 기본값 설정 (현재)
        if end is None:
            end = int(datetime.now().timestamp() * 1000)
        
        # 역사적 데이터 조회
        ohlcv_data = await fetcher.fetch_ohlcv_range(symbol, timeframe, start, end, limit)
        
        # 응답 데이터 변환
        formatted_data = []
        for candle in ohlcv_data:
            formatted_data.append(OHLCVData(
                timestamp=candle[0],
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
                volume=candle[5]
            ))
        
        return OHLCVResponse(
            symbol=symbol,
            timeframe=timeframe,
            data=formatted_data
        )
    except ValueError as e:
        logger.error(f"잘못된 요청 파라미터: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"역사적 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 최근 OHLCV 데이터 조회 (최근 N개 캔들)
@app.get("/recent/{symbol}/{timeframe}", response_model=OHLCVResponse)
async def get_recent_data(
    symbol: str,
    timeframe: str,
    limit: int = Query(100, description="캔들 수", ge=1, le=1000),
    fetcher: HistoricalDataFetcher = Depends(get_historical_fetcher)
):
    """
    특정 심볼과 타임프레임에 대한 최근 OHLCV 데이터를 반환합니다.
    
    - **symbol**: 심볼 (예: BTC/USDT)
    - **timeframe**: 타임프레임 (예: 5m)
    - **limit**: 캔들 수 (기본값: 100, 최대: 1000)
    """
    try:
        # 심볼 형식 검증 및 변환
        symbol = symbol.upper().replace('_', '/')
        
        # 최근 데이터 조회
        ohlcv_data = await fetcher.fetch_recent_ohlcv(symbol, timeframe, limit)
        
        # 응답 데이터 변환
        formatted_data = []
        for candle in ohlcv_data:
            formatted_data.append(OHLCVData(
                timestamp=candle[0],
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
                volume=candle[5]
            ))
        
        return OHLCVResponse(
            symbol=symbol,
            timeframe=timeframe,
            data=formatted_data
        )
    except ValueError as e:
        logger.error(f"잘못된 요청 파라미터: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"최근 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 서버 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """
    서버 시작 시 실행되는 이벤트 핸들러
    """
    logger.info("역사적 데이터 API 서버 시작")

# 서버 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """
    서버 종료 시 실행되는 이벤트 핸들러
    """
    logger.info("역사적 데이터 API 서버 종료")

# 직접 실행 시
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
