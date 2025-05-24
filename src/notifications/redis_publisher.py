"""
Redis 알림 발행자 모듈

이 모듈은 Redis를 사용하여 알림을 발행하는 기능을 제공합니다.
Redis PubSub 메커니즘을 통해 실시간 알림을 다른 시스템에 전달합니다.
"""
import logging
import json
import redis
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    """알림 채널 열거형"""
    TRADES = "nasos:notifications:trades"
    ORDERS = "nasos:notifications:orders"
    RISK = "nasos:notifications:risk"
    SYSTEM = "nasos:notifications:system"
    PERFORMANCE = "nasos:notifications:performance"
    ALL = "nasos:notifications:all"

class RedisPublisher:
    """Redis 알림 발행자 클래스"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Redis 알림 발행자 초기화
        
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis 데이터베이스
            password: Redis 비밀번호
        """
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
    
    def publish(self, channel: NotificationChannel, data: Dict[str, Any]) -> bool:
        """
        알림 발행
        
        Args:
            channel: 알림 채널
            data: 알림 데이터
            
        Returns:
            bool: 발행 성공 여부
        """
        if not self.connected:
            logger.warning("Redis 서버에 연결되어 있지 않습니다.")
            return False
        
        try:
            # 타임스탬프 추가
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            # JSON으로 직렬화
            message = json.dumps(data)
            
            # 채널에 발행
            self.redis_client.publish(channel.value, message)
            
            # 모든 채널에도 발행
            if channel != NotificationChannel.ALL:
                self.redis_client.publish(NotificationChannel.ALL.value, message)
            
            logger.debug(f"알림이 발행되었습니다: {channel.value}")
            return True
            
        except Exception as e:
            logger.error(f"알림 발행 실패: {e}")
            return False
    
    def publish_trade_notification(self, data: Dict[str, Any]) -> bool:
        """
        거래 알림 발행
        
        Args:
            data: 거래 데이터
            
        Returns:
            bool: 발행 성공 여부
        """
        return self.publish(NotificationChannel.TRADES, data)
    
    def publish_order_notification(self, data: Dict[str, Any]) -> bool:
        """
        주문 알림 발행
        
        Args:
            data: 주문 데이터
            
        Returns:
            bool: 발행 성공 여부
        """
        return self.publish(NotificationChannel.ORDERS, data)
    
    def publish_risk_notification(self, data: Dict[str, Any]) -> bool:
        """
        리스크 알림 발행
        
        Args:
            data: 리스크 데이터
            
        Returns:
            bool: 발행 성공 여부
        """
        return self.publish(NotificationChannel.RISK, data)
    
    def publish_system_notification(self, data: Dict[str, Any]) -> bool:
        """
        시스템 알림 발행
        
        Args:
            data: 시스템 데이터
            
        Returns:
            bool: 발행 성공 여부
        """
        return self.publish(NotificationChannel.SYSTEM, data)
    
    def publish_performance_notification(self, data: Dict[str, Any]) -> bool:
        """
        성능 알림 발행
        
        Args:
            data: 성능 데이터
            
        Returns:
            bool: 발행 성공 여부
        """
        return self.publish(NotificationChannel.PERFORMANCE, data)
    
    def store_notification(self, data: Dict[str, Any], expiry: int = 86400) -> bool:
        """
        알림 저장
        
        Args:
            data: 알림 데이터
            expiry: 만료 시간 (초)
            
        Returns:
            bool: 저장 성공 여부
        """
        if not self.connected:
            logger.warning("Redis 서버에 연결되어 있지 않습니다.")
            return False
        
        try:
            # 알림 ID 생성
            notification_id = f"notification:{datetime.now().strftime('%Y%m%d%H%M%S')}:{data.get('type', 'unknown')}"
            
            # 타임스탬프 추가
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            # JSON으로 직렬화
            message = json.dumps(data)
            
            # Redis에 저장
            self.redis_client.set(notification_id, message, ex=expiry)
            
            # 알림 목록에 추가
            self.redis_client.zadd(
                "notifications:recent",
                {notification_id: datetime.now().timestamp()}
            )
            
            # 최근 100개 알림만 유지
            self.redis_client.zremrangebyrank("notifications:recent", 0, -101)
            
            logger.debug(f"알림이 저장되었습니다: {notification_id}")
            return True
            
        except Exception as e:
            logger.error(f"알림 저장 실패: {e}")
            return False
    
    def get_recent_notifications(self, limit: int = 50) -> list:
        """
        최근 알림 가져오기
        
        Args:
            limit: 가져올 알림 수
            
        Returns:
            list: 알림 목록
        """
        if not self.connected:
            logger.warning("Redis 서버에 연결되어 있지 않습니다.")
            return []
        
        try:
            # 최근 알림 ID 가져오기
            notification_ids = self.redis_client.zrevrange("notifications:recent", 0, limit - 1)
            
            notifications = []
            for notification_id in notification_ids:
                # 알림 데이터 가져오기
                notification_data = self.redis_client.get(notification_id)
                if notification_data:
                    try:
                        notification = json.loads(notification_data)
                        notifications.append(notification)
                    except json.JSONDecodeError:
                        logger.warning(f"알림 데이터 파싱 실패: {notification_id}")
            
            return notifications
            
        except Exception as e:
            logger.error(f"최근 알림 가져오기 실패: {e}")
            return []
