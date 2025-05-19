"""
Technical indicators for strategy engine.
This module provides common technical indicators used by trading strategies.
"""
import numpy as np
import pandas as pd
import talib.abstract as ta
from typing import Dict, Optional, Tuple, Union, List


def calculate_ema(dataframe: pd.DataFrame, period: int, field='close') -> pd.Series:
    """
    Calculate Exponential Moving Average
    
    :param dataframe: OHLCV dataframe
    :param period: Period for EMA calculation
    :param field: Field to use for calculation (default: close)
    :return: Series with EMA values
    """
    return ta.EMA(dataframe, timeperiod=period, price=field)


def calculate_sma(dataframe: pd.DataFrame, period: int, field='close') -> pd.Series:
    """
    Calculate Simple Moving Average
    
    :param dataframe: OHLCV dataframe
    :param period: Period for SMA calculation
    :param field: Field to use for calculation (default: close)
    :return: Series with SMA values
    """
    return ta.SMA(dataframe, timeperiod=period, price=field)


def calculate_rsi(dataframe: pd.DataFrame, period: int, field='close') -> pd.Series:
    """
    Calculate Relative Strength Index
    
    :param dataframe: OHLCV dataframe
    :param period: Period for RSI calculation
    :param field: Field to use for calculation (default: close)
    :return: Series with RSI values
    """
    return ta.RSI(dataframe, timeperiod=period, price=field)


def calculate_ewo(dataframe: pd.DataFrame, ema_short=5, ema_long=35) -> pd.Series:
    """
    Calculate Elliott Wave Oscillator
    
    :param dataframe: OHLCV dataframe
    :param ema_short: Short period for EMA calculation
    :param ema_long: Long period for EMA calculation
    :return: Series with EWO values
    """
    df = dataframe.copy()
    df['ema_short'] = ta.EMA(df, timeperiod=ema_short)
    df['ema_long'] = ta.EMA(df, timeperiod=ema_long)
    df['ewo'] = (df['ema_short'] - df['ema_long']) / df['close'] * 100
    return df['ewo']


def calculate_stoch_rsi(dataframe: pd.DataFrame, period=14, rsi_period=14, k=3, d=3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic RSI
    
    :param dataframe: OHLCV dataframe
    :param period: Period for Stochastic calculation
    :param rsi_period: Period for RSI calculation
    :param k: K line period
    :param d: D line period
    :return: Tuple of Series (k_line, d_line)
    """
    rsi = ta.RSI(dataframe, timeperiod=rsi_period)
    stoch_k, stoch_d = ta.STOCH(
        pd.DataFrame({
            'high': rsi,
            'low': rsi,
            'close': rsi,
        }),
        fastk_period=period,
        slowk_period=k,
        slowd_period=d
    )
    return stoch_k, stoch_d


def calculate_bollinger_bands(dataframe: pd.DataFrame, period=20, stddev=2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands
    
    :param dataframe: OHLCV dataframe
    :param period: Period for moving average
    :param stddev: Standard deviation multiplier
    :return: Tuple of Series (upper, middle, lower)
    """
    return ta.BBANDS(dataframe, timeperiod=period, nbdevup=stddev, nbdevdn=stddev)


def calculate_macd(dataframe: pd.DataFrame, fast=12, slow=26, signal=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD
    
    :param dataframe: OHLCV dataframe
    :param fast: Fast period
    :param slow: Slow period
    :param signal: Signal period
    :return: Tuple of Series (macd, signal, histogram)
    """
    return ta.MACD(dataframe, fastperiod=fast, slowperiod=slow, signalperiod=signal)


def calculate_wma(dataframe: pd.DataFrame, period: int, field='close') -> pd.Series:
    """
    Calculate Weighted Moving Average
    
    :param dataframe: OHLCV dataframe
    :param period: Period for WMA calculation
    :param field: Field to use for calculation (default: close)
    :return: Series with WMA values
    """
    try:
        # Try using talib if available
        return ta.WMA(dataframe, timeperiod=period, price=field)
    except:
        # Fallback to manual calculation
        weights = np.arange(1, period + 1)
        data = dataframe[field].values if isinstance(field, str) else field.values
        wma = pd.Series(
            index=dataframe.index,
            data=np.nan_to_num(pd.Series(data).rolling(period).apply(
                lambda x: np.sum(weights * x) / np.sum(weights), raw=True).values)
        )
        return wma


def calculate_hma(dataframe: pd.DataFrame, period: int, field='close') -> pd.Series:
    """
    Calculate Hull Moving Average
    HMA = WMA(2*WMA(n/2) - WMA(n)), sqrt(n))
    
    :param dataframe: OHLCV dataframe
    :param period: Period for HMA calculation
    :param field: Field to use for calculation (default: close)
    :return: Series with HMA values
    """
    half_length = period // 2
    sqrt_length = int(np.sqrt(period))
    
    # Calculate WMAs
    wma_half = calculate_wma(dataframe, half_length, field)
    wma_full = calculate_wma(dataframe, period, field)
    
    # Calculate 2*WMA(n/2) - WMA(n)
    hma_data = 2 * wma_half - wma_full
    
    # Calculate final HMA
    hma = calculate_wma(pd.DataFrame({field: hma_data}), sqrt_length, field)
    
    return hma
