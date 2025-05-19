"""
데이터베이스 통합 모듈

이 모듈은 실행 엔진과 데이터베이스 간의 통합을 관리합니다.
주문 및 거래 데이터를 데이터베이스에 저장하고 관리하는 기능을 제공합니다.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

from src.database.repository import OrderRepository, IndicatorRepository, TradeSessionRepository, FillRepository
from src.database.models import OrderStatus, OrderType, OrderSide, TimeFrame
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)

class TradingDataManager:
    """거래 데이터 관리자 클래스"""
    
    def __init__(self):
        """거래 데이터 관리자 초기화"""
        self.order_repo = OrderRepository()
        self.indicator_repo = IndicatorRepository()
        self.session_repo = TradeSessionRepository()
        self.fill_repo = FillRepository()
        
        logger.info("거래 데이터 관리자 초기화됨")
    
    async def create_order(self, order_data: Dict[str, Any]) -> str:
        """
        주문 생성
        
        Args:
            order_data: 주문 데이터
            
        Returns:
            str: 주문 ID
        """
        try:
            # 주문 ID 생성 (없는 경우)
            if 'order_id' not in order_data or not order_data['order_id']:
                order_data['order_id'] = str(uuid.uuid4())
            
            # 주문 생성
            order = self.order_repo.create_order(order_data)
            
            logger.info(f"주문 생성됨: {order.order_id}, 심볼: {order.symbol}, 유형: {order.type.value if order.type else None}")
            
            return order.order_id
            
        except Exception as e:
            logger.error(f"주문 생성 실패: {e}")
            raise
    
    async def update_order_status(self, order_id: str, status: Union[OrderStatus, str], 
                                 additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        주문 상태 업데이트
        
        Args:
            order_id: 주문 ID
            status: 새 상태
            additional_data: 추가 데이터 (선택 사항)
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 업데이트 데이터 준비
            update_data = {'status': status}
            
            # 추가 데이터 병합 (있는 경우)
            if additional_data:
                update_data.update(additional_data)
            
            # 주문 업데이트
            order = self.order_repo.update_order(order_id, update_data)
            
            if not order:
                logger.warning(f"업데이트할 주문을 찾을 수 없음: {order_id}")
                return False
            
            logger.info(f"주문 상태 업데이트됨: {order_id}, 상태: {order.status.value if order.status else None}")
            
            return True
            
        except Exception as e:
            logger.error(f"주문 상태 업데이트 실패: {e}")
            return False
    
    async def process_order_fill(self, order_id: str, fill_data: Dict[str, Any]) -> bool:
        """
        주문 체결 처리
        
        Args:
            order_id: 주문 ID
            fill_data: 체결 데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 체결 추가
            fill = self.order_repo.add_fill(order_id, fill_data)
            
            if not fill:
                logger.warning(f"체결을 추가할 주문을 찾을 수 없음: {order_id}")
                return False
            
            logger.info(f"주문 체결 처리됨: {order_id}, 체결 ID: {fill.fill_id}, 수량: {fill.quantity}, 가격: {fill.price}")
            
            return True
            
        except Exception as e:
            logger.error(f"주문 체결 처리 실패: {e}")
            return False
    
    async def record_order_error(self, order_id: str, error_message: str, 
                               error_code: Optional[str] = None,
                               error_details: Optional[Dict[str, Any]] = None,
                               update_status: bool = False) -> bool:
        """
        주문 오류 기록
        
        Args:
            order_id: 주문 ID
            error_message: 오류 메시지
            error_code: 오류 코드 (선택 사항)
            error_details: 오류 세부 정보 (선택 사항)
            update_status: 주문 상태를 오류로 업데이트할지 여부
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 오류 데이터 준비
            error_data = {
                'error_message': error_message,
                'error_code': error_code,
                'error_details': error_details,
                'timestamp': datetime.utcnow(),
                'update_status': update_status
            }
            
            # 오류 추가
            error = self.order_repo.add_error(order_id, error_data)
            
            if not error:
                logger.warning(f"오류를 추가할 주문을 찾을 수 없음: {order_id}")
                return False
            
            logger.info(f"주문 오류 기록됨: {order_id}, 코드: {error_code}, 메시지: {error_message}")
            
            return True
            
        except Exception as e:
            logger.error(f"주문 오류 기록 실패: {e}")
            return False
    
    async def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        ID로 주문 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Optional[Dict[str, Any]]: 주문 정보 또는 None
        """
        try:
            # 주문 조회
            order = self.order_repo.get_order_by_id(order_id)
            
            if not order:
                logger.debug(f"주문을 찾을 수 없음: {order_id}")
                return None
            
            # 딕셔너리로 변환
            return order.to_dict()
            
        except Exception as e:
            logger.error(f"주문 조회 실패: {e}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        미체결 주문 조회
        
        Args:
            symbol: 심볼 (선택 사항)
            
        Returns:
            List[Dict[str, Any]]: 미체결 주문 목록
        """
        try:
            # 미체결 주문 조회
            orders = self.order_repo.get_open_orders(symbol)
            
            # 딕셔너리로 변환
            return [order.to_dict() for order in orders]
            
        except Exception as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            return []
    
    async def save_indicator_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """
        지표 스냅샷 저장
        
        Args:
            snapshot_data: 스냅샷 데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 스냅샷 생성
            snapshot = self.indicator_repo.create_snapshot(snapshot_data)
            
            logger.debug(f"지표 스냅샷 저장됨: 심볼: {snapshot.symbol}, 시간 프레임: {snapshot.timeframe.value if snapshot.timeframe else None}")
            
            return True
            
        except Exception as e:
            logger.error(f"지표 스냅샷 저장 실패: {e}")
            return False
    
    async def get_latest_indicators(self, symbol: str, timeframe: Union[TimeFrame, str]) -> Optional[Dict[str, Any]]:
        """
        최신 지표 조회
        
        Args:
            symbol: 심볼
            timeframe: 시간 프레임
            
        Returns:
            Optional[Dict[str, Any]]: 지표 정보 또는 None
        """
        try:
            # 최신 스냅샷 조회
            snapshot = self.indicator_repo.get_latest_snapshot(symbol, timeframe)
            
            if not snapshot:
                logger.debug(f"지표 스냅샷을 찾을 수 없음: 심볼: {symbol}, 시간 프레임: {timeframe}")
                return None
            
            # 딕셔너리로 변환
            return snapshot.to_dict()
            
        except Exception as e:
            logger.error(f"최신 지표 조회 실패: {e}")
            return None
        
    async def get_average_buy_price(self, pair: str) -> Optional[float]:
        """
        특정 페어의 평균 매수 가격 계산
        
        Args:
            pair: 거래 페어 (BTC/USDT 형식)
            
        Returns:
            Optional[float]: 평균 매수 가격 또는 None
        """
        try:
            # 페어 포맷 변환 (BTC/USDT -> BTCUSDT)
            symbol = pair.replace('/', '')
            
            # 매수 주문만 조회 (체결된 주문)
            buy_orders = self.order_repo.get_filled_orders_by_symbol_and_side(
                symbol=symbol,
                side=OrderSide.BUY.value
            )
            
            if not buy_orders or len(buy_orders) == 0:
                logger.debug(f"매수 주문을 찾을 수 없음: {pair}")
                return None
            
            # 총 매수량과 총 비용 계산
            total_quantity = 0.0
            total_cost = 0.0
            
            for order in buy_orders:
                # 체결량과 평균 가격 가져오기
                filled_quantity = order.filled_quantity or 0.0
                avg_price = order.average_price or 0.0
                
                if filled_quantity > 0 and avg_price > 0:
                    total_quantity += filled_quantity
                    total_cost += filled_quantity * avg_price
            
            # 평균 가격 계산
            if total_quantity > 0:
                avg_buy_price = total_cost / total_quantity
                logger.debug(f"평균 매수 가격 계산됨: {pair}, 가격: {avg_buy_price:.4f}")
                return avg_buy_price
            else:
                logger.debug(f"체결된 매수량이 없음: {pair}")
                return None
            
        except Exception as e:
            logger.error(f"평균 매수 가격 조회 실패: {e}")
            return None
            
    async def start_trade_session(self, strategy: str, config: Dict[str, Any], 
                                is_dry_run: bool = False) -> Optional[str]:
        """
        거래 세션 시작
        
        Args:
            strategy: 전략 이름
            config: 세션 설정
            is_dry_run: 드라이 런 여부
            
        Returns:
            Optional[str]: 세션 ID 또는 None
        """
        try:
            # 세션 데이터 준비
            session_data = {
                'session_id': str(uuid.uuid4()),
                'strategy': strategy,
                'start_time': datetime.utcnow(),
                'config': config,
                'is_active': True,
                'is_dry_run': is_dry_run
            }
            
            # 세션 생성
            session = self.session_repo.create_session(session_data)
            
            logger.info(f"거래 세션 시작됨: {session.session_id}, 전략: {session.strategy}")
            
            return session.session_id
            
        except Exception as e:
            logger.error(f"거래 세션 시작 실패: {e}")
            return None
    
    async def end_trade_session(self, session_id: str, results: Dict[str, Any] = None) -> bool:
        """
        거래 세션 종료
        
        Args:
            session_id: 세션 ID
            results: 세션 결과 (선택 사항)
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 세션 종료
            session = self.session_repo.end_session(session_id, results)
            
            if not session:
                logger.warning(f"종료할 거래 세션을 찾을 수 없음: {session_id}")
                return False
            
            logger.info(f"거래 세션 종료됨: {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"거래 세션 종료 실패: {e}")
            return False
    
    async def update_session_stats(self, session_id: str, stats: Dict[str, Any]) -> bool:
        """
        세션 통계 업데이트
        
        Args:
            session_id: 세션 ID
            stats: 통계 데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 세션 업데이트
            session = self.session_repo.update_session(session_id, stats)
            
            if not session:
                logger.warning(f"업데이트할 거래 세션을 찾을 수 없음: {session_id}")
                return False
            
            logger.info(f"세션 통계 업데이트됨: {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"세션 통계 업데이트 실패: {e}")
            return False
