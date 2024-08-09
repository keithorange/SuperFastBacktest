# FIRE

import pandas as pd
import numpy as np
import vectorbt as vbt

def heikin_ashi_color_change_strategy(data):
    """
    Kozlod - Heikin-Ashi Bar Color Change Strategy

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """
    
    # Calculate Heikin-Ashi values
    ha_open = (data['Open'].shift(1) + data['Close'].shift(1)) / 2
    ha_close = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
    ha_high = data[['High', 'Close', 'Open']].max(axis=1)
    ha_low = data[['Low', 'Close', 'Open']].min(axis=1)

    # Fill initial ha_open value
    ha_open.iloc[0] = (data['Open'].iloc[0] + data['Close'].iloc[0]) / 2
    
    # Calculate Heikin-Ashi bar color
    ha_color = np.where(ha_close > ha_open, 'green', 'red')

    # Determine signals
    turn_green = (ha_close > ha_open) & (ha_close.shift(1) <= ha_open.shift(1))
    turn_red = (ha_close <= ha_open) & (ha_close.shift(1) > ha_open.shift(1))

    # Entries and exits
    entries = turn_green
    exits = turn_red

    return entries, exits


param_grid = {
    # No parameters to vary for this strategy as it stands; using defaults
}
