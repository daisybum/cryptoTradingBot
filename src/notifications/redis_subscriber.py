"""
Redis 알림 구독자 모듈

이 모듈은 Redis를 사용하여 알림을 구독하는 기능을 제공합니다.
Redis PubSub 메커니즘을 통해 실시간 알림을 수신하고 처리합니다.
"""
import logging
import json
import threading
import time
import redis
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

from src.notifications.redis_publisher import NotificationChannel
from src.notifications.handlers import NotificationHandler, EventType

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedisSubscriber:
    """Redis 알림 구독자 클래스"""
    
    def __init__(self, notification_handler: Optional[NotificationHandler] = None,
                host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Redis 알림 구독자 초기화
        
        Args:
            notification_handler: 알림 핸들러 인스턴스
            host: Redis 호스트
            port: Redis 포트
            db: Redis 데이터베이스
            password: Redis 비밀번호
        """
        self.notification_handler = notification_handler
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.pubsub = None
        self.subscriber_thread = None
        self.running = False
        self.connected = False
        
        # 채널별 콜백 함수
        self.callbacks = {}
        
        # Redis 클라이언트 초기화
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            self.redis_client.ping()  # 연결 테스트
            logger.info(f"Redis 서버에 연결되었습니다: {host}:{port}")
            self.connected = True
        except redis.ConnectionError as e:
            logger.error(f"Redis 서버 연결 실패: {e}")
            self.connected = False
    
    def register_callback(self, channel: NotificationChannel, callback: Callable[[Dict[str, Any]], None]):
        """
        콜백 함수 등록
        
        Args:
            channel: 알림 채널
            callback: 콜백 함수
        """
        self.callbacks[channel.value] = callback
        logger.debug(f"콜백 함수가 등록되었습니다: {channel.value}")
    
    def _message_handler(self, message):
        """
        메시지 핸들러
        
        Args:
            message: Redis 메시지
        """
        try:
            if message['type'] == 'message':
                channel = message['channel']
                data = json.loads(message['data'])
                
                # 채널별 콜백 함수 호출
                if channel in self.callbacks:
                    self.callbacks[channel](data)
                
                # 알림 핸들러로 전달
                if self.notification_handler:
                    event_type = self._map_channel_to_event_type(channel, data)
                    if event_type:
                        self.notification_handler.notify(event_type, data)
                
                logger.debug(f"메시지 수신: {channel}")
        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {e}")
    
    def _map_channel_to_event_type(self, channel: str, data: Dict[str, Any]) -> Optional[EventType]:
        """
        채널을 이벤트 유형으로 매핑
        
        Args:
            channel: 알림 채널
            data: 알림 데이터
            
        Returns:
            Optional[EventType]: 이벤트 유형
        """
        if channel == NotificationChannel.TRADES.value:
            if data.get('status') == 'open':
                return EventType.TRADE_OPEN
            elif data.get('status') == 'closed':
                return EventType.TRADE_CLOSE
        elif channel == NotificationChannel.ORDERS.value:
            if data.get('status') == 'new':
                return EventType.ORDER_PLACED
            elif data.get('status') == 'filled':
                return EventType.ORDER_FILLED
            elif data.get('status') == 'canceled':
                return EventType.ORDER_CANCELED
        elif channel == NotificationChannel.RISK.value:
            return EventType.RISK_ALERT
        elif channel == NotificationChannel.SYSTEM.value:
            return EventType.SYSTEM_STATUS
        elif channel == NotificationChannel.PERFORMANCE.value:
            return EventType.PERFORMANCE_UPDATE
        
        # 기본 이벤트 유형
        if data.get('level') == 'error':
            return EventType.ERROR
        elif data.get('level') == 'warning':
            return EventType.WARNING
        elif data.get('level') == 'info':
            return EventType.INFO
        
        return None
    
    def start(self, channels: Optional[List[NotificationChannel]] = None):
        """
        구독 시작
        
        Args:
            channels: 구독할 채널 목록 (기본값: 모든 채널)
        """
        if not self.connected:
            logger.warning("Redis 서버에 연결되어 있지 않습니다.")
            return False
        
        try:
            # PubSub 객체 생성
            self.pubsub = self.redis_client.pubsub()
            
            # 채널 구독
            if not channels:
                channels = list(NotificationChannel)
            
            for channel in channels:
                self.pubsub.subscribe(channel.value)
                logger.info(f"채널 구독: {channel.value}")
            
            # 구독 스레드 시작
            self.running = True
            self.subscriber_thread = threading.Thread(target=self._subscriber_loop)
            self.subscriber_thread.daemon = True
            self.subscriber_thread.start()
            
            logger.info("Redis 구독자가 시작되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"구독 시작 실패: {e}")
            return False
    
    def _subscriber_loop(self):
        """구독 루프"""
        while self.running:
            try:
                # 메시지 수신
                message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    self._message_handler(message)
                time.sleep(0.01)  # CPU 사용량 감소
            except redis.ConnectionError as e:
                logger.error(f"Redis 연결 오류: {e}")
                self._reconnect()
            except Exception as e:
                logger.error(f"구독 루프 중 오류 발생: {e}")
    
    def _reconnect(self):
        """Redis 재연결"""
        try:
            logger.info("Redis 서버에 재연결 시도 중...")
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            self.redis_client.ping()  # 연결 테스트
            
            # PubSub 객체 재생성
            self.pubsub = self.redis_client.pubsub()
            
            # 채널 재구독
            for channel in NotificationChannel:
                self.pubsub.subscribe(channel.value)
            
            logger.info("Redis 서버에 재연결되었습니다.")
            self.connected = True
        except Exception as e:
            logger.error(f"Redis 재연결 실패: {e}")
            self.connected = False
            time.sleep(5)  # 재시도 전 대기
    
    def stop(self):
        """구독 중지"""
        self.running = False
        if self.subscriber_thread:
            self.subscriber_thread.join(timeout=2.0)
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        logger.info("Redis 구독자가 중지되었습니다.")
