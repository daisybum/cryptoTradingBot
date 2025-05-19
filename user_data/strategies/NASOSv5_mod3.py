# --- Rewritten NASOSv5_mod3 Strategy ---
from freqtrade.strategy import IStrategy, stoploss_from_open, merge_informative_pair, DecimalParameter, IntParameter, CategoricalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import logging

logger = logging.getLogger(__name__)

class NASOSv5_mod3(IStrategy):
    INTERFACE_VERSION = 3

    # Minimal ROI: practically disable ROI-based exit (use strategy's sell logic)
    minimal_roi = {"0": 10}
    stoploss = -0.15  # 15% stoploss
    timeframe = '5m'
    process_only_new_candles = False  # evaluate on every tick for timely checks
    use_custom_stoploss = True

    # Buy hyperspace parameters (for hyperopt reference)
    buy_params = {
        "base_nb_candles_buy": 20,
        "ewo_high": 4.299,
        "ewo_high_2": 8.492,
        "ewo_low": -8.476,
        "low_offset": 0.984,
        "low_offset_2": 0.901,
        "lookback_candles": 7,
        "profit_threshold": 1.036,
        "rsi_buy": 44,
        "rsi_fast_buy": 30
    }

    # Sell hyperspace parameters (for hyperopt reference)
    sell_params = {
        "high_offset": 1.149,
        "high_offset_2": 1.064,
        "pHSL": -0.08,
        "pPF_1": 0.02,
        "pPF_2": 0.06,
        "pSL_1": 0.02,
        "pSL_2": 0.06
    }

    # Buy signal parameters (with ranges for optimization)
    base_nb_candles_buy = IntParameter(5, 80, default=buy_params['base_nb_candles_buy'], space='buy', optimize=True)
    ewo_high = DecimalParameter(-20.0, 20.0, default=buy_params['ewo_high'], space='buy', optimize=True)
    ewo_high_2 = DecimalParameter(-20.0, 20.0, default=buy_params['ewo_high_2'], space='buy', optimize=True)
    ewo_low = DecimalParameter(-20.0, 20.0, default=buy_params['ewo_low'], space='buy', optimize=True)
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
    # Trailing stoploss profit points (for custom_stoploss)
    pHSL = DecimalParameter(-0.20, -0.04, default=sell_params['pHSL'], space='sell', optimize=True, load=True)
    pPF_1 = DecimalParameter(0.01, 0.05, default=sell_params['pPF_1'], space='sell', optimize=True)
    pPF_2 = DecimalParameter(0.04, 0.20, default=sell_params['pPF_2'], space='sell', optimize=True)
    pSL_1 = DecimalParameter(0.01, 0.05, default=sell_params['pSL_1'], space='sell', optimize=True)
    pSL_2 = DecimalParameter(0.04, 0.20, default=sell_params['pSL_2'], space='sell', optimize=True)

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

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI indicators
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi'] = dataframe['rsi_slow']

        # Baseline moving average for buy (length = base_nb_candles_buy)
        length = int(self.base_nb_candles_buy.value)
        ma_col = f"ma_{length}"
        if self.buy_ma_type.value == 'SMA':
            dataframe[ma_col] = ta.SMA(dataframe, timeperiod=length)
        else:
            dataframe[ma_col] = ta.EMA(dataframe, timeperiod=length)
        # Ensure baseline MA shows in plot
        self.plot_config['main_plot'][ma_col] = {}

        # Additional MAs for sell logic
        dataframe['sma_9'] = ta.SMA(dataframe, timeperiod=9)
        dataframe['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        # Hull Moving Average 50 (via WMA calculation)
        half_length = 25
        sqrt_length = int(np.sqrt(50))
        wma_half = ta.WMA(dataframe, timeperiod=half_length)
        wma_full = ta.WMA(dataframe, timeperiod=50)
        # HMA50 = WMA(2*WMA(25) - WMA(50), sqrt(50))
        dataframe['hma_50'] = ta.WMA(DataFrame({'close': 2 * wma_half - wma_full}), timeperiod=sqrt_length)

        # Elliott Wave Oscillator (EWO)
        ema_short = ta.EMA(dataframe, timeperiod=5)
        ema_long = ta.EMA(dataframe, timeperiod=35)
        dataframe['EWO'] = (ema_short - ema_long) / dataframe['close'] * 100

        # Anti-pump indicators
        dataframe['ispumping'] = (dataframe['close'] > dataframe['close'].shift(1) * 1.08).astype('int')
        dataframe['islongpumping'] = (dataframe['close'] > dataframe['close'].shift(12) * 1.30).astype('int')
        # recentispumping = True if any pump in last ~25 hours
        recent_window = 300  # 300 * 5m = 1500 minutes = 25 hours
        dataframe['recentispumping'] = (
            (dataframe['ispumping'].rolling(recent_window).max() > 0) |
            (dataframe['islongpumping'].rolling(recent_window).max() > 0)
        ).astype('int')

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['buy'] = 0
        dataframe['buy_tag'] = None
        base_length = int(self.base_nb_candles_buy.value)
        base_ma_col = f"ma_{base_length}"

        # Buy condition for normal/neutral market
        cond_bull = (
            (dataframe['close'] < dataframe[base_ma_col] * self.low_offset.value) &  # price below baseline * offset
            (dataframe['rsi'] < self.rsi_buy.value) &  # RSI below threshold (e.g. 44)
            (dataframe['rsi_fast'] < self.rsi_fast_buy.value) &  # fast RSI below its threshold
            (dataframe['EWO'] > self.ewo_low.value) &    # EWO above bear threshold
            (dataframe['EWO'] < self.ewo_high_2.value) & # EWO below upper bound (not during extreme pump)
            (dataframe['volume'] > 0) &
            (dataframe['recentispumping'] == 0)         # no recent pump activity
        )

        # Buy condition for bearish market (allow deeper dip buy)
        cond_bear = (
            (dataframe['close'] < dataframe[base_ma_col] * self.low_offset_2.value) &  # price much below baseline
            (dataframe['rsi'] < self.rsi_buy.value) &
            (dataframe['rsi_fast'] < self.rsi_fast_buy.value) &
            (dataframe['EWO'] < self.ewo_low.value) &   # EWO below bearish threshold (strong downtrend)
            (dataframe['volume'] > 0) &
            (dataframe['recentispumping'] == 0)
        )

        dataframe.loc[cond_bear, ['buy', 'buy_tag']] = (1, 'ewo_bear')
        dataframe.loc[cond_bull, ['buy', 'buy_tag']] = (1, 'ewo_bull')
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['sell'] = 0

        base_length = int(self.base_nb_candles_buy.value)
        base_ma_col = f"ma_{base_length}"

        # Sell conditions (any triggers a sell)
        sell_cond1 = dataframe['close'] > dataframe['sma_9']  # price above SMA9
        sell_cond2_bull = (dataframe['close'] > dataframe[base_ma_col] * self.high_offset.value) & (dataframe['EWO'] >= self.ewo_low.value)
        sell_cond2_bear = (dataframe['close'] > dataframe[base_ma_col] * self.high_offset_2.value) & (dataframe['EWO'] < self.ewo_low.value)
        sell_cond3 = dataframe['rsi'] > 50  # RSI above 50
        sell_cond4 = dataframe['rsi_fast'] > dataframe['rsi_slow']  # RSI fast > RSI slow (upward RSI cross)
        sell_cond5 = (dataframe['close'] < dataframe['hma_50']) & (dataframe['rsi_fast'] > dataframe['rsi_slow'])  # price fell below HMA50 while RSI momentum up

        if_sell = sell_cond1 | sell_cond2_bull | sell_cond2_bear | sell_cond3 | sell_cond4 | sell_cond5
        dataframe.loc[if_sell, 'sell'] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs) -> float:
        """
        Custom trailing stoploss to ride profits:
        Increases stoploss as profit reaches defined thresholds.
        """
        # If profit below first threshold, keep default stoploss
        if current_profit < self.pPF_1.value:
            return 1  # 100% (no immediate stop, use global stoploss)
        # Between first and second profit threshold: interpolate stoploss between SL_1 and SL_2
        if current_profit < self.pPF_2.value:
            profit_range = self.pPF_2.value - self.pPF_1.value
            if profit_range > 0:
                sl_profit = self.pSL_1.value + ((current_profit - self.pPF_1.value) * (self.pSL_2.value - self.pSL_1.value) / profit_range)
            else:
                sl_profit = self.pSL_1.value
        else:
            # Above second threshold: use final hard stoploss value (pHSL)
            sl_profit = self.pHSL.value
        # Convert desired profit-based stoploss to actual stoploss relative to current price
        return stoploss_from_open(sl_profit, current_profit)
        
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag: str = None, **kwargs) -> bool:
        """
        슬리피지 보호 및 진입 확인을 위한 메서드
        
        :param pair: 거래 쌍
        :param order_type: 주문 유형
        :param amount: 거래량
        :param rate: 진입 가격
        :param time_in_force: 주문 유효 시간
        :param current_time: 현재 시간
        :param entry_tag: 진입 태그
        :return: 거래 진입 여부 (True/False)
        """
        max_slippage = 0.03  # 3% 허용 슬리피지
        max_retries = 3

        # 참조 가격 (마지막 캔들 종가)
        df = self.dp.get_pair_dataframe(pair, self.timeframe)
        last_close = df['close'].iloc[-1] if len(df) > 0 else rate
        current_rate = rate if rate else last_close

        if current_rate > last_close * (1 + max_slippage):
            # 가격이 허용 슬리피지를 초과함
            retries = self.entry_retries.get(pair, 0) + 1
            self.entry_retries[pair] = retries
            if retries >= max_retries:
                logger.info(f"슬리피지 보호: {pair}의 가격이 신호보다 {max_slippage*100:.1f}% 이상 높습니다. {retries}회 재시도 후 거래를 취소합니다.")
                self.entry_retries[pair] = 0  # 카운터 초기화
                return False  # 진입 취소
            else:
                logger.info(f"슬리피지 보호: {pair} 진입 가격이 너무 높습니다. 다음 캔들에서 {retries}/{max_retries} 재시도합니다.")
                return False  # 다음 캔들로 진입 연기
        else:
            # 가격이 허용 가능한 슬리피지 범위 내에 있음, 진입 허용
            if pair in self.entry_retries:
                self.entry_retries[pair] = 0  # 성공 시 재시도 카운터 초기화
            return True
        
    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, current_time, **kwargs) -> bool:
        """
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
        # 진입 재시도 카운터 초기화
        if pair in self.entry_retries:
            self.entry_retries[pair] = 0
            
        return True
