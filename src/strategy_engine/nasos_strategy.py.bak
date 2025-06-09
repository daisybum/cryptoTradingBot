"""
NASOSv5_mod3 strategy implementation for the strategy engine.
This module provides the complete implementation of the NASOSv5_mod3 strategy.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta

from src.strategy_engine.indicators import (
    calculate_ema, calculate_sma, calculate_rsi, calculate_ewo,
    calculate_stoch_rsi, calculate_bollinger_bands, calculate_macd,
    calculate_wma, calculate_hma
)

logger = logging.getLogger(__name__)


class NASOSStrategy:
    """
    NASOSv5_mod3 strategy implementation.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the NASOS strategy.
        
        :param config: Configuration dictionary
        """
        self.config = config or {}
        self.entry_retries = {}
        
        # Default parameters (can be overridden by config)
        self.params = {
            # Buy parameters
            "base_nb_candles_buy": 20,
            "ewo_high": 4.299,
            "ewo_high_2": 8.492,
            "ewo_low": -8.476,
            "low_offset": 0.984,
            "low_offset_2": 0.901,
            "lookback_candles": 7,
            "profit_threshold": 1.036,
            "rsi_buy": 44,
            "rsi_fast_buy": 30,
            "buy_ma_type": "EMA",
            
            # Sell parameters
            "high_offset": 1.149,
            "high_offset_2": 1.064,
            "pHSL": -0.08,
            "pPF_1": 0.02,
            "pPF_2": 0.06,
            "pSL_1": 0.02,
            "pSL_2": 0.06,
            
            # Slippage protection
            "max_slippage": 0.03,
            "max_retries": 3
        }
        
        # Override default parameters with config values if provided
        if config and 'strategy_parameters' in config:
            for key, value in config['strategy_parameters'].items():
                if key in self.params:
                    self.params[key] = value
    
    def prepare_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare dataframe with indicators for the NASOS strategy.
        
        :param dataframe: OHLCV dataframe
        :return: Dataframe with added indicators
        """
        if dataframe.empty:
            return dataframe
        
        # Create a copy to avoid modifying the original
        df = dataframe.copy()
        
        # RSI indicators
        df['rsi_fast'] = calculate_rsi(df, 4)
        df['rsi_slow'] = calculate_rsi(df, 14)
        df['rsi'] = df['rsi_slow']
        
        # Baseline moving average for buy
        base_length = self.params["base_nb_candles_buy"]
        ma_col = f"ma_{base_length}"
        if self.params["buy_ma_type"] == 'SMA':
            df[ma_col] = calculate_sma(df, base_length)
        else:
            df[ma_col] = calculate_ema(df, base_length)
        
        # Additional MAs for sell logic
        df['sma_9'] = calculate_sma(df, 9)
        df['ema_100'] = calculate_ema(df, 100)
        
        # Hull Moving Average 50
        df['hma_50'] = calculate_hma(df, 50)
        
        # Elliott Wave Oscillator (EWO)
        df['ema_short'] = calculate_ema(df, 5)
        df['ema_long'] = calculate_ema(df, 35)
        df['EWO'] = (df['ema_short'] - df['ema_long']) / df['close'] * 100
        
        # Anti-pump indicators
        df['ispumping'] = (df['close'] > df['close'].shift(1) * 1.08).astype('int')
        df['islongpumping'] = (df['close'] > df['close'].shift(12) * 1.30).astype('int')
        
        # recentispumping = True if any pump in last ~25 hours
        recent_window = 300  # 300 * 5m = 1500 minutes = 25 hours
        df['recentispumping'] = (
            (df['ispumping'].rolling(recent_window).max() > 0) |
            (df['islongpumping'].rolling(recent_window).max() > 0)
        ).astype('int')
        
        return df
    
    def generate_buy_signals(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy signals based on the NASOS strategy.
        
        :param dataframe: Dataframe with indicators
        :return: Dataframe with buy signals
        """
        df = dataframe.copy()
        df['buy'] = 0
        df['buy_tag'] = None
        
        base_length = self.params["base_nb_candles_buy"]
        base_ma_col = f"ma_{base_length}"
        
        # Buy condition for normal/neutral market
        cond_bull = (
            (df['close'] < df[base_ma_col] * self.params["low_offset"]) &  # price below baseline * offset
            (df['rsi'] < self.params["rsi_buy"]) &  # RSI below threshold
            (df['rsi_fast'] < self.params["rsi_fast_buy"]) &  # fast RSI below its threshold
            (df['EWO'] > self.params["ewo_low"]) &    # EWO above bear threshold
            (df['EWO'] < self.params["ewo_high_2"]) & # EWO below upper bound (not during extreme pump)
            (df['volume'] > 0) &
            (df['recentispumping'] == 0)         # no recent pump activity
        )
        
        # Buy condition for bearish market (allow deeper dip buy)
        cond_bear = (
            (df['close'] < df[base_ma_col] * self.params["low_offset_2"]) &  # price much below baseline
            (df['rsi'] < self.params["rsi_buy"]) &
            (df['rsi_fast'] < self.params["rsi_fast_buy"]) &
            (df['EWO'] < self.params["ewo_low"]) &   # EWO below bearish threshold (strong downtrend)
            (df['volume'] > 0) &
            (df['recentispumping'] == 0)
        )
        
        df.loc[cond_bear, ['buy', 'buy_tag']] = (1, 'ewo_bear')
        df.loc[cond_bull, ['buy', 'buy_tag']] = (1, 'ewo_bull')
        
        return df
    
    def generate_sell_signals(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Generate sell signals based on the NASOS strategy.
        
        :param dataframe: Dataframe with indicators
        :return: Dataframe with sell signals
        """
        df = dataframe.copy()
        df['sell'] = 0
        
        base_length = self.params["base_nb_candles_buy"]
        base_ma_col = f"ma_{base_length}"
        
        # Sell conditions (any triggers a sell)
        sell_cond1 = df['close'] > df['sma_9']  # price above SMA9
        sell_cond2_bull = (df['close'] > df[base_ma_col] * self.params["high_offset"]) & (df['EWO'] >= self.params["ewo_low"])
        sell_cond2_bear = (df['close'] > df[base_ma_col] * self.params["high_offset_2"]) & (df['EWO'] < self.params["ewo_low"])
        sell_cond3 = df['rsi'] > 50  # RSI above 50
        sell_cond4 = df['rsi_fast'] > df['rsi_slow']  # RSI fast > RSI slow (upward RSI cross)
        sell_cond5 = (df['close'] < df['hma_50']) & (df['rsi_fast'] > df['rsi_slow'])  # price fell below HMA50 while RSI momentum up
        
        if_sell = sell_cond1 | sell_cond2_bull | sell_cond2_bear | sell_cond3 | sell_cond4 | sell_cond5
        df.loc[if_sell, 'sell'] = 1
        
        return df
    
    def calculate_custom_stoploss(self, current_profit: float) -> float:
        """
        Calculate custom stoploss based on current profit.
        
        :param current_profit: Current profit percentage
        :return: Stoploss percentage
        """
        # If profit below first threshold, keep default stoploss
        if current_profit < self.params["pPF_1"]:
            return 1  # 100% (no immediate stop, use global stoploss)
        
        # Between first and second profit threshold: interpolate stoploss between SL_1 and SL_2
        if current_profit < self.params["pPF_2"]:
            profit_range = self.params["pPF_2"] - self.params["pPF_1"]
            if profit_range > 0:
                sl_profit = self.params["pSL_1"] + ((current_profit - self.params["pPF_1"]) * 
                                                  (self.params["pSL_2"] - self.params["pSL_1"]) / profit_range)
            else:
                sl_profit = self.params["pSL_1"]
        else:
            # Above second threshold: use final hard stoploss value (pHSL)
            sl_profit = self.params["pHSL"]
        
        # Convert desired profit-based stoploss to actual stoploss relative to current price
        return self.stoploss_from_open(sl_profit, current_profit)
    
    def stoploss_from_open(self, stoploss: float, current_profit: float) -> float:
        """
        Calculate new stoploss relative to current price based on desired stoploss from open.
        
        :param stoploss: Desired stoploss percentage from open
        :param current_profit: Current profit percentage
        :return: New stoploss percentage
        """
        if stoploss >= 0:
            return stoploss
        
        # Calculate new stoploss relative to current price
        if current_profit > 0:
            return (stoploss + current_profit) / (1 + current_profit)
        else:
            return stoploss / (1 + current_profit)
    
    def check_slippage(self, symbol: str, current_price: float, signal_price: float) -> Tuple[bool, Optional[str]]:
        """
        Check if the current price has excessive slippage compared to the signal price.
        
        :param symbol: Trading symbol
        :param current_price: Current price
        :param signal_price: Price at signal generation
        :return: Tuple of (allow_trade, retry_timeframe)
        """
        max_slippage = self.params.get("max_slippage", 0.03)  # 3% allowable slippage by default
        max_retries = self.params.get("max_retries", 3)
        
        # For buy orders, check if current price is too high above signal price
        if current_price > signal_price * (1 + max_slippage):
            retries = self.entry_retries.get(symbol, 0) + 1
            self.entry_retries[symbol] = retries
            
            if retries >= max_retries:
                logger.info(f"Slippage guard: price for {symbol} > {max_slippage*100:.1f}% above signal. "
                           f"Aborting trade after {retries} retries.")
                self.entry_retries[symbol] = 0  # reset counter
                return False, None  # cancel entry
            else:
                logger.info(f"Slippage guard: {symbol} entry price too high, retry {retries}/{max_retries} next candle.")
                return False, '5m'  # postpone entry to next candle
        else:
            # Price is within acceptable slippage range, allow entry
            if symbol in self.entry_retries:
                self.entry_retries[symbol] = 0  # reset retry counter on success
            return True, None
    
    def analyze_multi_timeframe(self, dataframes: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple timeframes and generate signals.
        
        :param dataframes: Dictionary of dataframes for different timeframes
        :return: Dictionary with analysis results for each symbol
        """
        results = {}
        
        # Process 5m timeframe (main timeframe)
        if '5m' not in dataframes or dataframes['5m'].empty:
            logger.warning("Missing 5m timeframe data")
            return results
        
        df_5m = self.prepare_dataframe(dataframes['5m'])
        df_5m = self.generate_buy_signals(df_5m)
        df_5m = self.generate_sell_signals(df_5m)
        
        # Process higher timeframes if available
        df_15m = self.prepare_dataframe(dataframes.get('15m', pd.DataFrame())) if '15m' in dataframes else pd.DataFrame()
        df_1h = self.prepare_dataframe(dataframes.get('1h', pd.DataFrame())) if '1h' in dataframes else pd.DataFrame()
        
        # Generate signals for each symbol
        for symbol in df_5m['symbol'].unique():
            symbol_5m = df_5m[df_5m['symbol'] == symbol]
            if symbol_5m.empty:
                continue
            
            # Get latest candle
            latest_5m = symbol_5m.iloc[-1]
            
            # Initialize result for this symbol
            results[symbol] = {
                'buy': bool(latest_5m['buy']),
                'sell': bool(latest_5m['sell']),
                'buy_tag': latest_5m['buy_tag'] if 'buy_tag' in latest_5m and latest_5m['buy_tag'] else None,
                'buy_confidence': 0.0,
                'sell_confidence': 0.0
            }
            
            # Set base confidence based on 5m signals
            if results[symbol]['buy']:
                results[symbol]['buy_confidence'] = 0.6
            if results[symbol]['sell']:
                results[symbol]['sell_confidence'] = 0.6
            
            # Enhance confidence with higher timeframe analysis if available
            if not df_15m.empty and not df_1h.empty:
                symbol_15m = df_15m[df_15m['symbol'] == symbol]
                symbol_1h = df_1h[df_1h['symbol'] == symbol]
                
                if not symbol_15m.empty and not symbol_1h.empty:
                    latest_15m = symbol_15m.iloc[-1]
                    latest_1h = symbol_1h.iloc[-1]
                    
                    # Check trend alignment across timeframes
                    bullish_alignment = (
                        latest_5m['close'] > latest_5m['ema_100'] and
                        latest_15m['close'] > latest_15m['ema_100'] and
                        latest_1h['close'] > latest_1h['ema_100']
                    )
                    
                    bearish_alignment = (
                        latest_5m['close'] < latest_5m['ema_100'] and
                        latest_15m['close'] < latest_15m['ema_100'] and
                        latest_1h['close'] < latest_1h['ema_100']
                    )
                    
                    # Adjust confidence based on alignment
                    if results[symbol]['buy'] and bullish_alignment:
                        results[symbol]['buy_confidence'] += 0.2
                    
                    if results[symbol]['sell'] and bearish_alignment:
                        results[symbol]['sell_confidence'] += 0.2
        
        return results
    
    def get_plot_config(self) -> Dict:
        """
        Get plotting configuration for the strategy.
        
        :return: Plot configuration dictionary
        """
        return {
            'main_plot': {
                f"ma_{self.params['base_nb_candles_buy']}": {'color': 'blue'},
                'ema_100': {'color': 'green'},
                'hma_50': {'color': 'purple'}
            },
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
