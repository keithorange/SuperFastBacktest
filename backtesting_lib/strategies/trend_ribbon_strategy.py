import pandas as pd
import pandas_ta as ta

def trend_ribbon_strategy(data, ma_type="SMA", ma_length=20):
    """
    Noro's Trend Ribbon Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - ma_type (str): Type of moving average ("SMA", "EMA", "VWMA", "RMA").
    - ma_length (int): Length of the moving average.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    
    close = data['Close']
    
    # Calculate the selected moving average
    if ma_type == "SMA":
        ma = ta.sma(close, length=ma_length)
    elif ma_type == "EMA":
        ma = ta.ema(close, length=ma_length)
    elif ma_type == "VWMA":
        ma = ta.vwma(close, length=ma_length)
    elif ma_type == "RMA":
        ma = ta.rma(close, length=ma_length)
    else:
        raise ValueError("Invalid moving average type")
    
    # Calculate the highest and lowest of the moving average
    high = ma.rolling(window=ma_length).max()
    low = ma.rolling(window=ma_length).min()
    
    # Determine trend
    trend = pd.Series(0, index=data.index)
    trend[close > high.shift(1)] = 1
    trend[close < low.shift(1)] = -1
    trend = trend.ffill().fillna(0)
    
    # Long entry and exit signals
    long_entries = (trend == 1)
    long_exits = (trend == -1)
    
    return long_entries, long_exits

param_grid = {
    'ma_type': ["SMA", "EMA", "VWMA", "RMA"],
    'ma_length': [10, 20, 30, 50]
}
