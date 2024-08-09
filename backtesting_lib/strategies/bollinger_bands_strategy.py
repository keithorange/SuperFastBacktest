import pandas as pd
import pandas_ta as ta

def bollinger_bands_strategy(data, length=55, mult=1.0, show='Both', initial_capital=100000, percent_of_equity=100):
    """
    Bollinger Bands Breakout Strategy.
    
    This strategy uses Bollinger Bands to generate buy and sell signals.
    
    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with 'Close' prices.
    - length (int): Period for the SMA (default: 55).
    - mult (float): Multiplier for the standard deviation (default: 1.0).
    - show (str): Type of trades to show ('Longs Only', 'Shorts Only', 'Both').
    - initial_capital (float): Initial capital for backtesting (default: 100000).
    - percent_of_equity (float): Percentage of equity to use per trade (default: 100).

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """

    # Calculate Bollinger Bands
    bb = ta.bbands(data['Close'], length=length, std=mult)
    data['Upper'] = bb['BBU_55_1.0']
    data['Lower'] = bb['BBL_55_1.0']

    # Generate long and short signals
    data['Long'] = data['Close'] > data['Upper']
    data['Short'] = data['Close'] < data['Lower']
    
    # Generate entry and exit signals
    data['LongSignal'] = data['Long'] & ~data['Long'].shift(1).fillna(False)
    data['ShortSignal'] = data['Short'] & ~data['Short'].shift(1).fillna(False)
    
    # Filter based on 'show' parameter
    if show == 'Longs Only':
        data['ShortSignal'] = False
    elif show == 'Shorts Only':
        data['LongSignal'] = False
    
    entries = data['LongSignal']
    exits = data['ShortSignal']
    
    return entries, exits


param_grid = {
    'length': [20, 55, 100],
    'mult': [1.0, 2.0, 3.0],
    'show': ['Longs Only', 'Shorts Only', 'Both']
}
