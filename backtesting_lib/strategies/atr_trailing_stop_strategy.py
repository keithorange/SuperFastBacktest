import pandas as pd
import numpy as np
import pandas_ta as ta

def atr_trailing_stop_strategy(data, source='Close', fast_atr_period=5, fast_atr_multiplier=0.5, slow_atr_period=10, slow_atr_multiplier=3):
    """
    ATR Trailing Stop Strategy by ceyhun.
    
    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data
    - source (str): Price source for calculation (default: 'Close')
    - fast_atr_period (int): Fast ATR period (default: 5)
    - fast_atr_multiplier (float): Fast ATR multiplier (default: 0.5)
    - slow_atr_period (int): Slow ATR period (default: 10)
    - slow_atr_multiplier (float): Slow ATR multiplier (default: 3)
    
    Returns:
    - entries (pd.Series): Buy signals
    - exits (pd.Series): Sell signals
    """

    # Ensure the source column is in the DataFrame
    if source not in data.columns:
        raise ValueError(f"Source column '{source}' not found in data")

    # Calculate ATR
    data['ATR_Fast'] = ta.atr(high=data['High'], low=data['Low'], close=data[source], length=fast_atr_period)
    data['ATR_Slow'] = ta.atr(high=data['High'], low=data['Low'], close=data[source], length=slow_atr_period)

    # Calculate Stop Losses
    data['SL1'] = fast_atr_multiplier * data['ATR_Fast']
    data['SL2'] = slow_atr_multiplier * data['ATR_Slow']

    # Initialize Trailing Stops
    data['Trail1'] = np.nan
    data['Trail2'] = np.nan

    # Calculate Trailing Stops
    for i in range(1, len(data)):
        if data[source].iloc[i] > data['Trail1'].iloc[i - 1] and data[source].iloc[i - 1] > data['Trail1'].iloc[i - 1]:
            data.at[data.index[i], 'Trail1'] = max(data['Trail1'].iloc[i - 1], data[source].iloc[i] - data['SL1'].iloc[i])
        elif data[source].iloc[i] < data['Trail1'].iloc[i - 1] and data[source].iloc[i - 1] < data['Trail1'].iloc[i - 1]:
            data.at[data.index[i], 'Trail1'] = min(data['Trail1'].iloc[i - 1], data[source].iloc[i] + data['SL1'].iloc[i])
        else:
            data.at[data.index[i], 'Trail1'] = data[source].iloc[i] - data['SL1'].iloc[i] if data[source].iloc[i] > data['Trail1'].iloc[i - 1] else data[source].iloc[i] + data['SL1'].iloc[i]

        if data[source].iloc[i] > data['Trail2'].iloc[i - 1] and data[source].iloc[i - 1] > data['Trail2'].iloc[i - 1]:
            data.at[data.index[i], 'Trail2'] = max(data['Trail2'].iloc[i - 1], data[source].iloc[i] - data['SL2'].iloc[i])
        elif data[source].iloc[i] < data['Trail2'].iloc[i - 1] and data[source].iloc[i - 1] < data['Trail2'].iloc[i - 1]:
            data.at[data.index[i], 'Trail2'] = min(data['Trail2'].iloc[i - 1], data[source].iloc[i] + data['SL2'].iloc[i])
        else:
            data.at[data.index[i], 'Trail2'] = data[source].iloc[i] - data['SL2'].iloc[i] if data[source].iloc[i] > data['Trail2'].iloc[i - 1] else data[source].iloc[i] + data['SL2'].iloc[i]

    # Generate entry and exit signals
    data['Buy'] = (data['Trail1'] > data['Trail2']) & (data[source] > data['Trail2']) & (data['Low'] > data['Trail2'])
    data['Sell'] = (data['Trail2'] > data['Trail1']) & (data[source] < data['Trail2']) & (data['High'] < data['Trail2'])

    entries = data['Buy']
    exits = data['Sell']

    return entries, exits

param_grid= {
    'fast_atr_period': [5, 7, 10],
    'fast_atr_multiplier': [0.5, 1.0, 1.5],
    'slow_atr_period': [10, 14, 20],
    'slow_atr_multiplier': [2.0, 3.0, 4.0]
}
