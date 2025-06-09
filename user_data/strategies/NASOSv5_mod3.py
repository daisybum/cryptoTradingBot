# --- Rewritten NASOSv5_mod3 Strategy ---
from freqtrade.strategy import IStrategy, stoploss_from_open, merge_informative_pair, DecimalParameter, IntParameter, CategoricalParameter
import numpy as np
import pandas as pd
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pathlib import Path
import sys
from typing import Optional, Dict, Any, List
import logging

# Elliott Wave Oscillator 함수 정의
def EWO(dataframe, sma1_length=5, sma2_length=35):
    df = dataframe.copy()
    sma1 = ta.SMA(df, timeperiod=sma1_length)
    sma2 = ta.SMA(df, timeperiod=sma2_length)
    smadif = (sma1 - sma2) / df['close'] * 100
    return smadif

# 리스크 관리 시스템 임포트
sys.path.append(str(Path(__file__).parent.absolute()))
try:
    from risk_manager import RiskManager
    RISK_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"리스크 관리 모듈 로드 실패: {e}")
    RISK_MANAGER_AVAILABLE = False
except Exception as e:
    logger.warning(f"리스크 관리 모듈 로드 중 오류 발생: {e}")
    RISK_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

class NASOSv5_mod3(IStrategy):
    INTERFACE_VERSION = 3

    # Minimal ROI: practically disable ROI-based exit (use strategy's sell logic)
    minimal_roi = {
        "0": 0.201,
        "38": 0.057,
        "73": 0.028,
    }
    stoploss = -0.05  # 하이퍼옵트 결과에 따라 수정
    timeframe = '5m'
    process_only_new_candles = True  # evaluate on every tick for timely checks
    use_custom_stoploss = True

    # Buy hyperspace parameters (for hyperopt reference)
    buy_params = {
        "base_nb_candles_buy": 29,
        "buy_ma_type": "EMA",
        "ewo_high": 3.847,
        "ewo_high_2": 8.101,
        "ewo_low": -1.623,
        "lookback_candles": 7,
        "low_offset": 1.117,
        "low_offset_2": 0.768,
        "profit_threshold": 0.912,
        "rsi_buy": 44,
        "rsi_fast_buy": 30,
    }

    # Sell hyperspace parameters (for hyperopt reference)
    sell_params = {
        "high_offset": 1.172,
        "high_offset_2": 1.065,
        "pHSL": -0.035,
        "pPF_1": 0.03,
        "pPF_2": 0.083,
        "pSL_1": 0.014,
        "pSL_2": 0.085,
    }

    # Buy signal parameters (with ranges for optimization)
    base_nb_candles_buy = IntParameter(5, 80, default=buy_params['base_nb_candles_buy'], space='buy', optimize=True)
    # 매수 조건 완화를 위해 ewo_high 범위를 2.0~4.0으로 제한
    ewo_high = DecimalParameter(2.0, 4.0, default=buy_params['ewo_high'], space='buy', optimize=True)
    ewo_high_2 = DecimalParameter(4.0, 10.0, default=buy_params['ewo_high_2'], space='buy', optimize=True)
    # 매수 조건 완화를 위해 ewo_low 범위를 -2.0~0.0으로 제한
    ewo_low = DecimalParameter(-2.0, 0.0, default=buy_params['ewo_low'], space='buy', optimize=True)
    low_offset = DecimalParameter(0.5, 1.5, default=buy_params['low_offset'], space='buy', optimize=True)
    low_offset_2 = DecimalParameter(0.5, 1.5, default=buy_params['low_offset_2'], space='buy', optimize=True)
    lookback_candles = IntParameter(1, 30, default=buy_params['lookback_candles'], space='buy', optimize=False)
    profit_threshold = DecimalParameter(0.9, 1.1, default=buy_params['profit_threshold'], space='buy', optimize=True)
    rsi_buy = IntParameter(10, 50, default=buy_params['rsi_buy'], space='buy', optimize=False)
    rsi_fast_buy = IntParameter(5, 50, default=buy_params['rsi_fast_buy'], space='buy', optimize=False)
    # Optionally choose SMA or EMA for baseline MA (default EMA)
    buy_ma_type = CategoricalParameter(['SMA', 'EMA'], default='EMA', space='buy', optimize=False)

    # Sell signal / trailing parameters
    high_offset = DecimalParameter(1.0, 1.5, default=sell_params['high_offset'], space='sell', optimize=True)
    high_offset_2 = DecimalParameter(1.0, 1.5, default=sell_params['high_offset_2'], space='sell', optimize=True)
    # Trailing stoploss profit points (for custom_stoploss) - more aggressive settings
    pHSL = DecimalParameter(-0.10, -0.03, default=-0.05, space='sell', optimize=True, load=True)  # Hard stoploss level
    pPF_1 = DecimalParameter(0.005, 0.03, default=0.01, space='sell', optimize=True)  # Lower profit threshold
    pPF_2 = DecimalParameter(0.03, 0.15, default=0.05, space='sell', optimize=True)  # Higher profit threshold
    pSL_1 = DecimalParameter(0.005, 0.03, default=0.01, space='sell', optimize=True)  # Stoploss at first profit threshold
    pSL_2 = DecimalParameter(0.03, 0.15, default=0.04, space='sell', optimize=True)  # Stoploss at second profit threshold

    # Optional plotting of indicators
    plot_config = {
        'main_plot': {},
        'subplots': {
            "RSI": {
                'rsi_fast': {'color': 'red'},
                'rsi_slow': {'color': 'green'},
            },
            "EWO": {
                'EWO': {'color': 'orange'}
            }
        }
    }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Track entry retries for slippage protection
        self.entry_retries = {}
        
        # 리스크 관리 시스템 초기화
        self.risk_manager = None
        if RISK_MANAGER_AVAILABLE:
            try:
                self.risk_manager = RiskManager(
                    max_drawdown_allowed=0.08,  # 최대 8% 드로다운 허용 (더 엄격한 설정)
                    risk_free_rate=0.01,        # 1% 무위험 수익률
                    use_redis=True,             # Redis 사용
                    max_risk_per_trade=0.02,    # 거래당 최대 위험 2%
                    max_open_trades=5           # 최대 동시 거래 수 5개
                )
                logger.info("리스크 관리 시스템이 성공적으로 초기화되었습니다.")
            except Exception as e:
                logger.error(f"리스크 관리 시스템 초기화 중 오류 발생: {e}")
                self.risk_manager = None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI 지표
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)
        
        # 이동평균 지표
        dataframe['sma_9'] = ta.SMA(dataframe, timeperiod=9)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # EWO - Elliott Wave Oscillator
        dataframe['ewo'] = EWO(dataframe, 50, 200)
        
        # 추가 지표
        dataframe['close_prev'] = dataframe['close'].shift(1)
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=30).mean()
        
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['buy'] = 0
        dataframe['buy_tag'] = None
        
        # 최적화된 매수 조건
        # 1. 볼륨이 매우 높고 RSI가 매우 낮을 때 (과매도 상태에서 강한 반등 기대)
        # 2. 가격이 전날보다 3% 이상 하락했을 때 (급락 후 반등 기대)
        strong_dip_condition = (
            (dataframe['volume'] > dataframe['volume_mean'] * 1.5) &  # 볼륨이 평균의 150% 이상
            (dataframe['rsi'] < 20) &  # 매우 낮은 RSI
            (dataframe['close'] < dataframe['close_prev'] * 0.97)  # 3% 이상 하락
        )
        
        # 추가 매수 조건: 중간 강도 딱 + 기술적 지표 추가
        medium_dip_condition = (
            (dataframe['volume'] > dataframe['volume_mean']) &  # 볼륨이 평균 이상
            (dataframe['rsi'] < 30) &  # 낮은 RSI
            (dataframe['rsi_fast'] < dataframe['rsi_slow']) &  # RSI 하락 추세
            (dataframe['close'] < dataframe['ema_50']) &  # 가격이 EMA-50 아래
            (dataframe['close'] < dataframe['close_prev'] * 0.99)  # 1% 이상 하락
        )
        
        # 추가 매수 조건: 기술적 반전 신호
        reversal_condition = (
            (dataframe['rsi'] > dataframe['rsi'].shift(1)) &  # RSI 상승 시작
            (dataframe['rsi'] < 35) &  # 여전히 낮은 RSI
            (dataframe['close'] > dataframe['close_prev']) &  # 가격 상승 시작
            (dataframe['close'] < dataframe['ema_50'] * 0.95) &  # EMA-50보다 아직 많이 낮음
            (dataframe['volume'] > dataframe['volume_mean'] * 0.8)  # 적절한 볼륨
        )
        
        # 최적화된 매수 조건 적용
        dataframe.loc[strong_dip_condition, 'buy'] = 1
        dataframe.loc[strong_dip_condition, 'buy_tag'] = 'strong_dip'
        
        dataframe.loc[medium_dip_condition, 'buy'] = 1
        dataframe.loc[medium_dip_condition, 'buy_tag'] = 'medium_dip'
        
        dataframe.loc[reversal_condition, 'buy'] = 1
        dataframe.loc[reversal_condition, 'buy_tag'] = 'reversal'
        
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['sell'] = 0

        # 최적화된 매도 조건
        # 1. RSI가 매우 높을 때 (과매수 상태)
        overbought_condition = dataframe['rsi'] > 80
        
        # 2. 가격이 EMA-50 위에 있고 RSI가 높을 때 (상승 추세에서 고점 근처)
        uptrend_peak_condition = (dataframe['close'] > dataframe['ema_50'] * 1.05) & (dataframe['rsi'] > 70)
        
        # 3. 가격이 전날보다 크게 상승했을 때 (급등 후 이익 실현)
        quick_rise_condition = dataframe['close'] > dataframe['close_prev'] * 1.04
        
        # 4. RSI 디버전스 (가격은 상승하나 RSI는 하락 - 약세 신호)
        rsi_divergence = (dataframe['close'] > dataframe['close'].shift(1)) & \
                         (dataframe['rsi'] < dataframe['rsi'].shift(1)) & \
                         (dataframe['rsi'] > 70) & \
                         (dataframe['close'] > dataframe['ema_50'])
        
        # 5. 이동평균 크로스오버 (하락 신호)
        ema_crossover_condition = (dataframe['ema_50'].shift(1) > dataframe['ema_200'].shift(1)) & \
                                  (dataframe['ema_50'] < dataframe['ema_200']) & \
                                  (dataframe['close'] < dataframe['ema_200'])
        
        optimized_sell_condition = overbought_condition | uptrend_peak_condition | quick_rise_condition | rsi_divergence | ema_crossover_condition
        
        # 최적화된 매도 조건 적용
        dataframe.loc[optimized_sell_condition, 'sell'] = 1
        
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs) -> float:
        """
        Custom stoploss logic, returning the new distance relative to current_rate (as ratio).
        For example returning -0.05 would create a stoploss 5% below current_rate.
        """
        # 수익에 따른 동적 트레일링 스탑로스 설정
        # 수익이 증가할수록 더 적극적으로 이익을 보호
        
        # 거래 시간에 따른 스탑로스 조정
        # 거래 시간이 짧을수록 어떠한 수익이라도 지켜내기 위해 여유를 더 준다
        hours_open = (current_time - trade.open_date_utc).total_seconds() / 3600
        
        # 거래 시간이 2시간 미만이면 스탑로스를 더 느슬하게 설정
        time_factor = 1.0
        if hours_open < 2:
            time_factor = 0.5  # 스탑로스를 더 느슬하게 (50% 수준)
        elif hours_open < 6:
            time_factor = 0.7  # 스탑로스를 약간 느슬하게 (70% 수준)
        
        # 수익에 따른 스탑로스 조정
        if current_profit > 0.15:  # 15% 이상 수익
            return max(current_profit * -0.5, -0.02)  # 수익의 50%를 보호, 최소 2% 이상
        elif current_profit > 0.1:  # 10% 이상 수익
            return max(current_profit * -0.4, -0.03) * time_factor  # 수익의 40%를 보호, 시간 고려
        elif current_profit > 0.05:  # 5% 이상 수익
            return max(current_profit * -0.3, -0.04) * time_factor  # 수익의 30%를 보호, 시간 고려
        elif current_profit > 0.02:  # 2% 이상 수익
            return -0.05 * time_factor  # 5% 스탑로스, 시간 고려
        
        # 손실 상태에서는 기본 스탑로스 유지
        return -0.05  # 5% 스탑로스
        
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time, entry_tag: Optional[str],
                           side: str, **kwargs) -> bool:
        """
        Entry confirmation logic with risk management integration.
        """
        # 리스크 관리 시스템 활성화
        if self.risk_manager is not None:
            # 글로벌 드로다운 확인
            current_drawdown = self.risk_manager.get_current_drawdown()
            if current_drawdown > 0.05:  # 5% 이상 드로다운 발생 시 거래 제한
                if entry_tag != 'strong_dip':  # strong_dip 신호만 허용 (매우 강한 신호일 때만 거래)
                    logger.info(f"{pair}: 드로다운 {current_drawdown:.2%}로 인해 거래 거부 (strong_dip 아님)")
                    return False
            
            # 특정 페어에 대한 거래 허용 여부 확인
            if not self.risk_manager.check_trade_allowed(pair):
                logger.info(f"{pair}: 리스크 관리 시스템에 의해 거래 거부")
                return False
        
        # 기본적으로 거래 허용
        return True

    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, current_time, **kwargs) -> bool:
        """
        Exit confirmation logic - always allow exits for testing purposes.
        
        거래 종료 확인을 위한 메서드
        
        :param pair: 거래 쌍
        :param trade: 거래 객체
        :param order_type: 주문 유형
        :param amount: 거래량
        :param rate: 종료 가격
        :param time_in_force: 주문 유효 시간
        :param exit_reason: 종료 이유
        :param current_time: 현재 시간
        :return: 거래 종료 여부 (True/False)
        """
        # 항상 거래 종료 허용
        return True
