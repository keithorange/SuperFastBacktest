import pandas as pd
import numpy as np
import pandas_ta as ta
import vectorbt as vbt

def heikin_ashi_psar_strategy(data, psar_start=0.02, psar_increment=0.02, psar_max=0.2):
    """
    Heikin-Ashi PSAR Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - psar_start (float): Initial acceleration factor for PSAR.
    - psar_increment (float): Increment for the acceleration factor.
    - psar_max (float): Maximum value for the acceleration factor.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    # Calculate Heikin-Ashi values
    ha_close = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
    ha_open = ha_close.copy()
    ha_open.iloc[0] = (data['Open'].iloc[0] + data['Close'].iloc[0]) / 2
    ha_open = ha_open.shift().fillna(ha_open.iloc[0]).rolling(window=2).mean()
    ha_high = pd.concat([data['High'], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([data['Low'], ha_open, ha_close], axis=1).min(axis=1)

    # Calculate PSAR
    psar = ta.psar(high=data['High'], low=data['Low'], close=data['Close'], af0=psar_start, af_increment=psar_increment, af_max=psar_max)
    psar_values = psar.iloc[:, 0].shift(1)  # Select the first column which is the PSAR values and shift

    # Determine trend direction
    trend_dir = np.where(ha_close > ha_open, 1, -1)

    # Calculate trend change
    sar_long_to_short = (trend_dir[:-1] == 1) & (ha_close[1:] <= psar_values[1:])
    sar_short_to_long = (trend_dir[:-1] == -1) & (ha_close[1:] >= psar_values[1:])

    # Adjust lengths to match original data
    sar_long_to_short = np.append([False], sar_long_to_short)
    sar_short_to_long = np.append([False], sar_short_to_long)

    # Long entry and exit signals
    long_entries = pd.Series(sar_short_to_long, index=data.index)
    long_exits = pd.Series(sar_long_to_short, index=data.index)

    return long_entries, long_exits


param_grid = {
    'psar_start': [0.01, 0.02, 0.03],
    'psar_increment': [0.01, 0.02, 0.03],
    'psar_max': [0.1, 0.2, 0.3]
}
