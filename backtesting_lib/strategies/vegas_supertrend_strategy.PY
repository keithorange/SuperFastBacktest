import pandas as pd
import numpy as np
import pandas_ta as ta
import vectorbt as vbt

def vegas_supertrend_strategy(data, atr_period=10, vegas_window=100, supertrend_multiplier=5, volatility_adjustment=5):
    """
    Vegas SuperTrend Enhanced Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - atr_period (int): Length of the ATR for volatility measurement.
    - vegas_window (int): Length of the moving average for the Vegas Channel.
    - supertrend_multiplier (int): Base multiplier for the SuperTrend calculation.
    - volatility_adjustment (float): Factor to adjust the SuperTrend sensitivity to the Vegas Channel width.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    
    close = data['Close']
    high = data['High']
    low = data['Low']
    hlc3 = (high + low + close) / 3
    
    # Calculate the Vegas Channel
    vegas_moving_average = ta.sma(close, length=vegas_window)
    vegas_channel_stddev = ta.stdev(close, length=vegas_window)
    vegas_channel_upper = vegas_moving_average + vegas_channel_stddev
    vegas_channel_lower = vegas_moving_average - vegas_channel_stddev
    
    # Adjust the SuperTrend multiplier based on the width of the Vegas Channel
    channel_volatility_width = vegas_channel_upper - vegas_channel_lower
    adjusted_multiplier = supertrend_multiplier + volatility_adjustment * (channel_volatility_width / vegas_moving_average)
    
    # Calculate the SuperTrend indicator values
    average_true_range = ta.atr(high, low, close, length=atr_period)
    supertrend_upper = hlc3 - (adjusted_multiplier * average_true_range)
    supertrend_lower = hlc3 + (adjusted_multiplier * average_true_range)
    
    supertrend_prev_upper = supertrend_upper.copy()
    supertrend_prev_lower = supertrend_lower.copy()
    market_trend = pd.Series(1, index=data.index)
    
    for i in range(1, len(data)):
        supertrend_prev_upper[i] = supertrend_upper[i] if market_trend[i-1] == 1 else min(supertrend_upper[i], supertrend_prev_upper[i-1])
        supertrend_prev_lower[i] = supertrend_lower[i] if market_trend[i-1] == -1 else max(supertrend_lower[i], supertrend_prev_lower[i-1])
        market_trend[i] = 1 if close[i] > supertrend_prev_lower[i] else -1 if close[i] < supertrend_prev_upper[i] else market_trend[i-1]
    
    trend_shift_to_bullish = (market_trend == 1) & (market_trend.shift(1) == -1)
    trend_shift_to_bearish = (market_trend == -1) & (market_trend.shift(1) == 1)
    
    entries = trend_shift_to_bullish
    exits = trend_shift_to_bearish

    return entries, exits

param_grid = {
    'atr_period': [10, 14, 20],
    'vegas_window': [50, 100, 150],
    'supertrend_multiplier': [3, 5, 7],
    'volatility_adjustment': [2, 5, 8]
}
