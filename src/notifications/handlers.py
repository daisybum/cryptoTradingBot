"""
알림 핸들러 모듈

이 모듈은 다양한 이벤트에 대한 알림 핸들러를 제공합니다.
각 핸들러는 특정 이벤트 유형에 대한 알림을 처리합니다.
"""
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import threading
import time
from enum import Enum

from src.notifications.telegram import TelegramNotifier, NotificationLevel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EventType(Enum):
    """이벤트 유형 열거형"""
    TRADE_OPEN = "trade_open"
    TRADE_CLOSE = "trade_close"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELED = "order_canceled"
    RISK_ALERT = "risk_alert"
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_UPDATE = "performance_update"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class NotificationHandler:
    """알림 핸들러 클래스"""
    
    def __init__(self, telegram_notifier: Optional[TelegramNotifier] = None):
        """
        알림 핸들러 초기화
        
        Args:
            telegram_notifier: 텔레그램 알림 관리자 인스턴스
        """
        self.telegram = telegram_notifier
        self.event_handlers = {}
        self.notification_queue = []
        self.queue_lock = threading.Lock()
        self.is_processing = False
        self.batch_size = 5  # 한 번에 처리할 최대 알림 수
        self.batch_interval = 10  # 배치 처리 간격 (초)
        
        # 이벤트 핸들러 등록
        self._register_default_handlers()
        
        # 알림 처리 스레드 시작
        self._start_notification_processor()
    
    def _register_default_handlers(self):
        """기본 이벤트 핸들러 등록"""
        self.register_handler(EventType.TRADE_OPEN, self._handle_trade_open)
        self.register_handler(EventType.TRADE_CLOSE, self._handle_trade_close)
        self.register_handler(EventType.ORDER_PLACED, self._handle_order_placed)
        self.register_handler(EventType.ORDER_FILLED, self._handle_order_filled)
        self.register_handler(EventType.ORDER_CANCELED, self._handle_order_canceled)
        self.register_handler(EventType.RISK_ALERT, self._handle_risk_alert)
        self.register_handler(EventType.SYSTEM_STATUS, self._handle_system_status)
        self.register_handler(EventType.PERFORMANCE_UPDATE, self._handle_performance_update)
        self.register_handler(EventType.ERROR, self._handle_error)
        self.register_handler(EventType.WARNING, self._handle_warning)
        self.register_handler(EventType.INFO, self._handle_info)
    
    def register_handler(self, event_type: EventType, handler_func: Callable):
        """
        이벤트 핸들러 등록
        
        Args:
            event_type: 이벤트 유형
            handler_func: 핸들러 함수
        """
        self.event_handlers[event_type] = handler_func
        logger.debug(f"핸들러 등록됨: {event_type.value}")
    
    def notify(self, event_type: EventType, data: Dict[str, Any], immediate: bool = False):
        """
        알림 전송
        
        Args:
            event_type: 이벤트 유형
            data: 이벤트 데이터
            immediate: 즉시 전송 여부 (True인 경우 큐에 넣지 않고 즉시 처리)
        """
        if immediate:
            self._process_notification(event_type, data)
        else:
            with self.queue_lock:
                self.notification_queue.append((event_type, data))
                logger.debug(f"알림이 큐에 추가됨: {event_type.value}")
    
    def _start_notification_processor(self):
        """알림 처리 스레드 시작"""
        def processor():
            while True:
                try:
                    self._process_notification_batch()
                    time.sleep(self.batch_interval)
                except Exception as e:
                    logger.error(f"알림 처리 중 오류 발생: {e}")
        
        thread = threading.Thread(target=processor, daemon=True)
        thread.start()
        logger.info("알림 처리 스레드가 시작되었습니다.")
    
    def _process_notification_batch(self):
        """알림 배치 처리"""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        try:
            batch = []
            with self.queue_lock:
                batch_size = min(len(self.notification_queue), self.batch_size)
                if batch_size > 0:
                    batch = self.notification_queue[:batch_size]
                    self.notification_queue = self.notification_queue[batch_size:]
            
            for event_type, data in batch:
                self._process_notification(event_type, data)
                
        finally:
            self.is_processing = False
    
    def _process_notification(self, event_type: EventType, data: Dict[str, Any]):
        """
        알림 처리
        
        Args:
            event_type: 이벤트 유형
            data: 이벤트 데이터
        """
        if not self.telegram:
            logger.warning(f"텔레그램 알림 관리자가 설정되지 않았습니다. 알림을 처리할 수 없습니다: {event_type.value}")
            return
        
        handler = self.event_handlers.get(event_type)
        if handler:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"알림 핸들러 실행 중 오류 발생: {e}")
        else:
            logger.warning(f"이벤트 유형 {event_type.value}에 대한 핸들러가 없습니다.")
    
    def _handle_trade_open(self, data: Dict[str, Any]):
        """
        거래 시작 알림 처리
        
        Args:
            data: 거래 데이터
        """
        if not self.telegram:
            return
        
        self.telegram.send_trade_notification(data)
    
    def _handle_trade_close(self, data: Dict[str, Any]):
        """
        거래 종료 알림 처리
        
        Args:
            data: 거래 데이터
        """
        if not self.telegram:
            return
        
        self.telegram.send_trade_notification(data)
    
    def _handle_order_placed(self, data: Dict[str, Any]):
        """
        주문 생성 알림 처리
        
        Args:
            data: 주문 데이터
        """
        if not self.telegram:
            return
        
        order_id = data.get('order_id', 'N/A')
        symbol = data.get('symbol', 'N/A')
        side = data.get('side', 'N/A').upper()
        order_type = data.get('type', 'N/A').upper()
        quantity = data.get('quantity', 'N/A')
        price = data.get('price', 'N/A')
        
        emoji = "🟢" if side == "BUY" else "🔴"
        
        message = f"{emoji} *주문 생성*\n"
        message += f"ID: `{order_id}`\n"
        message += f"심볼: `{symbol}`\n"
        message += f"방향: `{side}`\n"
        message += f"유형: `{order_type}`\n"
        message += f"수량: `{quantity}`\n"
        
        if price != 'N/A':
            message += f"가격: `{price}`\n"
        
        self.telegram.send_message(message, NotificationLevel.INFO)
    
    def _handle_order_filled(self, data: Dict[str, Any]):
        """
        주문 체결 알림 처리
        
        Args:
            data: 주문 데이터
        """
        if not self.telegram:
            return
        
        order_id = data.get('order_id', 'N/A')
        symbol = data.get('symbol', 'N/A')
        side = data.get('side', 'N/A').upper()
        quantity = data.get('quantity', 'N/A')
        price = data.get('price', 'N/A')
        
        emoji = "✅" if side == "BUY" else "💰"
        
        message = f"{emoji} *주문 체결*\n"
        message += f"ID: `{order_id}`\n"
        message += f"심볼: `{symbol}`\n"
        message += f"방향: `{side}`\n"
        message += f"수량: `{quantity}`\n"
        message += f"가격: `{price}`\n"
        
        self.telegram.send_message(message, NotificationLevel.INFO)
    
    def _handle_order_canceled(self, data: Dict[str, Any]):
        """
        주문 취소 알림 처리
        
        Args:
            data: 주문 데이터
        """
        if not self.telegram:
            return
        
        order_id = data.get('order_id', 'N/A')
        symbol = data.get('symbol', 'N/A')
        reason = data.get('reason', 'N/A')
        
        message = f"❌ *주문 취소*\n"
        message += f"ID: `{order_id}`\n"
        message += f"심볼: `{symbol}`\n"
        message += f"이유: `{reason}`\n"
        
        self.telegram.send_message(message, NotificationLevel.INFO)
    
    def _handle_risk_alert(self, data: Dict[str, Any]):
        """
        리스크 알림 처리
        
        Args:
            data: 리스크 데이터
        """
        if not self.telegram:
            return
        
        alert_type = data.get('alert_type', 'N/A')
        value = data.get('value', 'N/A')
        threshold = data.get('threshold', 'N/A')
        
        emoji = "⚠️"
        if alert_type.lower() == 'kill_switch':
            emoji = "🔴"
        elif alert_type.lower() == 'circuit_breaker':
            emoji = "🟠"
        elif alert_type.lower() == 'drawdown':
            emoji = "📉"
        
        message = f"{emoji} *리스크 알림*\n"
        message += f"유형: `{alert_type}`\n"
        message += f"값: `{value}`\n"
        message += f"임계값: `{threshold}`\n"
        
        if 'description' in data:
            message += f"설명: {data['description']}\n"
        
        self.telegram.send_message(message, NotificationLevel.WARNING)
    
    def _handle_system_status(self, data: Dict[str, Any]):
        """
        시스템 상태 알림 처리
        
        Args:
            data: 시스템 상태 데이터
        """
        if not self.telegram:
            return
        
        status = data.get('status', 'N/A')
        component = data.get('component', 'N/A')
        
        emoji = "🟢"
        if status.lower() == 'error':
            emoji = "🔴"
        elif status.lower() == 'warning':
            emoji = "🟠"
        elif status.lower() == 'info':
            emoji = "🔵"
        
        message = f"{emoji} *시스템 상태*\n"
        message += f"컴포넌트: `{component}`\n"
        message += f"상태: `{status}`\n"
        
        if 'description' in data:
            message += f"설명: {data['description']}\n"
        
        level = NotificationLevel.INFO
        if status.lower() == 'error':
            level = NotificationLevel.ERROR
        elif status.lower() == 'warning':
            level = NotificationLevel.WARNING
        
        self.telegram.send_message(message, level)
    
    def _handle_performance_update(self, data: Dict[str, Any]):
        """
        성능 업데이트 알림 처리
        
        Args:
            data: 성능 데이터
        """
        if not self.telegram:
            return
        
        self.telegram.send_performance_report(data)
    
    def _handle_error(self, data: Dict[str, Any]):
        """
        오류 알림 처리
        
        Args:
            data: 오류 데이터
        """
        if not self.telegram:
            return
        
        message = data.get('message', 'N/A')
        self.telegram.send_error(message)
    
    def _handle_warning(self, data: Dict[str, Any]):
        """
        경고 알림 처리
        
        Args:
            data: 경고 데이터
        """
        if not self.telegram:
            return
        
        message = data.get('message', 'N/A')
        self.telegram.send_warning(message)
    
    def _handle_info(self, data: Dict[str, Any]):
        """
        정보 알림 처리
        
        Args:
            data: 정보 데이터
        """
        if not self.telegram:
            return
        
        message = data.get('message', 'N/A')
        self.telegram.send_info(message)
    
    def get_queue_size(self) -> int:
        """
        알림 큐 크기 가져오기
        
        Returns:
            int: 알림 큐 크기
        """
        with self.queue_lock:
            return len(self.notification_queue)
