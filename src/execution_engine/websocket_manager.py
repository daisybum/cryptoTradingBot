"""
WebSocket 관리자 모듈

이 모듈은 Binance WebSocket 연결을 관리하고 실시간 주문 상태 업데이트를 처리합니다.
사용자 데이터 스트림을 구독하여 주문 체결, 취소 등의 이벤트를 실시간으로 추적합니다.
"""

import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable, Coroutine
import threading
import queue
from datetime import datetime, timedelta

# python-binance 라이브러리 임포트
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.exceptions import BinanceAPIException, BinanceRequestException

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Binance WebSocket 관리자 클래스"""
    
    def __init__(self, api_key: str, api_secret: str, is_testnet: bool = False):
        """
        WebSocket 관리자 초기화
        
        Args:
            api_key: Binance API 키
            api_secret: Binance API 시크릿
            is_testnet: 테스트넷 사용 여부
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_testnet = is_testnet
        
        # Binance 클라이언트 초기화
        self.client = Client(api_key, api_secret, testnet=is_testnet)
        
        # WebSocket 관련 변수
        self.bsm = None  # BinanceSocketManager
        self.user_socket = None  # 사용자 데이터 스트림 소켓
        self.conn_key = None  # 연결 키
        self.listen_key = None  # 리슨 키
        
        # 메시지 처리 콜백
        self.callbacks = {
            'executionReport': [],  # 주문 실행 보고서 콜백
            'outboundAccountPosition': [],  # 계정 포지션 업데이트 콜백
            'balanceUpdate': [],  # 잔액 업데이트 콜백
            'listStatus': []  # OCO 주문 상태 콜백
        }
        
        # 재연결 설정
        self.reconnect_count = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # 초
        
        # 메시지 큐 (스레드 간 통신용)
        self.message_queue = queue.Queue()
        
        # 상태 변수
        self.running = False
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # 초
        
        logger.info("WebSocket 관리자 초기화됨")
    
    async def start(self):
        """WebSocket 연결 시작"""
        if self.running:
            logger.warning("WebSocket 관리자가 이미 실행 중입니다")
            return
        
        self.running = True
        
        try:
            # 리슨 키 가져오기
            self.listen_key = self.client.stream_get_listen_key()
            logger.info(f"리슨 키 획득: {self.listen_key[:10]}...")
            
            # 리슨 키 갱신 태스크 시작
            asyncio.create_task(self._keep_listen_key_alive())
            
            # WebSocket 연결 시작
            self.bsm = BinanceSocketManager(self.client)
            self.conn_key = self.bsm.start_user_socket(self._process_user_socket_message)
            self.bsm.start()
            
            logger.info("WebSocket 연결 시작됨")
            
            # 메시지 처리 태스크 시작
            asyncio.create_task(self._process_message_queue())
            
            # 연결 모니터링 태스크 시작
            asyncio.create_task(self._monitor_connection())
            
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"WebSocket 연결 시작 실패: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """WebSocket 연결 중지"""
        if not self.running:
            logger.warning("WebSocket 관리자가 이미 중지되었습니다")
            return
        
        self.running = False
        
        try:
            # WebSocket 연결 종료
            if self.bsm and self.conn_key:
                self.bsm.stop_socket(self.conn_key)
                self.bsm.close()
                self.bsm = None
                self.conn_key = None
            
            # 리슨 키 해제
            if self.listen_key:
                self.client.stream_close(self.listen_key)
                self.listen_key = None
            
            logger.info("WebSocket 연결 중지됨")
            
        except Exception as e:
            logger.error(f"WebSocket 연결 중지 중 오류 발생: {e}")
    
    def register_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """
        이벤트 콜백 등록
        
        Args:
            event_type: 이벤트 유형 (executionReport, outboundAccountPosition, balanceUpdate, listStatus)
            callback: 콜백 함수
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"{event_type} 이벤트에 콜백 등록됨")
        else:
            logger.warning(f"알 수 없는 이벤트 유형: {event_type}")
    
    def _process_user_socket_message(self, msg: Dict[str, Any]):
        """
        사용자 소켓 메시지 처리 (WebSocket 스레드에서 호출)
        
        Args:
            msg: WebSocket 메시지
        """
        # 메시지를 큐에 추가 (스레드 안전)
        self.message_queue.put(msg)
    
    async def _process_message_queue(self):
        """메시지 큐 처리 (비동기 태스크)"""
        logger.info("메시지 큐 처리 시작됨")
        
        while self.running:
            try:
                # 큐에서 메시지 가져오기 (비차단)
                try:
                    msg = self.message_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                # 하트비트 메시지 처리
                if 'e' not in msg:
                    if 'error' in msg:
                        logger.error(f"WebSocket 오류: {msg['error']}")
                        await self._handle_connection_error()
                    self.message_queue.task_done()
                    continue
                
                # 이벤트 유형 확인
                event_type = msg['e']
                self.last_heartbeat = time.time()
                
                # 이벤트 유형에 따라 콜백 호출
                if event_type in self.callbacks:
                    for callback in self.callbacks[event_type]:
                        try:
                            callback(msg)
                        except Exception as e:
                            logger.exception(f"{event_type} 콜백 실행 중 오류 발생: {e}")
                
                # 특정 이벤트 유형에 따른 추가 처리
                if event_type == 'executionReport':
                    await self._handle_execution_report(msg)
                elif event_type == 'outboundAccountPosition':
                    await self._handle_account_position(msg)
                
                # 메시지 처리 완료 표시
                self.message_queue.task_done()
                
            except Exception as e:
                logger.exception(f"메시지 큐 처리 중 오류 발생: {e}")
                await asyncio.sleep(1)
    
    async def _keep_listen_key_alive(self):
        """리슨 키 갱신 (비동기 태스크)"""
        logger.info("리슨 키 갱신 태스크 시작됨")
        
        while self.running and self.listen_key:
            try:
                # 30분마다 리슨 키 갱신 (Binance 요구사항)
                await asyncio.sleep(60 * 30)
                
                if self.running and self.listen_key:
                    self.client.stream_keepalive(self.listen_key)
                    logger.info(f"리슨 키 갱신됨: {self.listen_key[:10]}...")
                
            except Exception as e:
                logger.error(f"리슨 키 갱신 중 오류 발생: {e}")
                await asyncio.sleep(5)  # 오류 발생 시 잠시 대기
    
    async def _monitor_connection(self):
        """연결 모니터링 (비동기 태스크)"""
        logger.info("WebSocket 연결 모니터링 시작됨")
        
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # 하트비트 체크
                if time.time() - self.last_heartbeat > self.heartbeat_interval * 2:
                    logger.warning(f"WebSocket 하트비트 누락: {time.time() - self.last_heartbeat:.1f}초 경과")
                    await self._handle_connection_error()
                
            except Exception as e:
                logger.exception(f"연결 모니터링 중 오류 발생: {e}")
                await asyncio.sleep(5)
    
    async def _handle_connection_error(self):
        """연결 오류 처리"""
        if not self.running:
            return
        
        self.reconnect_count += 1
        
        if self.reconnect_count > self.max_reconnect_attempts:
            logger.error(f"최대 재연결 시도 횟수({self.max_reconnect_attempts})를 초과했습니다")
            await self.stop()
            return
        
        logger.warning(f"WebSocket 재연결 시도 중... ({self.reconnect_count}/{self.max_reconnect_attempts})")
        
        # 기존 연결 종료
        if self.bsm and self.conn_key:
            try:
                self.bsm.stop_socket(self.conn_key)
            except:
                pass
        
        # 재연결 지연
        await asyncio.sleep(self.reconnect_delay * self.reconnect_count)
        
        try:
            # 리슨 키 갱신
            self.listen_key = self.client.stream_get_listen_key()
            
            # WebSocket 재연결
            self.bsm = BinanceSocketManager(self.client)
            self.conn_key = self.bsm.start_user_socket(self._process_user_socket_message)
            self.bsm.start()
            
            self.last_heartbeat = time.time()
            logger.info("WebSocket 재연결 성공")
            
        except Exception as e:
            logger.error(f"WebSocket 재연결 실패: {e}")
    
    async def _handle_execution_report(self, msg: Dict[str, Any]):
        """
        주문 실행 보고서 처리
        
        Args:
            msg: 주문 실행 보고서 메시지
        """
        try:
            order_id = msg.get('i')  # 주문 ID
            client_order_id = msg.get('c')  # 클라이언트 주문 ID
            symbol = msg.get('s')  # 심볼
            side = msg.get('S')  # 매수/매도
            order_type = msg.get('o')  # 주문 유형
            status = msg.get('X')  # 주문 상태
            price = float(msg.get('p', 0))  # 주문 가격
            qty = float(msg.get('q', 0))  # 주문량
            filled_qty = float(msg.get('z', 0))  # 체결량
            cummulative_quote_qty = float(msg.get('Z', 0))  # 체결 금액
            
            logger.info(f"주문 상태 업데이트: {symbol} {side} {status} - ID: {order_id}, 체결량: {filled_qty}/{qty}")
            
            # 주문 상태에 따른 추가 처리는 콜백에서 수행
            
        except Exception as e:
            logger.exception(f"주문 실행 보고서 처리 중 오류 발생: {e}")
    
    async def _handle_account_position(self, msg: Dict[str, Any]):
        """
        계정 포지션 업데이트 처리
        
        Args:
            msg: 계정 포지션 메시지
        """
        try:
            event_time = msg.get('E')
            balances = msg.get('B', [])
            
            for balance in balances:
                asset = balance.get('a')  # 자산
                free = float(balance.get('f', 0))  # 사용 가능 수량
                locked = float(balance.get('l', 0))  # 잠긴 수량
                
                logger.debug(f"잔액 업데이트: {asset} - 사용 가능: {free}, 잠김: {locked}")
            
        except Exception as e:
            logger.exception(f"계정 포지션 업데이트 처리 중 오류 발생: {e}")


class OrderTracker:
    """주문 추적 클래스"""
    
    def __init__(self, ws_manager: WebSocketManager, execution_engine=None):
        """
        주문 추적기 초기화
        
        Args:
            ws_manager: WebSocket 관리자 인스턴스
            execution_engine: 실행 엔진 인스턴스 (옵션)
        """
        self.ws_manager = ws_manager
        self.execution_engine = execution_engine
        
        # 주문 추적 상태
        self.tracked_orders = {}  # 추적 중인 주문
        self.order_updates = {}  # 주문 업데이트 이력
        
        # WebSocket 콜백 등록
        self.ws_manager.register_callback('executionReport', self._on_execution_report)
        
        logger.info("주문 추적기 초기화됨")
    
    def _on_execution_report(self, msg: Dict[str, Any]):
        """
        주문 실행 보고서 콜백
        
        Args:
            msg: 주문 실행 보고서 메시지
        """
        try:
            # 주문 정보 추출
            order_id = str(msg.get('i'))  # 주문 ID
            client_order_id = msg.get('c')  # 클라이언트 주문 ID
            symbol = msg.get('s')  # 심볼
            side = msg.get('S').lower()  # 매수/매도
            order_type = msg.get('o').lower()  # 주문 유형
            status = msg.get('X')  # 주문 상태
            price = float(msg.get('p', 0))  # 주문 가격
            qty = float(msg.get('q', 0))  # 주문량
            filled_qty = float(msg.get('z', 0))  # 체결량
            remaining_qty = qty - filled_qty  # 남은 수량
            
            # 주문 상태 매핑
            status_map = {
                'NEW': 'open',
                'PARTIALLY_FILLED': 'partially_filled',
                'FILLED': 'filled',
                'CANCELED': 'canceled',
                'REJECTED': 'rejected',
                'EXPIRED': 'expired'
            }
            
            mapped_status = status_map.get(status, 'unknown')
            
            # 주문 업데이트 생성
            order_update = {
                'id': order_id,
                'client_order_id': client_order_id,
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'status': mapped_status,
                'price': price,
                'quantity': qty,
                'filled_quantity': filled_qty,
                'remaining_quantity': remaining_qty,
                'timestamp': msg.get('E', int(time.time() * 1000)),
                'is_maker': msg.get('m', False),
                'is_reduce_only': msg.get('R', False)
            }
            
            # 체결 정보가 있는 경우 추가
            if mapped_status in ['partially_filled', 'filled'] and float(msg.get('L', 0)) > 0:
                last_filled_price = float(msg.get('L', 0))
                last_filled_qty = float(msg.get('l', 0))
                
                fill_info = {
                    'price': last_filled_price,
                    'quantity': last_filled_qty,
                    'timestamp': msg.get('E', int(time.time() * 1000))
                }
                
                if 'fills' not in order_update:
                    order_update['fills'] = []
                
                order_update['fills'].append(fill_info)
            
            # 주문 추적 상태 업데이트
            self.tracked_orders[order_id] = order_update
            
            # 주문 업데이트 이력에 추가
            if order_id not in self.order_updates:
                self.order_updates[order_id] = []
            
            self.order_updates[order_id].append(order_update)
            
            # 로그 기록
            logger.info(f"주문 상태 업데이트: {symbol} {side} {mapped_status} - ID: {order_id}, 체결량: {filled_qty}/{qty}")
            
            # 실행 엔진에 업데이트 전달 (있는 경우)
            if self.execution_engine:
                asyncio.create_task(self._update_execution_engine(order_id, order_update))
            
        except Exception as e:
            logger.exception(f"주문 실행 보고서 처리 중 오류 발생: {e}")
    
    async def _update_execution_engine(self, order_id: str, order_update: Dict[str, Any]):
        """
        실행 엔진에 주문 업데이트 전달
        
        Args:
            order_id: 주문 ID
            order_update: 주문 업데이트 정보
        """
        try:
            # 실행 엔진의 주문 업데이트 메서드 호출
            if hasattr(self.execution_engine, 'update_order_from_websocket'):
                await self.execution_engine.update_order_from_websocket(order_id, order_update)
            
        except Exception as e:
            logger.exception(f"실행 엔진 업데이트 중 오류 발생: {e}")
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        주문 상태 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Optional[Dict[str, Any]]: 주문 상태 정보
        """
        return self.tracked_orders.get(order_id)
    
    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """
        주문 업데이트 이력 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            List[Dict[str, Any]]: 주문 업데이트 이력
        """
        return self.order_updates.get(order_id, [])
