import pandas as pd
import pandas_ta as ta

def calculate_heikin_ashi(data):
    """
    Calculate Heikin Ashi values for the given data.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data

    Returns:
    - ha_close (pd.Series): Series containing Heikin Ashi close prices
    """
    ha_close = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
    ha_open = (data['Open'] + data['Close']) / 2
    ha_high = data[['Open', 'High', 'Low', 'Close']].max(axis=1)
    ha_low = data[['Open', 'High', 'Low', 'Close']].min(axis=1)
    
    ha_open.iloc[0] = (data['Open'].iloc[0] + data['Close'].iloc[0]) / 2
    
    for i in range(1, len(data)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2

    return ha_close

def ut_bot_strategy(data, key_value=1, atr_period=14, heikin_ashi=False, ema_length=2):
    """
    Implements the UT Bot Strategy.

    UT Bot Strategy combines the Average True Range (ATR) with Exponential Moving Average (EMA) and optionally 
    uses Heikin Ashi candlesticks to generate buy and sell signals based on trailing stops.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data
    - key_value (int): Sensitivity of the strategy, affects the trailing stop calculation
    - atr_period (int): Period for the ATR calculation
    - heikin_ashi (bool): Use Heikin Ashi close prices if True
    - ema_length (int): Length of the EMA

    Returns:
    - entries (pd.Series): Buy signals
    - exits (pd.Series): Sell signals
    """
    # Use Heikin Ashi close prices if specified
    if heikin_ashi:
        src = calculate_heikin_ashi(data)
    else:
        src = data['Close']

    # Calculate ATR using pandas_ta
    data['ATR'] = ta.atr(high=data['High'], low=data['Low'], close=data['Close'], length=atr_period)

    # Calculate EMA using pandas_ta
    data['EMA'] = ta.ema(src, length=ema_length)

    # Initialize Trailing Stop
    data['ATR_TrailingStop'] = pd.Series(0.0, index=data.index)

    for i in range(1, len(data)):
        if src.iloc[i] > data['ATR_TrailingStop'].iloc[i - 1] and src.iloc[i - 1] > data['ATR_TrailingStop'].iloc[i - 1]:
            data.loc[data.index[i], 'ATR_TrailingStop'] = max(data['ATR_TrailingStop'].iloc[i - 1], src.iloc[i] - key_value * data['ATR'].iloc[i])
        elif src.iloc[i] < data['ATR_TrailingStop'].iloc[i - 1] and src.iloc[i - 1] < data['ATR_TrailingStop'].iloc[i - 1]:
            data.loc[data.index[i], 'ATR_TrailingStop'] = min(data['ATR_TrailingStop'].iloc[i - 1], src.iloc[i] + key_value * data['ATR'].iloc[i])
        else:
            data.loc[data.index[i], 'ATR_TrailingStop'] = src.iloc[i] - key_value * data['ATR'].iloc[i] if src.iloc[i] > data['ATR_TrailingStop'].iloc[i - 1] else src.iloc[i] + key_value * data['ATR'].iloc[i]

    # Determine buy and sell signals
    data['Buy'] = (src > data['ATR_TrailingStop']) & (data['EMA'] > data['ATR_TrailingStop'])
    data['Sell'] = (src < data['ATR_TrailingStop']) & (data['EMA'] < data['ATR_TrailingStop'])

    entries = data['Buy']
    exits = data['Sell']

    return entries, exits


param_grid = {
    'key_value': [0.5, 1, 3],
    'atr_period': [6, 14, 30],
    'heikin_ashi': [False, True],
    'ema_length': [8, 20, 50]
}