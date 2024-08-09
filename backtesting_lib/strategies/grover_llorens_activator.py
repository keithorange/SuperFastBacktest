import pandas as pd
import numpy as np
import pandas_ta as ta

"""
From the provided data, it appears that the different parameter sets performed quite similarly, as evidenced by the mean values of key performance metrics such as total profit, total return, sharpe ratio, calmar ratio, omega ratio, sortino ratio, win rate, and expectancy. While there are some variations, these differences are relatively minor. Let's look at a comparison of the mean values for each parameter set:

### Comparison of Key Metrics for Each Parameter Set:

| Parameters | Total Profit | Sharpe Ratio | Calmar Ratio | Omega Ratio | Sortino Ratio | Win Rate | Expectancy |
|------------|--------------|--------------|--------------|-------------|---------------|----------|------------|
| 240, 8     | 391.4642     | 0.3779       | 0.3626       | 1.1434      | 0.7682        | 35.29%   | 0.1049     |
| 80, 20     | 391.4577     | 0.3775       | 0.3625       | 1.1433      | 0.7676        | 35.29%   | 0.1049     |
| 80, 8      | 391.4555     | 0.3774       | 0.3625       | 1.1433      | 0.7676        | 35.29%   | 0.1049     |
| 80, 14     | 391.4547     | 0.3774       | 0.3625       | 1.1433      | 0.7675        | 35.29%   | 0.1049     |
| 240, 14    | 389.9445     | 0.3777       | 0.3624       | 1.1432      | 0.7670        | 35.30%   | 0.1045     |
| 240, 20    | 389.8065     | 0.3776       | 0.3623       | 1.1432      | 0.7668        | 35.30%   | 0.1044     |
| 480, 8     | 389.8065     | 0.3776       | 0.3623       | 1.1432      | 0.7668        | 35.30%   | 0.1044     |
| 480, 14    | 389.8065     | 0.3776       | 0.3623       | 1.1432      | 0.7668        | 35.30%   | 0.1044     |
| 720, 14    | 389.8055     | 0.3776       | 0.3623       | 1.1432      | 0.7668        | 35.30%   | 0.1044     |
| 480, 20    | 389.8028     | 0.3773       | 0.3622       | 1.1431      | 0.7664        | 35.30%   | 0.1044     |
| 720, 8     | 389.8022     | 0.3773       | 0.3622       | 1.1431      | 0.7664        | 35.30%   | 0.1044     |
| 720, 20    | 389.4400     | 0.3776       | 0.3622       | 1.1432      | 0.7668        | 35.30%   | 0.1044     |

### Analysis:
1. **Total Profit:** All parameter sets result in a similar total profit, with slight variations.
2. **Sharpe Ratio:** The differences are minimal, with all parameter sets showing similar risk-adjusted returns.
3. **Calmar Ratio:** The ratios are very close across all sets, indicating similar performance in terms of return versus drawdown.
4. **Omega Ratio:** Slight variations, but all parameter sets are in a close range.
5. **Sortino Ratio:** Very minor differences, indicating similar downside risk performance.
6. **Win Rate:** All parameter sets have a win rate around 35.29% to 35.30%.
7. **Expectancy:** All parameter sets show very similar expectancy values, around 0.1044 to 0.1049.

### Conclusion:
The performance metrics for the different parameter sets are extremely close to each other, indicating that the parameters did not significantly impact the strategy's overall performance. The minor variations observed in the metrics are within a narrow range, suggesting that the strategy is robust to changes in these specific parameters. Therefore, it can be concluded that the strategy's performance is relatively stable across the tested parameter sets.
"""

def grover_llorens_activator(data, length=240, mult=8):
    """
    Grover Llorens Activator Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - length (int): ATR period.
    - mult (float): Multiplier for ATR.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """

    # Calculate ATR
    atr = ta.atr(high=data['High'], low=data['Low'], close=data['Close'], length=length)
    
    # Initialize ts and diff
    ts = pd.Series(0.0, index=data.index)
    diff = data['Close'].diff()

    # Determine up and dn conditions
    up = diff > 0
    dn = diff < 0

    # Calculate valuewhen and bars since
    val = np.where(up | dn, atr / length, np.nan)
    val = pd.Series(val, index=data.index).ffill()
    bars = (up | dn).cumsum()

    # Calculate ts
    ts[up] = data['Close'][up] - atr[up] * mult
    ts[dn] = data['Close'][dn] + atr[dn] * mult
    ts = ts.ffill()
    
    ts = pd.Series(np.where(up, ts + np.sign(diff) * val * bars, ts), index=data.index)

    # Generate signals
    long_entries = up
    long_exits = dn

    return long_entries, long_exits

param_grid = {
    'length': [80, 240, 480, 720],
    'mult': [8, 14, 20]
}
