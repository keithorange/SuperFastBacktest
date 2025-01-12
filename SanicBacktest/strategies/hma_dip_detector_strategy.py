
import pandas as pd
import numpy as np
import pandas_ta as pta
from typing import Tuple

from .helpers import *
from .exit_helpers import apply_take_profit_ema_entry, apply_take_profit_prices, apply_trailing_stop_ema

import pandas as pd
import numpy as np
import pandas_ta as pta
from typing import Tuple

from .helpers import *
from .exit_helpers import apply_trailing_stop_ema




def hma_dip_detector_strategy(
    data: pd.DataFrame,
    long_ma_period: int = 30,
    short_ma_period: int = 6,
    short_ma_type: str = "HMA",
    slope_period: int = 6,
    accel_period: int = 6,
    dip_threshold: float = 0,
    hma_slope_min_threshold: float = -0.15,
    hma_slope_max_threshold: float = 0.15,
    hma_accel_threshold: float = 0.0,
    use_heikin_ashi: bool = True,
    tsl_ema_period: int = 5,
    tsl_params: list = [(5, 0), (0.5, 1), (0.1, 3)],
    use_rsi_filter: bool = False,
    rsi_period: int = 14,
    rsi_oversold: float = 30,
    use_bb_squeeze: bool = False,
    bb_length: int = 20,
    bb_std: float = 2.0,
    bb_squeeze_threshold: float = 0.1,
    c1: float = 1.0,
    use_tp: bool = False,
    take_profit_percentage: float = 5.0,
) -> Tuple[pd.Series, pd.Series]:
    
    # Cast integers
    long_ma_period, short_ma_period, slope_period, accel_period, tsl_ema_period, rsi_period, bb_length = map(
        int, (long_ma_period, short_ma_period, slope_period, accel_period, tsl_ema_period, rsi_period, bb_length))

    # Create copy and calculate base data
    df = data.copy()
    if use_heikin_ashi:
        df = calculate_heikin_ashi(df)

    # Vectorized mean price calculation
    df['mean_price'] = df[['Open', 'High', 'Low', 'Close']].mean(axis=1)
    
    # Vectorized MA calculations
    df['long_ma'] = pta.ema(df['mean_price'], length=long_ma_period)
    df['short_ma'] = pta.hma(df['mean_price'], length=short_ma_period) if short_ma_type == "HMA" else pta.ema(df['mean_price'], length=short_ma_period)

    # Vectorized dip depth calculation
    dip_depth = (df['long_ma'] - df['short_ma']) / df['long_ma'] * 100
    df['dip_depth_normalized'] = one_to_one_slope(dip_depth.values, slope_period)
    
    # Vectorized slope and acceleration
    df['short_ma_slope'] = one_to_one_slope(df['short_ma'].values, slope_period)
    df['short_ma_accel'] = one_to_one_slope(df['short_ma_slope'].values, accel_period)

    # Vectorized RSI condition
    rsi_condition = pd.Series(True, index=df.index)
    if use_rsi_filter:
        df['rsi'] = pta.rsi(df['Close'], length=rsi_period)
        rsi_condition = df['rsi'] < rsi_oversold

    # Vectorized BB squeeze condition
    bb_squeeze_condition = pd.Series(True, index=df.index)
    if use_bb_squeeze:
        bbands = pta.bbands(df['Close'], length=bb_length, std=bb_std)
        squeeze_value = (bbands[f'BBU_{bb_length}_{bb_std}'] - bbands[f'BBL_{bb_length}_{bb_std}']) / df['Close']
        squeeze_normalized = squeeze_value.rolling(bb_length).apply(
            lambda x: one_to_one_slope(x.values, len(x))
        )
        bb_squeeze_condition = squeeze_normalized < bb_squeeze_threshold

    # Vectorized entry conditions
    entries = (
        (df['short_ma'] < df['long_ma'] * c1) &
        (df['dip_depth_normalized'] > dip_threshold) &
        (df['short_ma_slope'] >= hma_slope_min_threshold) &
        (df['short_ma_slope'] <= hma_slope_max_threshold) &
        (df['short_ma_accel'] > hma_accel_threshold) &
        rsi_condition &
        bb_squeeze_condition
    )

    # Ensure entries start after all indicators are valid
    start_idx = max(long_ma_period, short_ma_period, slope_period, accel_period)
    entries.iloc[:start_idx] = False

    # Calculate exits
    exits = pd.Series(False, index=df.index)
    exits = apply_trailing_stop_ema(data, entries, exits, tsl_params=tsl_params)
    
    if use_tp:
        exits |= apply_take_profit_ema_entry(
            df['Close'], 
            df['short_ma'],
            entries, 
            exits, 
            take_profit_percentage
        )

    return entries, exits

# # not vectorized (slow)
# def hma_dip_detector_strategy(
#     data: pd.DataFrame,
#     long_ma_period: int = 30,
#     short_ma_period: int = 6,
#     short_ma_type: str = "HMA",
#     slope_period: int = 6,
#     accel_period: int = 6,
#     dip_threshold: float = 0,
#     hma_slope_min_threshold: float = -0.15,  # Now in -1 to 1 range
#     hma_slope_max_threshold: float = 0.15,   # Now in -1 to 1 range
#     hma_accel_threshold: float = 0.0,        # Now in -1 to 1 range
#     use_heikin_ashi: bool = True,
#     tsl_ema_period: int = 5,
#     tsl_params: list = [(5, 0), (0.5, 1), (0.1, 3)],
#     use_rsi_filter: bool = False,
#     rsi_period: int = 14,
#     rsi_oversold: float = 30,
#     use_bb_squeeze: bool = False,
#     bb_length: int = 20,
#     bb_std: float = 2.0,
#     bb_squeeze_threshold: float = 0.1,
#     c1: float = 1.0,

#     use_tp:bool = False,
#     take_profit_percentage: float = 5.0,
# ) -> Tuple[pd.Series, pd.Series]:

#     # typecast
#     long_ma_period, short_ma_period, slope_period, accel_period, tsl_ema_period, rsi_period, bb_length = map(
#         int, (long_ma_period, short_ma_period, slope_period, accel_period, tsl_ema_period, rsi_period, bb_length))

#     # Create copy of data for calculations
#     df = data.copy()
#     entries = pd.Series(False, index=df.index)

#     # Calculate Heikin Ashi if enabled
#     if use_heikin_ashi:
#         df = calculate_heikin_ashi(df)

#     # Calculate mean price
#     df['mean_price'] = df[['Open', 'High', 'Low', 'Close']].mean(axis=1)

#     # Calculate moving averages
#     df['long_ma'] = pta.ema(df['mean_price'], length=long_ma_period)
#     if short_ma_type == "HMA":
#         df['short_ma'] = pta.hma(df['mean_price'], length=short_ma_period)
#     else:
#         df['short_ma'] = pta.ema(df['mean_price'], length=short_ma_period)

#     # Calculate dip depth using one_to_one normalization
#     dip_depth = (df['long_ma'] - df['short_ma']) / df['long_ma'] * 100
#     df['dip_depth_normalized'] = one_to_one_slope(dip_depth.values, slope_period)

#     # Calculate slope using our normalized method
#     df['short_ma_slope'] = one_to_one_slope(df['short_ma'].values, slope_period)

#     # Calculate acceleration using normalized slope
#     df['short_ma_accel'] = one_to_one_slope(df['short_ma_slope'].values, accel_period)

#     # Start index for calculations
#     start_idx = max(long_ma_period, short_ma_period, slope_period, accel_period)

#     # Main loop for signal generation
#     for i in range(start_idx, len(df)):
#         # RSI filter
#         if use_rsi_filter:
#             df['rsi'] = pta.rsi(df['Close'], length=rsi_period)
#             rsi_condition = df['rsi'].iloc[i] < rsi_oversold
#         else:
#             rsi_condition = True

#         # BB squeeze calculation
#         if use_bb_squeeze:
#             bbands = pta.bbands(df['Close'], length=bb_length, std=bb_std)
#             squeeze_value = (bbands[f'BBU_{bb_length}_{bb_std}'] - 
#                         bbands[f'BBL_{bb_length}_{bb_std}']) / df['Close']
#             squeeze_normalized = pd.Series([one_to_one_slope(squeeze_value.values[max(0, j-bb_length):j+1], bb_length) 
#                                             for j in range(len(squeeze_value))])
#             bb_squeeze_condition = squeeze_normalized.iloc[i] < bb_squeeze_threshold
#         else:
#             bb_squeeze_condition = True

#         # Entry logic
#         if (df['short_ma'].iloc[i] < df['long_ma'].iloc[i] * c1 and
#             df['dip_depth_normalized'].iloc[i] > dip_threshold and
#             df['short_ma_slope'].iloc[i] >= hma_slope_min_threshold and
#             df['short_ma_slope'].iloc[i] <= hma_slope_max_threshold and
#             df['short_ma_accel'].iloc[i] > hma_accel_threshold and
#             rsi_condition and
#             bb_squeeze_condition):
#             entries.iloc[i] = True

#     # Calculate exits after all entries determined
#     exits = pd.Series(False, index=df.index)
#     exits = apply_trailing_stop_ema(
#         data, entries, exits, tsl_params=tsl_params
#     )
#     if use_tp:
#         # # NOTE: entry based on ema line, exit on close price
#         # exits |= apply_take_profit_prices(df['Close'], entries, exits, take_profit_percentage)

#         # Version: exit on EMA!
#         exits |= apply_take_profit_ema_entry(
#             df['Close'], df['short_ma'], # use distance between short ma to close price for TP calculations
#             entries, exits, take_profit_percentage)


#     return entries, exits


# # Updated parameter space for hyperparameter optimization would follow here...

#     # # Updated parameter space
#     # strategy_name = 'hma_dip_detector_strategy'
#     # param_space = {
#     #     'long_ma_period': hp.quniform('long_ma_period', 20, 200, 1),
#     #     'short_ma_period': hp.quniform('short_ma_period', 4, 30, 1),
#     #     'short_ma_type': hp.choice('short_ma_type', ['HMA', 'EMA']),
#     #     'slope_period': hp.quniform('slope_period', 3, 80, 1),
#     #     'accel_period': hp.quniform('accel_period', 3, 80, 1),
#     #     'dip_threshold': hp.uniform('dip_threshold', -1.0, 1.0),
#     #     'hma_slope_min_threshold': hp.uniform('hma_slope_min_threshold', -1.0, 1.0),
#     #     'hma_slope_max_threshold': hp.uniform('hma_slope_max_threshold', -1.0, 1.0),
#     #     'hma_accel_threshold': hp.uniform('hma_accel_threshold', -1.0, 1.0),
#     #     'use_heikin_ashi': hp.choice('use_heikin_ashi', [True, False]),
#     #     'tsl_ema_period': hp.quniform('tsl_ema_period', 3, 9, 1),
#     #     'use_rsi_filter': hp.choice('use_rsi_filter', [True, False]),
#     #     'rsi_period': hp.quniform('rsi_period', 7, 50, 1),
#     #     'rsi_oversold': hp.uniform('rsi_oversold', 5, 50),
#     #     'use_bb_squeeze': hp.choice('use_bb_squeeze', [True, False]),
#     #     'bb_length': hp.quniform('bb_length', 6, 50, 1),
#     #     'bb_std': hp.uniform('bb_std', 1.0, 3.0),
#     #     'bb_squeeze_threshold': hp.uniform('bb_squeeze_threshold', 0.00, 0.5),
#     #     'tsl_params': create_tsl_hyperopt_space(),
#     # 'c1': hp.uniform('c1', 0.1, 4.0),

#     # }


# def check_constraints(params, verbose=False):
#     """Check all constraints for the given parameters."""
#     if verbose:
#         print(f"Checking constraints for params: {params}")

#     # Ensure hma_slope_max_threshold > hma_slope_min_threshold
#     if params['hma_slope_max_threshold'] <= params['hma_slope_min_threshold']:
#         if verbose:
#             print("hma_slope_max_threshold must be greater than hma_slope_min_threshold")
#         return {'loss': float('inf'), 'status': 'fail'}

#     # Ensure short_ma_period < long_ma_period
#     if params['short_ma_period'] >= params['long_ma_period']:
#         if verbose:
#             print("short_ma_period must be less than long_ma_period")
#         return {'loss': float('inf'), 'status': 'fail'}

#     return None
