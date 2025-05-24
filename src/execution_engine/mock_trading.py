#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 서버를 위한 모의 거래 모듈

이 모듈은 API 서버에서 사용할 모의 거래 기능을 제공합니다.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

class MockTradingBot:
    """
    모의 트레이딩 봇 클래스
    """
    
    def __init__(self):
        """
        MockTradingBot 초기화
        """
        self.status = "stopped"
        self.start_time = None
        self.config = {}
    
    def start(self, config: Optional[Dict[str, Any]] = None):
        """
        봇 시작
        
        Args:
            config (Optional[Dict[str, Any]]): 설정
        """
        if self.status == "running":
            logger.warning("Bot is already running")
            return
        
        if config:
            self.config = config
        
        logger.info("Starting mock trading bot")
        self.status = "running"
        self.start_time = datetime.utcnow()
    
    def stop(self):
        """
        봇 중지
        """
        if self.status == "stopped":
            logger.warning("Bot is already stopped")
            return
        
        logger.info("Stopping mock trading bot")
        self.status = "stopped"
        self.start_time = None
    
    def pause(self):
        """
        봇 일시 중지
        """
        if self.status != "running":
            logger.warning(f"Cannot pause bot: current status is {self.status}")
            return
        
        logger.info("Pausing mock trading bot")
        self.status = "paused"
    
    def resume(self):
        """
        봇 재개
        """
        if self.status != "paused":
            logger.warning(f"Cannot resume bot: current status is {self.status}")
            return
        
        logger.info("Resuming mock trading bot")
        self.status = "running"
    
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
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "mode": "mock",
            "active_trades": 0,
            "balance": 1000.0,
            "equity": 1000.0
        }

def start_mock_trading(config: Optional[Dict[str, Any]] = None) -> MockTradingBot:
    """
    모의 거래 시작
    
    Args:
        config (Optional[Dict[str, Any]]): 설정
    
    Returns:
        MockTradingBot: 모의 트레이딩 봇 인스턴스
    """
    bot = MockTradingBot()
    bot.start(config)
    
    return bot
