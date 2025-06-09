# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.optimize.hyperopt import IHyperOptLoss


class ShortTermProfitHyperOptLoss(IHyperOptLoss):
    """
    단기 수익률을 극대화하는 손실함수
    
    특징:
    - 짧은 거래 기간에 더 높은 가중치 부여 (1시간 이내 거래에 3배 가중치)
    - 이익 거래에 추가 가중치 부여
    - 손실 거래에 페널티 부여
    - 거래 횟수에 대한 보너스 (더 많은 거래 장려)
    - 연속 이익 거래에 보너스 부여
    
    이 손실함수는 단기간에 빠른 수익을 내는 전략을 찾는 데 최적화되어 있습니다.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                              min_date: datetime, max_date: datetime,
                              config: Dict, processed: Dict[str, DataFrame],
                              backtest_stats: Dict[str, Any],
                              *args, **kwargs) -> float:
        if not trade_count:
            return 100000  # 거래가 없으면 큰 손실 값 반환
        
        if backtest_stats["profit_total"] <= 0:
            return 10000 - backtest_stats["profit_total"]  # 총 손실이 클수록 더 큰 값 반환
        
        # 거래 기간에 따른 가중치 부여 (단위: 시간)
        results["duration_hours"] = results["trade_duration"].dt.total_seconds() / 3600
        
        # 단기 거래에 더 높은 가중치 부여
        results["weight"] = 1.0
        results.loc[results["duration_hours"] <= 1, "weight"] = 3.0      # 1시간 이내 거래
        results.loc[(results["duration_hours"] > 1) & (results["duration_hours"] <= 4), "weight"] = 2.0  # 1-4시간 거래
        results.loc[(results["duration_hours"] > 4) & (results["duration_hours"] <= 12), "weight"] = 1.5  # 4-12시간 거래
        results.loc[(results["duration_hours"] > 12) & (results["duration_hours"] <= 24), "weight"] = 1.2  # 12-24시간 거래
        
        # 이익 거래에 추가 가중치 부여, 손실 거래에 페널티 부여
        results.loc[results["profit_ratio"] > 0, "weight"] *= 1.5
        results.loc[results["profit_ratio"] < 0, "weight"] *= 0.5
        
        # 가중 평균 수익률 계산
        weighted_profit = (results["profit_ratio"] * results["weight"]).sum() / results["weight"].sum()
        
        # 승률 계산 및 보너스
        win_count = len(results[results["profit_ratio"] > 0])
        win_rate = win_count / trade_count if trade_count > 0 else 0
        win_rate_bonus = win_rate * 0.5  # 승률이 높을수록 보너스 (최대 0.5)
        
        # 거래 수에 대한 보너스 (더 많은 거래 장려)
        trade_count_bonus = min(trade_count / 1000, 0.5)  # 최대 0.5
        
        # 최대 연속 이익 거래에 대한 보너스
        max_consecutive_wins = backtest_stats.get("max_consecutive_wins", 0)
        consecutive_win_bonus = min(max_consecutive_wins / 20, 0.5)  # 최대 0.5
        
        # 최종 점수 계산 (높을수록 좋음)
        score = weighted_profit * (1 + win_rate_bonus + trade_count_bonus + consecutive_win_bonus)
        
        # 드로다운에 대한 페널티
        max_drawdown = backtest_stats.get("max_drawdown", 0)
        if max_drawdown > 0.3:  # 30% 이상 드로다운에 페널티
            score = score * (1 - (max_drawdown - 0.3))
        
        # 음수로 반환하여 최대화
        return -score
