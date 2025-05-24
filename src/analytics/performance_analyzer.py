#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 서버를 위한 성능 분석 클래스

이 모듈은 API 서버에서 사용할 성능 분석 기능을 제공합니다.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

class PerformanceAnalyzer:
    """
    API 서버를 위한 성능 분석 클래스
    """
    
    def __init__(self, trades: List[Any]):
        """
        PerformanceAnalyzer 초기화
        
        Args:
            trades (List[Any]): 거래 목록
        """
        self.trades = trades
        self.df = self._prepare_dataframe()
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """
        거래 데이터를 DataFrame으로 변환
        
        Returns:
            pd.DataFrame: 거래 데이터 DataFrame
        """
        if not self.trades:
            return pd.DataFrame()
        
        # 거래 데이터 추출
        data = []
        for trade in self.trades:
            data.append({
                'id': trade.id,
                'symbol': trade.symbol,
                'strategy': trade.strategy,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'amount': trade.amount,
                'fee': trade.fee,
                'profit': trade.profit,
                'profit_percentage': trade.profit_percentage,
                'status': trade.status,
                'trade_type': trade.trade_type
            })
        
        df = pd.DataFrame(data)
        
        # 날짜 형식 변환
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        # 거래 기간 계산
        df['duration'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60  # 분 단위
        
        return df
    
    def calculate_win_rate(self) -> float:
        """
        승률 계산
        
        Returns:
            float: 승률 (0.0 ~ 1.0)
        """
        if self.df.empty:
            return 0.0
        
        winning_trades = self.df[self.df['profit'] > 0].shape[0]
        total_trades = self.df.shape[0]
        
        return winning_trades / total_trades if total_trades > 0 else 0.0
    
    def calculate_profit_factor(self) -> float:
        """
        수익 요소 계산 (총 이익 / 총 손실)
        
        Returns:
            float: 수익 요소
        """
        if self.df.empty:
            return 0.0
        
        gross_profit = self.df[self.df['profit'] > 0]['profit'].sum()
        gross_loss = abs(self.df[self.df['profit'] < 0]['profit'].sum())
        
        return gross_profit / gross_loss if gross_loss > 0 else 0.0
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Sharpe 비율 계산
        
        Args:
            risk_free_rate (float): 무위험 수익률
        
        Returns:
            float: Sharpe 비율
        """
        if self.df.empty:
            return 0.0
        
        # 일별 수익률 계산
        daily_returns = self._calculate_daily_returns()
        
        if daily_returns.empty:
            return 0.0
        
        # Sharpe 비율 계산
        excess_returns = daily_returns - risk_free_rate / 365
        sharpe_ratio = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0.0
        
        # 연간화 (252 거래일)
        sharpe_ratio *= np.sqrt(252)
        
        return sharpe_ratio
    
    def calculate_max_drawdown(self) -> float:
        """
        최대 낙폭 계산
        
        Returns:
            float: 최대 낙폭 (0.0 ~ 1.0)
        """
        if self.df.empty:
            return 0.0
        
        # 자본 곡선 계산
        equity_curve = self._calculate_equity_curve_values()
        
        if not equity_curve:
            return 0.0
        
        # 최대 낙폭 계산
        cumulative_max = np.maximum.accumulate(equity_curve)
        drawdown = (cumulative_max - equity_curve) / cumulative_max
        max_drawdown = np.max(drawdown)
        
        return max_drawdown
    
    def calculate_equity_curve(self) -> List[Dict[str, Any]]:
        """
        자본 곡선 계산
        
        Returns:
            List[Dict[str, Any]]: 자본 곡선 데이터
        """
        if self.df.empty:
            return []
        
        # 거래를 종료 시간 기준으로 정렬
        sorted_df = self.df.sort_values('exit_time')
        
        # 초기 자본 (예: 1000)
        initial_capital = 1000
        equity = initial_capital
        
        equity_curve = []
        
        for _, trade in sorted_df.iterrows():
            # 거래 후 자본 업데이트
            equity += trade.profit if trade.profit else 0
            
            equity_curve.append({
                'timestamp': trade.exit_time.isoformat(),
                'equity': equity,
                'trade_id': trade.id,
                'profit': trade.profit if trade.profit else 0,
                'symbol': trade.symbol
            })
        
        return equity_curve
    
    def _calculate_equity_curve_values(self) -> List[float]:
        """
        자본 곡선 값 계산 (내부 사용)
        
        Returns:
            List[float]: 자본 곡선 값
        """
        if self.df.empty:
            return []
        
        # 거래를 종료 시간 기준으로 정렬
        sorted_df = self.df.sort_values('exit_time')
        
        # 초기 자본 (예: 1000)
        initial_capital = 1000
        equity = initial_capital
        
        equity_values = [initial_capital]
        
        for _, trade in sorted_df.iterrows():
            # 거래 후 자본 업데이트
            equity += trade.profit if trade.profit else 0
            equity_values.append(equity)
        
        return equity_values
    
    def _calculate_daily_returns(self) -> pd.Series:
        """
        일별 수익률 계산 (내부 사용)
        
        Returns:
            pd.Series: 일별 수익률
        """
        if self.df.empty:
            return pd.Series()
        
        # 자본 곡선 계산
        equity_curve = self._calculate_equity_curve_values()
        
        if not equity_curve:
            return pd.Series()
        
        # 일별 수익률 계산
        equity_series = pd.Series(equity_curve)
        daily_returns = equity_series.pct_change().dropna()
        
        return daily_returns
    
    def calculate_drawdown_series(self) -> List[Dict[str, Any]]:
        """
        낙폭 시리즈 계산
        
        Returns:
            List[Dict[str, Any]]: 낙폭 시리즈 데이터
        """
        if self.df.empty:
            return []
        
        # 자본 곡선 계산
        equity_curve_data = self.calculate_equity_curve()
        
        if not equity_curve_data:
            return []
        
        # 자본 값 추출
        equity_values = [data['equity'] for data in equity_curve_data]
        timestamps = [data['timestamp'] for data in equity_curve_data]
        
        # 낙폭 계산
        cumulative_max = np.maximum.accumulate(equity_values)
        drawdown_values = [(cm - ev) / cm if cm > 0 else 0 for cm, ev in zip(cumulative_max, equity_values)]
        
        drawdown_series = []
        for i, (timestamp, drawdown) in enumerate(zip(timestamps, drawdown_values)):
            drawdown_series.append({
                'timestamp': timestamp,
                'drawdown': drawdown,
                'equity': equity_values[i]
            })
        
        return drawdown_series
    
    def calculate_monthly_returns(self, year: int) -> List[float]:
        """
        월별 수익률 계산
        
        Args:
            year (int): 연도
        
        Returns:
            List[float]: 월별 수익률 (1월부터 12월까지)
        """
        if self.df.empty:
            return [0.0] * 12
        
        # 해당 연도의 거래만 필터링
        year_df = self.df[self.df['exit_time'].dt.year == year]
        
        if year_df.empty:
            return [0.0] * 12
        
        # 월별 수익률 계산
        monthly_returns = []
        
        for month in range(1, 13):
            month_df = year_df[year_df['exit_time'].dt.month == month]
            month_profit = month_df['profit'].sum() if not month_df.empty else 0.0
            monthly_returns.append(month_profit)
        
        return monthly_returns
    
    def calculate_win_loss_distribution(self) -> Tuple[List[float], List[float]]:
        """
        승패 분포 계산
        
        Returns:
            Tuple[List[float], List[float]]: 승리 거래 분포, 손실 거래 분포
        """
        if self.df.empty:
            return [], []
        
        # 승리 거래와 손실 거래 분리
        winning_trades = self.df[self.df['profit'] > 0]['profit_percentage'].tolist()
        losing_trades = self.df[self.df['profit'] < 0]['profit_percentage'].tolist()
        
        return winning_trades, losing_trades
