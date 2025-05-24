#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
봇 제어 클래스

이 모듈은 트레이딩 봇의 시작, 중지, 일시 중지, 재개 등의 제어 기능을 제공합니다.
"""

import os
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.execution_engine.mock_trading import MockTradingBot, start_mock_trading
from src.strategy_engine.strategy_loader import StrategyLoader
from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

class BotController:
    """
    트레이딩 봇 제어 클래스
    """
    
    def __init__(self):
        """
        BotController 초기화
        """
        self.trading_bot = None
        self.execution_engine = None
        self.status = "stopped"
        self.start_time = None
    
    def start(self) -> Dict[str, Any]:
        """
        봇 시작
        
        Returns:
            Dict[str, Any]: 시작 결과
        """
        if self.status == "running":
            logger.warning("Bot is already running")
            return {"status": "warning", "message": "Bot is already running"}
        
        try:
            # 모의 트레이딩 봇 인스턴스 생성
            config = {}
            self.trading_bot = start_mock_trading(config)
            
            # 상태 업데이트
            self.status = "running"
            self.start_time = datetime.utcnow()
            
            logger.info("Bot started successfully")
            return {"status": "success", "message": "Bot started successfully"}
        
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}")
            return {"status": "error", "message": f"Failed to start bot: {str(e)}"}
    
    def stop(self) -> Dict[str, Any]:
        """
        봇 중지
        
        Returns:
            Dict[str, Any]: 중지 결과
        """
        if self.status == "stopped":
            logger.warning("Bot is already stopped")
            return {"status": "warning", "message": "Bot is already stopped"}
        
        try:
            if self.trading_bot:
                self.trading_bot.stop()
            
            # 상태 업데이트
            self.status = "stopped"
            self.start_time = None
            
            logger.info("Bot stopped successfully")
            return {"status": "success", "message": "Bot stopped successfully"}
        
        except Exception as e:
            logger.error(f"Failed to stop bot: {str(e)}")
            return {"status": "error", "message": f"Failed to stop bot: {str(e)}"}
    
    def pause(self) -> Dict[str, Any]:
        """
        봇 일시 중지
        
        Returns:
            Dict[str, Any]: 일시 중지 결과
        """
        if self.status != "running":
            logger.warning(f"Cannot pause bot: current status is {self.status}")
            return {"status": "warning", "message": f"Cannot pause bot: current status is {self.status}"}
        
        try:
            if self.trading_bot:
                self.trading_bot.pause()
            
            # 상태 업데이트
            self.status = "paused"
            
            logger.info("Bot paused successfully")
            return {"status": "success", "message": "Bot paused successfully"}
        
        except Exception as e:
            logger.error(f"Failed to pause bot: {str(e)}")
            return {"status": "error", "message": f"Failed to pause bot: {str(e)}"}
    
    def resume(self) -> Dict[str, Any]:
        """
        봇 재개
        
        Returns:
            Dict[str, Any]: 재개 결과
        """
        if self.status != "paused":
            logger.warning(f"Cannot resume bot: current status is {self.status}")
            return {"status": "warning", "message": f"Cannot resume bot: current status is {self.status}"}
        
        try:
            if self.trading_bot:
                self.trading_bot.resume()
            
            # 상태 업데이트
            self.status = "running"
            
            logger.info("Bot resumed successfully")
            return {"status": "success", "message": "Bot resumed successfully"}
        
        except Exception as e:
            logger.error(f"Failed to resume bot: {str(e)}")
            return {"status": "error", "message": f"Failed to resume bot: {str(e)}"}
    
    def get_status(self) -> Dict[str, Any]:
        """
        봇 상태 조회
        
        Returns:
            Dict[str, Any]: 봇 상태 정보
        """
        uptime = None
        if self.start_time and self.status == "running":
            uptime = int((datetime.utcnow() - self.start_time).total_seconds())
        
        return {
            "status": self.status,
            "uptime": uptime,
            "start_time": self.start_time.isoformat() if self.start_time else None
        }
    
    def get_supported_exchanges(self) -> List[str]:
        """
        지원되는 거래소 목록 조회
        
        Returns:
            List[str]: 지원되는 거래소 목록
        """
        # 예시 거래소 목록 (실제로는 동적으로 로드)
        return ["binance", "bybit", "kucoin", "okx", "huobi"]
    
    def get_available_strategies(self) -> List[str]:
        """
        사용 가능한 전략 목록 조회
        
        Returns:
            List[str]: 사용 가능한 전략 목록
        """
        try:
            # 전략 로더를 통해 사용 가능한 전략 목록 로드
            strategy_loader = StrategyLoader()
            strategies = strategy_loader.list_available_strategies()
            
            return strategies
        
        except Exception as e:
            logger.error(f"Failed to get available strategies: {str(e)}")
            return []
