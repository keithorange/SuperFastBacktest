import pandas as pd
import pandas_ta as ta
import vectorbt as vbt

def trend_ma_strategy(data, fast_period=10, slow_period=30, ma_type="SMA"):
    """
    Noro's TrendMA Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - fast_period (int): Period for the fast moving average.
    - slow_period (int): Period for the slow moving average.
    - ma_type (str): Type of moving average ("SMA", "EMA").

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    
    close = data['Close']
    
    # Calculate the fast and slow moving averages
    if ma_type == "SMA":
        fast_ma = ta.sma(close, length=fast_period)
        slow_ma = ta.sma(close, length=slow_period)
    elif ma_type == "EMA":
        fast_ma = ta.ema(close, length=fast_period)
        slow_ma = ta.ema(close, length=slow_period)
    else:
        raise ValueError("Invalid moving average type")
    
    # Determine trend
    trend1 = (fast_ma > fast_ma.shift(1)).astype(int) - (fast_ma < fast_ma.shift(1)).astype(int)
    trend2 = (slow_ma > slow_ma.shift(1)).astype(int) - (slow_ma < slow_ma.shift(1)).astype(int)
    trend = pd.Series(0, index=data.index)
    trend[(trend1 == 1) & (trend2 == 1)] = 1
    trend[(trend1 == -1) & (trend2 == -1)] = -1
    trend = trend.ffill().fillna(0)
    
    # Long entry and exit signals
    long_entries = (trend == 1)
    long_exits = (trend == -1)
    
    return long_entries, long_exits

param_grid = {
    'fast_period': [10, 20, 30],
    'slow_period': [30, 50, 100],
    'ma_type': ["SMA", "EMA"]
}
