"""
데이터 액세스 레이어 (DAL) 확장 모듈

이 모듈은 추가적인 데이터 액세스 레이어 클래스를 제공합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Union
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from sqlalchemy.orm import Session
# DEAD CODE: from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from src.database.connection import get_db_manager
from src.database.models import (
    Base, Order, Fill, OrderError, IndicatorSnapshot, TradeSession,
    Trade, EquityCurve, ParamSet, StatsDaily
)
from src.database.dal import BaseDAL

logger = logging.getLogger(__name__)


# DEAD CODE: class ParamSetDAL(BaseDAL[ParamSet]):
    """
    파라미터 세트 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(ParamSet)
    
# DEAD CODE:     def get_active_params(self, strategy: str) -> Optional[ParamSet]:
        """
        활성화된 파라미터 세트 조회
        
        Args:
            strategy: 전략 이름
            
        Returns:
            Optional[ParamSet]: 활성화된 파라미터 세트 또는 None
        """
        with self.get_session() as session:
            return session.query(ParamSet).filter(
                ParamSet.strategy == strategy,
                ParamSet.is_active == True
            ).first()
    
# DEAD CODE:     def get_params_by_strategy(self, strategy: str) -> List[ParamSet]:
        """
        전략별 파라미터 세트 조회
        
        Args:
            strategy: 전략 이름
            
        Returns:
            List[ParamSet]: 파라미터 세트 목록
        """
        with self.get_session() as session:
            return session.query(ParamSet).filter(
                ParamSet.strategy == strategy
            ).order_by(desc(ParamSet.created_at)).all()
    
# DEAD CODE:     def activate_param_set(self, param_id: int) -> bool:
        """
        파라미터 세트 활성화
        
        Args:
            param_id: 파라미터 세트 ID
            
        Returns:
            bool: 활성화 성공 여부
        """
        with self.get_session() as session:
            # 현재 활성화된 파라미터 세트 비활성화
            param_set = session.query(ParamSet).filter(ParamSet.id == param_id).first()
            if not param_set:
                return False
                
            # 같은 전략의 모든 파라미터 세트 비활성화
            session.query(ParamSet).filter(
                ParamSet.strategy == param_set.strategy
            ).update({ParamSet.is_active: False})
            
            # 선택한 파라미터 세트 활성화
            param_set.is_active = True
            session.flush()
            
            return True


# DEAD CODE: class StatsDailyDAL(BaseDAL[StatsDaily]):
    """
    일일 통계 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(StatsDaily)
    
    def get_by_date(self, target_date: date, strategy: Optional[str] = None, 
                   pair: Optional[str] = None) -> Optional[StatsDaily]:
        """
        날짜별 통계 조회
        
        Args:
            target_date: 대상 날짜
            strategy: 전략 이름 (선택 사항)
            pair: 거래 쌍 (선택 사항)
            
        Returns:
            Optional[StatsDaily]: 일일 통계 또는 None
        """
        with self.get_session() as session:
            query = session.query(StatsDaily).filter(StatsDaily.date == target_date)
            
            if strategy:
                query = query.filter(StatsDaily.strategy == strategy)
            
            if pair:
                query = query.filter(StatsDaily.pair == pair)
                
            return query.first()
    
# DEAD CODE:     def get_stats_by_date_range(self, start_date: date, end_date: date, 
                               strategy: Optional[str] = None,
                               pair: Optional[str] = None) -> List[StatsDaily]:
        """
        날짜 범위별 통계 조회
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 전략 이름 (선택 사항)
            pair: 거래 쌍 (선택 사항)
            
        Returns:
            List[StatsDaily]: 일일 통계 목록
        """
        with self.get_session() as session:
            query = session.query(StatsDaily).filter(
                StatsDaily.date >= start_date,
                StatsDaily.date <= end_date
            )
            
            if strategy:
                query = query.filter(StatsDaily.strategy == strategy)
            
            if pair:
                query = query.filter(StatsDaily.pair == pair)
                
            return query.order_by(StatsDaily.date).all()
    
# DEAD CODE:     def calculate_daily_stats(self, target_date: date, strategy: Optional[str] = None,
                             pair: Optional[str] = None) -> Optional[StatsDaily]:
        """
        일일 통계 계산 및 저장
        
        Args:
            target_date: 대상 날짜
            strategy: 전략 이름 (선택 사항)
            pair: 거래 쌍 (선택 사항)
            
        Returns:
            Optional[StatsDaily]: 계산된 일일 통계 또는 None
        """
        # 날짜 범위 설정
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        # 거래 데이터 조회
        trade_dal = TradeDAL()
        trades = trade_dal.get_trades_by_date_range(
            start_date=start_datetime,
            end_date=end_datetime,
            strategy=strategy,
            pair=pair
        )
        
        if not trades:
            logger.info(f"계산할 거래 데이터가 없습니다: {target_date}")
            return None
        
        # 통계 계산
        total_trades = len(trades)
        win_trades = [t for t in trades if t.pnl and t.pnl > 0]
        loss_trades = [t for t in trades if t.pnl and t.pnl <= 0]
        
        win_count = len(win_trades)
        loss_count = len(loss_trades)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in trades if t.pnl) or 0
        
        # 수익 요소 계산
        total_profit = sum(t.pnl for t in win_trades if t.pnl) or 0
        total_loss = sum(abs(t.pnl) for t in loss_trades if t.pnl) or 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # 평균 거래 지속 시간
        durations = []
        for t in trades:
            if t.open_time and t.close_time:
                duration = (t.close_time - t.open_time).total_seconds() / 60  # 분 단위
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 평균 이익/손실 거래
        avg_profit = sum(t.pnl for t in win_trades if t.pnl) / win_count if win_count > 0 else 0
        avg_loss = sum(t.pnl for t in loss_trades if t.pnl) / loss_count if loss_count > 0 else 0
        
        # 최대 드로다운 계산 (해당 날짜의 자산 곡선에서)
        equity_dal = EquityCurveDAL()
        max_drawdown = equity_dal.get_max_drawdown(
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        # 기존 통계 확인
        existing_stats = self.get_by_date(target_date, strategy, pair)
        
        # 통계 데이터 생성 또는 업데이트
        stats_data = {
            'date': target_date,
            'strategy': strategy,
            'pair': pair,
            'trades_count': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'total_pnl_pct': None,  # 별도 계산 필요
            'max_drawdown': max_drawdown,
            'avg_trade_duration': avg_duration,
            'avg_profit_trade': avg_profit,
            'avg_loss_trade': avg_loss
        }
        
        if existing_stats:
            return self.update(existing_stats.id, stats_data)
        else:
            return self.create(stats_data)


# DEAD CODE: class OrderDAL(BaseDAL[Order]):
    """
    주문 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(Order)
    
# DEAD CODE:     def get_by_order_id(self, order_id: str) -> Optional[Order]:
        """
        주문 ID로 주문 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Optional[Order]: 조회된 주문 또는 None
        """
        with self.get_session() as session:
            return session.query(Order).filter(Order.order_id == order_id).first()
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        미체결 주문 조회
        
        Args:
            symbol: 거래 쌍 (선택 사항)
            
        Returns:
            List[Order]: 미체결 주문 목록
        """
        with self.get_session() as session:
            query = session.query(Order).filter(
                Order.status.in_(['pending', 'open', 'partially_filled'])
            )
            
            if symbol:
                query = query.filter(Order.symbol == symbol)
                
            return query.all()
    
# DEAD CODE:     def get_orders_by_date_range(self, start_date: datetime, end_date: datetime, 
                                symbol: Optional[str] = None,
                                status: Optional[str] = None) -> List[Order]:
        """
        날짜 범위로 주문 조회
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            symbol: 거래 쌍 (선택 사항)
            status: 주문 상태 (선택 사항)
            
        Returns:
            List[Order]: 주문 목록
        """
        with self.get_session() as session:
            query = session.query(Order).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
            
            if symbol:
                query = query.filter(Order.symbol == symbol)
            
            if status:
                query = query.filter(Order.status == status)
                
            return query.order_by(Order.created_at).all()


# DEAD CODE: class FillDAL(BaseDAL[Fill]):
    """
    체결 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(Fill)
    
# DEAD CODE:     def get_by_fill_id(self, fill_id: str) -> Optional[Fill]:
        """
        체결 ID로 체결 조회
        
        Args:
            fill_id: 체결 ID
            
        Returns:
            Optional[Fill]: 조회된 체결 또는 None
        """
        with self.get_session() as session:
            return session.query(Fill).filter(Fill.fill_id == fill_id).first()
    
# DEAD CODE:     def get_fills_by_order_id(self, order_id: str) -> List[Fill]:
        """
        주문 ID로 체결 목록 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            List[Fill]: 체결 목록
        """
        with self.get_session() as session:
            return session.query(Fill).filter(
                Fill.order_id == order_id
            ).order_by(Fill.timestamp).all()


# DEAD CODE: class OrderErrorDAL(BaseDAL[OrderError]):
    """
    주문 오류 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(OrderError)
    
# DEAD CODE:     def get_errors_by_order_id(self, order_id: str) -> List[OrderError]:
        """
        주문 ID로 오류 목록 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            List[OrderError]: 오류 목록
        """
        with self.get_session() as session:
            return session.query(OrderError).filter(
                OrderError.order_id == order_id
            ).order_by(desc(OrderError.timestamp)).all()
    
# DEAD CODE:     def get_recent_errors(self, limit: int = 50) -> List[OrderError]:
        """
        최근 오류 목록 조회
        
        Args:
            limit: 최대 레코드 수
            
        Returns:
            List[OrderError]: 오류 목록
        """
        with self.get_session() as session:
            return session.query(OrderError).order_by(
                desc(OrderError.timestamp)
            ).limit(limit).all()


# DEAD CODE: class IndicatorSnapshotDAL(BaseDAL[IndicatorSnapshot]):
    """
    지표 스냅샷 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(IndicatorSnapshot)
    
    def get_latest_snapshot(self, symbol: str, timeframe: str) -> Optional[IndicatorSnapshot]:
        """
        최신 지표 스냅샷 조회
        
        Args:
            symbol: 거래 쌍
            timeframe: 시간 프레임
            
        Returns:
            Optional[IndicatorSnapshot]: 지표 스냅샷 또는 None
        """
        with self.get_session() as session:
            return session.query(IndicatorSnapshot).filter(
                IndicatorSnapshot.symbol == symbol,
                IndicatorSnapshot.timeframe == timeframe
            ).order_by(desc(IndicatorSnapshot.timestamp)).first()
    
# DEAD CODE:     def get_snapshots_by_date_range(self, symbol: str, timeframe: str,
                                   start_date: datetime, end_date: datetime) -> List[IndicatorSnapshot]:
        """
        날짜 범위로 지표 스냅샷 조회
        
        Args:
            symbol: 거래 쌍
            timeframe: 시간 프레임
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            List[IndicatorSnapshot]: 지표 스냅샷 목록
        """
        with self.get_session() as session:
            return session.query(IndicatorSnapshot).filter(
                IndicatorSnapshot.symbol == symbol,
                IndicatorSnapshot.timeframe == timeframe,
                IndicatorSnapshot.timestamp >= start_date,
                IndicatorSnapshot.timestamp <= end_date
            ).order_by(IndicatorSnapshot.timestamp).all()


# DEAD CODE: class TradeSessionDAL(BaseDAL[TradeSession]):
    """
    거래 세션 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(TradeSession)
    
# DEAD CODE:     def get_by_session_id(self, session_id: str) -> Optional[TradeSession]:
        """
        세션 ID로 거래 세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Optional[TradeSession]: 조회된 거래 세션 또는 None
        """
        with self.get_session() as session:
            return session.query(TradeSession).filter(
                TradeSession.session_id == session_id
            ).first()
    
# DEAD CODE:     def get_active_sessions(self) -> List[TradeSession]:
        """
        활성 거래 세션 조회
        
        Returns:
            List[TradeSession]: 활성 거래 세션 목록
        """
        with self.get_session() as session:
            return session.query(TradeSession).filter(
                TradeSession.is_active == True
            ).all()
    
    def end_session(self, session_id: str, final_balance: float) -> bool:
        """
        거래 세션 종료
        
        Args:
            session_id: 세션 ID
            final_balance: 최종 잔고
            
        Returns:
            bool: 종료 성공 여부
        """
        with self.get_session() as session:
            trade_session = session.query(TradeSession).filter(
                TradeSession.session_id == session_id
            ).first()
            
            if not trade_session:
                return False
            
            trade_session.is_active = False
            trade_session.end_time = datetime.utcnow()
            trade_session.final_balance = final_balance
            
            # PnL 계산
            if trade_session.initial_balance > 0:
                trade_session.pnl = final_balance - trade_session.initial_balance
                trade_session.pnl_pct = (trade_session.pnl / trade_session.initial_balance) * 100
            
            session.flush()
            return True
