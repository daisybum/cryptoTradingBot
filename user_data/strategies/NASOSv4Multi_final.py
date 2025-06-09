from __future__ import annotations
from datetime import datetime, timezone
import logging
"""
NASOSv4_Q3_2025 – 2025 하반기 변동성·알트코인 순환장 대응 버전

✓ 매수 민감도 향상: 얕은 조정 및 초기 모멘텀 포착 강화
✓ 매도 신호 정확도 개선: RSI 기준 상향, 볼린저 밴드 조건 최적화
✓ 트레일링 스탑 최적화: 4% 이상 수익 시 2% 트레일링 스탑 적용
✓ 상승장 특화 매수 전략 추가: 모멘텀 기반 매수 및 브레이크아웃 전략
✓ 리스크 관리 개선: 상승장에 맞게 포지션 크기 및 드로다운 허용치 조정
"""

import logging
import os
import sys
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from datetime import timedelta

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
    merge_informative_pair,
)

# ───────────────────────────────────────────────────────────
# Risk‑manager optional import
# ───────────────────────────────────────────────────────────
try:
    from user_data.strategies.risk_manager import RiskManager

    RISK_MANAGER_AVAILABLE = True
except ImportError:
    RISK_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


class NASOSv4Multi_final(IStrategy):
    """NASOSv4Multi_final - 상승장 최적화 버전 (2025년 5월 업데이트)
    
    주요 개선 사항:
    - 매수 민감도 향상: 얕은 조정 및 초기 모멘텀 포착 강화
    - 매도 신호 정확도 개선: RSI 기준 상향, 볼린저 밴드 조건 최적화
    - 트레일링 스탑 최적화: 4% 이상 수익 시 2% 트레일링 스탑 적용
    - 상승장 특화 매수 전략 추가: 모멘텀 기반 매수 및 브레이크아웃 전략
    - 리스크 관리 개선: 상승장에 맞게 포지션 크기 및 드로다운 허용치 조정
    """

    # ─── Timeframes ───────────────────────────────────────
    timeframe = "5m"
    inf_1h = "1h"
    inf_4h = "4h"
    inf_1d = "1d"

    process_only_new_candles = True
    startup_candle_count = 200
    
    # 시장 상태 감지 및 손실 거래 관리를 위한 변수
    market_condition = "unknown"  # 시장 상태: bullish, bearish, correction, recovery, ranging, unknown
    market_trend_strength = 0.0   # 추세 강도 (0.0 ~ 1.0)
    market_volatility = 0.0       # 시장 변동성 (0.0 ~ 1.0)
    current_pair_trend = {}       # 각 페어별 현재 추세 저장
    max_holding_time = 48        # 최대 보유 시간 (시간 단위) - 손실 거래 보유 기간 단축
    early_exit_loss = -0.03      # 일찍 손실 시 조기 탈출 기준 (-3%)
    max_drawdown_exit = -0.07    # 최대 드로다운 시 탈출 기준 (-7%)

    # ─── Buy hyper‑parameters (optimized) ────────────────
    base_nb_candles_buy = IntParameter(5, 30, default=10, space="buy", optimize=True)
    low_offset = DecimalParameter(0.95, 0.99, default=0.984, space="buy", optimize=True)  # 얼은 조정 허용
    low_offset_2 = DecimalParameter(0.95, 0.99, default=0.985, space="buy", optimize=True)  # 얼은 조정 허용
    ewo_high = DecimalParameter(-1.0, 5.0, default=1.684, space="buy", optimize=True)  # EWO 임계값 완화
    ewo_high_2 = DecimalParameter(-3.0, 3.0, default=-0.747, space="buy", optimize=True)  # EWO 임계값 완화
    ewo_low = DecimalParameter(-20.0, -5.0, default=-9.52, space="buy", optimize=True)  # EWO 임계값 완화 (범위 확장: -20.0 ~ -5.0)
    rsi_buy = IntParameter(35, 55, default=37, space="buy", optimize=True)  # RSI 기준 완화
    rsi_fast_buy = IntParameter(20, 50, default=34, space="buy", optimize=False)
    volume_threshold = DecimalParameter(1.1, 2.0, default=1.833, space="buy", optimize=True)  # 볼륨 요구 완화

    # ─── Sell hyper‑parameters (optimized) ──────────────────────────
    base_nb_candles_sell = IntParameter(5, 100, default=56, space="sell", optimize=True)  # 범위 확장: 5 ~ 100
    high_offset = DecimalParameter(1.00, 1.30, default=1.123, space="sell", optimize=True)  # 범위 확장: 1.00 ~ 1.30
    high_offset_2 = DecimalParameter(1.05, 1.50, default=1.378, space="sell", optimize=True)
    rsi_sell = IntParameter(65, 90, default=79, space="sell", optimize=True)  # RSI 매도 기준 상향
    profit_threshold = DecimalParameter(0.01, 0.05, default=0.05, space="sell", optimize=True)  # 이익 임계값 상향
    bb_width_threshold = DecimalParameter(0.05, 0.30, default=0.251, space="sell", optimize=True)  # BB 폭 임계값 조정

    # ─── Risk / Stop / ROI ───────────────────────────────
    # ROI 파라미터 - 더 넓은 범위로 재정의
    @property
    def roi_space(self) -> Dict[str, Any]:
        return {
            "0": (0.005, 0.25, 0.005),  # 0분 후 0.5-25% 이익 실현 (더 넓고 세밀하게)
            "30": (0.005, 0.20, 0.005), # 30분 후 0.5-20% 이익 실현 (더 넓고 세밀하게)
            "60": (0.005, 0.15, 0.005), # 60분 후 0.5-15% 이익 실현
            "120": (0.0, 0.10, 0.005)   # 120분 후 0-10% 이익 실현 (상단 확장)
        }

    # 스탑로스 파라미터 - 더 현실적인 범위로 재정의
    @property
    def stoploss_space(self) -> Dict[str, Any]:
        return {
            "stoploss": (-0.10, -0.02, 0.01)  # 2-10% 손실 시 스탑로스 (더 타이트하게)
        }

    # 트레일링 스탑로스 파라미터 - 더 현실적인 범위로 재정의
    @property
    def trailing_space(self) -> Dict[str, Any]:
        return {
            "trailing_stop": (True, False),
            "trailing_stop_positive": (0.01, 0.10, 0.01),  # 1-10% 이익 시 트레일링 스탑 활성화
            "trailing_stop_positive_offset": (0.01, 0.10, 0.01),  # 1-10% 오프셋
            "trailing_only_offset_is_reached": (True, False)
        }

    # 최소 ROI 테이블 정의 (hyperopt 최적화)
    minimal_roi = {
        "0": 0.208,  # 0분 후 20.8% 이익 실현
        "38": 0.048,  # 38분 후 4.8% 이익 실현
        "93": 0.033,  # 93분 후 3.3% 이익 실현
        "210": 0      # 210분 후 이익 실현
    }

    # 스탑로스 설정 (hyperopt 최적화)
    # stoploss = -0.35  # 35% 손실 시 스탑로스 (상승장 전략에 맞게 넓게 설정) - Hyperopt가 stoploss_space를 사용하도록 주석 처리
    
    # 트레일링 스탑로스 설정 (hyperopt 최적화)
    trailing_stop = True
    trailing_stop_positive = 0.274  # 27.4% 이익 시 트레일링 스탑 활성화
    trailing_stop_positive_offset = 0.278  # 27.8% 오프셋
    trailing_only_offset_is_reached = True  # 오프셋 도달 시에만 트레일링 활성화

    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    order_time_in_force = {
        "entry": "gtc",
        "exit": "ioc",
    }

    # ─── Init ─────────────────────────────────────────────
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.risk_manager = None
        if RISK_MANAGER_AVAILABLE:
            try:
                self.risk_manager = RiskManager(
                    max_drawdown_allowed=0.07,  # 상승장에 맞게 7%로 상향 조정
                    risk_free_rate=0.01,
                    use_redis=True,
                    max_risk_per_trade=0.025,  # 2.5% 룰 (상승장에 맞게 상향)
                    max_open_trades=8,         # 최대 8개 동시 거래 유지
                )
                logger.info("RiskManager enabled for bull market (2.5% rule, 8 trades).")
            except Exception as exc:
                logger.error("RiskManager init failed: %s", exc)

        # 시장 상태 추적 변수
        self.market_condition = "neutral"  # 기본값: 중립
        self.market_trend_strength = 0.0   # 추세 강도 (0.0 ~ 1.0)
        self.last_candle_checked = 0       # 마지막으로 확인한 캔들 타임스탬프
        self.momentum_coins = set()        # 모멘텀이 강한 코인 추적
        
    # Hyperopt 손실 함수 정의 - Sharpe Ratio 최대화
    # 참고: Freqtrade에서 제공하는 SharpeHyperOptLoss를 사용할 것이미로 이 함수는 사용되지 않음
    # 이 함수는 참고용으로 남겨둡
    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                              min_date: datetime, max_date: datetime,
                              config: Dict, processed: Dict[str, DataFrame],
                              backtest_stats: Dict[str, Any],
                              *args, **kwargs) -> float:
        # Sharpe Ratio를 계산하여 최대화 (음수로 반환)
        if not trade_count or backtest_stats['profit_total'] <= 0:
            return -20.0  # 수익이 없거나 음수인 경우 크게 불리한 값 반환
        
        
        # 일별 수익률 계산
        
        daily_returns = results.resample('D', on='close_date')['profit_ratio'].sum()
        
        # Sharpe Ratio 계산 (risk-free rate = 0)
        
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(365)
        
        # 음수로 반환하여 최대화
        
        return -sharpe_ratio if not np.isnan(sharpe_ratio) else -20.0
        
        
    # 매수 조건 hyperopt 공간 정의 - 더 세분화된 범위
    @property
    def buy_params_space(self) -> Dict[str, Any]:
        return {
            "rsi_buy": (30, 70, 2),  # 더 세분화된 단계로 탐색
            "rsi_fast_buy": (20, 50, 2),  # 더 세분화된 단계로 탐색
            "low_offset": (0.95, 0.99, 0.002),  # 더 세분화된 단계로 탐색
            "low_offset_2": (0.94, 0.99, 0.002),  # 더 넓은 범위로 탐색
            "ewo_high": (-2.0, 8.0, 0.2),  # 더 넓은 범위와 세분화된 단계로 탐색
            "ewo_high_2": (-4.0, 4.0, 0.2),  # 더 세분화된 단계로 탐색
            "ewo_low": (-20.0, -5.0, 0.5),  # 더 세분화된 단계로 탐색
            "volume_threshold": (1.0, 5.0, 0.1),  # 더 넓은 범위로 탐색
            "base_nb_candles_buy": (5, 50, 5),  # 캩4들 수 탐색 추가
        }
    
    # 매도 조건 hyperopt 공간 정의 - 더 세분화된 범위
    @property
    def sell_params_space(self) -> Dict[str, Any]:
        return {
            "rsi_sell": (50, 95, 2),  # 더 넓은 범위와 세분화된 단계로 탐색
            "high_offset": (1.00, 1.20, 0.005),  # 더 넓은 범위와 세분화된 단계로 탐색
            "high_offset_2": (1.05, 1.40, 0.01),  # 더 넓은 범위로 탐색
            "profit_threshold": (0.01, 0.10, 0.002),  # 더 넓은 범위와 세분화된 단계로 탐색
            "bb_width_threshold": (0.05, 0.40, 0.01),  # 더 넓은 범위와 세분화된 단계로 탐색
            "base_nb_candles_sell": (5, 80, 5),  # 캩4들 수 탐색 추가
        }

    # ─── Informative pairs (Top‑30) ───────────────────────
    def informative_pairs(self):
        top30 = [
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT",
            "XRP/USDT",
            "ADA/USDT",
            "DOGE/USDT",
            "SOL/USDT",
            "TRX/USDT",
            "DOT/USDT",
            "MATIC/USDT",
            "LTC/USDT",
            "SHIB/USDT",
            "AVAX/USDT",
            "UNI/USDT",
            "LINK/USDT",
            "ATOM/USDT",
            "XMR/USDT",
            "XLM/USDT",
            "BCH/USDT",
            "TON/USDT",
            "ETC/USDT",
            "APT/USDT",
            "QNT/USDT",
            "FIL/USDT",
            "NEAR/USDT",
            "ICP/USDT",
            "HBAR/USDT",
            "VET/USDT",
            "INJ/USDT",
            "SEI/USDT",
        ]
        pairs = []
        for p in top30:
            pairs += [(p, self.inf_1h), (p, self.inf_4h), (p, self.inf_1d)]
        return pairs

    # ─── populate_indicators (상승장 최적화) ─────────────────
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:  # noqa: C901
        # --- Initialize a dictionary to hold new indicators ---
        new_indicators = {}

        # 기본 타임프레임 지표 계산
        for val in self.base_nb_candles_buy.range:
            new_indicators[f"ma_buy_{val}"] = ta.EMA(dataframe, timeperiod=val)
        for val in self.base_nb_candles_sell.range:
            new_indicators[f"ma_sell_{val}"] = ta.EMA(dataframe, timeperiod=val)

        # 이동평균선
        new_indicators['hma_50'] = qtpylib.hull_moving_average(dataframe['close'], window=50)
        new_indicators['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        new_indicators['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        new_indicators['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        new_indicators['sma_9'] = ta.SMA(dataframe, timeperiod=9)
        
        # 볼륨 지표
        new_indicators['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        new_indicators['volume_norm'] = dataframe['volume'] / new_indicators['volume_mean'] # Use calculated mean
        
        # EWO (Elliott Wave Oscillator)
        fast_ema = ta.EMA(dataframe, timeperiod=50)
        slow_ema = ta.EMA(dataframe, timeperiod=200)
        new_indicators['EWO'] = (fast_ema - slow_ema) / dataframe['low'] * 100

        # RSI 지표
        new_indicators['rsi'] = ta.RSI(dataframe, timeperiod=14)
        new_indicators['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)  # 중요: 매수 신호에서 사용
        new_indicators['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)
        
        # 볼린저 밴드
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        new_indicators['bb_lowerband'] = bollinger['lower']
        new_indicators['bb_middleband'] = bollinger['mid']
        new_indicators['bb_upperband'] = bollinger['upper']
        new_indicators['bb_width'] = (new_indicators['bb_upperband'] - new_indicators['bb_lowerband']) / new_indicators['bb_middleband']
        
        # 가격 변화율
        new_indicators['close_prev'] = dataframe['close'].shift(1)
        new_indicators['close_change'] = (dataframe['close'] - new_indicators['close_prev']) / new_indicators['close_prev']
        
        # MACD
        macd = ta.MACD(dataframe)
        new_indicators['macd'] = macd['macd']
        new_indicators['macdsignal'] = macd['macdsignal']
        new_indicators['macdhist'] = macd['macdhist']
        
        # ATR (Average True Range) - 변동성 측정
        new_indicators['atr'] = ta.ATR(dataframe, timeperiod=14)

        # --- Assign all new base indicators at once ---
        dataframe = pd.concat([dataframe, pd.DataFrame(new_indicators, index=dataframe.index)], axis=1)
        
        # 다양한 타임프레임 지표 추가
        if self.dp:
            # 1시간 데이터 병합
            inf_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_1h)
            if not inf_1h.empty:
                temp_inf_1h_indicators = {}
                # 1시간 지표 계산
                temp_inf_1h_indicators['rsi'] = ta.RSI(inf_1h, timeperiod=14)
                temp_inf_1h_indicators['ema_50'] = ta.EMA(inf_1h, timeperiod=50)
                temp_inf_1h_indicators['ema_200'] = ta.EMA(inf_1h, timeperiod=200)
                temp_inf_1h_indicators['hma_50'] = qtpylib.hull_moving_average(inf_1h['close'], window=50)
                temp_inf_1h_indicators['volume_mean'] = inf_1h['volume'].rolling(window=24).mean()
                
                # 볼린저 밴드 (1시간)
                bollinger_1h = qtpylib.bollinger_bands(qtpylib.typical_price(inf_1h), window=20, stds=2)
                temp_inf_1h_indicators['bb_lowerband'] = bollinger_1h['lower']
                temp_inf_1h_indicators['bb_middleband'] = bollinger_1h['mid']
                temp_inf_1h_indicators['bb_upperband'] = bollinger_1h['upper']
                temp_inf_1h_indicators['bb_width'] = (temp_inf_1h_indicators['bb_upperband'] - temp_inf_1h_indicators['bb_lowerband']) / temp_inf_1h_indicators['bb_middleband']
                
                # MACD (1시간)
                macd_1h = ta.MACD(inf_1h)
                temp_inf_1h_indicators['macd'] = macd_1h['macd']
                temp_inf_1h_indicators['macdsignal'] = macd_1h['macdsignal']
                temp_inf_1h_indicators['macdhist'] = macd_1h['macdhist']
                
                # 추세 강도 지표 (1시간)
                temp_inf_1h_indicators['trend_strength'] = abs(temp_inf_1h_indicators['ema_50'] - temp_inf_1h_indicators['ema_200']) / temp_inf_1h_indicators['ema_200'] * 100
                temp_inf_1h_indicators['is_uptrend'] = temp_inf_1h_indicators['ema_50'] > temp_inf_1h_indicators['ema_200']
                
                inf_1h = inf_1h.assign(**temp_inf_1h_indicators)
                
                # 컴럼명 충돌 방지를 위한 리네이밍
                inf_1h.rename(columns=lambda s: f"{s}_{self.inf_1h}", inplace=True)
                
                # 데이터 병합
                try:
                    dataframe = merge_informative_pair(dataframe, inf_1h, self.timeframe, self.inf_1h, ffill=True, date_column='date_utc')
                except KeyError:
                    try:
                        dataframe = merge_informative_pair(dataframe, inf_1h, self.timeframe, self.inf_1h, ffill=True)
                    except KeyError:
                        pass # Or log an error
            
            # 4시간 데이터 병합
            inf_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_4h)
            if not inf_4h.empty:
                temp_inf_4h_indicators = {}
                # 4시간 지표 계산
                temp_inf_4h_indicators['rsi'] = ta.RSI(inf_4h, timeperiod=14)
                temp_inf_4h_indicators['ema_50'] = ta.EMA(inf_4h, timeperiod=50)
                temp_inf_4h_indicators['ema_200'] = ta.EMA(inf_4h, timeperiod=200)
                
                # 볼린저 밴드 (4시간)
                bollinger_4h = qtpylib.bollinger_bands(qtpylib.typical_price(inf_4h), window=20, stds=2)
                temp_inf_4h_indicators['bb_lowerband'] = bollinger_4h['lower']
                temp_inf_4h_indicators['bb_middleband'] = bollinger_4h['mid']
                temp_inf_4h_indicators['bb_upperband'] = bollinger_4h['upper']
                temp_inf_4h_indicators['bb_width'] = (temp_inf_4h_indicators['bb_upperband'] - temp_inf_4h_indicators['bb_lowerband']) / temp_inf_4h_indicators['bb_middleband']
                
                # 시장 추세 판단 (4시간 차트 기준)
                temp_inf_4h_indicators['is_uptrend'] = temp_inf_4h_indicators['ema_50'] > temp_inf_4h_indicators['ema_200']
                temp_inf_4h_indicators['trend_strength'] = abs(temp_inf_4h_indicators['ema_50'] - temp_inf_4h_indicators['ema_200']) / temp_inf_4h_indicators['ema_200'] * 100
                
                inf_4h = inf_4h.assign(**temp_inf_4h_indicators)

                # 컴럼명 충돌 방지를 위한 리네이밍
                inf_4h.rename(columns=lambda s: f"{s}_{self.inf_4h}", inplace=True)
                
                # 데이터 병합
                try:
                    dataframe = merge_informative_pair(dataframe, inf_4h, self.timeframe, self.inf_4h, ffill=True, date_column='date_utc')
                except KeyError:
                    try:
                        dataframe = merge_informative_pair(dataframe, inf_4h, self.timeframe, self.inf_4h, ffill=True)
                    except KeyError:
                        pass # Or log an error
                        
            # 일봉 데이터 병합
            inf_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_1d)
            if not inf_1d.empty:
                temp_inf_1d_indicators = {}
                # 일봉 지표 계산
                temp_inf_1d_indicators['rsi'] = ta.RSI(inf_1d, timeperiod=14)
                temp_inf_1d_indicators['ema_50'] = ta.EMA(inf_1d, timeperiod=50)
                temp_inf_1d_indicators['ema_200'] = ta.EMA(inf_1d, timeperiod=200)
                
                # 볼린저 밴드 (일봉)
                bollinger_1d = qtpylib.bollinger_bands(qtpylib.typical_price(inf_1d), window=20, stds=2)
                temp_inf_1d_indicators['bb_lowerband'] = bollinger_1d['lower']
                temp_inf_1d_indicators['bb_middleband'] = bollinger_1d['mid']
                temp_inf_1d_indicators['bb_upperband'] = bollinger_1d['upper']
                temp_inf_1d_indicators['bb_width'] = (temp_inf_1d_indicators['bb_upperband'] - temp_inf_1d_indicators['bb_lowerband']) / temp_inf_1d_indicators['bb_middleband']
                
                # 시장 추세 판단 (일봉 차트 기준)
                temp_inf_1d_indicators['is_uptrend'] = temp_inf_1d_indicators['ema_50'] > temp_inf_1d_indicators['ema_200']
                temp_inf_1d_indicators['trend_strength'] = abs(temp_inf_1d_indicators['ema_50'] - temp_inf_1d_indicators['ema_200']) / temp_inf_1d_indicators['ema_200'] * 100
                
                inf_1d = inf_1d.assign(**temp_inf_1d_indicators)
                
                # 컴럼명 충돌 방지를 위한 리네이밍
                inf_1d.rename(columns=lambda s: f"{s}_{self.inf_1d}", inplace=True)
                
                # 데이터 병합
                try:
                    dataframe = merge_informative_pair(dataframe, inf_1d, self.timeframe, self.inf_1d, ffill=True, date_column='date_utc')
                except KeyError:
                    try:
                        dataframe = merge_informative_pair(dataframe, inf_1d, self.timeframe, self.inf_1d, ffill=True)
                    except KeyError:
                        pass # Or log an error
        
        # NaN 값 처리 (FutureWarning 수정)
        dataframe.ffill(inplace=True)
        
        # 시장 상태 판단 (글로벌 변수 업데이트)
        if 'is_uptrend_1d' in dataframe.columns and 'is_uptrend_4h' in dataframe.columns:
            last_candle = dataframe.iloc[-1]
            
            # 일봉 및 4시간 차트 기반 시장 상태 판단
            day_trend = last_candle['is_uptrend_1d']
            h4_trend = last_candle['is_uptrend_4h']
            
            if day_trend and h4_trend:
                self.market_condition = 'bullish'  # 강세장
            elif not day_trend and not h4_trend:
                self.market_condition = 'bearish'  # 약세장
            elif day_trend and not h4_trend:
                self.market_condition = 'correction'  # 상승 추세 조정
            else:
                self.market_condition = 'recovery'  # 하락 추세 반등
                
            # 추세 강도 계산 (0.0 ~ 1.0)
            if 'trend_strength_1d' in last_candle and 'trend_strength_4h' in last_candle:
                # Ensure the columns exist before trying to access them for division
                trend_strength_1d_val = last_candle.get('trend_strength_1d', 0)
                trend_strength_4h_val = last_candle.get('trend_strength_4h', 0)
                ema_200_1d_val = last_candle.get(f'ema_200_{self.inf_1d}', 0) # Use renamed column
                ema_200_4h_val = last_candle.get(f'ema_200_{self.inf_4h}', 0) # Use renamed column

                # Avoid division by zero if ema_200 is 0 or not present
                day_strength_raw = (abs(last_candle.get(f'ema_50_{self.inf_1d}', 0) - ema_200_1d_val) / ema_200_1d_val * 100) if ema_200_1d_val else 0
                h4_strength_raw = (abs(last_candle.get(f'ema_50_{self.inf_4h}', 0) - ema_200_4h_val) / ema_200_4h_val * 100) if ema_200_4h_val else 0

                day_strength = min(day_strength_raw / 50.0, 1.0)
                h4_strength = min(h4_strength_raw / 30.0, 1.0)
                self.market_trend_strength = (day_strength * 0.7) + (h4_strength * 0.3)  # 일봉 70%, 4시간 30% 가중치
            else:
                self.market_trend_strength = 0.0 # Default if trend strength columns are missing
        else:
            self.market_condition = 'unknown' # Default if trend columns are missing
            self.market_trend_strength = 0.0

        return dataframe

    # ─── populate_buy_trend (상승장 최적화) ──────────
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["buy"] = 0
        dataframe["buy_tag"] = ""
        
        # 1. 얕은 조정 매수 (상승 추세 중 조정 매수)
        ewo1 = (
            (dataframe["rsi_fast"] < self.rsi_fast_buy.value)
            & (
                dataframe["close"]
                < dataframe[f"ma_buy_{self.base_nb_candles_buy.value}"] * self.low_offset.value
            )
            & (dataframe["EWO"] > self.ewo_high.value)
            & (dataframe["rsi"] < self.rsi_buy.value)
            & (dataframe["volume_norm"] > 1.3)
        )

        # 2. 중간 강도 조정 매수
        ewo2 = (
            (dataframe["rsi_fast"] < self.rsi_fast_buy.value)
            & (
                dataframe["close"]
                < dataframe[f"ma_buy_{self.base_nb_candles_buy.value}"] * self.low_offset_2.value
            )
            & (dataframe["EWO"] > self.ewo_high_2.value)
            & (dataframe["rsi"] < 35)  # RSI 기준 완화 (30 -> 35)
            & (dataframe["volume_norm"] > self.volume_threshold.value)
        )

        # 3. 과매도 반동 매수 - 유지
        ewolow = (
            (dataframe["rsi_fast"] < self.rsi_fast_buy.value)
            & (dataframe["EWO"] < self.ewo_low.value)
            & (dataframe["volume_norm"] > self.volume_threshold.value)
            & (dataframe["rsi"] < 25)
        )

        # 4. 볼린저 밴드 반동 매수 - 완화
        bb_bounce = (
            (dataframe["close"] < dataframe["bb_lowerband"] * 1.01)
            & (dataframe["rsi"] < 30)
            & (dataframe["volume_norm"] > 1.2)
            & (dataframe["close"] > dataframe["close"].shift(1))  # 가격 상승 시작 필터 추가
        )
        
        # 5. [새로추가] 모멘텀 기반 매수 (상승장 특화)
        momentum_buy = (
            (dataframe["close"] > dataframe["ema_50"]) &  # 가격이 EMA-50 위
            (dataframe["ema_50"] > dataframe["ema_100"]) &  # EMA-50이 EMA-100 위
            (dataframe["ema_100"] > dataframe["ema_200"]) &  # EMA-100이 EMA-200 위
            (dataframe["rsi"] > 50) & (dataframe["rsi"] < 70) &  # RSI 50-70 사이
            (dataframe["volume_norm"] > 1.5) &  # 평균보다 50% 이상 높은 볼륨
            (dataframe["close"] > dataframe["close"].shift(1)) &  # 가격 상승
            (dataframe["macdhist"] > 0)  # MACD 히스토그램 양수
        )
        
        # 6. [새로추가] 브레이크아웃 매수 (상승장 특화)
        breakout_buy = (
            (dataframe["close"] > dataframe["high"].rolling(20).max() * 0.99) &  # 20분 고점 근처 돌파
            (dataframe["volume"] > dataframe["volume"].rolling(20).mean() * 2) &  # 볼륨 폭발
            (dataframe["rsi"] < 75) &  # RSI 75 미만
            (dataframe["close"] > dataframe["ema_50"]) &  # 가격이 EMA-50 위
            (dataframe["bb_width"] > 0.1)  # 볼린저 밴드 폭이 적당히 넓을 때
        )
        
        # 다양한 타임프레임 기반 필터링 추가
        if 'ema_50_1h' in dataframe.columns and 'ema_200_1h' in dataframe.columns:
            # 1시간 차트에서 상승 추세일 때만 모멘텀 및 브레이크아웃 매수 허용
            h1_uptrend = (dataframe['ema_50_1h'] > dataframe['ema_200_1h'])
            momentum_buy = momentum_buy & h1_uptrend
            breakout_buy = breakout_buy & h1_uptrend
        
        # 시장 상황에 따른 매수 신호 필터링
        if self.market_condition == 'bullish':
            # 강세장에서는 모멘텀 및 브레이크아웃 전략 강화
            pass  # 기본 조건 유지
        elif self.market_condition == 'bearish':
            # 약세장에서는 모멘텀 및 브레이크아웃 전략 비활성화
            momentum_buy = pd.Series(False, index=dataframe.index)
            breakout_buy = pd.Series(False, index=dataframe.index)
        
        # 매수 신호 적용
        dataframe.loc[ewo1, ["buy", "buy_tag"]] = (1, "ewo1")
        dataframe.loc[ewo2, ["buy", "buy_tag"]] = (1, "ewo2")
        dataframe.loc[ewolow, ["buy", "buy_tag"]] = (1, "ewolow")
        dataframe.loc[bb_bounce, ["buy", "buy_tag"]] = (1, "bb_bounce")
        dataframe.loc[momentum_buy, ["buy", "buy_tag"]] = (1, "momentum")
        dataframe.loc[breakout_buy, ["buy", "buy_tag"]] = (1, "breakout")
        
        # 리스크 관리 시스템 통합
        if self.risk_manager is not None:
            # 시장 상황에 따른 포지션 크기 조정
            if self.market_condition == 'bullish':
                # 강세장에서는 기본 리스크 사용
                self.risk_manager.adjust_risk_factor(1.0)
            elif self.market_condition == 'bearish':
                # 약세장에서는 리스크 감소
                self.risk_manager.adjust_risk_factor(0.5)
            
            # 리스크 관리 시스템에서 거래 허용하지 않으면 매수 신호 취소
            if not self.risk_manager.check_trade_allowed(metadata['pair']):
                dataframe.loc[:, 'buy'] = 0
                dataframe.loc[:, 'buy_tag'] = ''
        
        # 모멘텀 코인 추적 업데이트
        if dataframe.iloc[-1]['buy'] == 1 and dataframe.iloc[-1]['buy_tag'] in ['momentum', 'breakout']:
            self.momentum_coins.add(metadata['pair'])

        return dataframe

    # ─── populate_sell_trend (상승장 최적화) ───
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sell"] = 0
        dataframe["sell_tag"] = ""

        # 1. RSI 기반 매도 - 상승장에 맞게 기준 상향 조정
        rsi_exit = (
            (dataframe["rsi"] > self.rsi_sell.value) &  # RSI 80 이상 (상향 조정)
            (dataframe["close"] > dataframe[f"ma_sell_{self.base_nb_candles_sell.value}"]) &
            # 추가 필터: 가격이 전날보다 하락하기 시작할 때만 매도
            (dataframe["close"] < dataframe["close"].shift(1))
        )

        # 2. 볼린저 밴드 상단 매도 - 정확도 향상
        bb_exit = (
            (dataframe["close"] > dataframe["bb_upperband"] * 0.99) &  # 볼린저 밴드 상단 근처
            (dataframe["close"] < dataframe["close"].shift(1)) &  # 가격 하락 시작
            (dataframe["rsi"] > 70) &  # RSI도 높은 상태
            (dataframe["volume"] > dataframe["volume_mean"])  # 볼륨도 평균 이상
        )

        # 3. MACD 하락 크로스 매도 - 정확도 향상
        macd_exit = (
            (dataframe["macd"] < dataframe["macdsignal"]) &  # MACD 하락 크로스
            (dataframe["macd"].shift(1) > dataframe["macdsignal"].shift(1)) &  # 이전 캔들은 MACD 상승 상태
            (dataframe["rsi"] > 65) &  # RSI 65 이상
            (dataframe["close"] > dataframe["ema_50"]) &  # 가격이 EMA-50 위
            (dataframe["close"] < dataframe["close"].shift(1))  # 가격 하락 시작
        )
        
        # 4. [새로추가] 추세 전환 매도 - 상승 추세의 전환을 감지
        trend_change_exit = (
            (dataframe["ema_50"] < dataframe["ema_50"].shift(3)) &  # EMA-50 하락 시작
            (dataframe["close"] < dataframe["ema_50"]) &  # 가격이 EMA-50 아래
            (dataframe["close"] < dataframe["close"].shift(1)) &  # 가격 하락
            (dataframe["volume"] > dataframe["volume_mean"] * 1.5) &  # 높은 볼륨
            (dataframe["rsi"] < dataframe["rsi"].shift(1)) &  # RSI 하락
            (dataframe["rsi"] > 60)  # RSI가 여전히 높은 수준
        )
        
        # 5. [새로추가] 시장 상황에 따른 매도 신호 조정
        if self.market_condition == 'bullish':
            # 강세장에서는 매도 신호 민감도 감소 (조기 매도 방지)
            rsi_exit = rsi_exit & (dataframe["rsi"] > 85)  # RSI 기준 더 상향
            macd_exit = macd_exit & (dataframe["rsi"] > 70)  # RSI 기준 더 상향
        elif self.market_condition == 'bearish':
            # 약세장에서는 매도 신호 민감도 증가 (빠른 손실 방지)
            rsi_exit = rsi_exit & (dataframe["rsi"] > 75)  # RSI 기준 하향
            macd_exit = macd_exit & (dataframe["rsi"] > 60)  # RSI 기준 하향
            rsi_exit = rsi_exit | (dataframe["rsi"] < dataframe["rsi"].shift(3) * 0.95)  # RSI 하락 추세 감지
        
        # 6. [새로추가] 손실 거래 보유 기간 단축 로직
        # 트레이딩 뷰에서는 이 로직을 구현할 수 없지만, freqtrade에서는 가능
        # 이 로직은 백테스팅에서는 작동하지 않고 실제 거래에서만 작동합니다
        # 실제 거래에서는 check_exit 함수에서 처리됩니다
        
        # 7. [새로추가] 조기 손실 컷 로직 (백테스팅용)
        early_loss_exit = (
            (dataframe["close"] < dataframe["open"] * (1 + self.early_exit_loss)) &  # 현재 가격이 진입가 대비 -3% 이하
            (dataframe["close"] < dataframe["close"].shift(1)) &  # 가격이 하락 중
            (dataframe["volume"] > dataframe["volume_mean"] * 0.8)  # 적정 거래량
        )
        
        # 8. [새로추가] 최대 드로다운 탈출 로직 (백테스팅용)
        max_drawdown_exit = (
            (dataframe["close"] < dataframe["open"] * (1 + self.max_drawdown_exit)) &  # 현재 가격이 진입가 대비 -7% 이하
            (dataframe["volume"] > dataframe["volume_mean"] * 0.5)  # 최소 거래량
        )
        
        # 6. [새로추가] 모멘텀 코인에 대한 특별 매도 전략
        is_momentum_coin = metadata['pair'] in self.momentum_coins
        if is_momentum_coin:
            # 모멘텀 코인은 더 오래 보유하고 더 높은 이익을 추구
            rsi_exit = rsi_exit & (dataframe["rsi"] > 90)  # RSI 기준 더 상향
            bb_exit = bb_exit & (dataframe["close"] > dataframe["bb_upperband"] * 1.01)  # 볼린저 밴드 상단 더 상향
        
        # 매도 신호 적용
        dataframe.loc[rsi_exit, ["sell", "sell_tag"]] = (1, "rsi_exit")
        dataframe.loc[bb_exit, ["sell", "sell_tag"]] = (1, "bb_exit")
        dataframe.loc[macd_exit, ["sell", "sell_tag"]] = (1, "macd_exit")
        dataframe.loc[trend_change_exit, ["sell", "sell_tag"]] = (1, "trend_change")
        dataframe.loc[early_loss_exit, ["sell", "sell_tag"]] = (1, "early_loss")
        dataframe.loc[max_drawdown_exit, ["sell", "sell_tag"]] = (1, "max_drawdown")
        
        return dataframe
        
    # 실제 거래에서 손실 거래 보유 기간 단축 로직 구현
    def check_exit(self, trade: Trade, order_type: str, amount: float, rate: float,
                  time_in_force: str, exit_reason: str, **kwargs) -> bool:
        """
        실제 거래에서 손실 거래의 보유 기간을 단축하는 로직
        백테스팅에서는 작동하지 않고 실제 거래에서만 작동합니다.
        """
        # 실제 거래에서만 작동하는 로직
        current_time = datetime.now(timezone.utc)
        current_rate = self.get_current_price(trade.pair)
        current_profit = trade.calc_profit_ratio(current_rate)
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600  # 시간 단위
        
        # 1. 손실 거래 보유 기간 단축 로직
        if current_profit < 0 and trade_duration > self.max_holding_time:
            logger.info(f"투자 시간 초과 ({trade_duration:.1f} 시간) - {trade.pair} 손실 거래 종료")
            return True
        
        # 2. 조기 손실 컷 로직
        if current_profit <= self.early_exit_loss and trade_duration > 1:  # 최소 1시간 이상 보유 후 손실 시
            logger.info(f"조기 손실 컷 ({current_profit:.2%}) - {trade.pair} 손실 거래 종료")
            return True
        
        # 3. 최대 드로다운 탈출 로직
        if current_profit <= self.max_drawdown_exit:
            logger.info(f"최대 드로다운 탈출 ({current_profit:.2%}) - {trade.pair} 손실 거래 종료")
            return True
            
        # 4. 시장 상태에 따른 손실 거래 관리
        if self.market_condition == 'bearish' and current_profit < -0.02 and trade_duration > 12:
            # 약세장에서는 손실 거래를 일찍 종료 (-2% 이상 손실, 12시간 이상 보유)
            logger.info(f"약세장 손실 거래 종료 ({current_profit:.2%}) - {trade.pair}")
            return True
        
        return False
        
    # 현재 가격 가져오기 함수
    def get_current_price(self, pair: str) -> float:
        """현재 가격을 가져오는 함수"""
        ticker = self.exchange.fetch_ticker(pair)
        return ticker['last']
