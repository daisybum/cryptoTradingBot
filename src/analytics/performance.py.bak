"""
성능 분석 모듈

이 모듈은 트레이딩 봇의 성능을 분석하고 다양한 지표를 계산하는 기능을 제공합니다.
주요 성능 지표로는 승률, 수익 요소, Sharpe 비율, Calmar 비율, 최대 드로다운 등이 있습니다.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import math
from enum import Enum

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceMetric(Enum):
    """성능 지표 열거형"""
    TOTAL_TRADES = "total_trades"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    AVERAGE_PROFIT = "average_profit"
    AVERAGE_PROFIT_PERCENT = "average_profit_percent"
    AVERAGE_DURATION = "average_duration"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_DRAWDOWN_DURATION = "max_drawdown_duration"
    VOLATILITY = "volatility"
    EXPECTANCY = "expectancy"
    RECOVERY_FACTOR = "recovery_factor"
    PROFIT_TO_DRAWDOWN = "profit_to_drawdown"
    AVERAGE_WINNING_TRADE = "average_winning_trade"
    AVERAGE_LOSING_TRADE = "average_losing_trade"
    LARGEST_WINNING_TRADE = "largest_winning_trade"
    LARGEST_LOSING_TRADE = "largest_losing_trade"
    MAX_CONSECUTIVE_WINS = "max_consecutive_wins"
    MAX_CONSECUTIVE_LOSSES = "max_consecutive_losses"
    PROFIT_PER_DAY = "profit_per_day"
    ANNUAL_RETURN = "annual_return"

class PerformanceAnalyzer:
    """성능 분석 클래스"""
    
    def __init__(self, db_manager=None):
        """
        성능 분석 클래스 초기화
        
        Args:
            db_manager: 데이터베이스 관리자 인스턴스
        """
        self.db_manager = db_manager
        self.risk_free_rate = 0.02  # 연간 무위험 수익률 (2%)
    
    def calculate_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        거래 데이터로부터 성능 지표 계산
        
        Args:
            trades_df: 거래 데이터 DataFrame
                필수 열: 'pnl', 'pnl_pct', 'open_time', 'close_time'
                
        Returns:
            Dict[str, Any]: 계산된 성능 지표 딕셔너리
        """
        if trades_df.empty:
            logger.warning("거래 데이터가 없습니다.")
            return self._empty_metrics()
        
        # 기본 지표 계산
        total_trades = len(trades_df)
        profitable_trades = len(trades_df[trades_df['pnl'] > 0])
        unprofitable_trades = len(trades_df[trades_df['pnl'] <= 0])
        
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # 수익 관련 지표
        total_profit = trades_df['pnl'].sum()
        average_profit = trades_df['pnl'].mean()
        average_profit_percent = trades_df['pnl_pct'].mean()
        
        # 승리/손실 거래 평균
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        average_winning_trade = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        average_losing_trade = losing_trades['pnl'].mean() if not losing_trades.empty else 0
        
        # 최대 승리/손실 거래
        largest_winning_trade = winning_trades['pnl'].max() if not winning_trades.empty else 0
        largest_losing_trade = losing_trades['pnl'].min() if not losing_trades.empty else 0
        
        # 수익 요소 계산
        profit_factor = 0
        if unprofitable_trades > 0 and average_losing_trade < 0:
            profit_factor = (average_winning_trade * profitable_trades) / (-average_losing_trade * unprofitable_trades)
        
        # 거래 기간 계산
        trades_df['duration'] = (trades_df['close_time'] - trades_df['open_time']).dt.total_seconds() / 3600  # 시간 단위
        average_duration = trades_df['duration'].mean()
        
        # 최대 연속 승리/손실 계산
        trades_df['is_win'] = trades_df['pnl'] > 0
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades(trades_df['is_win'])
        
        # 드로다운 계산
        max_drawdown, max_drawdown_duration = self._calculate_drawdown(trades_df)
        
        # 변동성 계산
        daily_returns = self._calculate_daily_returns(trades_df)
        volatility = daily_returns['return'].std() * np.sqrt(365) if not daily_returns.empty else 0
        
        # Sharpe 비율 계산
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        
        # Sortino 비율 계산
        sortino_ratio = self._calculate_sortino_ratio(daily_returns)
        
        # Calmar 비율 계산
        calmar_ratio = self._calculate_calmar_ratio(daily_returns, max_drawdown)
        
        # 기대값 계산
        expectancy = (win_rate * average_winning_trade) + ((1 - win_rate) * average_losing_trade)
        
        # 회복 요소 계산
        recovery_factor = abs(total_profit / max_drawdown) if max_drawdown != 0 else 0
        
        # 수익 대 드로다운 비율
        profit_to_drawdown = abs(total_profit / max_drawdown) if max_drawdown != 0 else 0
        
        # 일일 수익 계산
        first_trade_date = trades_df['open_time'].min()
        last_trade_date = trades_df['close_time'].max()
        trading_days = (last_trade_date - first_trade_date).days + 1
        profit_per_day = total_profit / trading_days if trading_days > 0 else 0
        
        # 연간 수익률 계산
        annual_return = (profit_per_day * 365) / 10000  # 초기 자본 10,000 USDT 가정
        
        # 결과 딕셔너리 생성
        metrics = {
            PerformanceMetric.TOTAL_TRADES.value: total_trades,
            PerformanceMetric.WIN_RATE.value: win_rate,
            PerformanceMetric.PROFIT_FACTOR.value: profit_factor,
            PerformanceMetric.AVERAGE_PROFIT.value: average_profit,
            PerformanceMetric.AVERAGE_PROFIT_PERCENT.value: average_profit_percent,
            PerformanceMetric.AVERAGE_DURATION.value: average_duration,
            PerformanceMetric.SHARPE_RATIO.value: sharpe_ratio,
            PerformanceMetric.SORTINO_RATIO.value: sortino_ratio,
            PerformanceMetric.CALMAR_RATIO.value: calmar_ratio,
            PerformanceMetric.MAX_DRAWDOWN.value: max_drawdown,
            PerformanceMetric.MAX_DRAWDOWN_DURATION.value: max_drawdown_duration,
            PerformanceMetric.VOLATILITY.value: volatility,
            PerformanceMetric.EXPECTANCY.value: expectancy,
            PerformanceMetric.RECOVERY_FACTOR.value: recovery_factor,
            PerformanceMetric.PROFIT_TO_DRAWDOWN.value: profit_to_drawdown,
            PerformanceMetric.AVERAGE_WINNING_TRADE.value: average_winning_trade,
            PerformanceMetric.AVERAGE_LOSING_TRADE.value: average_losing_trade,
            PerformanceMetric.LARGEST_WINNING_TRADE.value: largest_winning_trade,
            PerformanceMetric.LARGEST_LOSING_TRADE.value: largest_losing_trade,
            PerformanceMetric.MAX_CONSECUTIVE_WINS.value: consecutive_wins,
            PerformanceMetric.MAX_CONSECUTIVE_LOSSES.value: consecutive_losses,
            PerformanceMetric.PROFIT_PER_DAY.value: profit_per_day,
            PerformanceMetric.ANNUAL_RETURN.value: annual_return
        }
        
        return metrics
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """
        빈 성능 지표 딕셔너리 생성
        
        Returns:
            Dict[str, Any]: 빈 성능 지표 딕셔너리
        """
        metrics = {}
        for metric in PerformanceMetric:
            metrics[metric.value] = 0
        return metrics
    
    def _calculate_consecutive_trades(self, is_win_series: pd.Series) -> Tuple[int, int]:
        """
        최대 연속 승리/손실 계산
        
        Args:
            is_win_series: 승리 여부 시리즈
            
        Returns:
            Tuple[int, int]: (최대 연속 승리, 최대 연속 손실)
        """
        if is_win_series.empty:
            return 0, 0
        
        # 연속 승리 계산
        consecutive_wins = 0
        current_streak = 0
        for is_win in is_win_series:
            if is_win:
                current_streak += 1
                consecutive_wins = max(consecutive_wins, current_streak)
            else:
                current_streak = 0
        
        # 연속 손실 계산
        consecutive_losses = 0
        current_streak = 0
        for is_win in is_win_series:
            if not is_win:
                current_streak += 1
                consecutive_losses = max(consecutive_losses, current_streak)
            else:
                current_streak = 0
        
        return consecutive_wins, consecutive_losses
    
    def _calculate_drawdown(self, trades_df: pd.DataFrame) -> Tuple[float, int]:
        """
        최대 드로다운 및 드로다운 기간 계산
        
        Args:
            trades_df: 거래 데이터 DataFrame
            
        Returns:
            Tuple[float, int]: (최대 드로다운, 최대 드로다운 기간)
        """
        if trades_df.empty:
            return 0, 0
        
        # 누적 수익 계산
        trades_df = trades_df.sort_values('close_time')
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        
        # 최대 누적 수익 계산
        trades_df['max_cumulative_pnl'] = trades_df['cumulative_pnl'].cummax()
        
        # 드로다운 계산
        trades_df['drawdown'] = trades_df['max_cumulative_pnl'] - trades_df['cumulative_pnl']
        trades_df['drawdown_pct'] = trades_df['drawdown'] / (trades_df['max_cumulative_pnl'] + 10000)  # 초기 자본 10,000 USDT 가정
        
        max_drawdown = trades_df['drawdown_pct'].max()
        
        # 드로다운 기간 계산
        if max_drawdown == 0:
            return 0, 0
        
        # 최대 드로다운 시작 및 종료 시간 찾기
        peak_idx = trades_df['cumulative_pnl'].idxmax()
        if pd.isna(peak_idx):
            return max_drawdown, 0
        
        peak_time = trades_df.loc[peak_idx, 'close_time']
        
        # 최대 드로다운 이후 회복 시간 찾기
        recovery_idx = trades_df[trades_df['close_time'] > peak_time]
        recovery_idx = recovery_idx[recovery_idx['cumulative_pnl'] >= trades_df.loc[peak_idx, 'cumulative_pnl']].index
        
        if len(recovery_idx) > 0:
            recovery_time = trades_df.loc[recovery_idx[0], 'close_time']
            drawdown_duration = (recovery_time - peak_time).days
        else:
            # 아직 회복되지 않은 경우
            drawdown_duration = (trades_df['close_time'].max() - peak_time).days
        
        return max_drawdown, drawdown_duration
    
    def _calculate_daily_returns(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        일일 수익률 계산
        
        Args:
            trades_df: 거래 데이터 DataFrame
            
        Returns:
            pd.DataFrame: 일일 수익률 DataFrame
        """
        if trades_df.empty:
            return pd.DataFrame(columns=['date', 'return'])
        
        # 일별 수익 계산
        trades_df['date'] = trades_df['close_time'].dt.date
        daily_pnl = trades_df.groupby('date')['pnl'].sum().reset_index()
        
        # 일일 수익률 계산 (초기 자본 10,000 USDT 가정)
        daily_pnl['cumulative_pnl'] = daily_pnl['pnl'].cumsum()
        daily_pnl['equity'] = 10000 + daily_pnl['cumulative_pnl']
        daily_pnl['equity_prev'] = daily_pnl['equity'].shift(1).fillna(10000)
        daily_pnl['return'] = daily_pnl['equity'] / daily_pnl['equity_prev'] - 1
        
        return daily_pnl[['date', 'return']]
    
    def _calculate_sharpe_ratio(self, daily_returns: pd.DataFrame) -> float:
        """
        Sharpe 비율 계산
        
        Args:
            daily_returns: 일일 수익률 DataFrame
            
        Returns:
            float: Sharpe 비율
        """
        if daily_returns.empty:
            return 0
        
        # 연간 수익률 및 표준편차 계산
        annual_return = daily_returns['return'].mean() * 365
        annual_std = daily_returns['return'].std() * np.sqrt(365)
        
        # 일일 무위험 수익률
        daily_risk_free_rate = self.risk_free_rate / 365
        
        # Sharpe 비율 계산
        if annual_std == 0:
            return 0
        
        sharpe_ratio = (annual_return - self.risk_free_rate) / annual_std
        
        return sharpe_ratio
    
    def _calculate_sortino_ratio(self, daily_returns: pd.DataFrame) -> float:
        """
        Sortino 비율 계산
        
        Args:
            daily_returns: 일일 수익률 DataFrame
            
        Returns:
            float: Sortino 비율
        """
        if daily_returns.empty:
            return 0
        
        # 연간 수익률 계산
        annual_return = daily_returns['return'].mean() * 365
        
        # 하방 표준편차 계산
        negative_returns = daily_returns[daily_returns['return'] < 0]['return']
        if negative_returns.empty:
            return 0
        
        downside_std = negative_returns.std() * np.sqrt(365)
        
        # Sortino 비율 계산
        if downside_std == 0:
            return 0
        
        sortino_ratio = (annual_return - self.risk_free_rate) / downside_std
        
        return sortino_ratio
    
    def _calculate_calmar_ratio(self, daily_returns: pd.DataFrame, max_drawdown: float) -> float:
        """
        Calmar 비율 계산
        
        Args:
            daily_returns: 일일 수익률 DataFrame
            max_drawdown: 최대 드로다운
            
        Returns:
            float: Calmar 비율
        """
        if daily_returns.empty or max_drawdown == 0:
            return 0
        
        # 연간 수익률 계산
        annual_return = daily_returns['return'].mean() * 365
        
        # Calmar 비율 계산
        calmar_ratio = annual_return / max_drawdown
        
        return calmar_ratio
    
    def get_trades_from_db(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, 
                          strategy: Optional[str] = None, pair: Optional[str] = None) -> pd.DataFrame:
        """
        데이터베이스에서 거래 데이터 가져오기
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 전략 이름
            pair: 거래 페어
            
        Returns:
            pd.DataFrame: 거래 데이터 DataFrame
        """
        if not self.db_manager:
            logger.error("데이터베이스 관리자가 초기화되지 않았습니다.")
            return pd.DataFrame()
        
        try:
            with self.db_manager.get_pg_session() as session:
                query = """
                SELECT 
                    trade_id, pair, strategy, open_time, close_time, 
                    entry_price, exit_price, quantity, side, status, 
                    pnl, pnl_pct, fee
                FROM trades
                WHERE status = 'closed'
                """
                
                params = {}
                
                if start_date:
                    query += " AND open_time >= :start_date"
                    params['start_date'] = start_date
                
                if end_date:
                    query += " AND close_time <= :end_date"
                    params['end_date'] = end_date
                
                if strategy:
                    query += " AND strategy = :strategy"
                    params['strategy'] = strategy
                
                if pair:
                    query += " AND pair = :pair"
                    params['pair'] = pair
                
                query += " ORDER BY open_time ASC"
                
                result = session.execute(query, params)
                trades = result.fetchall()
                
                if not trades:
                    logger.warning("조건에 맞는 거래 데이터가 없습니다.")
                    return pd.DataFrame()
                
                # DataFrame 생성
                columns = [
                    'trade_id', 'pair', 'strategy', 'open_time', 'close_time',
                    'entry_price', 'exit_price', 'quantity', 'side', 'status',
                    'pnl', 'pnl_pct', 'fee'
                ]
                
                trades_df = pd.DataFrame(trades, columns=columns)
                
                return trades_df
                
        except Exception as e:
            logger.error(f"거래 데이터 가져오기 실패: {e}")
            return pd.DataFrame()
    
    def analyze_performance(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                           strategy: Optional[str] = None, pair: Optional[str] = None) -> Dict[str, Any]:
        """
        성능 분석 실행
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 전략 이름
            pair: 거래 페어
            
        Returns:
            Dict[str, Any]: 성능 지표 딕셔너리
        """
        # 거래 데이터 가져오기
        trades_df = self.get_trades_from_db(start_date, end_date, strategy, pair)
        
        if trades_df.empty:
            logger.warning("분석할 거래 데이터가 없습니다.")
            return self._empty_metrics()
        
        # 성능 지표 계산
        metrics = self.calculate_metrics(trades_df)
        
        # 분석 결과 저장
        self._save_performance_metrics(metrics, start_date, end_date, strategy, pair)
        
        return metrics
    
    def _save_performance_metrics(self, metrics: Dict[str, Any], start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None, strategy: Optional[str] = None,
                                 pair: Optional[str] = None) -> bool:
        """
        성능 지표를 데이터베이스에 저장
        
        Args:
            metrics: 성능 지표 딕셔너리
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 전략 이름
            pair: 거래 페어
            
        Returns:
            bool: 저장 성공 여부
        """
        if not self.db_manager:
            logger.error("데이터베이스 관리자가 초기화되지 않았습니다.")
            return False
        
        try:
            with self.db_manager.get_pg_session() as session:
                # 성능 지표 저장
                query = """
                INSERT INTO performance_metrics (
                    timestamp, start_date, end_date, strategy, pair,
                    total_trades, win_rate, profit_factor, average_profit, average_profit_percent,
                    average_duration, sharpe_ratio, sortino_ratio, calmar_ratio, max_drawdown,
                    max_drawdown_duration, volatility, expectancy, recovery_factor, profit_to_drawdown,
                    average_winning_trade, average_losing_trade, largest_winning_trade, largest_losing_trade,
                    max_consecutive_wins, max_consecutive_losses, profit_per_day, annual_return
                ) VALUES (
                    NOW(), :start_date, :end_date, :strategy, :pair,
                    :total_trades, :win_rate, :profit_factor, :average_profit, :average_profit_percent,
                    :average_duration, :sharpe_ratio, :sortino_ratio, :calmar_ratio, :max_drawdown,
                    :max_drawdown_duration, :volatility, :expectancy, :recovery_factor, :profit_to_drawdown,
                    :average_winning_trade, :average_losing_trade, :largest_winning_trade, :largest_losing_trade,
                    :max_consecutive_wins, :max_consecutive_losses, :profit_per_day, :annual_return
                )
                """
                
                params = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'strategy': strategy,
                    'pair': pair,
                    'total_trades': metrics[PerformanceMetric.TOTAL_TRADES.value],
                    'win_rate': metrics[PerformanceMetric.WIN_RATE.value],
                    'profit_factor': metrics[PerformanceMetric.PROFIT_FACTOR.value],
                    'average_profit': metrics[PerformanceMetric.AVERAGE_PROFIT.value],
                    'average_profit_percent': metrics[PerformanceMetric.AVERAGE_PROFIT_PERCENT.value],
                    'average_duration': metrics[PerformanceMetric.AVERAGE_DURATION.value],
                    'sharpe_ratio': metrics[PerformanceMetric.SHARPE_RATIO.value],
                    'sortino_ratio': metrics[PerformanceMetric.SORTINO_RATIO.value],
                    'calmar_ratio': metrics[PerformanceMetric.CALMAR_RATIO.value],
                    'max_drawdown': metrics[PerformanceMetric.MAX_DRAWDOWN.value],
                    'max_drawdown_duration': metrics[PerformanceMetric.MAX_DRAWDOWN_DURATION.value],
                    'volatility': metrics[PerformanceMetric.VOLATILITY.value],
                    'expectancy': metrics[PerformanceMetric.EXPECTANCY.value],
                    'recovery_factor': metrics[PerformanceMetric.RECOVERY_FACTOR.value],
                    'profit_to_drawdown': metrics[PerformanceMetric.PROFIT_TO_DRAWDOWN.value],
                    'average_winning_trade': metrics[PerformanceMetric.AVERAGE_WINNING_TRADE.value],
                    'average_losing_trade': metrics[PerformanceMetric.AVERAGE_LOSING_TRADE.value],
                    'largest_winning_trade': metrics[PerformanceMetric.LARGEST_WINNING_TRADE.value],
                    'largest_losing_trade': metrics[PerformanceMetric.LARGEST_LOSING_TRADE.value],
                    'max_consecutive_wins': metrics[PerformanceMetric.MAX_CONSECUTIVE_WINS.value],
                    'max_consecutive_losses': metrics[PerformanceMetric.MAX_CONSECUTIVE_LOSSES.value],
                    'profit_per_day': metrics[PerformanceMetric.PROFIT_PER_DAY.value],
                    'annual_return': metrics[PerformanceMetric.ANNUAL_RETURN.value]
                }
                
                session.execute(query, params)
                session.commit()
                
                logger.info("성능 지표가 데이터베이스에 저장되었습니다.")
                return True
                
        except Exception as e:
            logger.error(f"성능 지표 저장 실패: {e}")
            return False
    
    def get_performance_summary(self, days: int = 30, strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        성능 요약 정보 가져오기
        
        Args:
            days: 분석할 일수
            strategy: 전략 이름
            
        Returns:
            Dict[str, Any]: 성능 요약 정보
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        metrics = self.analyze_performance(start_date, end_date, strategy)
        
        # 요약 정보 생성
        summary = {
            'period': f"최근 {days}일",
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'strategy': strategy if strategy else "전체",
            'total_trades': metrics[PerformanceMetric.TOTAL_TRADES.value],
            'win_rate': f"{metrics[PerformanceMetric.WIN_RATE.value] * 100:.2f}%",
            'profit_factor': f"{metrics[PerformanceMetric.PROFIT_FACTOR.value]:.2f}",
            'average_profit': f"{metrics[PerformanceMetric.AVERAGE_PROFIT.value]:.2f} USDT",
            'max_drawdown': f"{metrics[PerformanceMetric.MAX_DRAWDOWN.value] * 100:.2f}%",
            'sharpe_ratio': f"{metrics[PerformanceMetric.SHARPE_RATIO.value]:.2f}",
            'annual_return': f"{metrics[PerformanceMetric.ANNUAL_RETURN.value] * 100:.2f}%"
        }
        
        return summary
