"""
텔레그램 알림 시스템

이 모듈은 트레이딩 봇의 텔레그램 알림 기능을 제공합니다.
거래 신호, 오류, 경고 및 정보 메시지를 텔레그램을 통해 사용자에게 전송합니다.
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any, List
from enum import Enum

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """알림 레벨 열거형"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    TRADE = "trade"

class TelegramNotifier:
    """텔레그램 알림 관리자"""
    
    def __init__(self, token: str, chat_id: str):
        """
        텔레그램 알림 관리자 초기화
        
        Args:
            token: 텔레그램 봇 토큰
            chat_id: 메시지를 보낼 채팅 ID
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.active = True
        self.notification_level = NotificationLevel.INFO
        self.rate_limit = 20  # 초당 최대 메시지 수
        self.last_message_time = 0
        
        # 초기화 시 연결 테스트
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """
        텔레그램 API 연결 테스트
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=5)
            if response.status_code == 200:
                logger.info("텔레그램 API 연결 성공")
                return True
            else:
                logger.error(f"텔레그램 API 연결 실패: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"텔레그램 API 연결 테스트 중 오류 발생: {e}")
            return False
    
    def is_active(self) -> bool:
        """
        알림 시스템 활성화 상태 확인
        
        Returns:
            bool: 활성화 상태
        """
        return self.active
    
    def enable(self) -> None:
        """알림 시스템 활성화"""
        self.active = True
        logger.info("텔레그램 알림 시스템이 활성화되었습니다.")
    
    def disable(self) -> None:
        """알림 시스템 비활성화"""
        self.active = False
        logger.info("텔레그램 알림 시스템이 비활성화되었습니다.")
    
    def get_notification_level(self) -> str:
        """
        현재 알림 레벨 가져오기
        
        Returns:
            str: 알림 레벨 문자열
        """
        return self.notification_level.value
    
    def set_notification_level(self, level: str) -> None:
        """
        알림 레벨 설정
        
        Args:
            level: 알림 레벨 ('info', 'warning', 'error', 'trade')
        """
        try:
            self.notification_level = NotificationLevel(level)
            logger.info(f"알림 레벨이 '{level}'로 설정되었습니다.")
        except ValueError:
            logger.error(f"유효하지 않은 알림 레벨: {level}")
    
    def _should_send(self, level: NotificationLevel) -> bool:
        """
        주어진 레벨의 메시지를 보내야 하는지 확인
        
        Args:
            level: 확인할 알림 레벨
            
        Returns:
            bool: 메시지를 보내야 하는지 여부
        """
        if not self.active:
            return False
        
        # 레벨 우선순위: INFO < WARNING < ERROR, TRADE
        level_priority = {
            NotificationLevel.INFO: 0,
            NotificationLevel.WARNING: 1,
            NotificationLevel.ERROR: 2,
            NotificationLevel.TRADE: 2
        }
        
        return level_priority[level] >= level_priority[self.notification_level]
    
    def _rate_limit_check(self) -> None:
        """속도 제한 확인 및 대기"""
        current_time = time.time()
        time_since_last = current_time - self.last_message_time
        
        if time_since_last < 1.0 / self.rate_limit:
            # 속도 제한에 도달한 경우 대기
            sleep_time = (1.0 / self.rate_limit) - time_since_last
            time.sleep(sleep_time)
        
        self.last_message_time = time.time()
    
    def send_message(self, message: str, level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """
        텔레그램 메시지 전송
        
        Args:
            message: 전송할 메시지
            level: 메시지 레벨
            
        Returns:
            bool: 전송 성공 여부
        """
        if isinstance(level, str):
            try:
                level = NotificationLevel(level)
            except ValueError:
                level = NotificationLevel.INFO
        
        if not self._should_send(level):
            return False
        
        try:
            self._rate_limit_check()
            
            # HTML 모드를 사용하여 파싱 오류 해결
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"텔레그램 메시지 전송 성공: {message[:50]}...")
                return True
            else:
                logger.error(f"텔레그램 메시지 전송 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 중 오류 발생: {e}")
            return False
    
    def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """
        거래 알림 전송
        
        Args:
            trade_data: 거래 데이터 딕셔너리
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            trade_id = trade_data.get('trade_id', 'N/A')
            pair = trade_data.get('pair', 'N/A')
            side = trade_data.get('side', 'N/A')
            status = trade_data.get('status', 'N/A')
            
            # 거래 상태에 따라 이모지 선택
            emoji = "🟢" if side.lower() == 'buy' else "🔴"
            if status.lower() == 'closed':
                pnl = trade_data.get('pnl', 0)
                pnl_pct = trade_data.get('pnl_pct', 0)
                emoji = "✅" if pnl > 0 else "❌"
            
            # 메시지 구성
            message = f"{emoji} *거래 알림*\n"
            message += f"ID: `{trade_id}`\n"
            message += f"페어: `{pair}`\n"
            message += f"방향: `{side.upper()}`\n"
            message += f"상태: `{status.upper()}`\n"
            
            if status.lower() == 'open':
                entry_price = trade_data.get('entry_price', 'N/A')
                quantity = trade_data.get('quantity', 'N/A')
                message += f"진입가: `{entry_price}`\n"
                message += f"수량: `{quantity}`\n"
                
                # 손절 및 이익 실현 정보 추가
                stop_loss = trade_data.get('stop_loss')
                take_profit = trade_data.get('take_profit')
                
                if stop_loss:
                    message += f"손절가: `{stop_loss}`\n"
                if take_profit:
                    message += f"이익실현가: `{take_profit}`\n"
                
            elif status.lower() == 'closed':
                entry_price = trade_data.get('entry_price', 'N/A')
                exit_price = trade_data.get('exit_price', 'N/A')
                pnl = trade_data.get('pnl', 0)
                pnl_pct = trade_data.get('pnl_pct', 0)
                
                message += f"진입가: `{entry_price}`\n"
                message += f"청산가: `{exit_price}`\n"
                message += f"손익: `{pnl:.2f} USDT ({pnl_pct:.2f}%)`\n"
            
            return self.send_message(message, NotificationLevel.TRADE)
            
        except Exception as e:
            logger.error(f"거래 알림 전송 중 오류 발생: {e}")
            return False
    
    def send_error(self, error_message: str) -> bool:
        """
        오류 알림 전송
        
        Args:
            error_message: 오류 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"🚨 *오류 발생*\n{error_message}"
        return self.send_message(message, NotificationLevel.ERROR)
    
    def send_warning(self, warning_message: str) -> bool:
        """
        경고 알림 전송
        
        Args:
            warning_message: 경고 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"⚠️ *경고*\n{warning_message}"
        return self.send_message(message, NotificationLevel.WARNING)
    
    def send_info(self, info_message: str) -> bool:
        """
        정보 알림 전송
        
        Args:
            info_message: 정보 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"ℹ️ *정보*\n{info_message}"
        return self.send_message(message, NotificationLevel.INFO)
    
    def send_performance_report(self, performance_data: Dict[str, Any]) -> bool:
        """
        성능 보고서 알림 전송
        
        Args:
            performance_data: 성능 데이터 딕셔너리
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            total_trades = performance_data.get('total_trades', 0)
            win_rate = performance_data.get('win_rate', 0)
            total_profit = performance_data.get('total_profit', 0)
            max_drawdown = performance_data.get('max_drawdown', 0)
            
            message = f"📊 *성능 보고서*\n"
            message += f"총 거래 수: `{total_trades}`\n"
            message += f"승률: `{win_rate:.2f}%`\n"
            message += f"총 수익: `{total_profit:.2f} USDT`\n"
            message += f"최대 드로다운: `{max_drawdown:.2f}%`\n"
            
            return self.send_message(message, NotificationLevel.INFO)
            
        except Exception as e:
            logger.error(f"성능 보고서 알림 전송 중 오류 발생: {e}")
            return False
