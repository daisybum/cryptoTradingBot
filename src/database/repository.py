"""
데이터베이스 저장소 모듈

이 모듈은 데이터베이스 모델과 애플리케이션 간의 상호작용을 관리하는 저장소 클래스를 제공합니다.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta

from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import Order, Fill, OrderError, IndicatorSnapshot, TradeSession
from src.database.models import OrderStatus, OrderType, OrderSide, TimeFrame
from src.database.connection import get_db_manager

logger = logging.getLogger(__name__)

class BaseRepository:
    """기본 저장소 클래스"""
    
    def __init__(self):
        """저장소 초기화"""
        self.db_manager = get_db_manager()
        if not self.db_manager:
            raise RuntimeError("데이터베이스 관리자가 초기화되지 않았습니다")
    
    def get_session(self) -> Session:
        """
        데이터베이스 세션 가져오기
        
        Returns:
            Session: SQLAlchemy 세션
        """
        return self.db_manager.get_pg_session()


class OrderRepository(BaseRepository):
    """주문 저장소 클래스"""
    
    def create_order(self, order_data: Dict[str, Any]) -> Order:
        """
        새 주문 생성
        
        Args:
            order_data: 주문 데이터
            
        Returns:
            Order: 생성된 주문 객체
        """
        try:
            # 주문 ID 생성 (없는 경우)
            if 'order_id' not in order_data or not order_data['order_id']:
                order_data['order_id'] = str(uuid.uuid4())
            
            # 남은 수량 계산 (없는 경우)
            if 'remaining_quantity' not in order_data or order_data['remaining_quantity'] is None:
                order_data['remaining_quantity'] = order_data['quantity']
            
            # 주문 객체 생성
            order = Order.from_dict(order_data)
            
            # 데이터베이스에 저장
            with self.get_session() as session:
                session.add(order)
                session.commit()
                session.refresh(order)
                
                logger.info(f"주문 생성됨: {order.order_id}, 심볼: {order.symbol}, 유형: {order.type.value if order.type else None}")
                
                return order
                
        except SQLAlchemyError as e:
            logger.error(f"주문 생성 실패: {e}")
            raise
    
    def update_order(self, order_id: str, update_data: Dict[str, Any]) -> Optional[Order]:
        """
        주문 업데이트
        
        Args:
            order_id: 주문 ID
            update_data: 업데이트할 데이터
            
        Returns:
            Optional[Order]: 업데이트된 주문 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 주문 조회
                order = session.query(Order).filter(Order.order_id == order_id).first()
                
                if not order:
                    logger.warning(f"업데이트할 주문을 찾을 수 없음: {order_id}")
                    return None
                
                # 필드 업데이트
                for key, value in update_data.items():
                    if hasattr(order, key):
                        # 열거형 처리
                        if key == 'status' and value is not None:
                            order.status = OrderStatus(value) if isinstance(value, str) else value
                        elif key == 'type' and value is not None:
                            order.type = OrderType(value) if isinstance(value, str) else value
                        elif key == 'side' and value is not None:
                            order.side = OrderSide(value) if isinstance(value, str) else value
                        elif key == 'timeframe' and value is not None:
                            order.timeframe = TimeFrame(value) if isinstance(value, str) else value
                        else:
                            setattr(order, key, value)
                
                # 업데이트 시간 갱신
                order.updated_at = datetime.utcnow()
                
                session.commit()
                session.refresh(order)
                
                logger.info(f"주문 업데이트됨: {order.order_id}, 상태: {order.status.value if order.status else None}")
                
                return order
                
        except SQLAlchemyError as e:
            logger.error(f"주문 업데이트 실패: {e}")
            raise
    
    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """
        ID로 주문 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Optional[Order]: 주문 객체 또는 None
        """
        try:
            with self.get_session() as session:
                order = session.query(Order).filter(Order.order_id == order_id).first()
                
                if not order:
                    logger.debug(f"주문을 찾을 수 없음: {order_id}")
                
                return order
                
        except SQLAlchemyError as e:
            logger.error(f"주문 조회 실패: {e}")
            raise
            
    def get_filled_orders_by_symbol_and_side(self, symbol: str, side: str) -> List[Order]:
        """
        특정 심볼과 주문 방향에 대한 체결된 주문 조회
        
        Args:
            symbol: 심볼 (예: BTCUSDT)
            side: 주문 방향 (buy/sell)
            
        Returns:
            List[Order]: 체결된 주문 목록
        """
        try:
            with self.get_session() as session:
                # 체결된 주문만 조회
                orders = session.query(Order).filter(
                    and_(
                        Order.symbol == symbol,
                        Order.side == OrderSide(side) if isinstance(side, str) else side,
                        Order.status == OrderStatus.FILLED,
                        Order.filled_quantity > 0
                    )
                ).order_by(desc(Order.created_at)).all()
                
                return orders
                
        except SQLAlchemyError as e:
            logger.error(f"체결된 주문 조회 실패: {e}")
            return []
    
# DEAD CODE:     def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        """
        클라이언트 ID로 주문 조회
        
        Args:
            client_order_id: 클라이언트 주문 ID
            
        Returns:
            Optional[Order]: 주문 객체 또는 None
        """
        try:
            with self.get_session() as session:
                order = session.query(Order).filter(Order.client_order_id == client_order_id).first()
                
                if not order:
                    logger.debug(f"클라이언트 ID로 주문을 찾을 수 없음: {client_order_id}")
                
                return order
                
        except SQLAlchemyError as e:
            logger.error(f"클라이언트 ID로 주문 조회 실패: {e}")
            raise
    
# DEAD CODE:     def get_order_by_exchange_id(self, exchange_order_id: str) -> Optional[Order]:
        """
        거래소 ID로 주문 조회
        
        Args:
            exchange_order_id: 거래소 주문 ID
            
        Returns:
            Optional[Order]: 주문 객체 또는 None
        """
        try:
            with self.get_session() as session:
                order = session.query(Order).filter(Order.exchange_order_id == exchange_order_id).first()
                
                if not order:
                    logger.debug(f"거래소 ID로 주문을 찾을 수 없음: {exchange_order_id}")
                
                return order
                
        except SQLAlchemyError as e:
            logger.error(f"거래소 ID로 주문 조회 실패: {e}")
            raise
    
# DEAD CODE:     def get_orders_by_status(self, status: Union[OrderStatus, str], symbol: Optional[str] = None) -> List[Order]:
        """
        상태별 주문 조회
        
        Args:
            status: 주문 상태
            symbol: 심볼 (선택 사항)
            
        Returns:
            List[Order]: 주문 목록
        """
        try:
            with self.get_session() as session:
                query = session.query(Order)
                
                # 상태 필터링
                if isinstance(status, str):
                    status = OrderStatus(status)
                
                query = query.filter(Order.status == status)
                
                # 심볼 필터링 (있는 경우)
                if symbol:
                    query = query.filter(Order.symbol == symbol)
                
                # 최신 주문부터 정렬
                query = query.order_by(desc(Order.created_at))
                
                orders = query.all()
                
                return orders
                
        except SQLAlchemyError as e:
            logger.error(f"상태별 주문 조회 실패: {e}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        미체결 주문 조회
        
        Args:
            symbol: 심볼 (선택 사항)
            
        Returns:
            List[Order]: 미체결 주문 목록
        """
        try:
            with self.get_session() as session:
                query = session.query(Order)
                
                # 미체결 상태 필터링
                query = query.filter(or_(
                    Order.status == OrderStatus.OPEN,
                    Order.status == OrderStatus.PARTIALLY_FILLED
                ))
                
                # 심볼 필터링 (있는 경우)
                if symbol:
                    query = query.filter(Order.symbol == symbol)
                
                # 최신 주문부터 정렬
                query = query.order_by(desc(Order.created_at))
                
                orders = query.all()
                
                return orders
                
        except SQLAlchemyError as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            raise
    
# DEAD CODE:     def get_orders_by_symbol(self, symbol: str, limit: int = 100) -> List[Order]:
        """
        심볼별 주문 조회
        
        Args:
            symbol: 심볼
            limit: 최대 결과 수
            
        Returns:
            List[Order]: 주문 목록
        """
        try:
            with self.get_session() as session:
                query = session.query(Order).filter(Order.symbol == symbol)
                
                # 최신 주문부터 정렬
                query = query.order_by(desc(Order.created_at))
                
                # 결과 제한
                query = query.limit(limit)
                
                orders = query.all()
                
                return orders
                
        except SQLAlchemyError as e:
            logger.error(f"심볼별 주문 조회 실패: {e}")
            raise
    
    def add_fill(self, order_id: str, fill_data: Dict[str, Any]) -> Optional[Fill]:
        """
        체결 추가
        
        Args:
            order_id: 주문 ID
            fill_data: 체결 데이터
            
        Returns:
            Optional[Fill]: 추가된 체결 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 주문 조회
                order = session.query(Order).filter(Order.order_id == order_id).first()
                
                if not order:
                    logger.warning(f"체결을 추가할 주문을 찾을 수 없음: {order_id}")
                    return None
                
                # 체결 ID 생성 (없는 경우)
                if 'fill_id' not in fill_data or not fill_data['fill_id']:
                    fill_data['fill_id'] = str(uuid.uuid4())
                
                # 체결 객체 생성
                fill = Fill(
                    order_id=order_id,
                    fill_id=fill_data['fill_id'],
                    price=fill_data['price'],
                    quantity=fill_data['quantity'],
                    fee=fill_data.get('fee'),
                    fee_asset=fill_data.get('fee_asset'),
                    timestamp=fill_data.get('timestamp', datetime.utcnow()),
                    is_maker=fill_data.get('is_maker', False)
                )
                
                # 데이터베이스에 저장
                session.add(fill)
                
                # 주문 상태 업데이트
                order.filled_quantity += fill.quantity
                order.remaining_quantity = max(0, order.quantity - order.filled_quantity)
                
                # 평균 가격 계산
                if order.average_price is None:
                    order.average_price = fill.price
                else:
                    # 가중 평균 계산
                    total_filled_before = order.filled_quantity - fill.quantity
                    if total_filled_before > 0:
                        order.average_price = (
                            (order.average_price * total_filled_before) + (fill.price * fill.quantity)
                        ) / order.filled_quantity
                
                # 주문 상태 업데이트
                if abs(order.filled_quantity - order.quantity) < 1e-8:  # 부동 소수점 비교
                    order.status = OrderStatus.FILLED
                elif order.filled_quantity > 0:
                    order.status = OrderStatus.PARTIALLY_FILLED
                
                order.updated_at = datetime.utcnow()
                
                session.commit()
                session.refresh(fill)
                
                logger.info(f"체결 추가됨: {fill.fill_id}, 주문: {order_id}, 수량: {fill.quantity}, 가격: {fill.price}")
                
                return fill
                
        except SQLAlchemyError as e:
            logger.error(f"체결 추가 실패: {e}")
            raise
    
    def add_error(self, order_id: str, error_data: Dict[str, Any]) -> Optional[OrderError]:
        """
        오류 추가
        
        Args:
            order_id: 주문 ID
            error_data: 오류 데이터
            
        Returns:
            Optional[OrderError]: 추가된 오류 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 주문 조회
                order = session.query(Order).filter(Order.order_id == order_id).first()
                
                if not order:
                    logger.warning(f"오류를 추가할 주문을 찾을 수 없음: {order_id}")
                    return None
                
                # 오류 객체 생성
                error = OrderError(
                    order_id=order_id,
                    error_code=error_data.get('error_code'),
                    error_message=error_data['error_message'],
                    error_details=error_data.get('error_details'),
                    timestamp=error_data.get('timestamp', datetime.utcnow())
                )
                
                # 데이터베이스에 저장
                session.add(error)
                
                # 주문 상태 업데이트 (선택 사항)
                if error_data.get('update_status', False):
                    order.status = OrderStatus.ERROR
                    order.updated_at = datetime.utcnow()
                
                session.commit()
                session.refresh(error)
                
                logger.info(f"오류 추가됨: 주문: {order_id}, 코드: {error.error_code}, 메시지: {error.error_message}")
                
                return error
                
        except SQLAlchemyError as e:
            logger.error(f"오류 추가 실패: {e}")
            raise
    
# DEAD CODE:     def get_order_statistics(self, symbol: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        주문 통계 조회
        
        Args:
            symbol: 심볼 (선택 사항)
            days: 일수
            
        Returns:
            Dict[str, Any]: 통계 정보
        """
        try:
            with self.get_session() as session:
                # 시간 범위 계산
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # 기본 쿼리
                query = session.query(Order).filter(Order.created_at >= start_date)
                
                # 심볼 필터링 (있는 경우)
                if symbol:
                    query = query.filter(Order.symbol == symbol)
                
                # 전체 주문 수
                total_orders = query.count()
                
                # 상태별 주문 수
                status_counts = {}
                for status in OrderStatus:
                    count = query.filter(Order.status == status).count()
                    status_counts[status.value] = count
                
                # 유형별 주문 수
                type_counts = {}
                for order_type in OrderType:
                    count = query.filter(Order.type == order_type).count()
                    type_counts[order_type.value] = count
                
                # 방향별 주문 수
                side_counts = {}
                for side in OrderSide:
                    count = query.filter(Order.side == side).count()
                    side_counts[side.value] = count
                
                # 일별 주문 수
                daily_counts = []
                for i in range(days):
                    day_start = end_date - timedelta(days=i+1)
                    day_end = end_date - timedelta(days=i)
                    count = query.filter(Order.created_at >= day_start, Order.created_at < day_end).count()
                    daily_counts.append({
                        'date': day_start.date().isoformat(),
                        'count': count
                    })
                
                # 결과 반환
                return {
                    'total_orders': total_orders,
                    'status_counts': status_counts,
                    'type_counts': type_counts,
                    'side_counts': side_counts,
                    'daily_counts': daily_counts,
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'days': days
                    }
                }
                
        except SQLAlchemyError as e:
            logger.error(f"주문 통계 조회 실패: {e}")
            raise


class IndicatorRepository(BaseRepository):
    """지표 저장소 클래스"""
    
    def create_snapshot(self, snapshot_data: Dict[str, Any]) -> IndicatorSnapshot:
        """
        지표 스냅샷 생성
        
        Args:
            snapshot_data: 스냅샷 데이터
            
        Returns:
            IndicatorSnapshot: 생성된 스냅샷 객체
        """
        try:
            # 시간 프레임 변환 (문자열인 경우)
            if 'timeframe' in snapshot_data and isinstance(snapshot_data['timeframe'], str):
                snapshot_data['timeframe'] = TimeFrame(snapshot_data['timeframe'])
            
            # 타임스탬프 변환 (문자열인 경우)
            if 'timestamp' in snapshot_data and isinstance(snapshot_data['timestamp'], str):
                snapshot_data['timestamp'] = datetime.fromisoformat(snapshot_data['timestamp'])
            
            # 스냅샷 객체 생성
            snapshot = IndicatorSnapshot(**snapshot_data)
            
            # 데이터베이스에 저장
            with self.get_session() as session:
                session.add(snapshot)
                session.commit()
                session.refresh(snapshot)
                
                logger.debug(f"지표 스냅샷 생성됨: 심볼: {snapshot.symbol}, 시간 프레임: {snapshot.timeframe.value if snapshot.timeframe else None}")
                
                return snapshot
                
        except SQLAlchemyError as e:
            logger.error(f"지표 스냅샷 생성 실패: {e}")
            raise
    
# DEAD CODE:     def get_snapshots(self, symbol: str, timeframe: Union[TimeFrame, str], 
                     start_time: Optional[datetime] = None, 
                     end_time: Optional[datetime] = None,
                     limit: int = 100) -> List[IndicatorSnapshot]:
        """
        지표 스냅샷 조회
        
        Args:
            symbol: 심볼
            timeframe: 시간 프레임
            start_time: 시작 시간 (선택 사항)
            end_time: 종료 시간 (선택 사항)
            limit: 최대 결과 수
            
        Returns:
            List[IndicatorSnapshot]: 스냅샷 목록
        """
        try:
            with self.get_session() as session:
                # 시간 프레임 변환 (문자열인 경우)
                if isinstance(timeframe, str):
                    timeframe = TimeFrame(timeframe)
                
                # 기본 쿼리
                query = session.query(IndicatorSnapshot).filter(
                    IndicatorSnapshot.symbol == symbol,
                    IndicatorSnapshot.timeframe == timeframe
                )
                
                # 시간 범위 필터링
                if start_time:
                    query = query.filter(IndicatorSnapshot.timestamp >= start_time)
                
                if end_time:
                    query = query.filter(IndicatorSnapshot.timestamp <= end_time)
                
                # 타임스탬프 기준 정렬
                query = query.order_by(desc(IndicatorSnapshot.timestamp))
                
                # 결과 제한
                query = query.limit(limit)
                
                snapshots = query.all()
                
                return snapshots
                
        except SQLAlchemyError as e:
            logger.error(f"지표 스냅샷 조회 실패: {e}")
            raise
    
    def get_latest_snapshot(self, symbol: str, timeframe: Union[TimeFrame, str]) -> Optional[IndicatorSnapshot]:
        """
        최신 지표 스냅샷 조회
        
        Args:
            symbol: 심볼
            timeframe: 시간 프레임
            
        Returns:
            Optional[IndicatorSnapshot]: 스냅샷 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 시간 프레임 변환 (문자열인 경우)
                if isinstance(timeframe, str):
                    timeframe = TimeFrame(timeframe)
                
                # 최신 스냅샷 조회
                snapshot = session.query(IndicatorSnapshot).filter(
                    IndicatorSnapshot.symbol == symbol,
                    IndicatorSnapshot.timeframe == timeframe
                ).order_by(desc(IndicatorSnapshot.timestamp)).first()
                
                return snapshot
                
        except SQLAlchemyError as e:
            logger.error(f"최신 지표 스냅샷 조회 실패: {e}")
            raise


class TradeSessionRepository(BaseRepository):
    """거래 세션 저장소 클래스"""
    
    def create_session(self, session_data: Dict[str, Any]) -> TradeSession:
        """
        거래 세션 생성
        
        Args:
            session_data: 세션 데이터
            
        Returns:
            TradeSession: 생성된 세션 객체
        """
        try:
            # 세션 ID 생성 (없는 경우)
            if 'session_id' not in session_data or not session_data['session_id']:
                session_data['session_id'] = str(uuid.uuid4())
            
            # 세션 객체 생성
            session_obj = TradeSession(**session_data)
            
            # 데이터베이스에 저장
            with self.get_session() as session:
                session.add(session_obj)
                session.commit()
                session.refresh(session_obj)
                
                logger.info(f"거래 세션 생성됨: {session_obj.session_id}, 전략: {session_obj.strategy}")
                
                return session_obj
                
        except SQLAlchemyError as e:
            logger.error(f"거래 세션 생성 실패: {e}")
            raise
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> Optional[TradeSession]:
        """
        거래 세션 업데이트
        
        Args:
            session_id: 세션 ID
            update_data: 업데이트할 데이터
            
        Returns:
            Optional[TradeSession]: 업데이트된 세션 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 세션 조회
                session_obj = session.query(TradeSession).filter(TradeSession.session_id == session_id).first()
                
                if not session_obj:
                    logger.warning(f"업데이트할 거래 세션을 찾을 수 없음: {session_id}")
                    return None
                
                # 필드 업데이트
                for key, value in update_data.items():
                    if hasattr(session_obj, key):
                        setattr(session_obj, key, value)
                
                session.commit()
                session.refresh(session_obj)
                
                logger.info(f"거래 세션 업데이트됨: {session_obj.session_id}")
                
                return session_obj
                
        except SQLAlchemyError as e:
            logger.error(f"거래 세션 업데이트 실패: {e}")
            raise
    
    def end_session(self, session_id: str, results: Dict[str, Any] = None) -> Optional[TradeSession]:
        """
        거래 세션 종료
        
        Args:
            session_id: 세션 ID
            results: 세션 결과 (선택 사항)
            
        Returns:
            Optional[TradeSession]: 업데이트된 세션 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 세션 조회
                session_obj = session.query(TradeSession).filter(TradeSession.session_id == session_id).first()
                
                if not session_obj:
                    logger.warning(f"종료할 거래 세션을 찾을 수 없음: {session_id}")
                    return None
                
                # 세션 종료 시간 설정
                session_obj.end_time = datetime.utcnow()
                session_obj.is_active = False
                
                # 결과 업데이트 (있는 경우)
                if results:
                    for key, value in results.items():
                        if hasattr(session_obj, key):
                            setattr(session_obj, key, value)
                
                session.commit()
                session.refresh(session_obj)
                
                logger.info(f"거래 세션 종료됨: {session_obj.session_id}")
                
                return session_obj
                
        except SQLAlchemyError as e:
            logger.error(f"거래 세션 종료 실패: {e}")
            raise
    
# DEAD CODE:     def get_active_sessions(self) -> List[TradeSession]:
        """
        활성 거래 세션 조회
        
        Returns:
            List[TradeSession]: 활성 세션 목록
        """
        try:
            with self.get_session() as session:
                # 활성 세션 조회
                sessions = session.query(TradeSession).filter(TradeSession.is_active == True).all()
                
                return sessions
                
        except SQLAlchemyError as e:
            logger.error(f"활성 거래 세션 조회 실패: {e}")
            raise
    
# DEAD CODE:     def get_session_by_id(self, session_id: str) -> Optional[TradeSession]:
        """
        ID로 거래 세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Optional[TradeSession]: 세션 객체 또는 None
        """
        try:
            with self.get_session() as session:
                # 세션 조회
                session_obj = session.query(TradeSession).filter(TradeSession.session_id == session_id).first()
                
                if not session_obj:
                    logger.debug(f"거래 세션을 찾을 수 없음: {session_id}")
                
                return session_obj
                
        except SQLAlchemyError as e:
            logger.error(f"거래 세션 조회 실패: {e}")
            raise
