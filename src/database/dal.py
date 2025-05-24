"""
데이터 액세스 레이어 (DAL) 모듈

이 모듈은 데이터베이스 작업을 추상화하는 클래스를 제공합니다.
각 모델에 대한 CRUD 작업을 간소화하고 코드 재사용성을 높입니다.
"""

import logging
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Union
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from src.database.connection import get_db_manager
from src.database.models import (
    Base, Order, Fill, OrderError, IndicatorSnapshot, TradeSession,
    Trade, EquityCurve, ParamSet, StatsDaily
)

logger = logging.getLogger(__name__)

# 제네릭 타입 변수 정의
T = TypeVar('T', bound=Base)


class BaseDAL(Generic[T]):
    """
    기본 데이터 액세스 레이어
    
    모든 모델 DAL의 기본 클래스로, 공통 CRUD 작업을 제공합니다.
    """
    
    def __init__(self, model: Type[T]):
        """
        초기화
        
        Args:
            model: 데이터 모델 클래스
        """
        self.model = model
        self.db_manager = get_db_manager()
        
    @contextmanager
    def get_session(self) -> Session:
        """
        데이터베이스 세션 컨텍스트 관리자
        
        Yields:
            Session: 데이터베이스 세션
        """
        if not self.db_manager or not self.db_manager.pg_session_factory:
            raise RuntimeError("데이터베이스 관리자가 초기화되지 않았습니다.")
            
        session = self.db_manager.pg_session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"데이터베이스 작업 실패: {e}")
            raise
        finally:
            session.close()
    
    def create(self, data: Dict[str, Any]) -> T:
        """
        새 레코드 생성
        
        Args:
            data: 레코드 데이터
            
        Returns:
            T: 생성된 레코드
        """
        with self.get_session() as session:
            record = self.model(**data)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record
    
    def get_by_id(self, record_id: int) -> Optional[T]:
        """
        ID로 레코드 조회
        
        Args:
            record_id: 레코드 ID
            
        Returns:
            Optional[T]: 조회된 레코드 또는 None
        """
        with self.get_session() as session:
            return session.query(self.model).filter(self.model.id == record_id).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        모든 레코드 조회
        
        Args:
            limit: 최대 레코드 수
            offset: 시작 오프셋
            
        Returns:
            List[T]: 레코드 목록
        """
        with self.get_session() as session:
            return session.query(self.model).limit(limit).offset(offset).all()
    
    def update(self, record_id: int, data: Dict[str, Any]) -> Optional[T]:
        """
        레코드 업데이트
        
        Args:
            record_id: 레코드 ID
            data: 업데이트할 데이터
            
        Returns:
            Optional[T]: 업데이트된 레코드 또는 None
        """
        with self.get_session() as session:
            record = session.query(self.model).filter(self.model.id == record_id).first()
            if record:
                for key, value in data.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                session.flush()
                session.refresh(record)
                return record
            return None
    
    def delete(self, record_id: int) -> bool:
        """
        레코드 삭제
        
        Args:
            record_id: 레코드 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        with self.get_session() as session:
            record = session.query(self.model).filter(self.model.id == record_id).first()
            if record:
                session.delete(record)
                return True
            return False
    
    def count(self) -> int:
        """
        전체 레코드 수 조회
        
        Returns:
            int: 레코드 수
        """
        with self.get_session() as session:
            return session.query(func.count(self.model.id)).scalar() or 0


class TradeDAL(BaseDAL[Trade]):
    """
    거래 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(Trade)
    
    def get_by_trade_id(self, trade_id: str) -> Optional[Trade]:
        """
        거래 ID로 거래 조회
        
        Args:
            trade_id: 거래 ID
            
        Returns:
            Optional[Trade]: 조회된 거래 또는 None
        """
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.trade_id == trade_id).first()
    
    def get_open_trades(self, strategy: Optional[str] = None) -> List[Trade]:
        """
        오픈된 거래 조회
        
        Args:
            strategy: 전략 이름 (선택 사항)
            
        Returns:
            List[Trade]: 오픈된 거래 목록
        """
        with self.get_session() as session:
            query = session.query(Trade).filter(Trade.status == 'open')
            if strategy:
                query = query.filter(Trade.strategy == strategy)
            return query.all()
    
    def get_trades_by_date_range(self, start_date: datetime, end_date: datetime, 
                                strategy: Optional[str] = None, pair: Optional[str] = None) -> List[Trade]:
        """
        날짜 범위로 거래 조회
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 전략 이름 (선택 사항)
            pair: 거래 쌍 (선택 사항)
            
        Returns:
            List[Trade]: 거래 목록
        """
        with self.get_session() as session:
            query = session.query(Trade).filter(
                Trade.open_time >= start_date,
                Trade.open_time <= end_date
            )
            
            if strategy:
                query = query.filter(Trade.strategy == strategy)
            
            if pair:
                query = query.filter(Trade.pair == pair)
                
            return query.order_by(Trade.open_time).all()
    
    def get_trades_by_status(self, status: str, limit: int = 100) -> List[Trade]:
        """
        상태별 거래 조회
        
        Args:
            status: 거래 상태
            limit: 최대 레코드 수
            
        Returns:
            List[Trade]: 거래 목록
        """
        with self.get_session() as session:
            return session.query(Trade).filter(
                Trade.status == status
            ).order_by(desc(Trade.open_time)).limit(limit).all()
    
    def get_profit_stats(self, strategy: Optional[str] = None, 
                        pair: Optional[str] = None, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        수익 통계 조회
        
        Args:
            strategy: 전략 이름 (선택 사항)
            pair: 거래 쌍 (선택 사항)
            start_date: 시작 날짜 (선택 사항)
            end_date: 종료 날짜 (선택 사항)
            
        Returns:
            Dict[str, Any]: 수익 통계
        """
        with self.get_session() as session:
            # 기본 필터 조건
            conditions = [Trade.status == 'closed']
            
            # 추가 필터 조건
            if strategy:
                conditions.append(Trade.strategy == strategy)
            if pair:
                conditions.append(Trade.pair == pair)
            if start_date:
                conditions.append(Trade.close_time >= start_date)
            if end_date:
                conditions.append(Trade.close_time <= end_date)
            
            # 쿼리 실행
            query = session.query(
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.pnl).label('total_pnl'),
                func.avg(Trade.pnl).label('avg_pnl'),
                func.sum(Trade.pnl > 0).label('winning_trades'),
                func.sum(Trade.pnl <= 0).label('losing_trades')
            ).filter(*conditions)
            
            result = query.first()
            
            if not result or not result.total_trades:
                return {
                    'total_trades': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0
                }
            
            # 승률 계산
            win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
            
            # 수익 요소 계산 (총 이익 / 총 손실)
            profit_query = session.query(func.sum(Trade.pnl)).filter(
                Trade.pnl > 0, *conditions
            ).scalar() or 0
            
            loss_query = session.query(func.sum(Trade.pnl.op('abs')())).filter(
                Trade.pnl < 0, *conditions
            ).scalar() or 0
            
            profit_factor = profit_query / loss_query if loss_query > 0 else 0
            
            return {
                'total_trades': result.total_trades,
                'total_pnl': result.total_pnl,
                'avg_pnl': result.avg_pnl,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor
            }


class EquityCurveDAL(BaseDAL[EquityCurve]):
    """
    자산 곡선 데이터 액세스 레이어
    """
    
    def __init__(self):
        super().__init__(EquityCurve)
    
    def get_latest_equity(self) -> Optional[EquityCurve]:
        """
        최신 자산 곡선 데이터 조회
        
        Returns:
            Optional[EquityCurve]: 최신 자산 곡선 데이터 또는 None
        """
        with self.get_session() as session:
            return session.query(EquityCurve).order_by(desc(EquityCurve.ts)).first()
    
    def get_equity_by_date_range(self, start_date: datetime, end_date: datetime, 
                                session_id: Optional[str] = None) -> List[EquityCurve]:
        """
        날짜 범위로 자산 곡선 데이터 조회
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            session_id: 세션 ID (선택 사항)
            
        Returns:
            List[EquityCurve]: 자산 곡선 데이터 목록
        """
        with self.get_session() as session:
            query = session.query(EquityCurve).filter(
                EquityCurve.ts >= start_date,
                EquityCurve.ts <= end_date
            )
            
            if session_id:
                query = query.filter(EquityCurve.session_id == session_id)
                
            return query.order_by(EquityCurve.ts).all()
    
    def get_max_drawdown(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> float:
        """
        최대 드로다운 계산
        
        Args:
            start_date: 시작 날짜 (선택 사항)
            end_date: 종료 날짜 (선택 사항)
            
        Returns:
            float: 최대 드로다운 (%)
        """
        with self.get_session() as session:
            # 기본 필터 조건
            conditions = []
            
            # 추가 필터 조건
            if start_date:
                conditions.append(EquityCurve.ts >= start_date)
            if end_date:
                conditions.append(EquityCurve.ts <= end_date)
            
            # 쿼리 실행
            query = session.query(func.max(EquityCurve.drawdown_pct)).filter(*conditions)
            
            return query.scalar() or 0.0
