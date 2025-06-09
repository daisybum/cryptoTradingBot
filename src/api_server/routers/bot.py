#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
봇 상태 및 제어 관련 API 라우터
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api_server.models.database import get_db
from src.api_server.models.models import BotStatus, BotStatusResponse, BotStatusCreate, BotStatusUpdate
from src.api_server.auth.auth import get_current_active_user
from src.execution_engine.bot_controller import BotController

router = APIRouter(
    prefix="/bot",
    tags=["bot"],
    dependencies=[Depends(get_current_active_user)],
    responses={401: {"description": "Unauthorized"}},
)

# DEAD CODE: @router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(db: Session = Depends(get_db)):
    """
    현재 봇 상태 조회
    """
    bot_status = db.query(BotStatus).order_by(BotStatus.last_update.desc()).first()
    
    if not bot_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot status not found"
        )
    
    return bot_status

# DEAD CODE: @router.post("/status", response_model=BotStatusResponse)
async def create_bot_status(
    bot_status: BotStatusCreate,
    db: Session = Depends(get_db)
):
    """
    새 봇 상태 생성
    """
    db_bot_status = BotStatus(**bot_status.dict())
    
    db.add(db_bot_status)
    db.commit()
    db.refresh(db_bot_status)
    
    return db_bot_status

# DEAD CODE: @router.put("/status", response_model=BotStatusResponse)
async def update_bot_status(
    bot_status: BotStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    봇 상태 업데이트
    """
    db_bot_status = db.query(BotStatus).order_by(BotStatus.last_update.desc()).first()
    
    if not db_bot_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot status not found"
        )
    
    # 업데이트할 필드만 업데이트
    for key, value in bot_status.dict(exclude_unset=True).items():
        setattr(db_bot_status, key, value)
    
    db.commit()
    db.refresh(db_bot_status)
    
    return db_bot_status

@router.post("/start")
async def start_bot():
    """
    봇 시작
    """
    try:
        controller = BotController()
        controller.start()
        return {"status": "success", "message": "Bot started successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start bot: {str(e)}"
        )

@router.post("/stop")
async def stop_bot():
    """
    봇 중지
    """
    try:
        controller = BotController()
        controller.stop()
        return {"status": "success", "message": "Bot stopped successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop bot: {str(e)}"
        )

# DEAD CODE: @router.post("/pause")
async def pause_bot():
    """
    봇 일시 중지
    """
    try:
        controller = BotController()
        controller.pause()
        return {"status": "success", "message": "Bot paused successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause bot: {str(e)}"
        )

# DEAD CODE: @router.post("/resume")
async def resume_bot():
    """
    봇 재개
    """
    try:
        controller = BotController()
        controller.resume()
        return {"status": "success", "message": "Bot resumed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume bot: {str(e)}"
        )

@router.get("/exchanges")
async def get_supported_exchanges():
    """
    지원되는 거래소 목록 조회
    """
    try:
        controller = BotController()
        exchanges = controller.get_supported_exchanges()
        return {"exchanges": exchanges}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported exchanges: {str(e)}"
        )

@router.get("/strategies")
async def get_available_strategies():
    """
    사용 가능한 전략 목록 조회
    """
    try:
        controller = BotController()
        strategies = controller.get_available_strategies()
        return {"strategies": strategies}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available strategies: {str(e)}"
        )
