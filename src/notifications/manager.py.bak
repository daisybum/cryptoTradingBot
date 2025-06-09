"""
알림 관리자 모듈

이 모듈은 텔레그램 알림 시스템의 통합 관리자를 제공합니다.
텔레그램 알림, Redis 발행/구독, 알림 핸들러를 통합하여 완전한 알림 시스템을 구현합니다.
"""
import logging
import os
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from src.notifications.telegram import TelegramNotifier, NotificationLevel
from src.notifications.handlers import NotificationHandler, EventType
from src.notifications.templates import NotificationTemplates
from src.notifications.redis_publisher import RedisPublisher, NotificationChannel
from src.notifications.redis_subscriber import RedisSubscriber

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotificationManager:
    """알림 관리자 클래스"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None,
                redis_host: str = 'localhost', redis_port: int = 6379, redis_db: int = 0,
                redis_password: Optional[str] = None):
        """
        알림 관리자 초기화
        
        Args:
            telegram_token: 텔레그램 봇 토큰
            telegram_chat_id: 텔레그램 채팅 ID
            redis_host: Redis 호스트
            redis_port: Redis 포트
            redis_db: Redis 데이터베이스
            redis_password: Redis 비밀번호
        """
        if self._initialized:
            return
        
        # 환경 변수에서 설정 로드
        if not telegram_token:
            telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not telegram_chat_id:
            telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        if not redis_host:
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
        if not redis_port:
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
        if not redis_password:
            redis_password = os.environ.get('REDIS_PASSWORD')
        
        # 텔레그램 알림 관리자 초기화
        self.telegram = None
        if telegram_token and telegram_chat_id:
            self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
            logger.info("텔레그램 알림 관리자가 초기화되었습니다.")
        else:
            logger.warning("텔레그램 토큰 또는 채팅 ID가 설정되지 않았습니다. 텔레그램 알림이 비활성화됩니다.")
        
        # 알림 핸들러 초기화
        self.notification_handler = NotificationHandler(self.telegram)
        
        # Redis 발행자 초기화
        self.redis_publisher = RedisPublisher(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password
        )
        
        # Redis 구독자 초기화
        self.redis_subscriber = RedisSubscriber(
            notification_handler=self.notification_handler,
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password
        )
        
        # 상태 변수
        self.is_running = False
        self.notification_count = 0
        self.start_time = datetime.now()
        
        self._initialized = True
        logger.info("알림 관리자가 초기화되었습니다.")
    
    def start(self):
        """알림 시스템 시작"""
        if self.is_running:
            logger.warning("알림 시스템이 이미 실행 중입니다.")
            return False
        
        try:
            # Redis 구독자 시작
            if self.redis_subscriber.connected:
                self.redis_subscriber.start()
            
            # 알림 시스템 시작 메시지
            if self.telegram and self.telegram.is_active():
                self.telegram.send_info("🔔 알림 시스템이 시작되었습니다.")
            
            self.is_running = True
            logger.info("알림 시스템이 시작되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"알림 시스템 시작 실패: {e}")
            return False
    
    def stop(self):
        """알림 시스템 중지"""
        if not self.is_running:
            logger.warning("알림 시스템이 실행 중이 아닙니다.")
            return False
        
        try:
            # Redis 구독자 중지
            if self.redis_subscriber:
                self.redis_subscriber.stop()
            
            # 알림 시스템 중지 메시지
            if self.telegram and self.telegram.is_active():
                self.telegram.send_info("🔕 알림 시스템이 중지되었습니다.")
            
            self.is_running = False
            logger.info("알림 시스템이 중지되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"알림 시스템 중지 실패: {e}")
            return False
    
    def send_notification(self, event_type: EventType, data: Dict[str, Any], immediate: bool = False):
        """
        알림 전송
        
        Args:
            event_type: 이벤트 유형
            data: 이벤트 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 알림 핸들러로 전달
            self.notification_handler.notify(event_type, data, immediate)
            
            # Redis로 발행
            channel = self._map_event_type_to_channel(event_type)
            if channel and self.redis_publisher.connected:
                self.redis_publisher.publish(channel, data)
            
            # 알림 카운트 증가
            self.notification_count += 1
            
            return True
            
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
            return False
    
    def _map_event_type_to_channel(self, event_type: EventType) -> Optional[NotificationChannel]:
        """
        이벤트 유형을 채널로 매핑
        
        Args:
            event_type: 이벤트 유형
            
        Returns:
            Optional[NotificationChannel]: 알림 채널
        """
        mapping = {
            EventType.TRADE_OPEN: NotificationChannel.TRADES,
            EventType.TRADE_CLOSE: NotificationChannel.TRADES,
            EventType.ORDER_PLACED: NotificationChannel.ORDERS,
            EventType.ORDER_FILLED: NotificationChannel.ORDERS,
            EventType.ORDER_CANCELED: NotificationChannel.ORDERS,
            EventType.RISK_ALERT: NotificationChannel.RISK,
            EventType.SYSTEM_STATUS: NotificationChannel.SYSTEM,
            EventType.PERFORMANCE_UPDATE: NotificationChannel.PERFORMANCE,
            EventType.ERROR: NotificationChannel.SYSTEM,
            EventType.WARNING: NotificationChannel.SYSTEM,
            EventType.INFO: NotificationChannel.SYSTEM
        }
        
        return mapping.get(event_type)
    
    def get_status(self) -> Dict[str, Any]:
        """
        알림 시스템 상태 가져오기
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        status = {
            "is_running": self.is_running,
            "telegram_active": self.telegram.is_active() if self.telegram else False,
            "redis_publisher_connected": self.redis_publisher.connected,
            "redis_subscriber_connected": self.redis_subscriber.connected,
            "notification_count": self.notification_count,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": uptime,
            "queue_size": self.notification_handler.get_queue_size()
        }
        
        return status
    
    def send_trade_open_notification(self, trade_data: Dict[str, Any], immediate: bool = False) -> bool:
        """
        거래 시작 알림 전송
        
        Args:
            trade_data: 거래 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.TRADE_OPEN, trade_data, immediate)
    
    def send_trade_close_notification(self, trade_data: Dict[str, Any], immediate: bool = False) -> bool:
        """
        거래 종료 알림 전송
        
        Args:
            trade_data: 거래 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.TRADE_CLOSE, trade_data, immediate)
    
    def send_order_notification(self, order_data: Dict[str, Any], immediate: bool = False) -> bool:
        """
        주문 알림 전송
        
        Args:
            order_data: 주문 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        status = order_data.get('status', '').lower()
        
        if status == 'new':
            return self.send_notification(EventType.ORDER_PLACED, order_data, immediate)
        elif status == 'filled':
            return self.send_notification(EventType.ORDER_FILLED, order_data, immediate)
        elif status == 'canceled':
            return self.send_notification(EventType.ORDER_CANCELED, order_data, immediate)
        else:
            logger.warning(f"알 수 없는 주문 상태: {status}")
            return False
    
    def send_risk_alert(self, risk_data: Dict[str, Any], immediate: bool = True) -> bool:
        """
        리스크 알림 전송
        
        Args:
            risk_data: 리스크 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.RISK_ALERT, risk_data, immediate)
    
    def send_system_status(self, status_data: Dict[str, Any], immediate: bool = False) -> bool:
        """
        시스템 상태 알림 전송
        
        Args:
            status_data: 상태 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.SYSTEM_STATUS, status_data, immediate)
    
    def send_performance_update(self, performance_data: Dict[str, Any], immediate: bool = False) -> bool:
        """
        성능 업데이트 알림 전송
        
        Args:
            performance_data: 성능 데이터
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.PERFORMANCE_UPDATE, performance_data, immediate)
    
    def send_error(self, message: str, immediate: bool = True) -> bool:
        """
        오류 알림 전송
        
        Args:
            message: 오류 메시지
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.ERROR, {"message": message}, immediate)
    
    def send_warning(self, message: str, immediate: bool = False) -> bool:
        """
        경고 알림 전송
        
        Args:
            message: 경고 메시지
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.WARNING, {"message": message}, immediate)
    
    def send_info(self, message: str, immediate: bool = False) -> bool:
        """
        정보 알림 전송
        
        Args:
            message: 정보 메시지
            immediate: 즉시 전송 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.send_notification(EventType.INFO, {"message": message}, immediate)
