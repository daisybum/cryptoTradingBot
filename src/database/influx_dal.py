"""
InfluxDB 데이터 액세스 레이어 모듈

이 모듈은 InfluxDB에 시계열 데이터를 저장하고 조회하는 클래스를 제공합니다.
거래 데이터, 가격 데이터 및 성능 지표를 시계열 형식으로 관리합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta

from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.query_api import QueryApi

from src.database.connection import get_db_manager

logger = logging.getLogger(__name__)


class InfluxDAL:
    """
    InfluxDB 데이터 액세스 레이어
    
    시계열 데이터를 저장하고 조회하는 기능을 제공합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.db_manager = get_db_manager()
        
        if not self.db_manager or not self.db_manager.influx_client:
            logger.error("InfluxDB 클라이언트가 초기화되지 않았습니다.")
            raise RuntimeError("InfluxDB 클라이언트가 초기화되지 않았습니다.")
        
        self.write_api = self.db_manager.influx_client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.db_manager.influx_client.query_api()
        self.bucket = self.db_manager.influx_bucket
        self.org = self.db_manager.influx_org
    
    def write_price_data(self, symbol: str, timeframe: str, timestamp: datetime,
                        open_price: float, high_price: float, low_price: float,
                        close_price: float, volume: float) -> bool:
        """
        가격 데이터 저장
        
        Args:
            symbol: 거래 쌍
            timeframe: 시간 프레임
            timestamp: 타임스탬프
            open_price: 시가
            high_price: 고가
            low_price: 저가
            close_price: 종가
            volume: 거래량
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            point = Point("price_data") \
                .tag("symbol", symbol) \
                .tag("timeframe", timeframe) \
                .field("open", open_price) \
                .field("high", high_price) \
                .field("low", low_price) \
                .field("close", close_price) \
                .field("volume", volume) \
                .time(timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            logger.error(f"가격 데이터 저장 실패: {e}")
            return False
    
    def write_trade_data(self, trade_id: str, symbol: str, side: str, 
                        entry_price: float, exit_price: Optional[float],
                        quantity: float, pnl: Optional[float],
                        strategy: str, timestamp: datetime,
                        tags: Optional[Dict[str, str]] = None) -> bool:
        """
        거래 데이터 저장
        
        Args:
            trade_id: 거래 ID
            symbol: 거래 쌍
            side: 거래 방향 (buy/sell)
            entry_price: 진입 가격
            exit_price: 청산 가격 (선택 사항)
            quantity: 수량
            pnl: 손익 (선택 사항)
            strategy: 전략 이름
            timestamp: 타임스탬프
            tags: 추가 태그 (선택 사항)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            point = Point("trade_data") \
                .tag("trade_id", trade_id) \
                .tag("symbol", symbol) \
                .tag("side", side) \
                .tag("strategy", strategy)
            
            # 추가 태그 설정
            if tags:
                for key, value in tags.items():
                    point = point.tag(key, value)
            
            # 필드 설정
            point = point.field("entry_price", entry_price) \
                .field("quantity", quantity)
            
            if exit_price is not None:
                point = point.field("exit_price", exit_price)
            
            if pnl is not None:
                point = point.field("pnl", pnl)
            
            # 타임스탬프 설정
            point = point.time(timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            logger.error(f"거래 데이터 저장 실패: {e}")
            return False
    
    def write_indicator_data(self, symbol: str, timeframe: str, timestamp: datetime,
                            indicators: Dict[str, float], strategy: Optional[str] = None) -> bool:
        """
        지표 데이터 저장
        
        Args:
            symbol: 거래 쌍
            timeframe: 시간 프레임
            timestamp: 타임스탬프
            indicators: 지표 데이터 (이름: 값)
            strategy: 전략 이름 (선택 사항)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            point = Point("indicator_data") \
                .tag("symbol", symbol) \
                .tag("timeframe", timeframe)
            
            if strategy:
                point = point.tag("strategy", strategy)
            
            # 지표 필드 설정
            for name, value in indicators.items():
                if value is not None:
                    point = point.field(name, float(value))
            
            # 타임스탬프 설정
            point = point.time(timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            logger.error(f"지표 데이터 저장 실패: {e}")
            return False
    
    def write_performance_data(self, timestamp: datetime, balance: float, 
                              equity: float, drawdown: Optional[float] = None,
                              open_positions: int = 0, daily_pnl: Optional[float] = None,
                              tags: Optional[Dict[str, str]] = None) -> bool:
        """
        성능 데이터 저장
        
        Args:
            timestamp: 타임스탬프
            balance: 잔고
            equity: 자산 가치
            drawdown: 드로다운 (선택 사항)
            open_positions: 오픈 포지션 수 (선택 사항)
            daily_pnl: 일일 손익 (선택 사항)
            tags: 추가 태그 (선택 사항)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            point = Point("performance_data")
            
            # 추가 태그 설정
            if tags:
                for key, value in tags.items():
                    point = point.tag(key, value)
            
            # 필드 설정
            point = point.field("balance", balance) \
                .field("equity", equity) \
                .field("open_positions", open_positions)
            
            if drawdown is not None:
                point = point.field("drawdown", drawdown)
            
            if daily_pnl is not None:
                point = point.field("daily_pnl", daily_pnl)
            
            # 타임스탬프 설정
            point = point.time(timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            logger.error(f"성능 데이터 저장 실패: {e}")
            return False
    
    def get_price_data(self, symbol: str, timeframe: str, 
                      start_time: datetime, end_time: Optional[datetime] = None,
                      limit: int = 1000) -> List[Dict[str, Any]]:
        """
        가격 데이터 조회
        
        Args:
            symbol: 거래 쌍
            timeframe: 시간 프레임
            start_time: 시작 시간
            end_time: 종료 시간 (선택 사항, 기본값: 현재 시간)
            limit: 최대 레코드 수
            
        Returns:
            List[Dict[str, Any]]: 가격 데이터 목록
        """
        try:
            # 종료 시간이 없으면 현재 시간으로 설정
            if end_time is None:
                end_time = datetime.utcnow()
            
            # 쿼리 생성
            query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "price_data")
                    |> filter(fn: (r) => r.symbol == "{symbol}")
                    |> filter(fn: (r) => r.timeframe == "{timeframe}")
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> limit(n: {limit})
            '''
            
            # 쿼리 실행
            result = self.query_api.query_data_frame(query=query, org=self.org)
            
            # 결과가 비어있으면 빈 리스트 반환
            if result.empty:
                return []
            
            # 결과 변환
            data = []
            for _, row in result.iterrows():
                data.append({
                    'timestamp': row.get('_time'),
                    'symbol': row.get('symbol'),
                    'timeframe': row.get('timeframe'),
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'volume': row.get('volume')
                })
            
            return data
        except Exception as e:
            logger.error(f"가격 데이터 조회 실패: {e}")
            return []
    
    def get_indicator_data(self, symbol: str, timeframe: str, 
                          start_time: datetime, end_time: Optional[datetime] = None,
                          strategy: Optional[str] = None,
                          indicators: Optional[List[str]] = None,
                          limit: int = 1000) -> List[Dict[str, Any]]:
        """
        지표 데이터 조회
        
        Args:
            symbol: 거래 쌍
            timeframe: 시간 프레임
            start_time: 시작 시간
            end_time: 종료 시간 (선택 사항, 기본값: 현재 시간)
            strategy: 전략 이름 (선택 사항)
            indicators: 조회할 지표 목록 (선택 사항)
            limit: 최대 레코드 수
            
        Returns:
            List[Dict[str, Any]]: 지표 데이터 목록
        """
        try:
            # 종료 시간이 없으면 현재 시간으로 설정
            if end_time is None:
                end_time = datetime.utcnow()
            
            # 쿼리 생성
            query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "indicator_data")
                    |> filter(fn: (r) => r.symbol == "{symbol}")
                    |> filter(fn: (r) => r.timeframe == "{timeframe}")
            '''
            
            # 전략 필터 추가
            if strategy:
                query += f'    |> filter(fn: (r) => r.strategy == "{strategy}")\n'
            
            # 지표 필터 추가
            if indicators:
                indicator_filter = ' or '.join([f'r._field == "{ind}"' for ind in indicators])
                query += f'    |> filter(fn: (r) => {indicator_filter})\n'
            
            # 피벗 및 제한 추가
            query += f'''
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> limit(n: {limit})
            '''
            
            # 쿼리 실행
            result = self.query_api.query_data_frame(query=query, org=self.org)
            
            # 결과가 비어있으면 빈 리스트 반환
            if result.empty:
                return []
            
            # 결과 변환
            data = []
            for _, row in result.iterrows():
                item = {
                    'timestamp': row.get('_time'),
                    'symbol': row.get('symbol'),
                    'timeframe': row.get('timeframe')
                }
                
                # 지표 값 추가
                for col in result.columns:
                    if col not in ['_time', '_start', '_stop', '_measurement', 'symbol', 'timeframe', 'strategy']:
                        item[col] = row.get(col)
                
                data.append(item)
            
            return data
        except Exception as e:
            logger.error(f"지표 데이터 조회 실패: {e}")
            return []
    
    def get_performance_data(self, start_time: datetime, end_time: Optional[datetime] = None,
                            interval: str = "1h", tags: Optional[Dict[str, str]] = None,
                            limit: int = 1000) -> List[Dict[str, Any]]:
        """
        성능 데이터 조회
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간 (선택 사항, 기본값: 현재 시간)
            interval: 데이터 간격 (1h, 1d 등)
            tags: 필터링할 태그 (선택 사항)
            limit: 최대 레코드 수
            
        Returns:
            List[Dict[str, Any]]: 성능 데이터 목록
        """
        try:
            # 종료 시간이 없으면 현재 시간으로 설정
            if end_time is None:
                end_time = datetime.utcnow()
            
            # 쿼리 생성
            query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "performance_data")
            '''
            
            # 태그 필터 추가
            if tags:
                for key, value in tags.items():
                    query += f'    |> filter(fn: (r) => r.{key} == "{value}")\n'
            
            # 집계 및 피벗 추가
            query += f'''
                    |> aggregateWindow(every: {interval}, fn: last)
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> limit(n: {limit})
            '''
            
            # 쿼리 실행
            result = self.query_api.query_data_frame(query=query, org=self.org)
            
            # 결과가 비어있으면 빈 리스트 반환
            if result.empty:
                return []
            
            # 결과 변환
            data = []
            for _, row in result.iterrows():
                item = {
                    'timestamp': row.get('_time')
                }
                
                # 필드 값 추가
                for col in result.columns:
                    if col not in ['_time', '_start', '_stop', '_measurement']:
                        item[col] = row.get(col)
                
                data.append(item)
            
            return data
        except Exception as e:
            logger.error(f"성능 데이터 조회 실패: {e}")
            return []
    
    def get_trade_data(self, start_time: datetime, end_time: Optional[datetime] = None,
                      symbol: Optional[str] = None, strategy: Optional[str] = None,
                      limit: int = 1000) -> List[Dict[str, Any]]:
        """
        거래 데이터 조회
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간 (선택 사항, 기본값: 현재 시간)
            symbol: 거래 쌍 (선택 사항)
            strategy: 전략 이름 (선택 사항)
            limit: 최대 레코드 수
            
        Returns:
            List[Dict[str, Any]]: 거래 데이터 목록
        """
        try:
            # 종료 시간이 없으면 현재 시간으로 설정
            if end_time is None:
                end_time = datetime.utcnow()
            
            # 쿼리 생성
            query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "trade_data")
            '''
            
            # 거래 쌍 필터 추가
            if symbol:
                query += f'    |> filter(fn: (r) => r.symbol == "{symbol}")\n'
            
            # 전략 필터 추가
            if strategy:
                query += f'    |> filter(fn: (r) => r.strategy == "{strategy}")\n'
            
            # 피벗 및 제한 추가
            query += f'''
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> limit(n: {limit})
            '''
            
            # 쿼리 실행
            result = self.query_api.query_data_frame(query=query, org=self.org)
            
            # 결과가 비어있으면 빈 리스트 반환
            if result.empty:
                return []
            
            # 결과 변환
            data = []
            for _, row in result.iterrows():
                item = {
                    'timestamp': row.get('_time'),
                    'trade_id': row.get('trade_id'),
                    'symbol': row.get('symbol'),
                    'side': row.get('side'),
                    'strategy': row.get('strategy')
                }
                
                # 필드 값 추가
                for col in result.columns:
                    if col not in ['_time', '_start', '_stop', '_measurement', 'trade_id', 'symbol', 'side', 'strategy']:
                        item[col] = row.get(col)
                
                data.append(item)
            
            return data
        except Exception as e:
            logger.error(f"거래 데이터 조회 실패: {e}")
            return []
    
    def calculate_performance_metrics(self, start_time: datetime, 
                                     end_time: Optional[datetime] = None,
                                     strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        성능 지표 계산
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간 (선택 사항, 기본값: 현재 시간)
            strategy: 전략 이름 (선택 사항)
            
        Returns:
            Dict[str, Any]: 성능 지표
        """
        try:
            # 종료 시간이 없으면 현재 시간으로 설정
            if end_time is None:
                end_time = datetime.utcnow()
            
            # 거래 데이터 조회
            trades = self.get_trade_data(
                start_time=start_time,
                end_time=end_time,
                strategy=strategy,
                limit=10000  # 충분히 큰 값
            )
            
            if not trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'total_pnl': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0
                }
            
            # 지표 계산
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
            
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            
            total_profit = sum(t.get('pnl', 0) for t in winning_trades)
            total_loss = sum(abs(t.get('pnl', 0)) for t in losing_trades)
            
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            total_pnl = total_profit - total_loss
            
            # 성능 데이터에서 최대 드로다운 조회
            performance_data = self.get_performance_data(
                start_time=start_time,
                end_time=end_time,
                interval="1d"
            )
            
            max_drawdown = max([p.get('drawdown', 0) for p in performance_data]) if performance_data else 0
            
            # 샤프 비율 계산 (일별 수익률 기준)
            daily_returns = []
            
            if len(performance_data) >= 2:
                for i in range(1, len(performance_data)):
                    prev_equity = performance_data[i-1].get('equity', 0)
                    curr_equity = performance_data[i].get('equity', 0)
                    
                    if prev_equity > 0:
                        daily_return = (curr_equity - prev_equity) / prev_equity
                        daily_returns.append(daily_return)
            
            if daily_returns:
                import numpy as np
                avg_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            return {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio
            }
        except Exception as e:
            logger.error(f"성능 지표 계산 실패: {e}")
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'error': str(e)
            }
