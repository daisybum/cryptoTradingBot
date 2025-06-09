"""
리스크 관리자와 텔레그램 봇 통합 모듈

이 모듈은 리스크 관리자와 텔레그램 봇을 통합하는 기능을 제공합니다.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional

from src.risk_manager.risk_manager import get_risk_manager
from src.risk_manager.event_subscriber import get_event_subscriber
from src.notifications.telegram_bot import init_telegram_bot, get_telegram_bot

# 로깅 설정
logger = logging.getLogger(__name__)

# DEAD CODE: async def setup_telegram_integration():
    """
    텔레그램 봇과 리스크 관리자 통합 설정
    
    리스크 관리자의 이벤트를 텔레그램 봇에 연결합니다.
    """
    # 리스크 관리자 가져오기
    risk_manager = get_risk_manager()
    if not risk_manager:
        logger.error("리스크 관리자가 초기화되지 않았습니다.")
        return False
    
    # 이벤트 구독자 가져오기
    event_subscriber = get_event_subscriber()
    
    # 이벤트 구독자를 Redis에 연결
    if risk_manager.redis_client:
        await event_subscriber.connect(risk_manager.redis_client)
    else:
        logger.error("리스크 관리자의 Redis 클라이언트가 초기화되지 않았습니다.")
        return False
    
    # 텔레그램 봇 초기화
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        # 텔레그램 봇이 초기화되지 않은 경우 초기화
        telegram_bot = init_telegram_bot(
            risk_manager=risk_manager
        )
        
        if not telegram_bot:
            logger.error("텔레그램 봇 초기화 실패")
            return False
    
    # 텔레그램 봇 시작
    telegram_bot.start()
    
    logger.info("텔레그램 봇과 리스크 관리자 통합이 설정되었습니다.")
    return True

# DEAD CODE: async def send_telegram_notification(title: str, message: str, level: str = "info") -> bool:
    """
    텔레그램 알림 전송
    
    Args:
        title: 알림 제목
        message: 알림 메시지
        level: 알림 레벨 ('info', 'warning', 'error', 'trade')
        
    Returns:
        bool: 전송 성공 여부
    """
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        logger.error("텔레그램 봇이 초기화되지 않았습니다.")
        return False
    
    formatted_message = f"*{title}*\n{message}"
    return telegram_bot.send_message(formatted_message, level)

# DEAD CODE: async def send_telegram_trade_alert(trade_data: Dict[str, Any]) -> bool:
    """
    텔레그램 거래 알림 전송
    
    Args:
        trade_data: 거래 데이터
        
    Returns:
        bool: 전송 성공 여부
    """
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        logger.error("텔레그램 봇이 초기화되지 않았습니다.")
        return False
    
    return telegram_bot.send_trade_alert(trade_data)

# DEAD CODE: async def send_daily_performance_report(performance_data: Dict[str, Any]) -> bool:
    """
    일일 성능 보고서 알림 전송
    
    Args:
        performance_data: 성능 데이터
        
    Returns:
        bool: 전송 성공 여부
    """
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        logger.error("텔레그램 봇이 초기화되지 않았습니다.")
        return False
    
    # 텔레그램 알림 전송 (TelegramNotifier 클래스의 send_performance_report 메서드 사용)
    return telegram_bot.notifier.send_performance_report(performance_data)
