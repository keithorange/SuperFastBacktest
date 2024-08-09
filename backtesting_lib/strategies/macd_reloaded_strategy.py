import pandas as pd
import numpy as np
import pandas_ta as ta

def macd_reloaded_strategy(data, length=12, length1=26, length2=9, T3a1=0.7, mav='VAR'):
    """
    Implements the MACD ReLoaded Strategy.

    Parameters:
    - data (pd.DataFrame): DataFrame containing OHLC data
    - length (int): Short moving average length
    - length1 (int): Long moving average length
    - length2 (int): Trigger length
    - T3a1 (float): TILLSON T3 Volume Factor
    - mav (str): Moving average type

    Returns:
    - entries (pd.Series): Buy signals
    - exits (pd.Series): Sell signals
    """

    def get_ma(data, length, mav):
        if mav == 'SMA':
            return data.rolling(window=length).mean()
        elif mav == 'EMA':
            return data.ewm(span=length, adjust=False).mean()
        elif mav == 'WMA':
            weights = np.arange(1, length + 1)
            return data.rolling(window=length).apply(lambda prices: np.dot(prices, weights) / weights.sum(), raw=True)
        elif mav == 'DEMA':
            ema = data.ewm(span=length, adjust=False).mean()
            dema = 2 * ema - ema.ewm(span=length, adjust=False).mean()
            return dema
        elif mav == 'TMA':
            return data.rolling(window=length).mean().rolling(window=length).mean()
        elif mav == 'VAR':
            valpha = 2 / (length + 1)
            vud1 = data.diff().apply(lambda x: x if x > 0 else 0)
            vdd1 = data.diff().apply(lambda x: -x if x < 0 else 0)
            vUD = vud1.rolling(9).sum()
            vDD = vdd1.rolling(9).sum()
            vCMO = (vUD - vDD) / (vUD + vDD)
            var = pd.Series(0, index=data.index)
            var = valpha * abs(vCMO) * data + (1 - valpha * abs(vCMO)) * var.shift(1)
            return var
        elif mav == 'WWMA':
            wwalpha = 1 / length
            wwma = pd.Series(0, index=data.index)
            wwma = wwalpha * data + (1 - wwalpha) * wwma.shift(1)
            return wwma
        elif mav == 'ZLEMA':
            zxLag = length // 2
            zxEMAData = data + (data - data.shift(zxLag))
            return zxEMAData.ewm(span=length, adjust=False).mean()
        elif mav == 'TSF':
            lrc = data.rolling(window=length).apply(lambda x: np.polyval(np.polyfit(range(length), x, 1), length - 1))
            lrs = lrc - lrc.shift(1)
            return lrc + lrs
        elif mav == 'HULL':
            half_length = length // 2
            sqrt_length = int(np.sqrt(length))
            return data.rolling(window=half_length).mean().apply(lambda x: 2 * x - data.rolling(window=length).mean()).rolling(window=sqrt_length).mean()
        elif mav == 'TILL':
            t3e1 = data.ewm(span=length, adjust=False).mean()
            t3e2 = t3e1.ewm(span=length, adjust=False).mean()
            t3e3 = t3e2.ewm(span=length, adjust=False).mean()
            t3e4 = t3e3.ewm(span=length, adjust=False).mean()
            t3e5 = t3e4.ewm(span=length, adjust=False).mean()
            t3e6 = t3e5.ewm(span=length, adjust=False).mean()
            t3c1 = -T3a1 ** 3
            t3c2 = 3 * T3a1 ** 2 + 3 * T3a1 ** 3
            t3c3 = -6 * T3a1 ** 2 - 3 * T3a1 - 3 * T3a1 ** 3
            t3c4 = 1 + 3 * T3a1 + T3a1 ** 3 + 3 * T3a1 ** 2
            return t3c1 * t3e6 + t3c2 * t3e5 + t3c3 * t3e4 + t3c4 * t3e3
        return data

    MA12 = get_ma(data['Close'], length, mav)
    MA26 = get_ma(data['Close'], length1, mav)

    src2 = MA12 - MA26
    MATR = get_ma(src2, length2, mav)
    hist = src2 - MATR

    # Calculate buy and sell signals
    buy_signal = (hist > 0) & (hist.shift(1) <= 0)
    sell_signal = (hist < 0) & (hist.shift(1) >= 0)

    # Ensure the length of entries and exits matches the input data length
    entries = pd.Series(buy_signal, index=data.index)
    exits = pd.Series(sell_signal, index=data.index)

    return entries, exits

param_grid = {
    'length': [12, 20],
    'length1': [26, 35],
    'length2': [9, 15],
    'T3a1': [0.7, 0.9],
    'mav': ['SMA', 'EMA', 'WMA', 'DEMA', 'TMA', 'VAR', 'WWMA', 'ZLEMA', 'TSF', 'HULL', 'TILL'],
}
