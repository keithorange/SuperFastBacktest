import pandas as pd
import numpy as np
import pandas_ta as ta

def trailing_sl_strategy(data, sl_type='%', sl_perc=4.0, atr_length=10, atr_mult=2.0, sl_absol=10.0):
    """
    Trailing Stop Loss Strategy.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data
    - sl_type (str): Stop loss type ('%', 'ATR', 'Absolute')
    - sl_perc (float): Percentage stop loss
    - atr_length (int): ATR calculation period
    - atr_mult (float): ATR multiplier for stop loss
    - sl_absol (float): Absolute stop loss value

    Returns:
    - entries (pd.Series): Buy signals
    - exits (pd.Series): Sell signals
    """
    data = data.copy()  # Avoid modifying the original data

    # Calculate ATR if needed using pandas_ta
    if sl_type == 'ATR':
        data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=atr_length)

    # Calculate stop loss value
    if sl_type == '%':
        data['sl_val'] = data['Close'] * sl_perc / 100
    elif sl_type == 'ATR':
        data['sl_val'] = atr_mult * data['ATR']
    elif sl_type == 'Absolute':
        data['sl_val'] = sl_absol

    # Initialize position and trailing stop
    data['pos'] = 0
    data['trailing_sl'] = 0.0

    # Vectorized Signals and trailing stop calculation
    long_condition = (data['High'] > data['trailing_sl'].shift(1)) & (data['pos'].shift(1) != 1)
    short_condition = (data['Low'] < data['trailing_sl'].shift(1)) & (data['pos'].shift(1) != -1)

    data.loc[long_condition, 'pos'] = 1
    data.loc[long_condition, 'trailing_sl'] = data['Low'] - data['sl_val']

    data.loc[short_condition, 'pos'] = -1
    data.loc[short_condition, 'trailing_sl'] = data['High'] + data['sl_val']

    data['pos'].ffill(inplace=True)
    data['trailing_sl'].ffill(inplace=True)

    # Update trailing stop based on the position
    data.loc[data['pos'] == 1, 'trailing_sl'] = np.maximum(data['Low'] - data['sl_val'], data['trailing_sl'].shift(1))
    data.loc[data['pos'] == -1, 'trailing_sl'] = np.minimum(data['High'] + data['sl_val'], data['trailing_sl'].shift(1))

    # Entry and exit signals
    entries = data['pos'] == 1
    exits = data['pos'] == -1

    return entries, exits

param_grid = {
    'sl_type': ['%', 'ATR', 'Absolute'],
    'sl_perc': [2.0, 4.0, 6.0],
    'atr_length': [5, 10, 20],
    'atr_mult': [1.5, 2.0, 2.5],
    'sl_absol': [5.0, 10.0, 15.0]
}
