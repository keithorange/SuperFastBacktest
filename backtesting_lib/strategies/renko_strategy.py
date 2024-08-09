import pandas as pd
import numpy as np
import pandas_ta as ta

def renko_strategy(data, renko_atr_length=10):
    """
    [SMT] Buy & Sell Renko Based - Strategy

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - renko_atr_length (int): ATR length for Renko calculation.

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """
    # Calculate ATR
    atr = ta.atr(data['High'], data['Low'], data['Close'], length=renko_atr_length)
    atr = atr.ffill().bfill()  # Forward and backward fill to handle NaN values
    
    # Initialize Renko bricks
    renko_direction = []
    renko_close = []
    current_direction = 0
    current_price = data['Close'].iloc[0]
    
    # Renko calculation
    for close_price, atr_value in zip(data['Close'], atr):
        if current_direction == 0:
            if close_price > current_price + atr_value:
                current_direction = 1
                current_price += atr_value
                renko_direction.append(current_direction)
                renko_close.append(current_price)
            elif close_price < current_price - atr_value:
                current_direction = -1
                current_price -= atr_value
                renko_direction.append(current_direction)
                renko_close.append(current_price)
        elif current_direction == 1:
            if close_price >= current_price + atr_value:
                current_price += atr_value
                renko_direction.append(current_direction)
                renko_close.append(current_price)
            elif close_price <= current_price - atr_value:
                current_direction = -1
                current_price -= atr_value
                renko_direction.append(current_direction)
                renko_close.append(current_price)
        elif current_direction == -1:
            if close_price <= current_price - atr_value:
                current_price -= atr_value
                renko_direction.append(current_direction)
                renko_close.append(current_price)
            elif close_price >= current_price + atr_value:
                current_direction = 1
                current_price += atr_value
                renko_direction.append(current_direction)
                renko_close.append(current_price)
    
    renko_close_series = pd.Series(renko_close, index=data.index[:len(renko_close)])
    
    # Generate buy and sell signals
    buy_signal = (renko_close_series.shift(1) < renko_close_series) & (renko_close_series.shift(2) > renko_close_series.shift(1))
    sell_signal = (renko_close_series.shift(1) > renko_close_series) & (renko_close_series.shift(2) < renko_close_series.shift(1))
    
    # Define entries and exits with the same length as the input data
    entries = pd.Series(False, index=data.index)
    exits = pd.Series(False, index=data.index)
    
    entries[:len(buy_signal)] = buy_signal
    exits[:len(sell_signal)] = sell_signal

    return entries, exits

param_grid = {
    'renko_atr_length': [5, 10, 20]
}
