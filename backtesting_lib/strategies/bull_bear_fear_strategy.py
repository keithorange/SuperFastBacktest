import pandas as pd
import pandas_ta as ta
import vectorbt as vbt

def bull_bear_fear_strategy(data, n=12):
    """
    Bull and Bear Fear Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - n (int): Time periods for highest and lowest calculations.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    
    high_n = data['High'].rolling(window=n).max()
    low_n = data['Low'].rolling(window=n).min()
    
    BullFear = (high_n - low_n) / 2 + low_n
    BearFear = (high_n - low_n) / 2 + low_n

    long_entries = data['Close'] > BullFear.shift(1)
    long_exits = data['Close'] < BearFear.shift(1)
    
    return long_entries, long_exits


param_grid = {
    'n': [10, 12, 14, 20]
}
