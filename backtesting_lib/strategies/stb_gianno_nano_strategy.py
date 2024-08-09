import pandas as pd
import numpy as np
import pandas_ta as ta

def crossover(series1, series2):
    """
    Returns a boolean Series where True indicates a crossover.
    """
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))

def crossunder(series1, series2):
    """
    Returns a boolean Series where True indicates a crossunder.
    """
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))

def stb_gianno_nano_strategy(data, ema_fast=10, ema_slow=60, ema_stop_input=112, 
                             SL_Long_percent=3.0, TP_Long_percent=36.0, ema_stop_sl=False):
    """
    STB - Gianno Nano Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - ema_fast (int): Period for the fast EMA.
    - ema_slow (int): Period for the slow EMA.
    - ema_stop_input (int): Period for the stop loss EMA.
    - SL_Long_percent (float): Stop loss percentage for long positions.
    - TP_Long_percent (float): Take profit percentage for long positions.
    - ema_stop_sl (bool): Use EMA cross for stop loss.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    
    close = data['Close']
    
    # Calculate EMAs
    ema_fast_series = ta.ema(close, length=ema_fast)
    ema_slow_series = ta.ema(close, length=ema_slow)
    ema_stop_series = ta.ema(close, length=ema_stop_input)
    
    # Long entry and exit conditions
    long_entries = crossover(ema_fast_series, ema_slow_series)
    long_exits = crossunder(ema_fast_series, ema_slow_series)
    
    if ema_stop_sl:
        long_exits = long_exits | crossunder(close, ema_stop_series)
    
    # Calculate SL and TP levels
    entry_prices = close[long_entries].shift()
    sl_long = entry_prices * (1 - SL_Long_percent / 100)
    tp_long = entry_prices * (1 + TP_Long_percent / 100)
    
    # Remove NaN values for stop loss and take profit levels
    sl_long = sl_long.reindex(data.index).ffill()
    tp_long = tp_long.reindex(data.index).ffill()
    
    # Vectorized exit conditions
    in_position = long_entries.cumsum() > long_exits.cumsum()
    stop_reached = close < sl_long
    take_profit_reached = close > tp_long
    
    long_exits |= (in_position & (stop_reached | take_profit_reached))
    
    return long_entries, long_exits


param_grid = {
    'ema_fast': [5, 10, 20],
    'ema_slow': [50, 60, 100],
    'ema_stop_input': [50, 112, 150],
    'SL_Long_percent': [1.0, 2.0, 3.0],
    'TP_Long_percent': [10.0, 20.0, 30.0],
    'ema_stop_sl': [True, False]
}
