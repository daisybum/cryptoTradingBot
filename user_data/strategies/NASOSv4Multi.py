# NASOSv4 Strategy adapted for multi-coin backtesting (top 25 Binance pairs) 
# Timeframe: 5m default (supports 1m if configured), with 1h informative data
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from functools import reduce

# Freqtrade imports
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair
import freqtrade.vendor.qtpylib.indicators as qtpylib

class NASOSv4Multi(IStrategy):
    """
    NASOSv4 strategy adapted for multi-pair trading and backtesting.
    - Uses 5m timeframe by default (1m optional), with 1h informative timeframe for each pair.
    - Top 25 crypto pairs by market cap are considered.
    - Incorporates RSI, EMA, SMA, HMA, EWO indicators for buy/sell signals.
    - Trailing stop-loss enabled; no custom stoploss (for backtesting compatibility).
    """
    # Optimal timeframe for the strategy (can be overridden in config to 1m or others)
    timeframe = '5m'
    inf_1h = '1h'  # informative timeframe

    # Safety: process only new candles to avoid repeated processing on the same data
    process_only_new_candles = True
    startup_candle_count = 200  # ensure we have enough data for indicators (max period ~200)

    # Strategy parameters (with default values from NASOSv4)
    # Buy parameters (for dip entry)
    base_nb_candles_buy = IntParameter(5, 80, default=14, space='buy', optimize=True)
    low_offset = DecimalParameter(0.90, 0.99, default=0.975, space='buy', optimize=True)
    low_offset_2 = DecimalParameter(0.90, 0.99, default=0.955, space='buy', optimize=True)
    ewo_high = DecimalParameter(2.0, 12.0, default=2.327, space='buy', optimize=True)
    ewo_high_2 = DecimalParameter(-6.0, 12.0, default=-2.327, space='buy', optimize=True)
    ewo_low = DecimalParameter(-20.0, -8.0, default=-20.988, space='buy', optimize=True)
    rsi_buy = IntParameter(30, 70, default=69, space='buy', optimize=True)

    # Sell parameters (for exit conditions)
    base_nb_candles_sell = IntParameter(5, 80, default=24, space='sell', optimize=True)
    high_offset = DecimalParameter(0.95, 1.10, default=0.991, space='sell', optimize=True)
    high_offset_2 = DecimalParameter(0.99, 1.50, default=0.997, space='sell', optimize=True)

    # Trailing stop-loss (activated for backtesting as well)
    trailing_stop = True
    trailing_stop_positive = 0.005  # 0.5% trailing
    trailing_stop_positive_offset = 0.03  # start trailing when 3% profit reached
    trailing_only_offset_is_reached = True

    # Hard stoploss (static stop)
    stoploss = -0.15  # 15% stoploss as an absolute safety net

    # We will use sell signals (and not rely solely on ROI/stoploss)
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False  # allow ROI table to be overridden by buy signals
    # (No custom_stoploss defined, we rely on trailing_stop and static stoploss)

    # Optional order time in force (can use defaults: GTC for buy, IOC for sell)
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'ioc'
    }

    ### Multi-Pair Informative Timeframe Setup ###
    def informative_pairs(self):
        """
        Define informative pair/timeframe combinations to fetch.
        Returns 1h timeframe data for all top 25 trading pairs.
        """
        # List of top 25 crypto by market cap (USDT pairs on Binance)
        top25_pairs = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
            "DOGE/USDT", "SOL/USDT", "TRX/USDT", "DOT/USDT", "MATIC/USDT",
            "LTC/USDT", "SHIB/USDT", "AVAX/USDT", "UNI/USDT", "LINK/USDT",
            "ATOM/USDT", "XMR/USDT", "XLM/USDT", "BCH/USDT", "TON/USDT",
            "ETC/USDT", "APT/USDT", "QNT/USDT", "FIL/USDT", "NEAR/USDT"
        ]
        # Return all pairs with the 1h informative timeframe
        informative_pairs = [(pair, self.inf_1h) for pair in top25_pairs]
        return informative_pairs

    ### Indicator Calculation (with 1h data merge) ###
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate all indicators for the given timeframe dataframe.
        Merges 1h informative indicators for the same pair.
        """
        # Compute moving averages for all relevant lengths in range (to avoid re-computation during optimization)
        for val in self.base_nb_candles_buy.range:
            dataframe[f"ma_buy_{val}"] = ta.EMA(dataframe, timeperiod=val)
        for val in self.base_nb_candles_sell.range:
            dataframe[f"ma_sell_{val}"] = ta.EMA(dataframe, timeperiod=val)

        # Hull Moving Average and other fixed indicators on main timeframe
        dataframe['hma_50'] = qtpylib.hull_moving_average(dataframe['close'], window=50)
        dataframe['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['sma_9'] = ta.SMA(dataframe, timeperiod=9)

        # EWO indicator (difference between fast EMA and slow EMA as % of price)
        # using fast_ewo=50, slow_ewo=200 as defined in original strategy
        fast_ema = ta.EMA(dataframe, timeperiod=50)
        slow_ema = ta.EMA(dataframe, timeperiod=200)
        dataframe['EWO'] = (fast_ema - slow_ema) / dataframe['low'] * 100

        # RSI indicators
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)

        # Merge informative 1h data for this pair (if available)
        if self.dp:
            inf_df = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_1h)
            if not inf_df.empty:
                # Example: we could compute 1h volume average or trend indicators here if needed.
                inf_df['rsi_14'] = ta.RSI(inf_df, timeperiod=14)
                inf_df['avg_vol_24h'] = inf_df['volume'].rolling(window=24).mean()

                # Rename informative columns to avoid name collisions
                inf_df.rename(columns=lambda s: f"{s}_{self.inf_1h}", inplace=True)
                # Merge, forward-filling 1h values onto 5m rows
                dataframe = merge_informative_pair(dataframe, inf_df, self.timeframe, self.inf_1h, ffill=True)
                # After merge, we might have NaNs for initial candles; fill them if needed
                dataframe.fillna(method="ffill", inplace=True)

        return dataframe

    ### Buy Signal Conditions ###
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define the buy conditions for NASOSv4.
        Multiple conditions (ewo1, ewo2, ewolow) yield a 'buy' signal.
        """
        # No buy by default
        dataframe.loc[:, 'buy'] = 0

        # EWO1: Uptrend pullback buy
        dataframe.loc[
            (
                (dataframe['rsi_fast'] < 35) &  # short-term oversold
                (dataframe['close'] < dataframe[f"ma_buy_{self.base_nb_candles_buy.value}"] * self.low_offset.value) &
                (dataframe['EWO'] > self.ewo_high.value) &  # strong uptrend context
                (dataframe['rsi'] < self.rsi_buy.value) &   # not overbought on normal RSI
                (dataframe['volume'] > 0) &
                (dataframe['close'] < dataframe[f"ma_sell_{self.base_nb_candles_sell.value}"] * self.high_offset.value)
            ),
            ['buy', 'buy_tag']
        ] = (1, 'ewo1')

        # EWO2: Weak-trend deep oversold buy
        dataframe.loc[
            (
                (dataframe['rsi_fast'] < 35) &
                (dataframe['close'] < dataframe[f"ma_buy_{self.base_nb_candles_buy.value}"] * self.low_offset_2.value) &
                (dataframe['EWO'] > self.ewo_high_2.value) &  # weaker trend allowed (could be slightly negative EWO)
                (dataframe['rsi'] < self.rsi_buy.value) &
                (dataframe['volume'] > 0) &
                (dataframe['close'] < dataframe[f"ma_sell_{self.base_nb_candles_sell.value}"] * self.high_offset.value) &
                (dataframe['rsi'] < 25)  # require very low RSI for this deeper pullback
            ),
            ['buy', 'buy_tag']
        ] = (1, 'ewo2')

        # EWO Low: Downtrend extreme oversold buy
        dataframe.loc[
            (
                (dataframe['rsi_fast'] < 35) &
                (dataframe['close'] < dataframe[f"ma_buy_{self.base_nb_candles_buy.value}"] * self.low_offset.value) &
                (dataframe['EWO'] < self.ewo_low.value) &   # strong downtrend context
                (dataframe['volume'] > 0) &
                (dataframe['close'] < dataframe[f"ma_sell_{self.base_nb_candles_sell.value}"] * self.high_offset.value)
            ),
            ['buy', 'buy_tag']
        ] = (1, 'ewolow')

        return dataframe

    ### Sell Signal Conditions ###
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define the sell conditions for NASOSv4.
        Sells on either price spikes or trend weakness.
        """
        dataframe.loc[:, 'sell'] = 0  # default no sell

        # Condition 1: Price surge take-profit (price above SMA9 and high offset, RSI high)
        cond1 = (
            (dataframe['close'] > dataframe['sma_9']) &
            (dataframe['close'] > dataframe[f"ma_sell_{self.base_nb_candles_sell.value}"] * self.high_offset_2.value) &
            (dataframe['rsi'] > 50) &  # RSI indicates strength
            (dataframe['volume'] > 0) &
            (dataframe['rsi_fast'] > dataframe['rsi_slow'])  # short-term momentum still high
        )

        # Condition 2: Trend reversal exit (price dropped below HMA50 but still above longer EMA baseline)
        cond2 = (
            (dataframe['close'] < dataframe['hma_50']) &
            (dataframe['close'] > dataframe[f"ma_sell_{self.base_nb_candles_sell.value}"] * self.high_offset.value) &
            (dataframe['volume'] > 0) &
            (dataframe['rsi_fast'] > dataframe['rsi_slow'])
        )

        # Combine conditions
        dataframe.loc[cond1 | cond2, 'sell'] = 1

        return dataframe

    ### Sell Confirmation (optional) ###
    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float, rate: float, 
                            time_in_force: str, sell_reason: str, current_time) -> bool:
        """
        Optional confirmation for exit signals. 
        If the sell_reason is 'sell_signal', we can impose an additional check 
        to avoid premature selling during strong uptrends.
        """
        if sell_reason == 'sell_signal':
            # Get latest candle for this pair on main timeframe
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is None or dataframe.empty:
                return True  # no data, allow exit
            last_candle = dataframe.iloc[-1]
            # If we're in a very strong uptrend (HMA50 far above EMA100) and price is just slightly below EMA100,
            # then cancel the sell to give the trade more room (expecting a rebound).
            if (last_candle['hma_50'] * 1.149 > last_candle['ema_100']) and \
               (last_candle['close'] < last_candle['ema_100'] * 0.951):
                # HMA50 is significantly above EMA100 (strong uptrend) and price dipped below EMA100 by ~5%.
                # Likely just a pullback in a strong uptrend – do not exit yet.
                return False
        return True
