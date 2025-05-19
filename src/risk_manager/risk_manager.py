"""
리스크 관리 시스템

이 모듈은 거래 시스템의 리스크를 관리하는 기능을 제공합니다.
글로벌 드로다운 보호, 거래별 손절, 포지션 크기 조정 등의 기능을 포함합니다.
"""

import logging
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta, date
import uuid

import redis
from redis.asyncio import Redis

from src.database.connection import get_db_manager
from src.database.models import Order, OrderStatus, OrderSide

logger = logging.getLogger(__name__)

class RiskManager:
    """리스크 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        리스크 관리자 초기화
        
        Args:
            config: 리스크 관리 설정
        """
        self.config = config
        self.risk_config = config.get('risk_management', {})
        
        # 리스크 관리 설정
        self.max_drawdown = self.risk_config.get('max_drawdown', 0.15)  # 최대 드로다운 (15%)
        self.per_trade_stop_loss = self.risk_config.get('stop_loss', 0.035)  # 거래별 손절 (3.5%)
        self.risk_per_trade = self.risk_config.get('risk_per_trade', 0.02)  # 거래당 리스크 (2%)
        self.daily_trade_limit = self.risk_config.get('daily_trade_limit', 60)  # 일일 거래 제한 (60건)
        self.circuit_breaker = self.risk_config.get('circuit_breaker', 0.05)  # 서킷 브레이커 (5%)
        
        # 리스크 상태
        self.kill_switch_active = False
        self.circuit_breaker_active = False
        self.peak_balance = 0.0
        self.current_balance = 0.0
        self.daily_trades = {}  # 일별 거래 수 추적
        
        # Redis 연결 설정
        self.redis_config = config.get('redis', {})
        self.redis_client = None
        self.pubsub = None
        
        # 데이터베이스 관리자
        self.db_manager = get_db_manager()
        
        logger.info(f"리스크 관리자 초기화됨: max_drawdown={self.max_drawdown}, stop_loss={self.per_trade_stop_loss}, "
                   f"risk_per_trade={self.risk_per_trade}, daily_trade_limit={self.daily_trade_limit}")
    
    async def connect_redis(self):
        """Redis 연결 설정"""
        try:
            host = self.redis_config.get('host', 'localhost')
            port = self.redis_config.get('port', 6379)
            db = self.redis_config.get('db', 0)
            
            self.redis_client = Redis(host=host, port=port, db=db, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            
            # 리스크 이벤트 채널 구독
            await self.pubsub.subscribe('risk_events')
            
            logger.info(f"Redis 연결 설정됨: {host}:{port}/{db}")
            
            # 리스크 이벤트 처리 태스크 시작
            asyncio.create_task(self._process_risk_events())
            
            return True
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            return False
    
    async def _process_risk_events(self):
        """리스크 이벤트 처리 루프"""
        if not self.pubsub:
            logger.error("Redis PubSub이 초기화되지 않았습니다")
            return
        
        logger.info("리스크 이벤트 처리 루프 시작")
        
        try:
            while True:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    try:
                        channel = message['channel']
                        data = json.loads(message['data'])
                        
                        logger.info(f"리스크 이벤트 수신: {data}")
                        
                        # 이벤트 유형에 따른 처리
                        event_type = data.get('type')
                        if event_type == 'MAX_DRAWDOWN_EXCEEDED':
                            await self._handle_max_drawdown_event(data)
                        elif event_type == 'CIRCUIT_BREAKER_TRIGGERED':
                            await self._handle_circuit_breaker_event(data)
                        elif event_type == 'KILL_SWITCH_ACTIVATED':
                            await self._handle_kill_switch_event(data)
                        elif event_type == 'DAILY_TRADE_LIMIT_REACHED':
                            await self._handle_trade_limit_event(data)
                    except Exception as e:
                        logger.error(f"리스크 이벤트 처리 중 오류 발생: {e}")
                
                await asyncio.sleep(0.1)  # CPU 사용량 감소를 위한 짧은 대기
        except asyncio.CancelledError:
            logger.info("리스크 이벤트 처리 루프 종료")
        except Exception as e:
            logger.error(f"리스크 이벤트 처리 루프 오류: {e}")
    
    async def _handle_max_drawdown_event(self, data: Dict[str, Any]):
        """최대 드로다운 이벤트 처리"""
        logger.warning(f"최대 드로다운 초과: {data}")
        self.kill_switch_active = True
        
        # 알림 전송
        await self._send_alert("최대 드로다운 초과", f"현재 드로다운: {data.get('drawdown', 0) * 100:.2f}%, 최대 허용: {self.max_drawdown * 100:.2f}%")
    
    async def _handle_circuit_breaker_event(self, data: Dict[str, Any]):
        """서킷 브레이커 이벤트 처리"""
        logger.warning(f"서킷 브레이커 발동: {data}")
        self.circuit_breaker_active = True
        
        # 알림 전송
        await self._send_alert("서킷 브레이커 발동", f"가격 변동: {data.get('price_change', 0) * 100:.2f}%, 임계값: {self.circuit_breaker * 100:.2f}%")
        
        # 일정 시간 후 서킷 브레이커 해제
        recovery_time = data.get('recovery_time', 3600)  # 기본 1시간
        asyncio.create_task(self._reset_circuit_breaker(recovery_time))
    
    async def _handle_kill_switch_event(self, data: Dict[str, Any]):
        """킬 스위치 이벤트 처리"""
        logger.warning(f"킬 스위치 활성화: {data}")
        self.kill_switch_active = True
        
        # 알림 전송
        await self._send_alert("킬 스위치 활성화", f"사유: {data.get('reason', '알 수 없음')}")
    
    async def _handle_trade_limit_event(self, data: Dict[str, Any]):
        """거래 제한 이벤트 처리"""
        logger.warning(f"일일 거래 제한 도달: {data}")
        
        # 알림 전송
        await self._send_alert("일일 거래 제한 도달", f"오늘 거래 수: {data.get('trade_count', 0)}, 제한: {self.daily_trade_limit}")
    
    async def _reset_circuit_breaker(self, delay_seconds: int):
        """서킷 브레이커 재설정"""
        await asyncio.sleep(delay_seconds)
        self.circuit_breaker_active = False
        logger.info(f"서킷 브레이커 재설정됨 ({delay_seconds}초 후)")
        
        # 알림 전송
        await self._send_alert("서킷 브레이커 재설정", "거래가 재개됩니다")
    
    async def _send_alert(self, title: str, message: str):
        """알림 전송"""
        try:
            alert_data = {
                'title': title,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'level': 'warning'
            }
            
            # Redis에 알림 발행
            if self.redis_client:
                await self.redis_client.publish('alerts', json.dumps(alert_data))
                logger.info(f"알림 전송됨: {title}")
            else:
                logger.warning(f"Redis 연결 없음, 알림 전송 실패: {title}")
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
    
    async def publish_risk_event(self, event_type: str, data: Dict[str, Any] = None):
        """
        리스크 이벤트 발행
        
        Args:
            event_type: 이벤트 유형
            data: 이벤트 데이터 (선택 사항)
        """
        try:
            if not data:
                data = {}
            
            event_data = {
                'type': event_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Redis에 이벤트 발행
            if self.redis_client:
                await self.redis_client.publish('risk_events', json.dumps(event_data))
                logger.info(f"리스크 이벤트 발행됨: {event_type}")
            else:
                logger.warning(f"Redis 연결 없음, 리스크 이벤트 발행 실패: {event_type}")
        except Exception as e:
            logger.error(f"리스크 이벤트 발행 실패: {e}")
    
    async def update_balance(self, current_balance: float) -> bool:
        """
        잔액 업데이트 및 드로다운 검사
        
        Args:
            current_balance: 현재 잔액
            
        Returns:
            bool: 드로다운 제한 내이면 True, 초과하면 False
        """
        # 이전 잔액 저장
        previous_balance = self.current_balance
        
        # 현재 잔액 업데이트
        self.current_balance = current_balance
        
        # 최고 잔액 업데이트
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            logger.info(f"최고 잔액 갱신: {self.peak_balance:.2f}")
        
        # 드로다운 계산
        if self.peak_balance > 0:
            drawdown = 1 - (current_balance / self.peak_balance)
            drawdown_percent = drawdown * 100
            
            # 드로다운 기록 저장
            await self._record_drawdown_history(drawdown)
            
            # 잔액 변화율 계산
            if previous_balance > 0:
                balance_change = (current_balance - previous_balance) / previous_balance
                balance_change_percent = balance_change * 100
                
                # 급격한 잔액 변화 감지 (서킷 브레이커 발동 조건)
                if balance_change < -self.circuit_breaker:
                    logger.warning(f"급격한 잔액 감소 감지: {balance_change_percent:.2f}%")
                    await self.publish_risk_event('CIRCUIT_BREAKER_TRIGGERED', {
                        'balance_change': balance_change,
                        'balance_change_percent': balance_change_percent,
                        'current_balance': current_balance,
                        'previous_balance': previous_balance,
                        'recovery_time': 3600  # 1시간 후 서킷 브레이커 해제
                    })
                    self.circuit_breaker_active = True
            
            # 드로다운 임계값 검사
            if drawdown > self.max_drawdown:
                logger.warning(f"최대 드로다운 초과: {drawdown_percent:.2f}% > {self.max_drawdown*100:.2f}%")
                
                # 리스크 이벤트 발행
                await self.publish_risk_event('MAX_DRAWDOWN_EXCEEDED', {
                    'drawdown': drawdown,
                    'drawdown_percent': drawdown_percent,
                    'current_balance': current_balance,
                    'peak_balance': self.peak_balance,
                    'max_drawdown': self.max_drawdown
                })
                
                # 킬 스위치 활성화
                self.kill_switch_active = True
                return False
            
            # 경고 임계값 검사 (80% 수준에서 경고)
            warning_threshold = self.max_drawdown * 0.8
            if drawdown > warning_threshold:
                logger.warning(f"드로다운 경고 임계값 접근: {drawdown_percent:.2f}% (최대 허용의 {(drawdown/self.max_drawdown)*100:.1f}%)")
                
                # 경고 알림 전송
                await self._send_alert(
                    "드로다운 경고", 
                    f"현재 드로다운이 {drawdown_percent:.2f}%로 최대 허용치({self.max_drawdown*100:.2f}%)의 {(drawdown/self.max_drawdown)*100:.1f}% 수준에 도달했습니다."
                )
        
        return True
        
    async def _record_drawdown_history(self, drawdown: float):
        """드로다운 이력 기록"""
        try:
            # Redis에 드로다운 이력 기록
            if self.redis_client:
                key = f"drawdown:history:{datetime.now().strftime('%Y-%m-%d')}"
                await self.redis_client.lpush(key, json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'drawdown': drawdown,
                    'current_balance': self.current_balance,
                    'peak_balance': self.peak_balance
                }))
                
                # 기록 유지 기간 설정 (30일)
                await self.redis_client.expire(key, 60 * 60 * 24 * 30)
        except Exception as e:
            logger.error(f"드로다운 이력 기록 실패: {e}")
        
        # 드로다운 계산
        if self.peak_balance > 0:
            drawdown = 1 - (current_balance / self.peak_balance)
            
            # 최대 드로다운 초과 검사
            if drawdown > self.max_drawdown:
                logger.warning(f"최대 드로다운 초과: {drawdown:.4f} > {self.max_drawdown:.4f}")
                
                # 리스크 이벤트 발행
                await self.publish_risk_event('MAX_DRAWDOWN_EXCEEDED', {
                    'drawdown': drawdown,
                    'current_balance': current_balance,
                    'peak_balance': self.peak_balance
                })
                
                return False
        
        return True
    
    async def check_global_drawdown(self) -> bool:
        """
        글로벌 드로다운 검사
        
        Returns:
            bool: 드로다운 제한 내이면 True, 초과하면 False
        """
        if self.kill_switch_active:
            logger.warning("킬 스위치가 활성화되어 있어 거래가 중지됩니다")
            return False
        
        if self.circuit_breaker_active:
            logger.warning("서킷 브레이커가 활성화되어 있어 거래가 중지됩니다")
            return False
        
        if self.peak_balance > 0:
            drawdown = 1 - (self.current_balance / self.peak_balance)
            if drawdown > self.max_drawdown:
                logger.warning(f"최대 드로다운 초과: {drawdown:.4f} > {self.max_drawdown:.4f}")
                return False
        
        return True
    
    async def check_circuit_breaker(self, price_change: float) -> bool:
        """
        서킷 브레이커 검사
        
        Args:
            price_change: 가격 변동 비율 (소수점)
            
        Returns:
            bool: 서킷 브레이커 발동되지 않으면 True, 발동되면 False
        """
        if abs(price_change) > self.circuit_breaker:
            logger.warning(f"서킷 브레이커 발동: 가격 변동 {price_change:.4f} > {self.circuit_breaker:.4f}")
            
            # 리스크 이벤트 발행
            await self.publish_risk_event('CIRCUIT_BREAKER_TRIGGERED', {
                'price_change': price_change,
                'threshold': self.circuit_breaker,
                'recovery_time': 3600  # 1시간 후 재설정
            })
            
            self.circuit_breaker_active = True
            return False
        
        return True
    
    async def check_daily_trade_limit(self, pair: str) -> bool:
        """
        일일 거래 제한 검사
        
        Args:
            pair: 거래 페어
            
        Returns:
            bool: 거래 제한 내이면 True, 초과하면 False
        """
        today = date.today().isoformat()
        
        # 오늘 거래 수 가져오기
        if today not in self.daily_trades:
            self.daily_trades = {today: 0}  # 새 날짜로 초기화
        
        # 거래 제한 검사
        if self.daily_trades[today] >= self.daily_trade_limit:
            logger.warning(f"일일 거래 제한 초과: {self.daily_trades[today]} >= {self.daily_trade_limit}")
            
            # 리스크 이벤트 발행
            await self.publish_risk_event('DAILY_TRADE_LIMIT_REACHED', {
                'trade_count': self.daily_trades[today],
                'limit': self.daily_trade_limit,
                'date': today
            })
            
            return False
        
        return True
    
    async def increment_daily_trade_count(self, pair: str):
        """
        일일 거래 수 증가
        
        Args:
            pair: 거래 페어
        """
        today = date.today().isoformat()
        
        # 오늘 거래 수 가져오기
        if today not in self.daily_trades:
            self.daily_trades = {today: 0}  # 새 날짜로 초기화
        
        # 거래 수 증가
        self.daily_trades[today] += 1
        logger.info(f"일일 거래 수 증가: {pair}, 오늘 총 {self.daily_trades[today]} 건")
    
    async def calculate_position_size(self, account_balance: float, pair: str, entry_price: float) -> float:
        """
        포지션 크기 계산 (RISK_FIXED 모드)
        
        Args:
            account_balance: 계정 잔액
            pair: 거래 페어
            entry_price: 진입 가격
            
        Returns:
            float: 포지션 크기 (수량)
        """
        # 리스크 금액 계산 (계정 잔액의 2%)
        risk_amount = account_balance * self.risk_per_trade
        
        # 손절 가격 계산 (진입 가격의 3.5% 하락)
        stop_loss_price = entry_price * (1 - self.per_trade_stop_loss)
        
        # 손실 금액 계산
        price_difference = entry_price - stop_loss_price
        
        # 포지션 크기 계산
        if price_difference > 0:
            position_size = risk_amount / price_difference
        else:
            position_size = 0
            logger.warning(f"포지션 크기 계산 오류: 가격 차이가 0 이하입니다 ({price_difference})")
        
        logger.info(f"포지션 크기 계산: {pair}, 잔액={account_balance}, 리스크={risk_amount}, "
                   f"진입가={entry_price}, 손절가={stop_loss_price}, 포지션={position_size}")
        
        return position_size
    
    async def calculate_position_size(self, pair: str, price: float, risk_level: str = 'normal') -> float:
        """
        적절한 포지션 크기 계산
        
        Args:
            pair: 거래 페어
            price: 현재 가격
            risk_level: 리스크 레벨 ('low', 'normal', 'high')
            
        Returns:
            float: 계산된 포지션 크기 (거래량)
        """
        try:
            # 리스크 레벨에 따른 조정 계수
            risk_multipliers = {
                'low': 0.5,      # 리스크 레벨 낮음: 기본 리스크의 50%
                'normal': 1.0,   # 리스크 레벨 보통: 기본 리스크 적용
                'high': 1.5      # 리스크 레벨 높음: 기본 리스크의 150%
            }
            
            # 기본 리스크 레벨이 없으면 'normal' 사용
            multiplier = risk_multipliers.get(risk_level, 1.0)
            
            # 현재 잔액
            balance = self.current_balance
            
            # 잔액이 없으면 기본값 사용
            if balance <= 0:
                logger.warning(f"잔액이 없어 포지션 크기 계산 불가능: {balance}")
                return 0.0
            
            # Kelly Criterion 기반 포지션 크기 계산
            # Kelly = W - (1-W)/R where W is win rate and R is win/loss ratio
            
            # 전략별 승률 및 손익비 가져오기
            strategy = self.risk_config.get('strategy_stats', {}).get(pair, {
                'win_rate': 0.55,         # 기본 승률 55%
                'win_loss_ratio': 1.5,    # 기본 손익비 1.5
                'avg_profit': 0.03,       # 평균 이익 3%
                'avg_loss': 0.02,         # 평균 손실 2%
                'max_position_size': 0.1  # 최대 포지션 크기 (잔액의 10%)
            })
            
            win_rate = strategy.get('win_rate', 0.55)
            win_loss_ratio = strategy.get('win_loss_ratio', 1.5)
            max_position_size = strategy.get('max_position_size', 0.1)
            
            # Kelly 계수 계산
            kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
            
            # Kelly가 음수면 거래하지 않음
            if kelly <= 0:
                logger.warning(f"Kelly 계수가 음수여서 거래 불가: {kelly}")
                return 0.0
            
            # Kelly는 일반적으로 너무 공격적이므로 절반만 사용 (Half Kelly)
            kelly = kelly * 0.5
            
            # 리스크 레벨에 따라 조정
            adjusted_kelly = kelly * multiplier
            
            # 전체 잔액에 대한 비율로 계산
            position_size_ratio = min(adjusted_kelly, max_position_size)
            
            # 실제 포지션 크기 계산 (가격 고려)
            position_size_in_base = balance * position_size_ratio
            position_size = position_size_in_base / price
            
            # 최소 거래량 적용
            min_trade_amount = self.risk_config.get('min_trade_amount', {}).get(pair, 0.001)
            if position_size < min_trade_amount:
                position_size = min_trade_amount
            
            # 최대 거래량 적용
            max_trade_amount = self.risk_config.get('max_trade_amount', {}).get(pair, float('inf'))
            if position_size > max_trade_amount:
                position_size = max_trade_amount
            
            logger.info(f"포지션 크기 계산: {pair}, 가격={price}, 리스크 레벨={risk_level}, 계산량={position_size:.6f}")
            return position_size
            
        except Exception as e:
            logger.error(f"포지션 크기 계산 오류: {e}")
            return 0.0
    
    async def check_trade_allowed(self, pair: str, side: str, amount: float, price: Optional[float] = None) -> bool:
        """
        거래 허용 여부 검사
        
        Args:
            pair: 거래 페어
            side: 매수/매도
            amount: 거래량
            price: 가격 (선택 사항)
            
        Returns:
            bool: 거래 허용되면 True, 그렇지 않으면 False
        """
        # 킬 스위치 검사
        if self.kill_switch_active:
            logger.warning(f"거래 거부됨 (킬 스위치 활성화): {pair} {side} {amount}")
            return False
        
        # 서킷 브레이커 검사
        if self.circuit_breaker_active:
            logger.warning(f"거래 거부됨 (서킷 브레이커 활성화): {pair} {side} {amount}")
            return False
        
        # 글로벌 드로다운 검사
        if not await self.check_global_drawdown():
            logger.warning(f"거래 거부됨 (글로벌 드로다운 초과): {pair} {side} {amount}")
            return False
        
        # 일일 거래 제한 검사
        if not await self.check_daily_trade_limit(pair):
            logger.warning(f"거래 거부됨 (일일 거래 제한 초과): {pair} {side} {amount}")
            return False
        
        # 거래별 손절 및 이익 실현 로직
        if side == 'sell' and price is not None:
            # 현재 포지션 정보 가져오기
            position = await self.get_position(pair)
            if position and position['amount'] > 0:
                # 평균 매수가 가져오기
                avg_buy_price = position['avg_price']
                
                if avg_buy_price > 0:
                    # 현재 손익 계산
                    profit_percent = (price / avg_buy_price - 1) * 100
                    
                    # 손절 검사
                    stop_loss_threshold = -self.per_trade_stop_loss * 100
                    if profit_percent < stop_loss_threshold:
                        logger.warning(f"손절 발동: {pair}, 손익률: {profit_percent:.2f}%, 임계값: {stop_loss_threshold:.2f}%")
                        
                        # 손절 이벤트 발행
                        await self.publish_risk_event('STOP_LOSS_TRIGGERED', {
                            'pair': pair,
                            'profit_percent': profit_percent,
                            'threshold': stop_loss_threshold,
                            'avg_buy_price': avg_buy_price,
                            'current_price': price
                        })
                        
                        # 손절 알림 전송
                        await self._send_alert(
                            f"{pair} 손절 발동",
                            f"현재 손익률: {profit_percent:.2f}%, 임계값: {stop_loss_threshold:.2f}%"
                        )
                        
                        # 손절 발동 시 자동 전체 매도 실행 여부 검사
                        if self.risk_config.get('auto_stop_loss', True):
                            logger.info(f"자동 손절 매도 허용: {pair}")
                            return True
                        else:
                            logger.info(f"자동 손절 비활성화됨, 수동 매도 필요: {pair}")
                    
                    # 이익 실현 검사
                    take_profit_levels = self.risk_config.get('take_profit_levels', [
                        {'threshold': 3.0, 'percentage': 0.25},  # 3% 이익 시 25% 매도
                        {'threshold': 5.0, 'percentage': 0.5},   # 5% 이익 시 50% 매도
                        {'threshold': 10.0, 'percentage': 0.75},  # 10% 이익 시 75% 매도
                        {'threshold': 15.0, 'percentage': 1.0}    # 15% 이익 시 전체 매도
                    ])
                    
                    # 이익 실현 검사
                    for level in take_profit_levels:
                        if profit_percent >= level['threshold']:
                            suggested_amount = position['amount'] * level['percentage']
                            
                            # 이익 실현 이벤트 발행
                            await self.publish_risk_event('TAKE_PROFIT_TRIGGERED', {
                                'pair': pair,
                                'profit_percent': profit_percent,
                                'threshold': level['threshold'],
                                'suggested_percentage': level['percentage'],
                                'suggested_amount': suggested_amount,
                                'avg_buy_price': avg_buy_price,
                                'current_price': price
                            })
                            
                            # 이익 실현 알림 전송
                            await self._send_alert(
                                f"{pair} 이익 실현 기회",
                                f"현재 이익률: {profit_percent:.2f}%, 임계값: {level['threshold']:.2f}%, 제안 매도량: {level['percentage']*100:.0f}%"
                            )
                            
                            # 자동 이익 실현 여부 검사
                            if self.risk_config.get('auto_take_profit', False):
                                # 수량 조정 (제안된 비율로 매도)
                                if amount > suggested_amount:
                                    logger.info(f"자동 이익 실현: {pair}, 수량 조정 {amount} -> {suggested_amount}")
                                    # 여기서는 수량을 조정하지 않고 허용만 함
                                    # 실제 수량 조정은 실행 엔진에서 처리해야 함
                            break  # 가장 높은 임계값만 처리
        
        # 모든 검사 통과
        logger.info(f"거래 허용됨: {pair} {side} {amount}")
        return True
    
    async def get_position(self, pair: str) -> Optional[Dict[str, float]]:
        """
        특정 페어의 포지션 정보 가져오기
        
        Args:
            pair: 거래 페어
            
        Returns:
            Optional[Dict[str, float]]: 포지션 정보 (수량, 평균가) 또는 None
        """
        try:
            # Redis에서 포지션 정보 가져오기
            if self.redis_client:
                position_key = f"position:{pair}"
                position_data = await self.redis_client.get(position_key)
                
                if position_data:
                    position = json.loads(position_data)
                    return position
            
            # 데이터베이스에서 평균 매수가 가져오기
            if self.db_manager:
                with self.db_manager.get_pg_session() as session:
                    # 심볼 포맷 변환 (BTC/USDT -> BTCUSDT)
                    symbol = pair.replace('/', '')
                    
                    # 매수 주문만 조회 (체결된 주문)
                    from src.database.models import Order, OrderStatus, OrderSide
                    from sqlalchemy import and_, func
                    
                    buy_orders = session.query(Order).filter(
                        and_(
                            Order.symbol == symbol,
                            Order.side == OrderSide.BUY,
                            Order.status == OrderStatus.FILLED,
                            Order.filled_quantity > 0
                        )
                    ).all()
                    
                    sell_orders = session.query(Order).filter(
                        and_(
                            Order.symbol == symbol,
                            Order.side == OrderSide.SELL,
                            Order.status == OrderStatus.FILLED,
                            Order.filled_quantity > 0
                        )
                    ).all()
                    
                    # 총 매수량과 총 비용 계산
                    total_buy_quantity = sum(order.filled_quantity or 0 for order in buy_orders)
                    total_buy_cost = sum((order.filled_quantity or 0) * (order.average_price or 0) for order in buy_orders)
                    
                    # 총 매도량 계산
                    total_sell_quantity = sum(order.filled_quantity or 0 for order in sell_orders)
                    
                    # 현재 포지션 계산
                    current_amount = total_buy_quantity - total_sell_quantity
                    
                    if current_amount > 0 and total_buy_cost > 0:
                        avg_price = total_buy_cost / total_buy_quantity
                        position = {
                            'amount': current_amount,
                            'avg_price': avg_price
                        }
                        
                        # Redis에 캐싱
                        if self.redis_client:
                            await self.redis_client.set(
                                position_key,
                                json.dumps(position),
                                ex=60 * 60  # 1시간 동안 캐싱
                            )
                        
                        return position
            
            return None
        except Exception as e:
            logger.error(f"포지션 정보 조회 실패: {e}")
            return None
    
    async def update_position(self, pair: str, amount: float, price: float) -> None:
        """
        포지션 업데이트
        
        Args:
            pair: 거래 페어
            amount: 거래량 (매수는 양수, 매도는 음수)
            price: 거래 가격
        """
        try:
            # 현재 포지션 가져오기
            position = await self.get_position(pair) or {'amount': 0, 'avg_price': 0}
            
            # 포지션 업데이트
            if amount > 0:  # 매수
                new_amount = position['amount'] + amount
                new_avg_price = ((position['amount'] * position['avg_price']) + (amount * price)) / new_amount
                position = {
                    'amount': new_amount,
                    'avg_price': new_avg_price
                }
            else:  # 매도
                new_amount = position['amount'] + amount  # amount는 음수
                if new_amount <= 0:
                    position = {'amount': 0, 'avg_price': 0}
                else:
                    position['amount'] = new_amount
            
            # Redis에 저장
            if self.redis_client:
                position_key = f"position:{pair}"
                await self.redis_client.set(
                    position_key,
                    json.dumps(position),
                    ex=60 * 60  # 1시간 동안 캐싱
                )
            
            logger.info(f"포지션 업데이트: {pair}, 수량={position['amount']:.6f}, 평균가={position['avg_price']:.2f}")
        except Exception as e:
            logger.error(f"포지션 업데이트 실패: {e}")
    
    async def activate_kill_switch(self, reason: str = "수동 활성화"):
        """
        킬 스위치 활성화
        
        Args:
            reason: 활성화 이유
        """
        self.kill_switch_active = True
        logger.warning(f"킬 스위치 활성화됨: {reason}")
        
        # 리스크 이벤트 발행
        await self.publish_risk_event('KILL_SWITCH_ACTIVATED', {
            'reason': reason,
            'activated_by': 'manual',
            'timestamp': datetime.now().isoformat()
        })
        
        # 알림 전송
        await self._send_alert("킬 스위치 활성화", f"사유: {reason}")
    
    async def deactivate_kill_switch(self, reason: str = "수동 비활성화"):
        """
        킬 스위치 비활성화
        
        Args:
            reason: 비활성화 이유
        """
        self.kill_switch_active = False
        logger.info(f"킬 스위치 비활성화됨: {reason}")
        
        # 리스크 이벤트 발행
        await self.publish_risk_event('KILL_SWITCH_DEACTIVATED', {
            'reason': reason,
            'deactivated_by': 'manual',
            'timestamp': datetime.now().isoformat()
        })
        
        # 알림 전송
        await self._send_alert("킬 스위치 비활성화", f"사유: {reason}")
    
    async def close(self):
        """리소스 정리"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 연결 종료됨")


# 싱글톤 인스턴스
_risk_manager = None

async def init_risk_manager(config: Dict[str, Any]) -> RiskManager:
    """
    리스크 관리자 초기화
    
    Args:
        config: 리스크 관리 설정
        
    Returns:
        RiskManager: 리스크 관리자 인스턴스
    """
    global _risk_manager
    
    if _risk_manager is None:
        _risk_manager = RiskManager(config)
        
        # Redis 연결 설정
        await _risk_manager.connect_redis()
    
    return _risk_manager

def get_risk_manager() -> Optional[RiskManager]:
    """
    리스크 관리자 가져오기
    
    Returns:
        Optional[RiskManager]: 리스크 관리자 인스턴스
    """
    global _risk_manager
    
    if _risk_manager is None:
        logger.warning("리스크 관리자가 초기화되지 않았습니다. init_risk_manager()를 먼저 호출하세요.")
    
    return _risk_manager
