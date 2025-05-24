#!/usr/bin/env python
"""
텔레그램 봇 테스트 스크립트

이 스크립트는 텔레그램 봇의 기능을 테스트합니다.
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
from src.notifications.manager import NotificationManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_telegram_bot():
    """텔레그램 봇 테스트"""
    # 환경 변수 직접 설정
    telegram_token = "7679275139:AAGcA40OJHJd8A1OF-BSs5gTxIj4zBpuh_c"
    telegram_chat_id = "7892169109"
    
    # 환경 변수에 설정
    os.environ['TELEGRAM_BOT_TOKEN'] = telegram_token
    os.environ['TELEGRAM_CHAT_ID'] = telegram_chat_id
    
    logger.info(f"텔레그램 토큰: {telegram_token[:5]}...{telegram_token[-5:] if len(telegram_token) > 10 else ''}")
    logger.info(f"텔레그램 채팅 ID: {telegram_chat_id}")
    
    # 알림 관리자 초기화
    notification_manager = NotificationManager(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id
    )
    
    # 알림 시스템 시작
    notification_manager.start()
    
    # 정보 메시지 전송
    logger.info("정보 메시지 전송 테스트")
    notification_manager.send_info("🚀 테스트 메시지: 봇이 정상적으로 작동합니다!", immediate=True)
    
    # 경고 메시지 전송
    logger.info("경고 메시지 전송 테스트")
    notification_manager.send_warning("⚠️ 테스트 경고: 이것은 테스트 경고입니다.", immediate=True)
    
    # 오류 메시지 전송
    logger.info("오류 메시지 전송 테스트")
    notification_manager.send_error("🔴 테스트 오류: 이것은 테스트 오류입니다.", immediate=True)
    
    # 거래 알림 전송
    logger.info("거래 알림 전송 테스트")
    trade_data = {
        "trade_id": "TEST123",
        "pair": "BTC/USDT",
        "side": "BUY",
        "entry_price": "50000",
        "quantity": "0.1",
        "stop_loss": "49000",
        "take_profit": "52000",
        "strategy": "테스트 전략"
    }
    notification_manager.send_trade_open_notification(trade_data, immediate=True)
    
    # 시스템 상태 알림 전송
    logger.info("시스템 상태 알림 전송 테스트")
    status_data = {
        "component": "테스트 컴포넌트",
        "status": "info",
        "description": "이것은 테스트 시스템 상태 알림입니다."
    }
    notification_manager.send_system_status(status_data, immediate=True)
    
    # 잠시 대기
    await asyncio.sleep(5)
    
    # 알림 시스템 중지
    notification_manager.stop()
    
    logger.info("텔레그램 봇 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())
