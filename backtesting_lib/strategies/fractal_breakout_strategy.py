import pandas as pd
import numpy as np
import vectorbt as vbt

def fractal_breakout_strategy(data, lookback_period=8):
    """
    Fractal Breakout Strategy

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - lookback_period (int): The number of periods to look back for identifying fractals.

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """
    
    def is_fractal_up(highs):
        return (
            (highs[lookback_period] < highs[2] and highs[lookback_period-1] < highs[2] and highs[1] < highs[2] and highs[0] < highs[2]) or
            (highs[lookback_period+1] < highs[2] and highs[lookback_period] < highs[2] and highs[lookback_period-1] <= highs[2] and highs[1] < highs[2] and highs[0] < highs[2]) or
            (highs[lookback_period+2] < highs[2] and highs[lookback_period+1] < highs[2] and highs[lookback_period] <= highs[2] and highs[lookback_period-1] <= highs[2] and highs[1] < highs[2] and highs[0] < highs[2]) or
            (highs[lookback_period+3] < highs[2] and highs[lookback_period+2] < highs[2] and highs[lookback_period+1] <= highs[2] and highs[lookback_period] <= highs[2] and highs[lookback_period-1] <= highs[2] and highs[1] < highs[2] and highs[0] < highs[2]) or
            (highs[lookback_period+4] < highs[2] and highs[lookback_period+3] < highs[2] and highs[lookback_period+2] <= highs[2] and highs[lookback_period+1] <= highs[2] and highs[lookback_period] <= highs[2] and highs[lookback_period-1] <= highs[2] and highs[1] < highs[2] and highs[0] < highs[2])
        )

    def is_fractal_down(lows):
        return (
            (lows[lookback_period] > lows[2] and lows[lookback_period-1] > lows[2] and lows[1] > lows[2] and lows[0] > lows[2]) or
            (lows[lookback_period+1] > lows[2] and lows[lookback_period] > lows[2] and lows[lookback_period-1] >= lows[2] and lows[1] > lows[2] and lows[0] > lows[2]) or
            (lows[lookback_period+2] > lows[2] and lows[lookback_period+1] > lows[2] and lows[lookback_period] >= lows[2] and lows[lookback_period-1] >= lows[2] and lows[1] > lows[2] and lows[0] > lows[2]) or
            (lows[lookback_period+3] > lows[2] and lows[lookback_period+2] > lows[2] and lows[lookback_period+1] >= lows[2] and lows[lookback_period] >= lows[2] and lows[lookback_period-1] >= lows[2] and lows[1] > lows[2] and lows[0] > lows[2]) or
            (lows[lookback_period+4] > lows[2] and lows[lookback_period+3] > lows[2] and lows[lookback_period+2] >= lows[2] and lows[lookback_period+1] >= lows[2] and lows[lookback_period] >= lows[2] and lows[lookback_period-1] >= lows[2] and lows[1] > lows[2] and lows[0] > lows[2])
        )

    highs = data['High'].values
    lows = data['Low'].values
    closes = data['Close'].values

    fractal_up = np.full(len(highs), np.nan)
    fractal_down = np.full(len(lows), np.nan)

    for i in range(lookback_period+4, len(highs)):
        if is_fractal_up(highs[i-lookback_period-4:i+1]):
            fractal_up[i] = highs[i-lookback_period-2]
        if is_fractal_down(lows[i-lookback_period-4:i+1]):
            fractal_down[i] = lows[i-lookback_period-2]

    fractal_up = pd.Series(fractal_up, index=data.index)
    fractal_down = pd.Series(fractal_down, index=data.index)

    entries = closes > fractal_up.shift(1)
    exits = closes < fractal_down.shift(1)

    return entries, exits

param_grid = {
    'lookback_period': [8, 10, 12],
}
