"""
리스크 이벤트 구독 시스템

이 모듈은 리스크 관리자의 이벤트를 구독하고 처리하는 기능을 제공합니다.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Callable, List, Optional, Awaitable

# 로깅 설정
logger = logging.getLogger(__name__)

class EventSubscriber:
    """리스크 이벤트 구독자 클래스"""
    
    def __init__(self):
        """이벤트 구독자 초기화"""
        self.subscribers = {}
        self.running = False
        self.redis_client = None
        self.pubsub = None
    
    async def connect(self, redis_client):
        """Redis 연결 설정"""
        self.redis_client = redis_client
        self.pubsub = self.redis_client.pubsub()
        
        # 리스크 이벤트 채널 구독
        await self.pubsub.subscribe('risk_events')
        await self.pubsub.subscribe('alerts')
        
        logger.info("이벤트 구독자가 Redis에 연결되었습니다.")
        
        # 이벤트 처리 태스크 시작
        if not self.running:
            self.running = True
            asyncio.create_task(self._process_events())
    
    async def _process_events(self):
        """이벤트 처리 루프"""
        if not self.pubsub:
            logger.error("Redis PubSub이 초기화되지 않았습니다.")
            return
        
        logger.info("이벤트 처리 루프 시작")
        
        try:
            while self.running:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    try:
                        channel = message['channel']
                        data = json.loads(message['data'])
                        
                        logger.debug(f"이벤트 수신: {channel} - {data}")
                        
                        # 채널에 등록된 구독자들에게 이벤트 전달
                        if channel in self.subscribers:
                            for callback in self.subscribers[channel]:
                                try:
                                    await callback(data)
                                except Exception as e:
                                    logger.error(f"구독자 콜백 실행 중 오류 발생: {e}")
                        
                        # 텔레그램 봇에 이벤트 전달
                        try:
                            # 순환 참조 문제를 피하기 위해 함수 내부에서 임포트
                            from src.notifications.telegram_bot import get_telegram_bot
                            
                            telegram_bot = get_telegram_bot()
                            if telegram_bot:
                                if channel == b'risk_events':
                                    await telegram_bot.on_risk_event(data)
                                elif channel == b'alerts':
                                    level = data.get('level', 'info')
                                    title = data.get('title', '')
                                    message = data.get('message', '')
                                    telegram_bot.send_message(f"*{title}*\n{message}", level)
                        except ImportError as e:
                            logger.warning(f"텔레그램 봇 임포트 실패: {e}")
                        except Exception as e:
                            logger.error(f"텔레그램 봇 이벤트 전달 중 오류: {e}")
                    except Exception as e:
                        logger.error(f"이벤트 처리 중 오류 발생: {e}")
                
                await asyncio.sleep(0.1)  # CPU 사용량 감소를 위한 짧은 대기
        except asyncio.CancelledError:
            logger.info("이벤트 처리 루프 종료")
        except Exception as e:
            logger.error(f"이벤트 처리 루프 오류: {e}")
    
    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        이벤트 채널 구독
        
        Args:
            channel: 구독할 채널 이름
            callback: 이벤트 발생 시 호출될 콜백 함수
        """
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        
        self.subscribers[channel].append(callback)
        logger.info(f"채널 '{channel}'에 구독자 추가됨")
    
    def unsubscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        이벤트 채널 구독 취소
        
        Args:
            channel: 구독 취소할 채널 이름
            callback: 제거할 콜백 함수
        """
        if channel in self.subscribers and callback in self.subscribers[channel]:
            self.subscribers[channel].remove(callback)
            logger.info(f"채널 '{channel}'에서 구독자 제거됨")
    
    async def close(self):
        """리소스 정리"""
        self.running = False
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            self.pubsub = None
        
        logger.info("이벤트 구독자가 종료되었습니다.")

# 싱글톤 인스턴스
_event_subscriber = None

def get_event_subscriber() -> EventSubscriber:
    """
    이벤트 구독자 인스턴스 가져오기
    
    Returns:
        EventSubscriber: 이벤트 구독자 인스턴스
    """
    global _event_subscriber
    
    if _event_subscriber is None:
        _event_subscriber = EventSubscriber()
    
    return _event_subscriber
