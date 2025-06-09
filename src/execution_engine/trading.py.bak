"""
거래 실행 모듈

이 모듈은 Binance API를 통해 실제 거래를 실행하는 기능을 제공합니다.
지정가 주문과 시장가 폴백 기능을 포함합니다.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
import time
import uuid
import enum
import random
from datetime import datetime, timedelta
import os

from src.execution_engine.connector import BinanceConnector, setup_binance_connector
from src.execution_engine.websocket_manager import WebSocketManager, OrderTracker
from src.database.integration import TradingDataManager
from src.database.models import OrderStatus as DBOrderStatus, OrderType as DBOrderType, OrderSide as DBOrderSide
from src.risk_manager import RiskManager, init_risk_manager, get_risk_manager

logger = logging.getLogger(__name__)

# 주문 상태 열거형
class OrderStatus(enum.Enum):
    PENDING = 'pending'       # 주문 생성됨
    OPEN = 'open'             # 주문 제출됨
    PARTIALLY_FILLED = 'partially_filled'  # 부분 체결
    FILLED = 'filled'         # 완전 체결
    CANCELED = 'canceled'     # 취소됨
    REJECTED = 'rejected'     # 거부됨
    EXPIRED = 'expired'       # 만료됨
    FALLBACK = 'fallback'     # 폴백 진행 중
    ERROR = 'error'           # 오류 발생

# 주문 유형 열거형
class OrderType(enum.Enum):
    LIMIT = 'limit'           # 지정가 주문
    MARKET = 'market'         # 시장가 주문
    STOP_LOSS = 'stop_loss'   # 손절매 주문
    TAKE_PROFIT = 'take_profit'  # 이익 실현 주문

# 주문 방향 열거형
class OrderSide(enum.Enum):
    BUY = 'buy'               # 매수
    SELL = 'sell'             # 매도

class ExecutionEngine:
    """거래 실행 엔진 클래스"""
    
    def __init__(self, config: Dict[str, Any], risk_manager=None):
        """
        실행 엔진 초기화
        
        Args:
            config: 애플리케이션 설정
            risk_manager: 리스크 관리자 인스턴스 (옵션)
        """
        self.config = config
        self.connector = setup_binance_connector(config.get("freqtrade_config"))
        self.is_dry_run = self.connector.is_dry_run()
        self.order_queue = asyncio.Queue()
        self.running = False
        
        # 데이터베이스 통합 관리자 초기화
        self.data_manager = TradingDataManager()
        self.trade_session_id = None  # 현재 거래 세션 ID
        
        # 리스크 관리자 설정
        self.risk_manager = risk_manager
        # 외부에서 리스크 관리자가 제공되지 않은 경우 싱글톤 인스턴스 사용
        if self.risk_manager is None:
            self.risk_manager = get_risk_manager()
        
        # 주문 관련 설정
        self.order_settings = {
            # 주문 타임아웃 (초)
            'limit_order_timeout': config.get('limit_order_timeout', 60),
            # 슬리피지 허용 정도 (%)
            'slippage_tolerance': config.get('slippage_tolerance', 1.0),
            # 시장가 폴백 사용 여부
            'use_market_fallback': config.get('use_market_fallback', True),
            # 주문 체크 주기 (초)
            'order_check_interval': config.get('order_check_interval', 5),
            # WebSocket 사용 여부
            'use_websocket': config.get('use_websocket', True),
        }
        
        # 주문 추적 상태
        self.active_orders = {}  # 활성 주문 추적
        self.order_history = {}  # 주문 이력 추적
        
        # 주문 모니터링 태스크
        self.monitoring_tasks = {}
        
        # WebSocket 관리자 초기화
        self.ws_manager = None
        self.order_tracker = None
        
        # 실제 거래 모드에서만 WebSocket 사용
        if not self.is_dry_run and self.order_settings['use_websocket']:
            # API 키와 시크릿 가져오기
            api_key = self.connector.exchange_config.get('key', '')
            api_secret = self.connector.exchange_config.get('secret', '')
            
            if api_key and api_secret:
                # 테스트넷 사용 여부 확인
                is_testnet = 'testnet' in self.connector.exchange_config.get('name', '').lower()
                
                # WebSocket 관리자 초기화
                self.ws_manager = WebSocketManager(api_key, api_secret, is_testnet=is_testnet)
                self.order_tracker = OrderTracker(self.ws_manager, self)
                
                logger.info("WebSocket 관리자 초기화됨")
            else:
                logger.warning("API 키 또는 시크릿이 없어 WebSocket 기능을 사용할 수 없습니다")
        
        logger.info(f"실행 엔진 초기화됨 (드라이런 모드: {self.is_dry_run})")
        logger.info(f"주문 설정: {self.order_settings}")
    
    async def start(self):
        """실행 엔진 시작"""
        if self.running:
            logger.warning("실행 엔진이 이미 실행 중입니다")
            return
        
        self.running = True
        logger.info("실행 엔진 시작됨")
        
        # 리스크 관리자 초기화 (없는 경우)
        if self.risk_manager is None:
            try:
                # 리스크 관리 설정 가져오기
                risk_config = self.config.get('risk_management', {
                    'max_drawdown': 0.15,
                    'stop_loss': 0.035,
                    'risk_per_trade': 0.02,
                    'daily_trade_limit': 60,
                    'circuit_breaker': 0.05
                })
                
                # 리스크 관리자 초기화
                self.risk_manager = await init_risk_manager({
                    'risk_management': risk_config,
                    'redis': self.config.get('redis', {
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0
                    })
                })
                logger.info("리스크 관리자 초기화됨")
            except Exception as e:
                logger.error(f"리스크 관리자 초기화 실패: {e}")
        
        # 거래 세션 시작
        strategy_name = self.config.get('strategy_name', 'NASOSv5_mod3')
        session_config = {
            'order_settings': self.order_settings,
            'exchange': self.connector.exchange_config.get('name', 'binance'),
            'pairs': self.config.get('pairs', []),
            'stake_currency': self.config.get('stake_currency', 'USDT'),
            'stake_amount': self.config.get('stake_amount', 0.0)
        }
        
        try:
            self.trade_session_id = await self.data_manager.start_trade_session(
                strategy=strategy_name,
                config=session_config,
                is_dry_run=self.is_dry_run
            )
            logger.info(f"거래 세션 시작됨: {self.trade_session_id}")
            
            # 잠액 초기화 (리스크 관리자가 있는 경우)
            if self.risk_manager:
                try:
                    # 잠액 정보 가져오기
                    balance = self.connector.get_balance()
                    await self.risk_manager.update_balance(balance)
                    logger.info(f"잠액 정보 초기화됨: {balance}")
                except Exception as e:
                    logger.error(f"잠액 정보 초기화 실패: {e}")
        except Exception as e:
            logger.error(f"거래 세션 시작 실패: {e}")
        
        # WebSocket 연결 시작 (사용 가능한 경우)
        if self.ws_manager and not self.is_dry_run:
            try:
                await self.ws_manager.start()
                logger.info("WebSocket 연결 시작됨")
            except Exception as e:
                logger.error(f"WebSocket 연결 시작 실패: {e}")
        
        # 주문 처리 태스크 시작
        asyncio.create_task(self._process_order_queue())
    
    async def stop(self):
        """실행 엔진 중지"""
        if not self.running:
            logger.warning("실행 엔진이 이미 중지되었습니다")
            return
        
        self.running = False
        
        # 거래 세션 종료
        if self.trade_session_id:
            try:
                # 세션 결과 계산
                total_trades = len(self.order_history)
                profitable_trades = sum(1 for order in self.order_history.values() 
                                      if order.get('side') == 'sell' and order.get('profit', 0) > 0)
                total_profit = sum(order.get('profit', 0) for order in self.order_history.values())
                
                # 세션 종료
                session_results = {
                    'total_trades': total_trades,
                    'profitable_trades': profitable_trades,
                    'total_profit': total_profit,
                    'total_profit_percent': (total_profit / 100) if total_trades > 0 else 0.0
                }
                
                await self.data_manager.end_trade_session(self.trade_session_id, session_results)
                logger.info(f"거래 세션 종료됨: {self.trade_session_id}")
            except Exception as e:
                logger.error(f"거래 세션 종료 실패: {e}")
        
        # WebSocket 연결 종료 (사용 중인 경우)
        if self.ws_manager:
            try:
                await self.ws_manager.stop()
                logger.info("WebSocket 연결 종료됨")
            except Exception as e:
                logger.error(f"WebSocket 연결 종료 실패: {e}")
        
        # 모니터링 태스크 종료
        for task in self.monitoring_tasks.values():
            if not task.done():
                task.cancel()
        
        # 리스크 관리자 종료
        if self.risk_manager:
            try:
                await self.risk_manager.close()
                logger.info("리스크 관리자 종료됨")
            except Exception as e:
                logger.error(f"리스크 관리자 종료 실패: {e}")
        
        logger.info("실행 엔진 중지됨")
    
    async def place_order(self, pair: str, side: str, amount: float, price: Optional[float] = None, order_type: str = 'limit', custom_id: str = None):
        """
        주문 실행
        
        Args:
            pair: 거래 페어 (예: BTC/USDT)
            side: 매수/매도 (buy/sell)
            amount: 주문량
            price: 주문 가격 (limit 주문의 경우)
            order_type: 주문 유형 (limit/market)
            custom_id: 사용자 정의 주문 ID (옵션)
            
        Returns:
            Dict[str, Any]: 주문 정보
        """
        # 안전 검사
        if not self._check_safety():
            return None
            
        # 리스크 관리자 검사
        if self.risk_manager:
            try:
                trade_allowed = await self.risk_manager.check_trade_allowed(pair, side, amount, price)
                if not trade_allowed:
                    logger.warning(f"리스크 관리자가 거래를 거부했습니다: {pair} {side} {amount}")
                    return None
                
                # 거래 수 증가
                await self.risk_manager.increment_daily_trade_count(pair)
            except Exception as e:
                logger.error(f"리스크 검사 중 오류 발생: {e}")
                # 오류가 발생해도 거래는 허용 (안전을 위해)
        
        # 주문 유형 검증
        if order_type not in [t.value for t in OrderType]:
            logger.error(f"지원되지 않는 주문 유형: {order_type}")
            return None
        
        # 지정가 주문인데 가격이 없는 경우 검증
        if order_type == OrderType.LIMIT.value and price is None:
            logger.error(f"지정가 주문에는 가격이 필요합니다: {pair} {side}")
            return None
        
        # 주문 ID 생성
        order_id = custom_id or str(uuid.uuid4())
        
        # 주문 정보 생성
        order_info = {
            "id": order_id,
            "pair": pair,
            "side": side,
            "amount": amount,
            "price": price,
            "order_type": order_type,
            "timestamp": time.time(),
            "status": OrderStatus.PENDING.value,
            "filled_amount": 0.0,
            "remaining_amount": amount,
            "fills": [],
            "is_fallback": False,
            "parent_order_id": None,
            "is_dry_run": self.is_dry_run
        }
        
        # 활성 주문에 추가
        self.active_orders[order_id] = order_info
        
        # 주문 큐에 추가
        await self.order_queue.put(order_info)
        logger.info(f"주문이 큐에 추가됨: {order_info}")
        
        return order_info
    
    def _check_safety(self) -> bool:
        """
        안전 검사 수행
        
        Returns:
            bool: 안전하면 True, 그렇지 않으면 False
        """
        # 드라이런 모드가 아니고 지갑 잔액이 최소 요구사항보다 작은 경우
        if not self.is_dry_run and self.connector.get_dry_run_wallet() < 0.0001:
            logger.warning("실제 거래를 위한 지갑 잔액이 너무 적습니다 (최소 0.0001 BTC 필요)")
            return False
        
        return True
    
    async def _process_order_queue(self):
        """주문 큐 처리 루프"""
        logger.info("주문 큐 처리 시작됨")
        
        while self.running:
            try:
                # 큐에서 주문 가져오기
                order_info = await self.order_queue.get()
                
                # 주문 상태 업데이트
                order_id = order_info['id']
                self.active_orders[order_id]['status'] = OrderStatus.OPEN.value
                
                # 주문 실행
                result = await self._execute_order(order_info)
                
                # 주문 처리 완료 표시
                self.order_queue.task_done()
                
                # 결과 로깅 및 처리
                if result:
                    logger.info(f"주문 실행 성공: {result}")
                    
                    # 지정가 주문인 경우 모니터링 태스크 시작
                    if order_info['order_type'] == OrderType.LIMIT.value and self.order_settings['use_market_fallback']:
                        monitoring_task = asyncio.create_task(
                            self._monitor_limit_order(result)
                        )
                        self.monitoring_tasks[order_id] = monitoring_task
                else:
                    logger.warning(f"주문 실행 실패: {order_info}")
                    # 주문 상태 업데이트
                    if order_id in self.active_orders:
                        self.active_orders[order_id]['status'] = OrderStatus.ERROR.value
                        # 주문 이력으로 이동
                        self.order_history[order_id] = self.active_orders.pop(order_id)
                
            except Exception as e:
                logger.exception(f"주문 처리 중 오류 발생: {e}")
                await asyncio.sleep(1)  # 오류 발생 시 잠시 대기
    
    async def _execute_order(self, order_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        실제 주문 실행
        
        Args:
            order_info: 주문 정보
            
        Returns:
            Optional[Dict[str, Any]]: 주문 결과
        """
        order_id = order_info["id"]
        pair = order_info["pair"]
        side = order_info["side"]
        amount = order_info["amount"]
        price = order_info["price"]
        order_type = order_info["order_type"]
        is_fallback = order_info.get("is_fallback", False)
        parent_order_id = order_info.get("parent_order_id")
        
        # 데이터베이스용 주문 데이터 준비
        db_order_data = {
            'order_id': order_id,
            'client_order_id': f"bot_{order_id}",
            'symbol': pair.replace('/', ''),
            'side': side,
            'type': order_type,
            'status': DBOrderStatus.PENDING.value,
            'quantity': amount,
            'price': price,
            'filled_quantity': 0.0,
            'remaining_quantity': amount,
            'created_at': datetime.utcnow(),
            'is_dry_run': self.is_dry_run,
            'is_fallback': is_fallback,
            'parent_order_id': parent_order_id,
            'strategy': self.config.get('strategy_name', 'NASOSv5_mod3'),
            'timeframe': self.config.get('timeframe', '5m')
        }
        
        try:
            # 드라이런 모드인 경우 가상 주문 실행
            if self.is_dry_run:
                logger.info(f"[드라이런] 주문 실행: {pair} {side} {amount} @ {price} ({order_type})")
                
                # 가상 주문 결과 반환
                result = {
                    "id": order_id,
                    "pair": pair,
                    "side": side,
                    "amount": amount,
                    "price": price or 0.0,
                    "type": order_type,
                    "status": OrderStatus.OPEN.value,
                    "timestamp": time.time(),
                    "is_dry_run": True,
                    "is_fallback": is_fallback,
                    "parent_order_id": parent_order_id,
                    "filled_amount": 0.0,
                    "remaining_amount": amount,
                    "fills": []
                }
                
                # 드라이런에서는 시장가 주문은 즉시 체결된 것으로 가정
                if order_type == OrderType.MARKET.value:
                    result["status"] = OrderStatus.FILLED.value
                    result["filled_amount"] = amount
                    result["remaining_amount"] = 0.0
                    fill_price = price or self._get_market_price(pair)
                    result["fills"] = [{
                        "price": fill_price,
                        "amount": amount,
                        "timestamp": time.time()
                    }]
                    
                    # 데이터베이스 주문 상태 업데이트
                    db_order_data['status'] = DBOrderStatus.FILLED.value
                    db_order_data['filled_quantity'] = amount
                    db_order_data['remaining_quantity'] = 0.0
                    db_order_data['average_price'] = fill_price
                
                # 주문 상태 업데이트
                self.active_orders[order_id].update(result)
                
                # 데이터베이스에 주문 저장
                try:
                    await self.data_manager.create_order(db_order_data)
                    
                    # 시장가 주문이 체결된 경우 체결 데이터 추가
                    if order_type == OrderType.MARKET.value:
                        fill_data = {
                            'fill_id': f"{order_id}_fill_1",
                            'price': fill_price,
                            'quantity': amount,
                            'timestamp': datetime.utcnow(),
                            'fee': amount * fill_price * 0.001,  # 가상 수수료 0.1%
                            'fee_asset': pair.split('/')[1],
                            'is_maker': False
                        }
                        await self.data_manager.process_order_fill(order_id, fill_data)
                        
                    logger.info(f"주문 데이터 저장됨: {order_id}")
                except Exception as e:
                    logger.error(f"주문 데이터 저장 실패: {e}")
                
                return result
            
            # 실제 주문 실행 (Freqtrade Binance 커넥터 사용)
            logger.info(f"[실제] 주문 실행: {pair} {side} {amount} @ {price} ({order_type})")
            
            # 데이터베이스에 주문 저장
            try:
                await self.data_manager.create_order(db_order_data)
                logger.info(f"주문 데이터 저장됨: {order_id}")
            except Exception as e:
                logger.error(f"주문 데이터 저장 실패: {e}")
            
            # 주문 유형에 따라 다른 처리
            if order_type == OrderType.LIMIT.value and price:
                # 지정가 주문
                # TODO: Binance API를 통한 지정가 주문 실행
                # 실제 구현에서는 다음과 같이 Binance API 호출
                # order = await client.create_order(
                #     symbol=pair.replace('/', ''),
                #     side=side.upper(),
                #     type='LIMIT',
                #     timeInForce='GTC',
                #     quantity=amount,
                #     price=price
                # )
                # 
                # # Binance API 응답에서 교환 주문 ID 가져오기
                # exchange_order_id = order.get('orderId')
                # 
                # # 데이터베이스 주문 업데이트
                # await self.data_manager.update_order_status(
                #     order_id, 
                #     DBOrderStatus.OPEN.value, 
                #     {'exchange_order_id': exchange_order_id}
                # )
                pass
            else:
                # 시장가 주문
                # TODO: Binance API를 통한 시장가 주문 실행
                # 실제 구현에서는 다음과 같이 Binance API 호출
                # order = await client.create_order(
                #     symbol=pair.replace('/', ''),
                #     side=side.upper(),
                #     type='MARKET',
                #     quantity=amount
                # )
                # 
                # # Binance API 응답에서 정보 가져오기
                # exchange_order_id = order.get('orderId')
                # fills = order.get('fills', [])
                # 
                # # 체결 처리
                # filled_amount = 0.0
                # avg_price = 0.0
                # 
                # for fill in fills:
                #     fill_amount = float(fill.get('qty', 0))
                #     fill_price = float(fill.get('price', 0))
                #     filled_amount += fill_amount
                #     
                #     # 체결 데이터 저장
                #     fill_data = {
                #         'fill_id': fill.get('tradeId'),
                #         'price': fill_price,
                #         'quantity': fill_amount,
                #         'timestamp': datetime.utcnow(),
                #         'fee': float(fill.get('commission', 0)),
                #         'fee_asset': fill.get('commissionAsset', ''),
                #         'is_maker': fill.get('isMaker', False)
                #     }
                #     await self.data_manager.process_order_fill(order_id, fill_data)
                # 
                # # 데이터베이스 주문 업데이트
                # await self.data_manager.update_order_status(
                #     order_id, 
                #     DBOrderStatus.FILLED.value, 
                #     {
                #         'exchange_order_id': exchange_order_id,
                #         'filled_quantity': filled_amount,
                #         'remaining_quantity': 0.0
                #     }
                # )
                pass
            
            # 임시 주문 결과 (실제 구현에서는 Binance API 응답으로 대체)
            result = {
                "id": order_id,
                "pair": pair,
                "side": side,
                "amount": amount,
                "price": price or 0.0,
                "type": order_type,
                "status": OrderStatus.OPEN.value,
                "timestamp": time.time(),
                "is_dry_run": False,
                "is_fallback": is_fallback,
                "parent_order_id": parent_order_id,
                "filled_amount": 0.0,
                "remaining_amount": amount,
                "fills": []
            }
            
            # 시장가 주문은 즉시 체결된 것으로 가정
            if order_type == OrderType.MARKET.value:
                result["status"] = OrderStatus.FILLED.value
                result["filled_amount"] = amount
                result["remaining_amount"] = 0.0
                fill_price = price or self._get_market_price(pair)
                result["fills"] = [{
                    "price": fill_price,
                    "amount": amount,
                    "timestamp": time.time()
                }]
                
                # 데이터베이스 체결 처리
                try:
                    fill_data = {
                        'fill_id': f"{order_id}_fill_1",
                        'price': fill_price,
                        'quantity': amount,
                        'timestamp': datetime.utcnow(),
                        'fee': amount * fill_price * 0.001,  # 가상 수수료 0.1%
                        'fee_asset': pair.split('/')[1],
                        'is_maker': False
                    }
                    await self.data_manager.process_order_fill(order_id, fill_data)
                    
                    # 주문 상태 업데이트
                    await self.data_manager.update_order_status(
                        order_id, 
                        DBOrderStatus.FILLED.value, 
                        {
                            'filled_quantity': amount,
                            'remaining_quantity': 0.0,
                            'average_price': fill_price
                        }
                    )
                    
                    # 리스크 관리자에 손익 업데이트
                    if self.risk_manager:
                        try:
                            # 손익 계산
                            total_cost = amount * fill_price
                            fee = total_cost * 0.001  # 가상 수수료 0.1%
                            
                            # 매수/매도에 따른 손익 처리
                            if side == OrderSide.BUY.value:
                                # 매수는 포지션 추가
                                await self.risk_manager.update_position(pair, amount, fill_price)
                            elif side == OrderSide.SELL.value:
                                # 매도는 실현 이익/손실 계산
                                # 매수 가격을 가져오기 (실제로는 데이터베이스에서 가져와야 함)
                                avg_buy_price = await self.data_manager.get_average_buy_price(pair)
                                if avg_buy_price:
                                    profit = (fill_price - avg_buy_price) * amount - fee
                                    profit_percent = (fill_price / avg_buy_price - 1) * 100
                                    
                                    # 리스크 관리자에 이익/손실 업데이트
                                    await self.risk_manager.update_trade_result(pair, profit, profit_percent)
                                    
                                    # 포지션 업데이트 (매도량만큼 감소)
                                    await self.risk_manager.update_position(pair, -amount, fill_price)
                                    
                                    logger.info(f"거래 결과 업데이트: {pair}, 이익: {profit:.4f}, 이익률: {profit_percent:.2f}%")
                                else:
                                    logger.warning(f"평균 매수가격을 찾을 수 없어 손익 계산 실패: {pair}")
                        except Exception as e:
                            logger.error(f"리스크 관리자 손익 업데이트 실패: {e}")
                except Exception as e:
                    logger.error(f"체결 데이터 처리 실패: {e}")
            
            # 주문 상태 업데이트
            self.active_orders[order_id].update(result)
            
            return result
            
        except Exception as e:
            logger.exception(f"주문 실행 중 오류 발생: {e}")
            
            # 시장 변동성이 높은 경우 지정가 주문을 시장가로 폴백
            if "VolatilityException" in str(e) and order_type == OrderType.LIMIT.value and not is_fallback:
                logger.warning(f"변동성으로 인해 시장가 주문으로 폴백: {pair}")
                
                # 폴백 주문 정보 생성
                fallback_order_info = {
                    "id": str(uuid.uuid4()),
                    "pair": pair,
                    "side": side,
                    "amount": amount,
                    "price": None,
                    "order_type": OrderType.MARKET.value,
                    "timestamp": time.time(),
                    "status": OrderStatus.PENDING.value,
                    "is_fallback": True,
                    "parent_order_id": order_id,
                    "is_dry_run": self.is_dry_run
                }
                
                # 원래 주문 상태 업데이트
                self.active_orders[order_id]["status"] = OrderStatus.FALLBACK.value
                
                # 폴백 주문 실행
                return await self._execute_order(fallback_order_info)
            
            # 오류 발생 시 주문 상태 업데이트
            if order_id in self.active_orders:
                self.active_orders[order_id]["status"] = OrderStatus.ERROR.value
                self.active_orders[order_id]["error"] = str(e)
            
            return None
            
    def _get_market_price(self, pair: str) -> float:
        """
        시장 가격 가져오기 (가상 가격 생성)
        
        Args:
            pair: 거래 페어
            
        Returns:
            float: 시장 가격
        """
        # 실제 구현에서는 Binance API를 통해 시장 가격 조회
        # 임시 가격 생성
        if pair == "BTC/USDT":
            return 50000.0
        elif pair == "ETH/USDT":
            return 3000.0
        elif pair == "BNB/USDT":
            return 500.0
        elif pair == "SOL/USDT":
            return 100.0
        elif pair == "XRP/USDT":
            return 0.5
        elif pair == "ADA/USDT":
            return 0.4
        elif pair == "AVAX/USDT":
            return 30.0
        elif pair == "DOT/USDT":
            return 10.0
        elif pair == "LINK/USDT":
            return 15.0
        else:
            return 10.0


    async def _monitor_limit_order(self, order: Dict[str, Any]):
        """
        지정가 주문 모니터링 및 시장가 폴백
        
        Args:
            order: 주문 정보
        """
        order_id = order["id"]
        pair = order["pair"]
        side = order["side"]
        amount = order["amount"]
        price = order["price"]
        
        # 타임아웃 계산
        timeout = self.order_settings["limit_order_timeout"]
        check_interval = self.order_settings["order_check_interval"]
        start_time = time.time()
        end_time = start_time + timeout
        
        logger.info(f"지정가 주문 모니터링 시작: {order_id} ({timeout}초 타임아웃)")
        
        try:
            # 타임아웃까지 주문 상태 검사
            while time.time() < end_time and self.running:
                # 현재 주문 상태 가져오기
                current_order = self.active_orders.get(order_id)
                
                # 주문이 이미 완료되었거나 취소된 경우
                if not current_order or current_order["status"] in [
                    OrderStatus.FILLED.value, 
                    OrderStatus.CANCELED.value, 
                    OrderStatus.ERROR.value
                ]:
                    logger.info(f"주문 {order_id}의 모니터링 종료: 상태={current_order['status'] if current_order else 'unknown'}")
                    return
                
                # 실제 구현에서는 여기서 Binance API를 통해 주문 상태 조회
                # order_status = await client.get_order(symbol=pair.replace('/', ''), orderId=order_id)
                
                # 드라이런에서는 임의로 주문 상태 업데이트
                if self.is_dry_run and random.random() < 0.2:  # 20% 확률로 체결
                    fill_amount = min(current_order["remaining_amount"], current_order["amount"] * 0.5)  # 부분 체결
                    
                    # 주문 상태 업데이트
                    current_order["filled_amount"] += fill_amount
                    current_order["remaining_amount"] -= fill_amount
                    current_order["fills"].append({
                        "price": price,
                        "amount": fill_amount,
                        "timestamp": time.time()
                    })
                    
                    # 완전 체결 처리
                    if current_order["remaining_amount"] <= 0:
                        current_order["status"] = OrderStatus.FILLED.value
                        logger.info(f"주문 {order_id} 체결 완료")
                        return
                    else:
                        current_order["status"] = OrderStatus.PARTIALLY_FILLED.value
                        logger.info(f"주문 {order_id} 부분 체결: {current_order['filled_amount']}/{amount}")
                
                # 대기 후 다시 검사
                await asyncio.sleep(check_interval)
            
            # 타임아웃 발생 - 시장가 폴백 실행
            current_order = self.active_orders.get(order_id)
            if current_order and current_order["status"] in [OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]:
                logger.warning(f"지정가 주문 {order_id} 타임아웃 발생 ({timeout}초) - 시장가 폴백 실행")
                
                # 남은 주문량 계산
                remaining_amount = current_order["remaining_amount"]
                
                if remaining_amount > 0 and self.order_settings["use_market_fallback"]:
                    # 기존 주문 취소
                    # 실제 구현에서는 Binance API를 통해 주문 취소
                    # await client.cancel_order(symbol=pair.replace('/', ''), orderId=order_id)
                    
                    # 주문 상태 업데이트
                    current_order["status"] = OrderStatus.CANCELED.value
                    
                    # 시장가 폴백 주문 생성
                    fallback_order_info = {
                        "id": str(uuid.uuid4()),
                        "pair": pair,
                        "side": side,
                        "amount": remaining_amount,
                        "price": None,
                        "order_type": OrderType.MARKET.value,
                        "timestamp": time.time(),
                        "status": OrderStatus.PENDING.value,
                        "is_fallback": True,
                        "parent_order_id": order_id,
                        "is_dry_run": self.is_dry_run
                    }
                    
                    # 폴백 주문 실행
                    await self.place_order(
                        pair=pair,
                        side=side,
                        amount=remaining_amount,
                        price=None,
                        order_type=OrderType.MARKET.value,
                        custom_id=fallback_order_info["id"]
                    )
                else:
                    logger.info(f"폴백 실행 안 함: 남은 주문량={remaining_amount}, use_market_fallback={self.order_settings['use_market_fallback']}")
        
        except Exception as e:
            logger.exception(f"주문 모니터링 중 오류 발생: {e}")
        finally:
            # 모니터링 태스크 제거
            if order_id in self.monitoring_tasks:
                del self.monitoring_tasks[order_id]


    async def update_order_from_websocket(self, order_id: str, order_update: Dict[str, Any]):
        """
        WebSocket을 통한 주문 상태 업데이트 처리
        
        Args:
            order_id: 주문 ID
            order_update: 주문 업데이트 정보
        """
        try:
            # 활성 주문에 없는 경우 무시
            if order_id not in self.active_orders:
                logger.debug(f"WebSocket 업데이트 무시: 주문 ID {order_id}가 활성 주문에 없습니다")
                return
            
            # 주문 상태 가져오기
            current_order = self.active_orders[order_id]
            
            # 주문 상태 매핑
            status_map = {
                'open': OrderStatus.OPEN.value,
                'partially_filled': OrderStatus.PARTIALLY_FILLED.value,
                'filled': OrderStatus.FILLED.value,
                'canceled': OrderStatus.CANCELED.value,
                'rejected': OrderStatus.REJECTED.value,
                'expired': OrderStatus.EXPIRED.value
            }
            
            # 데이터베이스 주문 상태 매핑
            db_status_map = {
                'open': DBOrderStatus.OPEN.value,
                'partially_filled': DBOrderStatus.PARTIALLY_FILLED.value,
                'filled': DBOrderStatus.FILLED.value,
                'canceled': DBOrderStatus.CANCELED.value,
                'rejected': DBOrderStatus.REJECTED.value,
                'expired': DBOrderStatus.EXPIRED.value
            }
            
            # 주문 상태 업데이트
            new_status = status_map.get(order_update['status'], current_order['status'])
            old_status = current_order['status']
            
            # 상태가 변경된 경우에만 처리
            if new_status != old_status:
                logger.info(f"주문 {order_id} 상태 변경: {old_status} -> {new_status}")
                current_order['status'] = new_status
                
                # 데이터베이스 주문 상태 업데이트
                try:
                    db_status = db_status_map.get(order_update['status'], DBOrderStatus.PENDING.value)
                    await self.data_manager.update_order_status(order_id, db_status)
                    logger.info(f"데이터베이스 주문 상태 업데이트됨: {order_id}, 상태: {db_status}")
                except Exception as e:
                    logger.error(f"데이터베이스 주문 상태 업데이트 실패: {e}")
            
            # 체결량 업데이트
            if 'filled_quantity' in order_update:
                filled_quantity = order_update['filled_quantity']
                remaining_quantity = current_order['amount'] - filled_quantity
                current_order['filled_amount'] = filled_quantity
                current_order['remaining_amount'] = remaining_quantity
                
                # 데이터베이스 체결량 업데이트
                try:
                    await self.data_manager.update_order_status(
                        order_id, 
                        db_status_map.get(order_update['status'], DBOrderStatus.PENDING.value),
                        {
                            'filled_quantity': filled_quantity,
                            'remaining_quantity': remaining_quantity
                        }
                    )
                    logger.info(f"데이터베이스 체결량 업데이트됨: {order_id}, 체결량: {filled_quantity}")
                except Exception as e:
                    logger.error(f"데이터베이스 체결량 업데이트 실패: {e}")
            
            # 체결 정보 업데이트
            if 'fills' in order_update and order_update['fills']:
                if 'fills' not in current_order:
                    current_order['fills'] = []
                
                # 새로운 체결 정보만 추가
                for fill in order_update['fills']:
                    # 이미 있는 체결인지 확인 (중복 방지)
                    is_duplicate = False
                    for existing_fill in current_order['fills']:
                        if abs(existing_fill['timestamp'] - fill['timestamp']) < 1000 and \
                           abs(existing_fill['price'] - fill['price']) < 0.00001 and \
                           abs(existing_fill['quantity'] - fill['quantity']) < 0.00001:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        current_order['fills'].append(fill)
                        logger.info(f"주문 {order_id} 체결 추가: {fill['quantity']} @ {fill['price']}")
                        
                        # 데이터베이스에 체결 정보 추가
                        try:
                            fill_data = {
                                'fill_id': f"{order_id}_fill_{len(current_order['fills'])}",
                                'price': fill['price'],
                                'quantity': fill['quantity'],
                                'timestamp': datetime.fromtimestamp(fill['timestamp'] / 1000) if isinstance(fill['timestamp'], (int, float)) else datetime.utcnow(),
                                'fee': fill.get('fee', fill['price'] * fill['quantity'] * 0.001),  # 수수료 정보가 없는 경우 추정
                                'fee_asset': fill.get('fee_asset', current_order['pair'].split('/')[1]),
                                'is_maker': fill.get('is_maker', False)
                            }
                            await self.data_manager.process_order_fill(order_id, fill_data)
                            logger.info(f"데이터베이스에 체결 정보 추가됨: {order_id}, 체결 ID: {fill_data['fill_id']}")
                        except Exception as e:
                            logger.error(f"데이터베이스 체결 정보 추가 실패: {e}")
            
            # 주문이 완전히 체결되었거나 취소된 경우 처리
            if new_status in [OrderStatus.FILLED.value, OrderStatus.CANCELED.value, OrderStatus.REJECTED.value, OrderStatus.EXPIRED.value]:
                # 모니터링 태스크 종료 (있는 경우)
                if order_id in self.monitoring_tasks and not self.monitoring_tasks[order_id].done():
                    self.monitoring_tasks[order_id].cancel()
                    logger.info(f"주문 {order_id} 모니터링 태스크 종료")
                
                # 주문 이력으로 이동
                self.order_history[order_id] = current_order.copy()
                del self.active_orders[order_id]
                
                logger.info(f"주문 {order_id} 처리 완료 ({new_status})")
        
        except Exception as e:
            logger.exception(f"WebSocket 주문 업데이트 처리 중 오류 발생: {e}")


def start_trading(config: Dict[str, Any]):
    """
    거래 실행 시작
    
    Args:
        config: 애플리케이션 설정
    """
    logger.info("거래 실행 시작...")
    
    # 이벤트 루프 가져오기
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 이벤트 루프가 없는 경우 새로 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # 실행 엔진 초기화
    engine = ExecutionEngine(config)
    
    try:
        # 실행 엔진 시작
        loop.run_until_complete(engine.start())
        
        # 메인 루프 실행 (실제 애플리케이션에서는 다른 방식으로 구현할 수 있음)
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.exception(f"거래 실행 중 오류 발생: {e}")
    finally:
        # 실행 엔진 중지
        loop.run_until_complete(engine.stop())
        
        # 이벤트 루프 종료
        loop.close()
        
    logger.info("거래 실행 종료")
