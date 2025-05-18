"""
Binance WebSocket 연결 관리자

이 모듈은 Binance WebSocket 연결을 관리하고 실시간 데이터 스트리밍을 처리합니다.
복원력 있는 연결 관리, 재연결 로직, 속도 제한 모니터링 등을 제공합니다.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
import aiohttp
from datetime import datetime, timedelta

from src.utils.error_handler import CircuitBreaker, RetryWithBackoff

# 로깅 설정
logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Binance WebSocket 연결 관리자
    
    이 클래스는 Binance WebSocket 연결을 관리하고 실시간 데이터 스트리밍을 처리합니다.
    복원력 있는 연결 관리, 재연결 로직, 속도 제한 모니터링 등을 제공합니다.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        WebSocket 관리자 초기화
        
        Args:
            session: aiohttp 클라이언트 세션 (기본값: None, 내부적으로 생성)
        """
        # HTTP 세션
        self.session = session
        self.own_session = session is None
        
        # WebSocket 연결 목록
        self.connections: Dict[str, aiohttp.ClientWebSocketResponse] = {}
        
        # 연결 상태 추적
        self.connection_status: Dict[str, Dict[str, Any]] = {}
        
        # 속도 제한 모니터링
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        
        # 회로 차단기 (연결 실패 시 일시적으로 연결 중단)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # 재시도 로직
        self.retry_handler = RetryWithBackoff(
            max_retries=5,
            base_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0
        )
        
        # 작업 중단 플래그
        self.is_running = False
        
        # 연결 상태 모니터링 작업
        self.monitor_task = None
        
        # 메시지 핸들러
        self.message_handlers: Dict[str, Callable] = {}
    
    async def start(self):
        """
        WebSocket 관리자 시작
        """
        if self.is_running:
            logger.warning("WebSocket 관리자가 이미 실행 중입니다.")
            return
        
        self.is_running = True
        
        # 세션이 없는 경우 생성
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self.own_session = True
        
        # 연결 상태 모니터링 작업 시작
        self.monitor_task = asyncio.create_task(self._monitor_connections())
        
        logger.info("WebSocket 관리자 시작됨")
    
    async def stop(self):
        """
        WebSocket 관리자 중지
        """
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 모니터링 작업 취소
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # 모든 WebSocket 연결 닫기
        for stream_id, ws in list(self.connections.items()):
            if not ws.closed:
                await ws.close()
        
        self.connections.clear()
        self.connection_status.clear()
        
        # 자체 생성한 세션인 경우 닫기
        if self.own_session and self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        
        logger.info("WebSocket 관리자 중지됨")
    
    async def connect(self, stream_id: str, url: str, message_handler: Callable):
        """
        WebSocket 연결 생성
        
        Args:
            stream_id: 스트림 식별자 (예: 'btcusdt_5m')
            url: WebSocket URL
            message_handler: 메시지 처리 콜백 함수
        
        Returns:
            bool: 연결 성공 여부
        """
        # 회로 차단기 확인
        if stream_id in self.circuit_breakers and not self.circuit_breakers[stream_id].allow_request():
            logger.warning(f"회로 차단기 활성화됨: {stream_id}, 연결 시도 중단")
            return False
        
        # 이미 연결된 경우 닫기
        if stream_id in self.connections and not self.connections[stream_id].closed:
            await self.connections[stream_id].close()
        
        # 메시지 핸들러 등록
        self.message_handlers[stream_id] = message_handler
        
        # 연결 상태 초기화
        self.connection_status[stream_id] = {
            'url': url,
            'connected': False,
            'last_message_time': None,
            'connect_time': None,
            'disconnect_time': None,
            'reconnect_count': 0,
            'error_count': 0,
            'last_error': None
        }
        
        # 회로 차단기 초기화
        if stream_id not in self.circuit_breakers:
            self.circuit_breakers[stream_id] = CircuitBreaker(
                failure_threshold=3,
                reset_timeout=60.0
            )
        
        try:
            # WebSocket 연결
            ws = await self.session.ws_connect(url, heartbeat=30)
            
            # 연결 상태 업데이트
            self.connections[stream_id] = ws
            self.connection_status[stream_id]['connected'] = True
            self.connection_status[stream_id]['connect_time'] = time.time()
            
            # 메시지 처리 작업 시작
            asyncio.create_task(self._process_messages(stream_id, ws))
            
            # 회로 차단기 성공 기록
            self.circuit_breakers[stream_id].record_success()
            
            logger.info(f"WebSocket 연결 성공: {stream_id} - {url}")
            return True
        except Exception as e:
            # 연결 상태 업데이트
            self.connection_status[stream_id]['connected'] = False
            self.connection_status[stream_id]['error_count'] += 1
            self.connection_status[stream_id]['last_error'] = str(e)
            
            # 회로 차단기 실패 기록
            self.circuit_breakers[stream_id].record_failure()
            
            logger.error(f"WebSocket 연결 실패: {stream_id} - {url} - {e}")
            return False
    
    async def reconnect(self, stream_id: str):
        """
        WebSocket 재연결
        
        Args:
            stream_id: 스트림 식별자 (예: 'btcusdt_5m')
        
        Returns:
            bool: 재연결 성공 여부
        """
        if stream_id not in self.connection_status:
            logger.error(f"알 수 없는 스트림 ID: {stream_id}")
            return False
        
        # 회로 차단기 확인
        if not self.circuit_breakers[stream_id].allow_request():
            logger.warning(f"회로 차단기 활성화됨: {stream_id}, 재연결 시도 중단")
            return False
        
        # 재연결 횟수 증가
        self.connection_status[stream_id]['reconnect_count'] += 1
        
        # 재시도 지연 시간 계산
        retry_attempt = self.connection_status[stream_id]['reconnect_count']
        delay = self.retry_handler.get_delay(retry_attempt)
        
        logger.info(f"WebSocket 재연결 대기 중: {stream_id}, 시도 {retry_attempt}, 대기 시간 {delay}초")
        await asyncio.sleep(delay)
        
        # 재연결 시도
        url = self.connection_status[stream_id]['url']
        message_handler = self.message_handlers[stream_id]
        
        return await self.connect(stream_id, url, message_handler)
    
    async def _process_messages(self, stream_id: str, ws: aiohttp.ClientWebSocketResponse):
        """
        WebSocket 메시지 처리
        
        Args:
            stream_id: 스트림 식별자 (예: 'btcusdt_5m')
            ws: WebSocket 연결
        """
        try:
            async for msg in ws:
                if not self.is_running:
                    break
                
                # 메시지 타입에 따른 처리
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # 메시지 수신 시간 업데이트
                    self.connection_status[stream_id]['last_message_time'] = time.time()
                    
                    # 속도 제한 모니터링
                    self._update_rate_limit(stream_id)
                    
                    try:
                        # JSON 파싱
                        data = json.loads(msg.data)
                        
                        # 메시지 핸들러 호출
                        if stream_id in self.message_handlers:
                            await self.message_handlers[stream_id](data)
                    except json.JSONDecodeError as e:
                        logger.error(f"WebSocket 메시지 파싱 오류: {stream_id} - {e}")
                    except Exception as e:
                        logger.error(f"WebSocket 메시지 처리 중 오류 발생: {stream_id} - {e}")
                
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning(f"WebSocket 연결 닫힘: {stream_id}")
                    break
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket 오류: {stream_id} - {ws.exception()}")
                    
                    # 연결 상태 업데이트
                    self.connection_status[stream_id]['error_count'] += 1
                    self.connection_status[stream_id]['last_error'] = str(ws.exception())
                    
                    # 회로 차단기 실패 기록
                    self.circuit_breakers[stream_id].record_failure()
                    
                    break
        except asyncio.CancelledError:
            logger.info(f"WebSocket 메시지 처리 작업 취소됨: {stream_id}")
        except Exception as e:
            logger.error(f"WebSocket 메시지 처리 중 예외 발생: {stream_id} - {e}")
            
            # 연결 상태 업데이트
            self.connection_status[stream_id]['error_count'] += 1
            self.connection_status[stream_id]['last_error'] = str(e)
            
            # 회로 차단기 실패 기록
            self.circuit_breakers[stream_id].record_failure()
        finally:
            # 연결 상태 업데이트
            self.connection_status[stream_id]['connected'] = False
            self.connection_status[stream_id]['disconnect_time'] = time.time()
            
            # 연결이 끊어진 경우 재연결 시도
            if self.is_running:
                asyncio.create_task(self.reconnect(stream_id))
    
    async def _monitor_connections(self):
        """
        WebSocket 연결 상태 모니터링
        """
        try:
            while self.is_running:
                # 30초마다 연결 상태 확인
                await asyncio.sleep(30)
                
                now = time.time()
                
                for stream_id, status in list(self.connection_status.items()):
                    # 연결이 끊어진 경우 무시
                    if not status['connected']:
                        continue
                    
                    # 마지막 메시지 수신 시간 확인
                    last_message_time = status.get('last_message_time')
                    
                    # 5분 이상 메시지가 없는 경우 연결 재설정
                    if last_message_time and (now - last_message_time) > 300:
                        logger.warning(f"WebSocket 연결 타임아웃: {stream_id}, 마지막 메시지 {now - last_message_time:.1f}초 전")
                        
                        # 연결 닫기
                        if stream_id in self.connections and not self.connections[stream_id].closed:
                            await self.connections[stream_id].close()
                        
                        # 연결 상태 업데이트
                        status['connected'] = False
                        status['disconnect_time'] = now
                        
                        # 재연결 시도
                        asyncio.create_task(self.reconnect(stream_id))
        except asyncio.CancelledError:
            logger.info("WebSocket 연결 모니터링 작업 취소됨")
        except Exception as e:
            logger.error(f"WebSocket 연결 모니터링 중 오류 발생: {e}")
    
    def _update_rate_limit(self, stream_id: str):
        """
        속도 제한 모니터링 업데이트
        
        Args:
            stream_id: 스트림 식별자 (예: 'btcusdt_5m')
        """
        now = time.time()
        
        if stream_id not in self.rate_limits:
            self.rate_limits[stream_id] = {
                'count': 0,
                'window_start': now,
                'max_rate': 0
            }
        
        # 메시지 수 증가
        self.rate_limits[stream_id]['count'] += 1
        
        # 1분 간격으로 속도 계산
        window_duration = now - self.rate_limits[stream_id]['window_start']
        
        if window_duration >= 60:
            # 분당 메시지 수 계산
            rate = self.rate_limits[stream_id]['count'] / (window_duration / 60)
            
            # 최대 속도 업데이트
            if rate > self.rate_limits[stream_id]['max_rate']:
                self.rate_limits[stream_id]['max_rate'] = rate
            
            # 속도 제한 초기화
            self.rate_limits[stream_id]['count'] = 0
            self.rate_limits[stream_id]['window_start'] = now
            
            logger.debug(f"WebSocket 속도 제한: {stream_id} - {rate:.1f} 메시지/분 (최대: {self.rate_limits[stream_id]['max_rate']:.1f})")
    
    async def subscribe_kline(self, symbol: str, interval: str, stream_name: str):
        """
        캔들 스틱 데이터 구독
        
        Args:
            symbol: 심볼 (예: btcusdt)
            interval: 타임프레임 (예: 5m)
            stream_name: 스트림 이름
        
        Returns:
            bool: 구독 성공 여부
        """
        # Binance WebSocket URL 생성
        url = f"wss://stream.binance.com:9443/ws/{symbol}@kline_{interval}"
        
        # 메시지 핸들러 (stream_name을 사용하여 메시지 핸들러 호출)
        async def message_handler(data):
            if 'kline' in self.message_handlers:
                await self.message_handlers['kline'](data)
        
        # WebSocket 연결
        return await self.connect(stream_name, url, message_handler)
