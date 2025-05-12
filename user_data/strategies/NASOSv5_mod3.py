"""
NASOSv5_mod3 전략 (NotAnotherSMAOffsetStrategy v5 mod3)

이 전략은 RSI_fast + SMA 오프셋 조건에서 매수하고, EWO, EMA, MA_offset으로 필터링합니다.
5분 타임프레임에서 작동하며, 15분 및 1시간 타임프레임을 정보용으로 사용합니다.
"""

import logging
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter
from freqtrade.strategy.interface import IStrategy
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes

logger = logging.getLogger(__name__)


class NASOSv5_mod3(IStrategy):
    """
    NASOSv5_mod3 전략 (NotAnotherSMAOffsetStrategy v5 mod3)
    
    이 전략은 다음 지표를 사용합니다:
    - RSI (빠른 기간)
    - SMA 오프셋
    - EWO (Elliott Wave Oscillator)
    - EMA
    - MA 오프셋
    """
    
    # 전략 정보
    INTERFACE_VERSION = 3
    
    # 최소 ROI 테이블
    minimal_roi = {
        "0": 0.10,  # 10% 이상 수익 시 즉시 매도
        "30": 0.05,  # 30분 후 5% 이상 수익 시 매도
        "60": 0.03,  # 60분 후 3% 이상 수익 시 매도
        "120": 0.01  # 120분 후 1% 이상 수익 시 매도
    }
    
    # 손절매 설정
    stoploss = -0.035  # -3.5% 손절매
    
    # 타임프레임 설정
    timeframe = '5m'
    informative_timeframe = '1h'
    
    # 거래 설정
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # 매매 시간 설정
    process_only_new_candles = True
    startup_candle_count = 200
    
    # 매개변수 설정
    buy_rsi_fast = IntParameter(10, 50, default=11, space="buy")
    buy_rsi = IntParameter(10, 50, default=35, space="buy")
    buy_sma_offset = DecimalParameter(0.93, 0.99, default=0.965, space="buy")
    buy_ewo_high = DecimalParameter(2.0, 12.0, default=4.0, space="buy")
    buy_ewo_low = DecimalParameter(-12.0, -2.0, default=-6.0, space="buy")
    buy_ema_diff = DecimalParameter(0.022, 0.027, default=0.025, space="buy")
    buy_ema_high = DecimalParameter(0.9, 1.2, default=0.95, space="buy")
    buy_ema_low = DecimalParameter(0.8, 1.0, default=0.85, space="buy")
    
    # 매도 매개변수
    sell_rsi = IntParameter(50, 100, default=75, space="sell")
    
    def informative_pairs(self) -> List[Tuple[str, str]]:
        """
        정보용 타임프레임 페어 정의
        """
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        지표 계산
        """
        # 기본 타임프레임 지표
        dataframe['rsi'] = self.calculate_rsi(dataframe, 14)
        dataframe['rsi_fast'] = self.calculate_rsi(dataframe, self.buy_rsi_fast.value)
        dataframe['sma_9'] = self.calculate_sma(dataframe, 9)
        dataframe['sma_5'] = self.calculate_sma(dataframe, 5)
        dataframe['sma_21'] = self.calculate_sma(dataframe, 21)
        dataframe['sma_200'] = self.calculate_sma(dataframe, 200)
        dataframe['sma_200_1h'] = self.calculate_sma(dataframe, 200)
        dataframe['ema_8'] = self.calculate_ema(dataframe, 8)
        dataframe['ema_14'] = self.calculate_ema(dataframe, 14)
        dataframe['ema_26'] = self.calculate_ema(dataframe, 26)
        dataframe['ema_50'] = self.calculate_ema(dataframe, 50)
        dataframe['ema_200'] = self.calculate_ema(dataframe, 200)
        
        # EWO (Elliott Wave Oscillator) 계산
        dataframe['ewo'] = self.calculate_ewo(dataframe)
        
        # MA 오프셋 계산
        dataframe['ma_offset_buy'] = (dataframe['sma_9'] * self.buy_sma_offset.value)
        
        # EMA 차이 계산
        dataframe['ema_diff'] = (dataframe['ema_26'] - dataframe['ema_14']) / dataframe['ema_14']
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        매수 신호 생성
        """
        conditions = []
        
        # 기본 조건
        basic_conditions = (
            (dataframe['rsi_fast'] < self.buy_rsi.value) &
            (dataframe['close'] < dataframe['ma_offset_buy']) &
            (dataframe['ema_50'] > dataframe['ema_200']) &  # 장기 상승 추세
            (dataframe['volume'] > 0)
        )
        
        # EWO 조건 (상승 추세)
        ewo_high_cond = (
            basic_conditions &
            (dataframe['ewo'] > self.buy_ewo_high.value) &
            (dataframe['rsi'] < 35) &
            (dataframe['close'] < (dataframe['sma_5'] * self.buy_ema_high.value))
        )
        conditions.append(ewo_high_cond)
        
        # EWO 조건 (하락 추세)
        ewo_low_cond = (
            basic_conditions &
            (dataframe['ewo'] < self.buy_ewo_low.value) &
            (dataframe['ema_diff'] > self.buy_ema_diff.value) &
            (dataframe['close'] < (dataframe['sma_5'] * self.buy_ema_low.value))
        )
        conditions.append(ewo_low_cond)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'enter_long'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        매도 신호 생성
        """
        conditions = []
        
        # 기본 매도 조건
        conditions.append(
            (dataframe['rsi'] > self.sell_rsi.value) &
            (dataframe['volume'] > 0)
        )
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'exit_long'
            ] = 1
        
        return dataframe
    
    # 유틸리티 함수
    def calculate_rsi(self, dataframe: DataFrame, period: int) -> Series:
        """RSI 계산"""
        return ta.RSI(dataframe, timeperiod=period)
    
    def calculate_sma(self, dataframe: DataFrame, period: int) -> Series:
        """SMA 계산"""
        return ta.SMA(dataframe, timeperiod=period)
    
    def calculate_ema(self, dataframe: DataFrame, period: int) -> Series:
        """EMA 계산"""
        return ta.EMA(dataframe, timeperiod=period)
    
    def calculate_ewo(self, dataframe: DataFrame) -> Series:
        """Elliott Wave Oscillator 계산"""
        ema5 = ta.EMA(dataframe, timeperiod=5)
        ema35 = ta.EMA(dataframe, timeperiod=35)
        return (ema5 - ema35) / dataframe['close'] * 100
