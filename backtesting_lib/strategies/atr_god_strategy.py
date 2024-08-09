import pandas as pd
import numpy as np
import pandas_ta as ta

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
    # Calculate the supertrend using pandas_ta
    multiplier = float(multiplier)  # for df formatting
    supertrend = ta.supertrend(high=data['High'], low=data['Low'], close=data['Close'], length=period, multiplier=multiplier)
    supertrend_col = f"SUPERT_{period}_{multiplier}"
    supertrend_direction_col = f"SUPERTd_{period}_{multiplier}"
    return supertrend[supertrend_col], supertrend[supertrend_direction_col]

def atr_god_strategy(data, 
                     per_st_1=20, mult_st_1=2.0, 
                     per_st_2=5, mult_st_2=15, 
                     per_st_3=10, mult_st_3=3.0, 
                     per_st_4=20, mult_st_4=10.0,
                     atr_length=14, rr_ratio=1.5, 
                     nnatr_loss=4.5):
    """
    ATR GOD Strategy

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - per_st_1, per_st_2, per_st_3, per_st_4 (int): ATR periods for each supertrend.
    - mult_st_1, mult_st_2, mult_st_3, mult_st_4 (float): ATR multipliers for each supertrend.
    - atr_length (int): Length of the ATR period for stop loss calculation.
    - rr_ratio (float): Risk to reward ratio.
    - nnatr_loss (float): Base risk multiplier for stop loss.

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """
    
    # Supertrend calculations
    trend_st_1, dir_st_1 = calculate_supertrend(data, per_st_1, mult_st_1)
    trend_st_2, dir_st_2 = calculate_supertrend(data, per_st_2, mult_st_2)
    trend_st_3, dir_st_3 = calculate_supertrend(data, per_st_3, mult_st_3)
    trend_st_4, dir_st_4 = calculate_supertrend(data, per_st_4, mult_st_4)
    
    # Entry logic
    long_trends_ok = ((dir_st_1 == 1) & (dir_st_2 == 1) & (dir_st_3 == 1) & (dir_st_4 == 1))
    buy_signals = (dir_st_1 == 1) & (dir_st_2 == 1) & (dir_st_3 == 1) & (dir_st_4 == 1)
    
    # ATR based stop loss and profit targets
    atr = ta.atr(data['High'], data['Low'], data['Close'], length=atr_length)
    stop_loss = data['Close'] - (nnatr_loss * atr)
    profit_target = data['Close'] + (nnatr_loss * rr_ratio * atr)
    
    # Prepare signals
    entries = buy_signals & long_trends_ok
    exits = pd.Series(np.zeros(len(data)), index=data.index)
    for i in range(1, len(data)):
        if entries.iloc[i-1]:
            exits.iloc[i] = float((data['Close'].iloc[i] < stop_loss.iloc[i]) | (data['Close'].iloc[i] > profit_target.iloc[i]))
    
    return entries, exits

param_grid = {
    'per_st_1': [10, 20, 30],
    'mult_st_1': [2.0, 2.5, 3.0],
    'per_st_2': [5, 10, 15],
    'mult_st_2': [10.0, 15.0, 20.0],
    'per_st_3': [5, 10, 15],
    'mult_st_3': [2.0, 3.0, 4.0],
    'per_st_4': [15, 20, 25],
    'mult_st_4': [8.0, 10.0, 12.0],
    'atr_length': [10, 14, 20],
    'rr_ratio': [1.0, 1.5, 2.0],
    'nnatr_loss': [3.0, 4.0, 5.0]
}
