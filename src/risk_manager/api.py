"""
리스크 관리 API 서버

이 모듈은 FastAPI를 사용하여 리스크 관리 기능을 외부에 노출시키는 API 서버를 제공합니다.
"""

import logging
import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from src.risk_manager.risk_manager import get_risk_manager, init_risk_manager

logger = logging.getLogger(__name__)

# API 모델 정의
class BalanceUpdate(BaseModel):
    """잔액 업데이트 모델"""
    balance: float = Field(..., description="현재 계정 잔액")

class TradeCheck(BaseModel):
    """거래 검사 모델"""
    pair: str = Field(..., description="거래 페어 (예: BTC/USDT)")
    side: str = Field(..., description="매수/매도 (buy/sell)")
    amount: float = Field(..., description="거래량")
    price: Optional[float] = Field(None, description="가격 (선택 사항)")

class PositionSizeRequest(BaseModel):
    """포지션 크기 계산 요청 모델"""
    account_balance: float = Field(..., description="계정 잔액")
    pair: str = Field(..., description="거래 페어 (예: BTC/USDT)")
    entry_price: float = Field(..., description="진입 가격")

class CircuitBreakerCheck(BaseModel):
    """서킷 브레이커 검사 모델"""
    price_change: float = Field(..., description="가격 변동 비율 (소수점)")

class KillSwitchRequest(BaseModel):
    """킬 스위치 요청 모델"""
    reason: str = Field(..., description="활성화/비활성화 이유")

class RiskEvent(BaseModel):
    """리스크 이벤트 모델"""
    type: str = Field(..., description="이벤트 유형")
    data: Dict[str, Any] = Field(default_factory=dict, description="이벤트 데이터")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="이벤트 타임스탬프")

class RiskStatus(BaseModel):
    """리스크 상태 모델"""
    kill_switch_active: bool = Field(..., description="킬 스위치 활성화 여부")
    circuit_breaker_active: bool = Field(..., description="서킷 브레이커 활성화 여부")
    peak_balance: float = Field(..., description="최고 잔액")
    current_balance: float = Field(..., description="현재 잔액")
    current_drawdown: float = Field(..., description="현재 드로다운")
    daily_trade_count: int = Field(..., description="오늘 거래 수")
    max_drawdown: float = Field(..., description="최대 드로다운 설정")
    per_trade_stop_loss: float = Field(..., description="거래별 손절 설정")
    risk_per_trade: float = Field(..., description="거래당 리스크 설정")
    daily_trade_limit: int = Field(..., description="일일 거래 제한 설정")
    circuit_breaker: float = Field(..., description="서킷 브레이커 설정")

# FastAPI 앱 생성
app = FastAPI(
    title="리스크 관리 API",
    description="거래 시스템의 리스크를 관리하는 API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 의존성 주입: 리스크 관리자 가져오기
async def get_risk_manager_dependency():
    """리스크 관리자 의존성"""
    risk_manager = get_risk_manager()
    if risk_manager is None:
        raise HTTPException(status_code=500, detail="리스크 관리자가 초기화되지 않았습니다")
    return risk_manager

# 대시보드 UI 템플릿
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# API 라우트 정의
# DEAD CODE: @app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """대시보드 UI를 제공하는 루트 엔드포인트"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/status", response_model=RiskStatus, tags=["상태"])
async def get_status(risk_manager = Depends(get_risk_manager_dependency)):
    """리스크 관리 상태 조회"""
    today_date = datetime.now().date().isoformat()
    daily_trade_count = risk_manager.daily_trades.get(today_date, 0)
    
    # 현재 드로다운 계산
    current_drawdown = 0.0
    if risk_manager.peak_balance > 0:
        current_drawdown = 1 - (risk_manager.current_balance / risk_manager.peak_balance)
    
    return {
        "kill_switch_active": risk_manager.kill_switch_active,
        "circuit_breaker_active": risk_manager.circuit_breaker_active,
        "peak_balance": risk_manager.peak_balance,
        "current_balance": risk_manager.current_balance,
        "current_drawdown": current_drawdown,
        "daily_trade_count": daily_trade_count,
        "max_drawdown": risk_manager.max_drawdown,
        "per_trade_stop_loss": risk_manager.per_trade_stop_loss,
        "risk_per_trade": risk_manager.risk_per_trade,
        "daily_trade_limit": risk_manager.daily_trade_limit,
        "circuit_breaker": risk_manager.circuit_breaker
    }

@app.post("/balance", tags=["잔액"])
async def update_balance(balance_update: BalanceUpdate, risk_manager = Depends(get_risk_manager_dependency)):
    """잔액 업데이트"""
    result = await risk_manager.update_balance(balance_update.balance)
    
    # 드로다운 계산
    current_drawdown = 0.0
    if risk_manager.peak_balance > 0:
        current_drawdown = 1 - (risk_manager.current_balance / risk_manager.peak_balance)
    
    return {
        "success": result,
        "current_balance": risk_manager.current_balance,
        "peak_balance": risk_manager.peak_balance,
        "current_drawdown": current_drawdown,
        "max_drawdown": risk_manager.max_drawdown,
        "drawdown_percentage": current_drawdown * 100
    }

# DEAD CODE: @app.post("/check-trade", tags=["거래"])
async def check_trade(trade_check: TradeCheck, risk_manager = Depends(get_risk_manager_dependency)):
    """거래 허용 여부 검사"""
    result = await risk_manager.check_trade_allowed(
        pair=trade_check.pair,
        side=trade_check.side,
        amount=trade_check.amount,
        price=trade_check.price
    )
    
    response = {
        "allowed": result,
        "pair": trade_check.pair,
        "side": trade_check.side,
        "amount": trade_check.amount,
        "kill_switch_active": risk_manager.kill_switch_active,
        "circuit_breaker_active": risk_manager.circuit_breaker_active
    }
    
    # 거래가 허용되지 않은 경우 이유 추가
    if not result:
        if risk_manager.kill_switch_active:
            response["reason"] = "킬 스위치 활성화"
        elif risk_manager.circuit_breaker_active:
            response["reason"] = "서킷 브레이커 활성화"
        else:
            # 일일 거래 제한 검사
            today_date = datetime.now().date().isoformat()
            daily_trade_count = risk_manager.daily_trades.get(today_date, 0)
            if daily_trade_count >= risk_manager.daily_trade_limit:
                response["reason"] = "일일 거래 제한 초과"
            else:
                response["reason"] = "기타 리스크 제한"
    
    return response

@app.post("/position-size", tags=["포지션"])
async def calculate_position_size(
    pair: str = Query(..., description="거래 페어 (예: BTC/USDT)"),
    price: float = Query(..., description="현재 가격"),
    risk_level: str = Query("normal", description="리스크 레벨 (low, normal, high)"),
    risk_manager = Depends(get_risk_manager_dependency)
):
    """적절한 포지션 크기 계산"""
    position_size = await risk_manager.calculate_position_size(pair, price, risk_level)
    
    return {
        "pair": pair,
        "price": price,
        "risk_level": risk_level,
        "position_size": position_size,
        "position_value": position_size * price,
        "current_balance": risk_manager.current_balance
    }

# DEAD CODE: @app.get("/positions", tags=["포지션"])
async def get_positions(risk_manager = Depends(get_risk_manager_dependency)):
    """현재 포지션 정보 조회"""
    positions = {}
    
    # Redis에서 포지션 정보 가져오기
    if risk_manager.redis_client:
        try:
            # position: 키를 가진 모든 키 가져오기
            position_keys = await risk_manager.redis_client.keys("position:*")
            
            for key in position_keys:
                pair = key.split(":")[1]  # position:BTC/USDT에서 BTC/USDT 추출
                position_data = await risk_manager.redis_client.get(key)
                
                if position_data:
                    position = json.loads(position_data)
                    if position["amount"] > 0:  # 수량이 있는 포지션만 추가
                        positions[pair] = position
        except Exception as e:
            logger.error(f"포지션 정보 조회 실패: {e}")
    
    return {
        "positions": positions,
        "count": len(positions)
    }

@app.get("/position/{pair}", tags=["포지션"])
async def get_position(pair: str = Path(..., description="거래 페어 (예: BTC/USDT)"), risk_manager = Depends(get_risk_manager_dependency)):
    """특정 페어의 포지션 정보 조회"""
    position = await risk_manager.get_position(pair)
    
    if position is None:
        return {
            "pair": pair,
            "exists": False,
            "amount": 0,
            "avg_price": 0
        }
    
    return {
        "pair": pair,
        "exists": True,
        "amount": position["amount"],
        "avg_price": position["avg_price"],
        "value": position["amount"] * position["avg_price"]
    }

@app.post("/kill-switch/activate", tags=["킬 스위치"])
async def activate_kill_switch(request: KillSwitchRequest, risk_manager = Depends(get_risk_manager_dependency)):
    """킬 스위치 활성화"""
    await risk_manager.activate_kill_switch(request.reason)
    
    return {
        "success": True,
        "kill_switch_active": risk_manager.kill_switch_active,
        "reason": request.reason,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/kill-switch/deactivate", tags=["킬 스위치"])
async def deactivate_kill_switch(request: KillSwitchRequest, risk_manager = Depends(get_risk_manager_dependency)):
    """킬 스위치 비활성화"""
    risk_manager.kill_switch_active = False
    
    # 리스크 이벤트 발행
    await risk_manager.publish_risk_event('KILL_SWITCH_DEACTIVATED', {
        'reason': request.reason,
        'timestamp': datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "kill_switch_active": risk_manager.kill_switch_active,
        "reason": request.reason,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/circuit-breaker/check", tags=["서킷 브레이커"])
async def check_circuit_breaker(request: CircuitBreakerCheck, risk_manager = Depends(get_risk_manager_dependency)):
    """서킷 브레이커 검사"""
    result = await risk_manager.check_circuit_breaker(request.price_change)
    
    return {
        "triggered": not result,
        "price_change": request.price_change,
        "threshold": risk_manager.circuit_breaker,
        "circuit_breaker_active": risk_manager.circuit_breaker_active
    }

# DEAD CODE: @app.post("/circuit-breaker/reset", tags=["서킷 브레이커"])
async def reset_circuit_breaker(risk_manager = Depends(get_risk_manager_dependency)):
    """서킷 브레이커 재설정"""
    risk_manager.circuit_breaker_active = False
    
    # 리스크 이벤트 발행
    await risk_manager.publish_risk_event('CIRCUIT_BREAKER_RESET', {
        'timestamp': datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "circuit_breaker_active": risk_manager.circuit_breaker_active,
        "timestamp": datetime.now().isoformat()
    }
    
    # 드로다운 계산
    current_drawdown = 0.0
    if risk_manager.peak_balance > 0:
        current_drawdown = 1 - (risk_manager.current_balance / risk_manager.peak_balance)
    
    return {
        "kill_switch_active": risk_manager.kill_switch_active,
        "circuit_breaker_active": risk_manager.circuit_breaker_active,
        "peak_balance": risk_manager.peak_balance,
        "current_balance": risk_manager.current_balance,
        "current_drawdown": current_drawdown,
        "daily_trade_count": daily_trade_count,
        "max_drawdown": risk_manager.max_drawdown,
        "per_trade_stop_loss": risk_manager.per_trade_stop_loss,
        "risk_per_trade": risk_manager.risk_per_trade,
        "daily_trade_limit": risk_manager.daily_trade_limit,
        "circuit_breaker": risk_manager.circuit_breaker
    }

@app.post("/balance", tags=["잔액"])
async def update_balance(
    balance_update: BalanceUpdate,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """잔액 업데이트 및 드로다운 검사"""
    result = await risk_manager.update_balance(balance_update.balance)
    return {"success": result, "message": "잔액 업데이트됨"}

# DEAD CODE: @app.post("/trade/check", tags=["거래"])
async def check_trade(
    trade_check: TradeCheck,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """거래 허용 여부 검사"""
    result = await risk_manager.check_trade_allowed(
        trade_check.pair,
        trade_check.side,
        trade_check.amount,
        trade_check.price
    )
    return {"allowed": result}

@app.post("/trade/position-size", tags=["거래"])
async def calculate_position_size(
    request: PositionSizeRequest,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """포지션 크기 계산"""
    position_size = await risk_manager.calculate_position_size(
        request.account_balance,
        request.pair,
        request.entry_price
    )
    return {"position_size": position_size}

# DEAD CODE: @app.post("/trade/increment", tags=["거래"])
async def increment_trade_count(
    trade_check: TradeCheck,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """거래 수 증가"""
    await risk_manager.increment_daily_trade_count(trade_check.pair)
    
    today_date = datetime.now().date().isoformat()
    daily_trade_count = risk_manager.daily_trades.get(today_date, 0)
    
    return {"success": True, "daily_trade_count": daily_trade_count}

@app.post("/circuit-breaker/check", tags=["서킷 브레이커"])
async def check_circuit_breaker(
    request: CircuitBreakerCheck,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """서킷 브레이커 검사"""
    result = await risk_manager.check_circuit_breaker(request.price_change)
    return {"allowed": result, "circuit_breaker_active": risk_manager.circuit_breaker_active}

@app.post("/kill-switch/activate", tags=["킬 스위치"])
async def activate_kill_switch(
    request: KillSwitchRequest,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """킬 스위치 활성화"""
    await risk_manager.activate_kill_switch(request.reason)
    return {"success": True, "kill_switch_active": risk_manager.kill_switch_active}

@app.post("/kill-switch/deactivate", tags=["킬 스위치"])
async def deactivate_kill_switch(
    request: KillSwitchRequest,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """킬 스위치 비활성화"""
    await risk_manager.deactivate_kill_switch(request.reason)
    return {"success": True, "kill_switch_active": risk_manager.kill_switch_active}

# DEAD CODE: @app.post("/events/publish", tags=["이벤트"])
async def publish_event(
    event: RiskEvent,
    risk_manager = Depends(get_risk_manager_dependency)
):
    """리스크 이벤트 발행"""
    await risk_manager.publish_risk_event(event.type, event.data)
    return {"success": True, "event": event}

# 서버 시작 이벤트
# DEAD CODE: @app.on_event("startup")
async def startup_event():
    """서버 시작 이벤트"""
    try:
        # 기본 설정으로 리스크 관리자 초기화
        config = {
            'risk_management': {
                'max_drawdown': 0.15,
                'stop_loss': 0.035,
                'risk_per_trade': 0.02,
                'daily_trade_limit': 60,
                'circuit_breaker': 0.05
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            }
        }
        
        await init_risk_manager(config)
        logger.info("리스크 관리자 초기화됨")
    except Exception as e:
        logger.error(f"리스크 관리자 초기화 실패: {e}")

# 서버 종료 이벤트
# DEAD CODE: @app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 이벤트"""
    risk_manager = get_risk_manager()
    if risk_manager:
        await risk_manager.close()
        logger.info("리스크 관리자 종료됨")

# 메인 함수 (직접 실행 시)
def main():
    """메인 함수"""
    import uvicorn
    uvicorn.run("src.risk_manager.api:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
