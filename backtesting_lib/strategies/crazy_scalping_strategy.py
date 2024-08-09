import pandas as pd
import pandas_ta as ta
import vectorbt as vbt

def crazy_scalping_strategy(data, tmo_length=7, ama_length=50, ama_multi=2.00):
    """
    Crazy Scalping Strategy - Long Only

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data with columns ['Open', 'High', 'Low', 'Close'].
    - tmo_length (int): TMO Length.
    - ama_length (int): AMA Length.
    - ama_multi (float): Factor for AMA deviation.

    Returns:
    - entries (pd.Series): Long entry signals.
    - exits (pd.Series): Long exit signals.
    """
    
    # TMO calculation
    tmo_src = data['Close']
    tmo = ta.mom(ta.sma(ta.sma(tmo_src, tmo_length), tmo_length), tmo_length)
    
    # AMA calculation
    ama_src = data['Close']
    ama = ta.ema(ama_src, length=ama_length)
    deviation = ta.sma((ama_src - ama).abs(), ama_length) * ama_multi
    upper = ama + deviation
    lower = ama - deviation
    
    # Oscillator state
    cross_high = data['High'] > upper
    cross_low = data['Low'] < lower
    os = pd.Series(0, index=data.index)
    os = os.where(~cross_high, 1).where(~cross_low, 0)
    os = os.ffill()

    # Bull and bear conditions
    bull = (tmo < 0) & (tmo.shift(1) > tmo.shift(2)) & (tmo.shift(2) > tmo.shift(3))
    
    # Long entries and exits
    long_entries = (os == 1) & bull
    long_exits = (os == 0)
    
    return long_entries, long_exits


param_grid = {
    'tmo_length': [5, 7, 10],
    'ama_length': [20, 50, 100],
    'ama_multi': [1.5, 2.0, 2.5]
}
