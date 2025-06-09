"""
텔레그램 봇 모듈

이 모듈은 트레이딩 봇의 텔레그램 봇 기능을 제공합니다.
거래 알림, 리스크 알림, 원격 명령 등을 지원합니다.
"""

import os
import logging
import asyncio
import json
# DEAD CODE: import hmac
# DEAD CODE: import hashlib
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from functools import wraps

# DEAD CODE: from telegram import Update, Bot
from telegram import ParseMode
# DEAD CODE: # DEAD CODE: # DEAD CODE: from telegram.ext import (
    Updater, CommandHandler, CallbackContext, 
    MessageHandler, Filters, Dispatcher
)

from src.risk_manager.risk_manager import RiskManager, get_risk_manager
from src.execution_engine.trading import ExecutionEngine
from src.notifications.telegram import TelegramNotifier, NotificationLevel

# 로깅 설정
logger = logging.getLogger(__name__)

# 인증 데코레이터
def require_auth(func):
    """인증이 필요한 명령에 대한 데코레이터"""
    @wraps(func)
    async def wrapped(self, update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id in self.authorized_users:
            return await func(self, update, context, *args, **kwargs)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⛔ 권한이 없습니다. 이 명령을 실행할 수 없습니다."
            )
    return wrapped

class TelegramBot:
    """텔레그램 봇 클래스"""
    
    def __init__(
        self, 
        token: str, 
        chat_id: str, 
        risk_manager: Optional[RiskManager] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        authorized_users: Optional[List[int]] = None
    ):
        """
        텔레그램 봇 초기화
        
        Args:
            token: 텔레그램 봇 토큰
            chat_id: 메시지를 보낼 채팅 ID
            risk_manager: 리스크 관리자 인스턴스 (옵션)
            execution_engine: 실행 엔진 인스턴스 (옵션)
            authorized_users: 명령 실행이 허용된 사용자 ID 목록
        """
        self.token = token
        self.chat_id = chat_id
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # 리스크 관리자 설정
        self.risk_manager = risk_manager
        if self.risk_manager is None:
            self.risk_manager = get_risk_manager()
            
        # 실행 엔진 설정
        self.execution_engine = execution_engine
        
        # 알림 전송을 위한 TelegramNotifier 인스턴스 생성
        self.notifier = TelegramNotifier(token, chat_id)
        
        # 인증된 사용자 목록
        self.authorized_users = authorized_users or []
        
        # 명령 핸들러 등록
        self._register_handlers()
        
        # 리스크 이벤트 구독
        if self.risk_manager:
            # 리스크 이벤트 처리 메서드를 리스크 관리자에 등록
            # 이 부분은 리스크 관리자의 이벤트 시스템에 따라 달라질 수 있음
            pass
        
        logger.info("텔레그램 봇이 초기화되었습니다.")
    
    def _register_handlers(self):
        """명령 핸들러 등록"""
        # 기본 명령
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        
        # 거래 관련 명령
        self.dispatcher.add_handler(CommandHandler("status", self.status_command))
        self.dispatcher.add_handler(CommandHandler("balance", self.balance_command))
        self.dispatcher.add_handler(CommandHandler("trades", self.trades_command))
        
        # 리스크 관련 명령
        self.dispatcher.add_handler(CommandHandler("risk", self.risk_command))
        
        # 오류 핸들러
        self.dispatcher.add_error_handler(self.error_handler)
        
        logger.info("텔레그램 봇 명령 핸들러가 등록되었습니다.")
    
    def start(self):
        """봇 시작"""
        self.updater.start_polling()
        logger.info("텔레그램 봇이 시작되었습니다.")
        
        # 시작 메시지 전송
        self.send_message("🤖 트레이딩 봇이 시작되었습니다. `/help` 명령으로 사용 가능한 명령어를 확인하세요.")
    
    def stop(self):
        """봇 중지"""
        self.updater.stop()
        logger.info("텔레그램 봇이 중지되었습니다.")
    
    async def start_command(self, update: Update, context: CallbackContext):
        """시작 명령 처리"""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "👋 안녕하세요! 트레이딩 봇 텔레그램 인터페이스입니다.\n\n"
                "이 봇을 통해 거래 상태를 확인하고 리스크 설정을 관리할 수 있습니다.\n"
                "사용 가능한 명령어를 보려면 `/help` 명령을 사용하세요."
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: CallbackContext):
        """도움말 명령 처리"""
        help_text = (
            "*사용 가능한 명령어*\n\n"
            "기본 명령:\n"
            "• `/start` - 봇 시작 메시지\n"
            "• `/help` - 이 도움말 표시\n\n"
            
            "거래 정보:\n"
            "• `/status` - 현재 봇 상태 확인\n"
            "• `/balance` - 현재 잔액 확인\n"
            "• `/trades` - 최근 거래 내역 확인\n\n"
            
            "리스크 관리:\n"
            "• `/risk on` - 거래 활성화\n"
            "• `/risk off` - 거래 비활성화\n"
            "• `/risk status` - 현재 리스크 상태 확인\n"
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    @require_auth
    async def status_command(self, update: Update, context: CallbackContext):
        """상태 명령 처리"""
        if self.execution_engine:
            status = "활성화" if not self.risk_manager.kill_switch_active else "비활성화"
            
            status_text = (
                f"*봇 상태*\n\n"
                f"• 거래 상태: `{status}`\n"
            )
            
            if self.risk_manager:
                status_text += (
                    f"• 킬 스위치: `{'활성화' if self.risk_manager.kill_switch_active else '비활성화'}`\n"
                    f"• 서킷 브레이커: `{'활성화' if self.risk_manager.circuit_breaker_active else '비활성화'}`\n"
                )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 실행 엔진이 초기화되지 않았습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    @require_auth
    async def balance_command(self, update: Update, context: CallbackContext):
        """잔액 명령 처리"""
        if self.risk_manager:
            current_balance = self.risk_manager.current_balance
            peak_balance = self.risk_manager.peak_balance
            
            if peak_balance > 0:
                drawdown = 1 - (current_balance / peak_balance)
                drawdown_percent = drawdown * 100
            else:
                drawdown_percent = 0
            
            balance_text = (
                f"*계정 잔액*\n\n"
                f"• 현재 잔액: `{current_balance:.2f} USDT`\n"
                f"• 최고 잔액: `{peak_balance:.2f} USDT`\n"
                f"• 현재 드로다운: `{drawdown_percent:.2f}%`\n"
            )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=balance_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 리스크 관리자가 초기화되지 않았습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    @require_auth
    async def trades_command(self, update: Update, context: CallbackContext):
        """최근 거래 명령 처리"""
        if self.execution_engine:
            # 여기서는 실행 엔진에서 최근 거래 내역을 가져오는 로직이 필요합니다.
            # 실제 구현은 실행 엔진의 API에 따라 달라질 수 있습니다.
            trades = []  # 실제로는 실행 엔진에서 가져와야 함
            
            if trades:
                trades_text = "*최근 거래 내역*\n\n"
                
                for trade in trades[:5]:  # 최근 5개 거래만 표시
                    trade_id = trade.get('id', 'N/A')
                    pair = trade.get('pair', 'N/A')
                    side = trade.get('side', 'N/A')
                    status = trade.get('status', 'N/A')
                    
                    trades_text += (
                        f"ID: `{trade_id}`\n"
                        f"페어: `{pair}`\n"
                        f"방향: `{side.upper()}`\n"
                        f"상태: `{status.upper()}`\n\n"
                    )
            else:
                trades_text = "최근 거래 내역이 없습니다."
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=trades_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 실행 엔진이 초기화되지 않았습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    @require_auth
    async def risk_command(self, update: Update, context: CallbackContext):
        """리스크 명령 처리"""
        if not self.risk_manager:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 리스크 관리자가 초기화되지 않았습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if not context.args:
            # 인수가 없으면 현재 리스크 상태 표시
            await self._show_risk_status(update, context)
            return
        
        command = context.args[0].lower()
        
        if command == 'on':
            # 거래 활성화
            await self.risk_manager.deactivate_kill_switch("텔레그램 명령으로 비활성화")
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ 거래가 활성화되었습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif command == 'off':
            # 거래 비활성화
            await self.risk_manager.activate_kill_switch("텔레그램 명령으로 활성화")
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🛑 거래가 비활성화되었습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif command == 'status':
            # 리스크 상태 표시
            await self._show_risk_status(update, context)
            
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "⚠️ 알 수 없는 리스크 명령입니다.\n"
                    "사용 가능한 명령: `/risk on`, `/risk off`, `/risk status`"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _show_risk_status(self, update: Update, context: CallbackContext):
        """리스크 상태 표시"""
        if self.risk_manager:
            status_text = (
                f"*리스크 관리 상태*\n\n"
                f"• 킬 스위치: `{'활성화' if self.risk_manager.kill_switch_active else '비활성화'}`\n"
                f"• 서킷 브레이커: `{'활성화' if self.risk_manager.circuit_breaker_active else '비활성화'}`\n"
                f"• 최대 드로다운: `{self.risk_manager.max_drawdown * 100:.2f}%`\n"
                f"• 현재 드로다운: "
            )
            
            if self.risk_manager.peak_balance > 0:
                drawdown = 1 - (self.risk_manager.current_balance / self.risk_manager.peak_balance)
                status_text += f"`{drawdown * 100:.2f}%`\n"
            else:
                status_text += "`0.00%`\n"
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 리스크 관리자가 초기화되지 않았습니다.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def error_handler(self, update: Update, context: CallbackContext):
        """오류 핸들러"""
        logger.error(f"텔레그램 봇 오류: {context.error}")
        
        try:
            # 오류 메시지 전송
            if update:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ 오류가 발생했습니다: {context.error}",
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"오류 처리 중 추가 오류 발생: {e}")
    
    def send_message(self, message: str, level: Union[NotificationLevel, str] = NotificationLevel.INFO) -> bool:
        """
        텔레그램 메시지 전송
        
        Args:
            message: 전송할 메시지
            level: 메시지 레벨
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.notifier.send_message(message, level)
    
    def send_trade_alert(self, trade: Dict[str, Any]) -> bool:
        """
        거래 알림 전송
        
        Args:
            trade: 거래 데이터
            
        Returns:
            bool: 전송 성공 여부
        """
        return self.notifier.send_trade_notification(trade)
    
    async def on_risk_event(self, event: Dict[str, Any]) -> None:
        """
        리스크 이벤트 처리
        
        Args:
            event: 리스크 이벤트 데이터
        """
        event_type = event.get('type')
        event_data = event.get('data', {})
        
        if event_type == 'MAX_DRAWDOWN_EXCEEDED':
            drawdown = event_data.get('drawdown', 0)
            message = f"⚠️ *최대 드로다운 초과*\n현재 드로다운: `{drawdown * 100:.2f}%`"
            self.send_message(message, NotificationLevel.WARNING)
            
        elif event_type == 'CIRCUIT_BREAKER_TRIGGERED':
            price_change = event_data.get('price_change', 0)
            message = f"⚠️ *서킷 브레이커 발동*\n가격 변동: `{price_change * 100:.2f}%`"
            self.send_message(message, NotificationLevel.WARNING)
            
        elif event_type == 'KILL_SWITCH_ACTIVATED':
            reason = event_data.get('reason', '알 수 없음')
            message = f"🛑 *킬 스위치 활성화*\n사유: `{reason}`"
            self.send_message(message, NotificationLevel.ERROR)
            
        elif event_type == 'DAILY_TRADE_LIMIT_REACHED':
            trade_count = event_data.get('trade_count', 0)
            limit = event_data.get('limit', 0)
            message = f"⚠️ *일일 거래 제한 도달*\n오늘 거래 수: `{trade_count}`, 제한: `{limit}`"
            self.send_message(message, NotificationLevel.WARNING)

# 싱글톤 인스턴스
_telegram_bot = None

def init_telegram_bot(
    token: Optional[str] = None, 
    chat_id: Optional[str] = None,
    risk_manager: Optional[RiskManager] = None,
    execution_engine: Optional[ExecutionEngine] = None,
    authorized_users: Optional[List[int]] = None
) -> Optional[TelegramBot]:
    """
    텔레그램 봇 초기화
    
    Args:
        token: 텔레그램 봇 토큰 (None인 경우 환경 변수에서 가져옴)
        chat_id: 텔레그램 채팅 ID (None인 경우 환경 변수에서 가져옴)
        risk_manager: 리스크 관리자 인스턴스
        execution_engine: 실행 엔진 인스턴스
        authorized_users: 인증된 사용자 ID 목록
        
    Returns:
        Optional[TelegramBot]: 텔레그램 봇 인스턴스 또는 None (초기화 실패 시)
    """
    global _telegram_bot
    
    if _telegram_bot is not None:
        logger.info("이미 초기화된 텔레그램 봇 인스턴스가 있습니다.")
        return _telegram_bot
    
    # 환경 변수에서 토큰과 채팅 ID 가져오기
    if token is None:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if chat_id is None:
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    # 인증된 사용자 목록 설정
    if authorized_users is None:
        # 환경 변수에서 인증된 사용자 목록 가져오기
        auth_users_str = os.environ.get('TELEGRAM_AUTHORIZED_USERS', '')
        if auth_users_str:
            try:
                authorized_users = [int(user_id.strip()) for user_id in auth_users_str.split(',')]
            except ValueError:
                logger.error("인증된 사용자 ID 목록 파싱 오류")
                authorized_users = []
        else:
            authorized_users = []
    
    if not token or not chat_id:
        logger.error("텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다.")
        return None
    
    try:
        _telegram_bot = TelegramBot(
            token=token,
            chat_id=chat_id,
            risk_manager=risk_manager,
            execution_engine=execution_engine,
            authorized_users=authorized_users
        )
        logger.info("텔레그램 봇이 초기화되었습니다.")
        return _telegram_bot
    except Exception as e:
        logger.error(f"텔레그램 봇 초기화 중 오류 발생: {e}")
        return None

def get_telegram_bot() -> Optional[TelegramBot]:
    """
    텔레그램 봇 인스턴스 가져오기
    
    Returns:
        Optional[TelegramBot]: 텔레그램 봇 인스턴스 또는 None (초기화되지 않은 경우)
    """
    global _telegram_bot
    return _telegram_bot
