import pandas as pd
import numpy as np

def super_guppy_strategy(data, len1=3, len2=6, len3=9, len4=12, len5=15, len6=18, len7=21,
                         len8=24, len9=27, len10=30, len11=33, len12=36, len13=39, len14=42,
                         len15=45, len16=48, len17=51, len18=54, len19=57, len20=60, len21=63, len22=66, len23=200,
                         use_early_signals=True):
    
    #print(f"Running Super Guppy Strategy on data: {data.head()}")

    if 'Close' not in data.columns:
        raise KeyError("'Close' column not found in the data")

    # Calculate EMAs
    ema1 = data['Close'].ewm(span=len1, adjust=False).mean()
    ema2 = data['Close'].ewm(span=len2, adjust=False).mean()
    ema3 = data['Close'].ewm(span=len3, adjust=False).mean()
    ema4 = data['Close'].ewm(span=len4, adjust=False).mean()
    ema5 = data['Close'].ewm(span=len5, adjust=False).mean()
    ema6 = data['Close'].ewm(span=len6, adjust=False).mean()
    ema7 = data['Close'].ewm(span=len7, adjust=False).mean()
    ema8 = data['Close'].ewm(span=len8, adjust=False).mean()
    ema9 = data['Close'].ewm(span=len9, adjust=False).mean()
    ema10 = data['Close'].ewm(span=len10, adjust=False).mean()
    ema11 = data['Close'].ewm(span=len11, adjust=False).mean()
    ema12 = data['Close'].ewm(span=len12, adjust=False).mean()
    ema13 = data['Close'].ewm(span=len13, adjust=False).mean()
    ema14 = data['Close'].ewm(span=len14, adjust=False).mean()
    ema15 = data['Close'].ewm(span=len15, adjust=False).mean()
    ema16 = data['Close'].ewm(span=len16, adjust=False).mean()
    ema17 = data['Close'].ewm(span=len17, adjust=False).mean()
    ema18 = data['Close'].ewm(span=len18, adjust=False).mean()
    ema19 = data['Close'].ewm(span=len19, adjust=False).mean()
    ema20 = data['Close'].ewm(span=len20, adjust=False).mean()
    ema21 = data['Close'].ewm(span=len21, adjust=False).mean()
    ema22 = data['Close'].ewm(span=len22, adjust=False).mean()
    ema23 = data['Close'].ewm(span=len23, adjust=False).mean()

    # Fast and Slow EMA Color Rules
    colfastL = (ema1 > ema2) & (ema2 > ema3) & (ema3 > ema4) & (ema4 > ema5) & (ema5 > ema6) & (ema6 > ema7)
    colfastS = (ema1 < ema2) & (ema2 < ema3) & (ema3 < ema4) & (ema4 < ema5) & (ema5 < ema6) & (ema6 < ema7)
    
    colslowL = (ema8 > ema9) & (ema9 > ema10) & (ema10 > ema11) & (ema11 > ema12) & (ema12 > ema13) & (ema13 > ema14) & (ema14 > ema15) & (ema15 > ema16) & (ema16 > ema17) & (ema17 > ema18) & (ema18 > ema19) & (ema19 > ema20) & (ema20 > ema21) & (ema21 > ema22)
    colslowS = (ema8 < ema9) & (ema9 < ema10) & (ema10 < ema11) & (ema11 < ema12) & (ema12 < ema13) & (ema13 < ema14) & (ema14 < ema15) & (ema15 < ema16) & (ema16 < ema17) & (ema17 < ema18) & (ema18 < ema19) & (ema19 < ema20) & (ema20 < ema21) & (ema21 < ema22)

    # Signals
    long = ((colslowL.shift() == False) & (colslowL == True)) | ((colslowS == False) & (colslowL == True))

    if use_early_signals:
        entries = long
        exits = ~long
    else:
        open_long = (colslowL) & (colslowL.shift() == False)
        close_long = (colslowL.shift()) & (colslowL == False)
        
        entries = open_long
        exits = close_long

    return entries, exits

param_grid = {
    'len1': [3, 5, 7],
    'len2': [6, 8, 10],
    'len3': [9, 11, 13],
    'len4': [12, 14, 16],
    'len5': [15, 17, 19],
    'len6': [18, 20, 22],
    'len7': [21, 23, 25],
    'len8': [24, 26, 28],
    'len9': [27, 29, 31],
    'len10': [30, 32, 34],
    'len11': [33, 35, 37],
    'len12': [36, 38, 40],
    'len13': [39, 41, 43],
    'len14': [42, 44, 46],
    'len15': [45, 47, 49],
    'len16': [48, 50, 52],
    'len17': [51, 53, 55],
    'len18': [54, 56, 58],
    'len19': [57, 59, 61],
    'len20': [60, 62, 64],
    'len21': [63, 65, 67],
    'len22': [66, 68, 70],
    'len23': [200],
    'use_early_signals': [True, False]
}
