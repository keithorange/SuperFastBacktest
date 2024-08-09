import pandas as pd
import numpy as np
import pandas_ta as ta
import vectorbt as vbt

def calculate_supertrend(data, period, multiplier):
    """
    Calculate the Supertrend indicator.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - period (int): ATR period.
    - multiplier (float): Multiplier for ATR.

    Returns:
    - supertrend (pd.Series): Supertrend values.
    - supertrend_direction (pd.Series): Supertrend direction.
    """
    multiplier = float(multiplier) # for df formatting

    supertrend = ta.supertrend(high=data['High'], low=data['Low'], close=data['Close'], length=period, multiplier=multiplier)
    supertrend_col = f"SUPERT_{period}_{multiplier}"
    supertrend_direction_col = f"SUPERTd_{period}_{multiplier}"
    return supertrend[supertrend_col], supertrend[supertrend_direction_col]

def supertrend_strategy(data, atr_period=10, atr_multiplier=3.0):
    """
    SuperTrend Strategy using pandas_ta's supertrend calculation.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data
    - atr_period (int): ATR period
    - atr_multiplier (float): ATR multiplier

    Returns:
    - entries (pd.Series): Buy signals
    - exits (pd.Series): Sell signals
    """
    supertrend, supertrend_direction = calculate_supertrend(data, atr_period, atr_multiplier)
    
    # Calculate entry and exit signals
    buy_signal = (supertrend_direction == 1) & (supertrend_direction.shift(1) == -1)
    sell_signal = (supertrend_direction == -1) & (supertrend_direction.shift(1) == 1)

    entries = buy_signal.astype(int)
    exits = sell_signal.astype(int)

    return entries, exits

param_grid = {
    'atr_period': [5, 10, 20],
    'atr_multiplier': [2.0, 3.0, 4.0]
}
