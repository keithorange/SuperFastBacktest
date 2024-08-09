import pandas as pd
import pandas_ta as ta

def hullma_strategy(data, period=16):
    """
    Implements the Hull Moving Average (HullMA) Strategy.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data
    - period (int): Period for the HullMA calculation

    Returns:
    - entries (pd.Series): Buy signals
    - exits (pd.Series): Sell signals
    """
    # Calculate Hull Moving Average using pandas_ta
    hull_ma = ta.hma(data['Close'], length=period)

    # Generate buy and sell signals
    entries = hull_ma > hull_ma.shift()
    exits = hull_ma < hull_ma.shift()

    return entries, exits

param_grid = {
    'period': [10, 16, 20, 25, 30]
}
