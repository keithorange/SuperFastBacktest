import pandas as pd
import numpy as np
import pandas_ta as ta

def darvas_box_strategy(data, box_length=5):
    """
    Darvas Box Strategy V2.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data.
    - box_length (int): Length of the box.

    Returns:
    - entries (pd.Series): Buy signals.
    - exits (pd.Series): Sell signals.
    """

    # Calculate Lowest Low and Highest High
    data['LL'] = data['Low'].rolling(window=box_length).min()
    data['HH'] = data['High'].rolling(window=box_length).max()

    # Calculate New High
    data['NH'] = data['High'] > data['HH'].shift(1)

    # Calculate Box conditions
    data['box1'] = data['High'].shift(2) < data['High'].shift(1)

    # Calculate TopBox and BottomBox
    data['TopBox'] = np.where(data['NH'] & data['box1'], data['HH'], np.nan)
    data['BottomBox'] = np.where(data['NH'] & data['box1'], data['LL'], np.nan)

    # Forward fill TopBox and BottomBox
    data['TopBox'] = data['TopBox'].ffill()
    data['BottomBox'] = data['BottomBox'].ffill()

    # Generate entry and exit signals
    entries = (data['Close'] > data['TopBox'].shift(1)).astype(int)
    exits = (data['Close'] < data['BottomBox'].shift(1)).astype(int)

    # Drop unnecessary columns before returning
    data.drop(['LL', 'HH', 'NH', 'box1', 'TopBox', 'BottomBox'], axis=1, inplace=True)

    return entries, exits

param_grid = {
    'box_length': [5, 10, 20]
}
