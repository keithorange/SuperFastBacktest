import pandas as pd
import numpy as np
import pandas_ta as ta
import vectorbt as vbt

def uhl_ma_system(data, length=100, mult=1.0, src='Close'):
    """
    Uhl MA System - Strategy Analysis

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - length (int): Period for calculating the moving averages and variance.
    - mult (float): Multiplier used in the calculations.
    - src (str): Source column name in the data.

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """
    
    # Calculate Variance and SMA
    data['Var'] = data[src].rolling(window=length).var()
    data['SMA'] = data[src].rolling(window=length).mean()
    
    # Initialize custom moving averages
    data['CMA'] = np.nan
    data['CTS'] = np.nan
    
    # Loop through data to calculate custom moving averages
    for i in range(length, len(data)):
        prev_cma = data['CMA'].iloc[i-1] if not np.isnan(data['CMA'].iloc[i-1]) else data[src].iloc[i]
        prev_cts = data['CTS'].iloc[i-1] if not np.isnan(data['CTS'].iloc[i-1]) else data[src].iloc[i]
        
        secma = (data['SMA'].iloc[i] - prev_cma)**2
        sects = (data[src].iloc[i] - prev_cts)**2
        
        ka = 1 - data['Var'].iloc[i] / secma if data['Var'].iloc[i] < secma else 0
        kb = 1 - data['Var'].iloc[i] / sects if data['Var'].iloc[i] < sects else 0
        
        data.at[data.index[i], 'CMA'] = ka * data['SMA'].iloc[i] + (1 - ka) * prev_cma
        data.at[data.index[i], 'CTS'] = kb * data[src].iloc[i] + (1 - kb) * prev_cts
    
    # Generate entry signals
    data['Buy'] = (data['CTS'] > data['CMA']) & (data['CTS'].shift(1) <= data['CMA'].shift(1))
    data['Sell'] = (data['CTS'] < data['CMA']) & (data['CTS'].shift(1) >= data['CMA'].shift(1))
    
    # Define entries and exits
    entries = data['Buy']
    exits = data['Sell']
    
    return entries, exits

param_grid = {
    'length': [50, 100, 200],
    'mult': [0.5, 1.0, 2.0],
    'src': ['Close', 'Open', 'High', 'Low']
}
