from scipy import stats
from numba import jit  # Make sure to import jit from numba
import pandas_ta as pta
import pandas as pd
import math
from scipy.stats import linregress
import yfinance as yf
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt
import numpy as np
from numba import jit
from hyperopt import hp

from strategies.helpers import calculate_heikin_ashi
from strategies.exit_helpers import apply_take_profit_ema_entry, apply_trailing_stop_ema

# from .exit_helpers import apply_take_profit, apply_trailing_stop_ema, create_tsl_hyperopt_space
from .helpers import *


import numpy as np
from numba import njit



import numpy as np
import pandas as pd



def greasy_pig_strategy_long(df, ema_period=48, slope_period=20, tsl_params=[(5, 0.5, 12)],
                             take_profit_percentage=10, straightness_threshold=0.8,
                             slope_threshold=0.001, trend_score_window_size=8,
                             trend_score_smoothing_period=5, use_tp=True,
                             regression_period=100, max_deviation_percentage=2,
                             trend_ema_period=30, trend_ema_slope_period=20,
                             trend_ema_threshold=0.5, use_heikin_ashi=False):
    """
    Long strategy implementation.
    """
    # Typecast integer parameters to int
    ema_period = int(ema_period)
    slope_period = int(slope_period)
    take_profit_percentage = int(take_profit_percentage)
    trend_score_window_size = int(trend_score_window_size)
    trend_score_smoothing_period = int(trend_score_smoothing_period)
    regression_period = int(regression_period)
    max_deviation_percentage = int(max_deviation_percentage)
    trend_ema_period = int(trend_ema_period)
    trend_ema_slope_period = int(trend_ema_slope_period)

    closes = df['Close'].values
    n = len(closes)

    # Initialize result arrays
    long_entries = np.zeros(n, dtype=np.bool_)
    long_exits = np.zeros(n, dtype=np.bool_)
    
    # Initialize short entries and exits filled with zeros
    short_entries = np.zeros(n, dtype=np.bool_)
    short_exits = np.zeros(n, dtype=np.bool_)

    regression_line = np.zeros(n)
    dist_from_trend = np.zeros(n)

    # Calculate Heikin Ashi if enabled
    if use_heikin_ashi:
        df = calculate_heikin_ashi(df)

    # Calculate all indicators
    ema = calculate_ema(closes, ema_period)
    straightness_over_time = calculate_stickiness_index(
        ema, window_size=trend_score_window_size, score_ema_period=trend_score_smoothing_period)
    
    slope = calculate_slope(ema, slope_period)

    trend_ema = calculate_ema(closes, trend_ema_period)
    trend_ema_slope = calculate_slope(trend_ema, trend_ema_slope_period)

    # Start from the point where we have all required data
    start_idx = max(regression_period, slope_period,
                    ema_period, trend_score_window_size)

    # Vectorized calculation of linear regression parameters
    slopes, intercepts = calculate_vectorized_regression(closes[start_idx:], regression_period)

    # Create an array of indices for regression calculations
    x_indices = np.arange(regression_period)

    # Calculate regression line and distance from trend in a vectorized manner
    regression_line[start_idx: start_idx + len(slopes)] = slopes * (regression_period - 1) + intercepts
    dist_from_trend[start_idx: start_idx + len(slopes)] = (closes[start_idx: start_idx + len(slopes)] - regression_line[start_idx: start_idx + len(slopes)]) / regression_line[start_idx: start_idx + len(slopes)] * 100

    # Entry logic using vectorized comparison for long entries
    long_entries[start_idx: start_idx + len(slopes)] = (
        (straightness_over_time[start_idx: start_idx + len(slopes)] > straightness_threshold) &
        (dist_from_trend[start_idx: start_idx + len(slopes)] <= max_deviation_percentage) &
        (slope[start_idx: start_idx + len(slopes)] > slope_threshold) &
        (trend_ema_slope[start_idx: start_idx + len(slopes)] > trend_ema_threshold)
    )

    # Calculate exits based on entry signals and trailing stop loss (TSL) parameters for long trades
    long_exits |= apply_trailing_stop_ema(df, long_entries, long_exits, tsl_params=tsl_params)

    if use_tp:
        # Exit based on take profit percentage from entry price for long trades
        long_exits |= apply_take_profit_ema_entry(
            closes, ema,
            long_entries, long_exits, take_profit_percentage)

    return long_entries, long_exits, short_entries, short_exits


def greasy_pig_strategy_short(df, ema_period=48, slope_period=20, tsl_params=[(5, 0.5, 12)],
                              take_profit_percentage=10, straightness_threshold=0.8,
                              slope_threshold=0.001, trend_score_window_size=8,
                              trend_score_smoothing_period=5, use_tp=True,
                              regression_period=100, max_deviation_percentage=2,
                              trend_ema_period=30, trend_ema_slope_period=20,
                              trend_ema_threshold=0.5, use_heikin_ashi=False):
    
    """
    Short strategy implementation.
    
    This function mirrors the long strategy but is tailored for short positions.
    """
        
    # Typecast integer parameters to int (same as in long strategy)
    ema_period = int(ema_period)
    slope_period = int(slope_period)
    take_profit_percentage = int(take_profit_percentage)
    trend_score_window_size = int(trend_score_window_size)
    trend_score_smoothing_period = int(trend_score_smoothing_period)
    regression_period = int(regression_period)
    max_deviation_percentage = int(max_deviation_percentage)
    trend_ema_period = int(trend_ema_period)
    trend_ema_slope_period = int(trend_ema_slope_period)

    closes = df['Close'].values
    n = len(closes)

    # Initialize result arrays
    short_entries = np.zeros(n, dtype=np.bool_)
    short_exits = np.zeros(n, dtype=np.bool_)
    
    # Initialize long entries and exits filled with zeros
    long_entries = np.zeros(n, dtype=np.bool_)
    long_exits = np.zeros(n, dtype=np.bool_)
        
    regression_line_short = np.zeros(n)
    dist_from_trend_short = np.zeros(n)

    # Calculate Heikin Ashi if enabled (same as in long strategy)
    if use_heikin_ashi:
        df = calculate_heikin_ashi(df)

    # Calculate all indicators (same as in long strategy)
    ema_short = calculate_ema(closes, ema_period)
    straightness_over_time_short = calculate_stickiness_index(ema_short, window_size=trend_score_window_size,score_ema_period=trend_score_smoothing_period)
        
    slope_short = calculate_slope(ema_short, slope_period)

    trend_ema_short = calculate_ema(closes, trend_ema_period)
    trend_ema_slope_short = calculate_slope(trend_ema_short,
                                                trend_ema_slope_period)

    # Start from the point where we have all required data
    start_idx_short = max(regression_period,
                            slope_period,
                            ema_period,
                            trend_score_window_size)

    # Vectorized calculation of linear regression parameters for shorts
    slopes_short, intercepts_short =calculate_vectorized_regression(closes[start_idx_short:], regression_period)

    # Create an array of indices for regression calculations (same as in long strategy)
    x_indices_short = np.arange(regression_period)

    # Calculate regression line and distance from trend in a vectorized manner for shorts
    regression_line_short[start_idx_short:start_idx_short + len(slopes_short)] = slopes_short * (regression_period - 1) + intercepts_short

    dist_from_trend_short[start_idx_short:start_idx_short + len(slopes_short)] = (closes[start_idx_short:start_idx_short + len(slopes_short)] - regression_line_short[start_idx_short:start_idx_short + len(slopes_short)]) / regression_line_short[start_idx_short:start_idx_short + len(slopes_short)] * 100

    # Entry logic using vectorized comparison for short entries
    short_entries[start_idx_short:start_idx_short + len(slopes_short)] = ((straightness_over_time_short[start_idx_short:start_idx_short + len(slopes_short)] < -straightness_threshold) & (dist_from_trend_short[start_idx_short:start_idx_short + len(slopes_short)] >= -max_deviation_percentage) & (slope_short[start_idx_short:start_idx_short + len(slopes_short)] < -slope_threshold) & (trend_ema_slope_short[start_idx_short:start_idx_short + len(slopes_short)] < -trend_ema_threshold))

    # Calculate exits based on entry signals and trailing stop loss (TSL) parameters for short trades
    short_exits |= apply_trailing_stop_ema(df,
                                                short_entries,
                                                short_exits,
                                                tsl_params=tsl_params)

    if use_tp:
        # Exit based on take profit percentage from entry price for short trades
        short_exits |= apply_take_profit_ema_entry(
            closes,
            ema_short,
            short_entries,
            short_exits,
            take_profit_percentage)

    
    # Return both entry/exit signals for shorts and longs with appropriate zero-filling.
    return long_entries ,long_exits ,short_entries ,short_exits




    # Example usage:
# Assuming normalized_data is prepared and strategy_params is defined.
# long_entries ,long_exits ,short_entries ,short_exits =
# greasy_pig_strategy_long(normalized_data ,**strategy_params )
# or 
# greasy_pig_strategy(short_data ,**strategy_params )


# def greasy_pig_strategy(df, ema_period=48, slope_period=20, tsl_params=[(5, 0.5, 12)],
#                         take_profit_percentage=10, straightness_threshold=0.8,
#                         slope_threshold=0.001, trend_score_window_size=8, trend_score_smoothing_period=5,
#                         use_tp=True, regression_period=100, max_deviation_percentage=2,
#                         trend_ema_period=30, trend_ema_slope_period=20,
#                         trend_ema_threshold=0.5, use_heikin_ashi=False):

#     # Typecast integer parameters to int
#     ema_period = int(ema_period)
#     slope_period = int(slope_period)
#     take_profit_percentage = int(take_profit_percentage)
#     trend_score_window_size = int(trend_score_window_size)
#     trend_score_smoothing_period = int(trend_score_smoothing_period)
#     regression_period = int(regression_period)
#     max_deviation_percentage = int(max_deviation_percentage)
#     trend_ema_period = int(trend_ema_period)
#     trend_ema_slope_period = int(trend_ema_slope_period)

#     closes = df['Close'].values
#     n = len(closes)

#     # Initialize result arrays
#     entries = np.zeros(n, dtype=np.bool_)
#     exits = np.zeros(n, dtype=np.bool_)
#     regression_line = np.zeros(n)
#     dist_from_trend = np.zeros(n)

#     # Calculate Heikin Ashi if enabled
#     if use_heikin_ashi:
#         df = calculate_heikin_ashi(df)

#     # Calculate all indicators
#     ema = calculate_ema(closes, ema_period)
#     straightness_over_time = calculate_stickiness_index(
#         ema, window_size=trend_score_window_size, score_ema_period=trend_score_smoothing_period)
#     slope = calculate_slope(ema, slope_period)

#     trend_ema = calculate_ema(closes, trend_ema_period)
#     trend_ema_slope = calculate_slope(trend_ema, trend_ema_slope_period)

#     # Start from the point where we have all required data
#     start_idx = max(regression_period, slope_period,
#                     ema_period, trend_score_window_size)

#     # Vectorized calculation of linear regression parameters
#     slopes, intercepts = calculate_vectorized_regression(closes[start_idx:], regression_period)

#     # Create an array of indices for regression calculations
#     x_indices = np.arange(regression_period)

#     # Calculate regression line and distance from trend in a vectorized manner
#     regression_line[start_idx: start_idx + len(slopes)] = slopes * (regression_period - 1) + intercepts
#     dist_from_trend[start_idx: start_idx + len(slopes)] = (closes[start_idx: start_idx + len(slopes)] - regression_line[start_idx: start_idx + len(slopes)]) / regression_line[start_idx: start_idx + len(slopes)] * 100

#     # Entry logic using vectorized comparison
#     entries[start_idx: start_idx + len(slopes)] = (
#         (straightness_over_time[start_idx: start_idx + len(slopes)] > straightness_threshold) &
#         (dist_from_trend[start_idx: start_idx + len(slopes)] <= max_deviation_percentage) &
#         (slope[start_idx: start_idx + len(slopes)] > slope_threshold) &
#         (trend_ema_slope[start_idx: start_idx + len(slopes)] > trend_ema_threshold)
#     )

#     # Calculate exits based on entry signals and trailing stop loss (TSL) parameters
#     exits |= apply_trailing_stop_ema(df, entries, exits, tsl_params=tsl_params)
    
#     if use_tp:
#         # Exit based on take profit percentage from entry price
#         exits |= apply_take_profit_ema_entry(
#             closes, ema,
#             entries, exits, take_profit_percentage)

#     return entries, exits

def calculate_vectorized_regression(y_data, window_size):
    """
    Calculate slopes and intercepts for multiple linear regressions over sliding windows.

    Parameters:
        y_data (np.ndarray): Array of closing prices.
        window_size (int): Size of the sliding window for the linear regression.

    Returns:
        slopes (np.ndarray): Array of slopes for each window.
        intercepts (np.ndarray): Array of intercepts for each window.
    """
    
    n_windows = len(y_data) - window_size + 1
    x_indices = np.arange(window_size)

    # Precompute sums for vectorized regression calculation
    x_sum = np.sum(x_indices)  # This is constant for all windows
    x_squared_sum = np.sum(x_indices ** 2)  # This is also constant

    # Create a rolling window over closes to get y values
    y_windows = np.lib.stride_tricks.sliding_window_view(y_data, window_shape=(window_size,))
    
    # Calculate means for y values in each window
    y_means = np.mean(y_windows, axis=1)

    # Calculate slopes using vectorized operations
    slopes_numerator = (window_size * np.sum(y_windows * x_indices[None, :], axis=1)) - (x_sum * np.sum(y_windows, axis=1))
    
    slopes_denominator = (window_size * x_squared_sum) - (x_sum ** 2)

    slopes = slopes_numerator / slopes_denominator
    
    # Calculate intercepts
    intercepts = y_means - slopes * (window_size - 1) / 2  # Mean of x is (window_size - 1)/2

    return slopes, intercepts



# # slow fix
# def greasy_pig_strategy(df, ema_period=48, slope_period=20, tsl_params=[(5, 0.5, 12)],
#                         take_profit_percentage=10, straightness_threshold=0.8,
#                         slope_threshold=0.001, trend_score_window_size=8, trend_score_smoothing_period=5, use_tp=True,
#                         regression_period=100, max_deviation_percentage=2, trend_ema_period=30, trend_ema_slope_period=20, trend_ema_threshold=0.5,
#                         use_heikin_ashi= False,
#                         ):
    
#     # Typecast integer parameters to int
#     ema_period = int(ema_period)
#     slope_period = int(slope_period)
#     take_profit_percentage = int(take_profit_percentage)
#     trend_score_window_size = int(trend_score_window_size)
#     trend_score_smoothing_period = int(trend_score_smoothing_period)
#     regression_period = int(regression_period)
#     max_deviation_percentage = int(max_deviation_percentage)
#     trend_ema_period = int(trend_ema_period)
#     trend_ema_slope_period = int(trend_ema_slope_period)
    
#     closes = df['Close'].values
#     highs = df['High'].values
#     n = len(closes)

#     # Initialize result arrays
#     entries = np.zeros(n, dtype=np.bool_)
#     regression_line = np.zeros(n)
#     dist_from_trend = np.zeros(n)

#     # Calculate Heikin Ashi if enabled
#     if use_heikin_ashi:
#         df = calculate_heikin_ashi(df)

#     # Calculate all indicators
#     ema = calculate_ema(closes, ema_period)
#     straightness_over_time = calculate_stickiness_index(
#         ema, window_size=trend_score_window_size, score_ema_period=trend_score_smoothing_period)
#     slope = calculate_slope(ema, slope_period)

#     trend_ema = calculate_ema(closes, trend_ema_period)
#     trend_ema_slope = calculate_slope(trend_ema, trend_ema_slope_period)

#     # Start from the point where we have all required data
#     start_idx = max(regression_period, slope_period,
#                     ema_period, trend_score_window_size)

#     # Main strategy loop
#     for i in range(start_idx, n):
#         # Calculate regression for current window
#         window_data = closes[i-regression_period:i]
#         x = np.arange(regression_period)
#         slope_reg, intercept = manual_linear_regression(x, window_data)

#         # Current regression value and deviation
#         regression_line[i] = slope_reg * (regression_period - 1) + intercept
#         dist_from_trend[i] = (closes[i] - regression_line[i]
#                               ) / regression_line[i] * 100

#         # Entry logic
#         if (
#             straightness_over_time[i] > straightness_threshold and
#             dist_from_trend[i] <= max_deviation_percentage and
#             slope[i] > slope_threshold and
#             trend_ema_slope[i] > trend_ema_threshold
#         ):
#             entries[i] = True

#     # Calculate exits
#     exits = np.zeros_like(entries)
#     exits |= apply_trailing_stop_ema(df, entries, exits, tsl_params=tsl_params)
#     if use_tp:

#         # NOTE: entry based on ema line, exit on close price
#         exits |= apply_take_profit_ema_entry(
#             closes, ema,
#             entries, exits, take_profit_percentage)

#     return entries, exits


# # Parameter space for hyperoptimization
# strategy_name = 'greasy_pig_strategy'
# param_space = {
#     'ema_period': hp.quniform('ema_period', 6, 60, 1),
#     'slope_period': hp.quniform('slope_period', 5, 50, 1),
#     'straightness_threshold': hp.uniform('straightness_threshold', 0.0, 1.0),
#     # Corrected range
#     'slope_threshold': hp.uniform('slope_threshold', -1.0, 1.0),
    # 'take_profit_percentage': hp.uniform('take_profit_percentage', 0.2, 5),

#     'trend_score_window_size': hp.quniform('trend_score_window_size', 4, 60, 1),
#     'trend_score_smoothing_period': hp.quniform('trend_score_smoothing_period', 4, 20, 1),
# 'max_deviation_percentage': hp.uniform('max_deviation_percentage', -2, 3),
# 'use_tp':hp.choice('use_tp', [True, False]),
#     'tsl_params': create_tsl_hyperopt_space(),
# }


# TEST PLOT FNS
if __name__ == "__main__":

    # Example usage (ensure you fetch data correctly before calling this function)
    # prices = ... (your price data here)
    symbol = np.random.choice(
        ['BTC-USD', 'ETH-USD', 'GC=F', 'SI=F', 'EURUSD=X'])
    data = yf.download(symbol, start='2024-01-01', interval='1h')
    chunks = []

    # Get 9 random 500-point chunks
    for _ in range(9):
        if len(data) > 500:
            start_idx = np.random.randint(0, len(data) - 500)
            chunk = data['Close'][start_idx:start_idx + 500]
            chunks.append((f"{symbol}_{start_idx}", chunk))

    # Plotting
    fig, axs = plt.subplots(3, 3, figsize=(20, 20))
    axs = axs.ravel()

    for idx, (chunk_name, prices) in enumerate(chunks):
        if idx >= 9:
            break

        # Normalize prices
        prices = (prices - prices.mean()) / prices.std()

        # Calculate trend scores
        trend_scores = calculate_trend_scores(prices.values)

        # Plotting results
        ax = axs[idx]
        ax.plot(prices.values, 'gray', alpha=0.3, label='Price')

        ax_straight = ax.twinx()
        ax_straight.plot(trend_scores, 'red', alpha=0.3,
                         label='Smoothed Trend Scores', linewidth=1)

        if idx == 0:
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax_straight.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2,
                      loc='upper left', fontsize=8)

    plt.tight_layout()
    plt.show()
