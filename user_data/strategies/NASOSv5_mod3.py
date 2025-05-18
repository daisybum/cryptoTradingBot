"""
NASOSv5_mod3 전략 (NotAnotherSMAOffsetStrategy v5 mod3)

- 5분 봉 기준 매매, 15분‧1시간 봉 정보 보강
- RSI_fast + SMA 오프셋 진입, EWO·EMA·MA 필터링
- 최적화용 하이퍼파라미터(IntParameter, DecimalParameter) 적용
"""

# --- 필수 라이브러리 ---
from functools import reduce
from datetime import datetime
from typing import List, Tuple
import logging

import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    stoploss_from_open,
)
from freqtrade.strategy.strategy_helper import merge_informative_pair
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 보조 지표 함수
# -----------------------------------------------------------------------------

def ewo(dataframe: DataFrame, fast: int = 5, slow: int = 35) -> Series:
    """Elliott Wave Oscillator (EWO)"""
    ema_fast = ta.EMA(dataframe, timeperiod=fast)
    ema_slow = ta.EMA(dataframe, timeperiod=slow)
    return (ema_fast - ema_slow) / dataframe["close"] * 100


def hma(dataframe: DataFrame, period: int) -> Series:
    """Hull Moving Average"""
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    wma1 = ta.WMA(dataframe, timeperiod=half_period)
    wma2 = ta.WMA(dataframe, timeperiod=period)
    hull = 2 * wma1 - wma2
    return ta.WMA(hull, timeperiod=sqrt_period)


# -----------------------------------------------------------------------------
# 메인 전략 클래스
# -----------------------------------------------------------------------------

class NASOSv5_mod3(IStrategy):
    INTERFACE_VERSION = 3

    # --------------------------------------------------
    # ROI / 손절 / 트레일링 설정
    # --------------------------------------------------
    minimal_roi = {
        "0": 0.10,
        "30": 0.05,
        "60": 0.03,
        "120": 0.01,
    }

    stoploss = -0.035
    trailing_stop = True
    trailing_stop_positive = 0.002
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # --------------------------------------------------
    # 타임프레임
    # --------------------------------------------------
    timeframe = "5m"
    informative_tf_15m = "15m"
    informative_tf_1h = "1h"

    process_only_new_candles = True
    startup_candle_count = 200

    # --------------------------------------------------
    # 하이퍼파라미터 정의
    # --------------------------------------------------
    buy_rsi_fast = IntParameter(10, 50, default=11, space="buy")
    buy_rsi = IntParameter(10, 50, default=35, space="buy")
    buy_sma_offset = DecimalParameter(0.93, 0.99, default=0.965, space="buy")
    buy_ewo_high = DecimalParameter(2.0, 12.0, default=4.0, space="buy")
    buy_ewo_low = DecimalParameter(-12.0, -2.0, default=-6.0, space="buy")
    buy_ema_diff = DecimalParameter(0.022, 0.03, default=0.025, space="buy")
    buy_ema_high = DecimalParameter(0.9, 1.2, default=0.95, space="buy")
    buy_ema_low = DecimalParameter(0.8, 1.0, default=0.85, space="buy")

    sell_rsi = IntParameter(50, 100, default=75, space="sell")

    # --------------------------------------------------
    # 보호 로직 (옵션)
    # --------------------------------------------------
    protections = [
        {
            "method": "LowProfitPairs",
            "lookback_period_candles": 60,
            "trade_limit": 1,
            "stop_duration": 60,
            "required_profit": -0.05,
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 24,
            "trade_limit": 1,
            "stop_duration_candles": 12,
            "max_allowed_drawdown": 0.20,
        },
    ]

    # --------------------------------------------------
    # 정보용 페어 정의
    # --------------------------------------------------
    def informative_pairs(self) -> List[Tuple[str, str]]:
        pairs = self.dp.current_whitelist()
        inf_pairs = []
        for pair in pairs:
            inf_pairs.append((pair, self.informative_tf_15m))
            inf_pairs.append((pair, self.informative_tf_1h))
        return inf_pairs

    # --------------------------------------------------
    # 지표 계산
    # --------------------------------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if dataframe.empty:
            return dataframe

        # 기본(5m) 지표
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["rsi_fast"] = ta.RSI(dataframe, timeperiod=self.buy_rsi_fast.value)
        dataframe["sma_9"] = ta.SMA(dataframe, timeperiod=9)
        dataframe["sma_5"] = ta.SMA(dataframe, timeperiod=5)
        dataframe["ema_14"] = ta.EMA(dataframe, timeperiod=14)
        dataframe["ema_26"] = ta.EMA(dataframe, timeperiod=26)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["ema_diff"] = (dataframe["ema_26"] - dataframe["ema_14"]) / dataframe["ema_14"]
        dataframe["ewo"] = ewo(dataframe)
        dataframe["ma_offset_buy"] = dataframe["sma_9"] * self.buy_sma_offset.value

        # 정보용 15m, 1h 병합
        inf_15m = self.dp.get_pair_dataframe(metadata["pair"], timeframe=self.informative_tf_15m)
        inf_1h = self.dp.get_pair_dataframe(metadata["pair"], timeframe=self.informative_tf_1h)

        for inf_df, tf in ((inf_15m, self.informative_tf_15m), (inf_1h, self.informative_tf_1h)):
            if inf_df is None or inf_df.empty:
                continue
            inf_df[f"rsi_{tf}"] = ta.RSI(inf_df, timeperiod=14)
            inf_df[f"sma_200_{tf}"] = ta.SMA(inf_df, timeperiod=200)
            inf_df[f"hma_50_{tf}"] = hma(inf_df, 50)
            dataframe = merge_informative_pair(
                dataframe, inf_df, self.timeframe, tf, ffill=True
            )

        return dataframe

    # --------------------------------------------------
    # 매수 조건
    # --------------------------------------------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        if dataframe.empty:
            return dataframe

        basic = (
            (dataframe["rsi_fast"] < self.buy_rsi.value) &
            (dataframe["close"] < dataframe["ma_offset_buy"]) &
            (dataframe["ema_50"] > dataframe["ema_200"]) &
            (dataframe["volume"] > 0)
        )

        cond_high = (
            basic &
            (dataframe["ewo"] > self.buy_ewo_high.value) &
            (dataframe["rsi"] < 35) &
            (dataframe["close"] < dataframe["sma_5"] * self.buy_ema_high.value)
        )

        cond_low = (
            basic &
            (dataframe["ewo"] < self.buy_ewo_low.value) &
            (dataframe["ema_diff"] > self.buy_ema_diff.value) &
            (dataframe["close"] < dataframe["sma_5"] * self.buy_ema_low.value)
        )

        dataframe.loc[cond_high | cond_low, "enter_long"] = 1
        return dataframe

    # --------------------------------------------------
    # 매도 조건
    # --------------------------------------------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        if dataframe.empty:
            return dataframe

        sell_cond = (
            (dataframe["rsi"] > self.sell_rsi.value) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[sell_cond, "exit_long"] = 1
        return dataframe

    # --------------------------------------------------
    # 동적 손절매
    # --------------------------------------------------
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        hsl = self.stoploss
        if current_profit > 0.05:
            hsl = -0.01
        elif current_profit > 0.02:
            hsl = -0.02
        return hsl

    # --------------------------------------------------
    # 진입 확인 (선택)
    # --------------------------------------------------
    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        **kwargs,
    ) -> bool:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return False
        last = df.iloc[-1]

        # 1시간 RSI가 과열(>85)인 경우 진입 차단
        try:
            df1h, _ = self.dp.get_analyzed_dataframe(pair, self.informative_tf_1h)
            if df1h is not None and not df1h.empty:
                rsi_col = f"rsi_{self.informative_tf_1h}"
                if rsi_col in df1h.columns and df1h.iloc[-1][rsi_col] > 85:
                    return False
        except Exception as e:
            logger.warning(f"1시간 RSI 확인 중 오류 발생: {e}")

        # 최근 거래량이 평균의 50% 미만이면 패스
        try:
            if "volume" in df.columns:
                vol_mean = df["volume"].rolling(10).mean().iloc[-1]
                if not np.isnan(vol_mean) and last["volume"] < vol_mean * 0.5:
                    return False
        except Exception as e:
            logger.warning(f"거래량 확인 중 오류 발생: {e}")

        return True
