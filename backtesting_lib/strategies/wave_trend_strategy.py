import pandas as pd
import numpy as np
import pandas_ta as ta

def wave_trend_strategy(data, use_arr=True):
    """
    Noro's WaveTrend Strategy v1.0.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - use_arr (bool): If True, new trend arrows will be considered for signals.

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """

    # Calculate WaveTrend Oscillator (WTO) components
    esa = ta.ema(data['Close'], length=10)
    d = ta.ema(np.abs(data['Close'] - esa), length=10)
    ci = (data['Close'] - esa) / (0.015 * d)
    tci = ta.ema(ci, length=21)

    # Determine WTO trend
    data['WTOtrend'] = np.where(tci > 0, 1, np.where(tci < 0, -1, 0))

    # Determine trading positions
    data['posi'] = data['WTOtrend'].replace(0, np.nan).ffill().fillna(0)
    data['arr'] = np.where((use_arr) & (data['posi'] == 1) & (data['posi'].shift(1) < 1), 1,
                           np.where((use_arr) & (data['posi'] == -1) & (data['posi'].shift(1) > -1), -1, np.nan))

    # Generate Entry Signals
    data['longCondition'] = (data['posi'] == 1) & (data['posi'].shift(1) < 1)
    data['shortCondition'] = (data['posi'] == -1) & (data['posi'].shift(1) > -1)

    # Define Entry and Exit signals
    data['entries'] = data['longCondition'].astype(int)
    data['exits'] = data['shortCondition'].astype(int)

    return data['entries'], data['exits']

param_grid = {
    'use_arr': [True, False]
}
