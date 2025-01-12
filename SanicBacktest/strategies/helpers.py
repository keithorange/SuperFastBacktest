
from numba import njit
import numpy as np
import pandas as pd

from numba import jit

import numpy as np



#@njit
def one_to_one_slope(data, period):
    """ Calculate normalized slope where: 
    -1.0 = straight down vertical (|)
    -0.5 = diagonal down (\\) at 45 degrees
    0.0 = flat horizontal (-)
    0.5 = diagonal up (/) at 45 degrees
    1.0 = straight up vertical (|)
    """
    period = int(period)
    n = len(data)

    if n < period:
        return 0.0

    # Get the window we'll work with
    start_idx = max(0, n - period)
    window = data[start_idx:]
    n_window = len(window)

    # Create x values
    x = np.arange(n_window)

    # Calculate means
    x_mean = (n_window - 1) / 2  # Simplified mean of arange
    y_mean = np.mean(window)

    # Calculate slope
    x_diff = x - x_mean
    y_diff = window - y_mean
    numerator = np.sum(x_diff * y_diff)
    denominator = np.sum(x_diff ** 2)

    if denominator == 0:
        return 0.0

    slope = numerator / denominator

    # Convert to angle and normalize
    angle = np.arctan(slope)
    normalized_slope = angle / (np.pi/2)

    # Clip to ensure we're in [-1, 1] range
    # Use np.minimum and np.maximum instead of np.clip
    return np.maximum(-1.0, np.minimum(normalized_slope, 1.0))





# Ensure all helper functions are also optimized with #@njit
#@njit
def hull_moving_average(data, period):
    """Calculate Hull Moving Average (HMA)."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    half_period = period // 2
    sqrt_period = int(np.sqrt(period))

    wma_half = weighted_moving_average(data, half_period)
    wma_full = weighted_moving_average(data, period)

    hma = 2 * wma_half - wma_full
    hma_final = weighted_moving_average(hma, sqrt_period)

    return hma_final


#@njit
def weighted_moving_average(data: np.ndarray, period: int) -> np.ndarray:
    """Calculate Weighted Moving Average (WMA)."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    weights = np.arange(1, period + 1)  # Weights are 1, 2, ..., period
    wma = np.convolve(data, weights[::-1] / weights.sum(), mode='valid')

    wma_full = np.full(len(data), np.nan)  # Initialize with NaN
    wma_full[period - 1:] = wma  # Fill in the valid part

    return wma_full


#@njit
def calculate_ema(prices, period):
    """Calculate Exponential Moving Average (EMA)."""
    alpha = 2 / (period + 1)
    ema = np.zeros_like(prices)

    ema[0] = prices[0]

    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]

    return ema


#@njit
def manual_linear_regression(x, y):
    """Perform linear regression and return slope and intercept."""
    n = len(x)

    if n == 0:
        return 0.0, 0.0  # Avoid division by zero

    x_mean = np.mean(x)
    y_mean = np.mean(y)

    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return 0.0, y_mean  # If all x values are the same

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    return slope, intercept


#@njit
def calculate_slope(ema, period):
    n = len(ema)
    x = np.arange(period)
    x_mean = np.mean(x)
    x_diff = x - x_mean
    x_diff_sq_sum = np.sum(x_diff ** 2)

    y = np.lib.stride_tricks.sliding_window_view(ema, period)
    y_mean = np.mean(y, axis=1)
    slope = np.sum(
        x_diff * (y - y_mean[:, np.newaxis]), axis=1) / x_diff_sq_sum

    return np.pad(slope, (period - 1, 0), mode='constant')


def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Heikin Ashi candles from a DataFrame containing OHLC data.

    Parameters:
    - df (pd.DataFrame): DataFrame containing 'Open', 'High', 'Low', 'Close' columns.

    Returns:
    - pd.DataFrame: DataFrame containing Heikin Ashi 'Open', 'High', 'Low', and 'Close'.
    """
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
    ha_high = df[['High', 'Open', 'Close']].max(axis=1)
    ha_low = df[['Low', 'Open', 'Close']].min(axis=1)

    return pd.DataFrame({
        'Open': ha_open,
        'High': ha_high,
        'Low': ha_low,
        'Close': ha_close
    }, index=df.index)


#@njit
def calculate_ema(prices, period):
    alpha = 2 / (period + 1)
    ema = np.zeros_like(prices)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
    return ema



def calculate_wma(data, period):
    weights = np.arange(1, period + 1)
    wma = np.zeros_like(data)
    for i in range(period - 1, len(data)):
        wma[i] = np.sum(data[i - period + 1 : i + 1] * weights) / np.sum(weights)
    return wma

#@njit
def calculate_hma(prices, period):
    sqrt_period = int(np.sqrt(period))
    
    wma1 = calculate_wma(prices, period // 2)
    wma2 = calculate_wma(prices, period)
    
    diff = 2 * wma1 - wma2
    hma = calculate_wma(diff, sqrt_period)
    
    return hma


#@njit
def manual_linear_regression(x, y):
    """Perform linear regression and return slope and intercept."""
    n = len(x)
    if n == 0:
        return 0.0, 0.0  # Avoid division by zero

    x_mean = np.mean(x)
    y_mean = np.mean(y)

    # Calculate the slope (m) and intercept (b)
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return 0.0, y_mean  # If all x values are the same

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


#@njit
def weighted_moving_average(data: np.ndarray, period: int) -> np.ndarray:
    """Calculate Weighted Moving Average (WMA)."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    weights = np.arange(1, period + 1)  # Weights are 1, 2, ..., period
    # Reverse weights for convolution
    wma = np.convolve(data, weights[::-1] / weights.sum(), mode='valid')
    wma_full = np.full(len(data), np.nan)  # Initialize with NaN
    wma_full[period - 1:] = wma  # Fill in the valid part

    return wma_full


#@njit
def hull_moving_average(data: np.ndarray, period: int) -> np.ndarray:
    """Calculate Hull Moving Average (HMA)."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    half_period = period // 2
    sqrt_period = int(np.sqrt(period))

    # Calculate WMA for half and full periods
    wma_half = weighted_moving_average(data, half_period)
    wma_full = weighted_moving_average(data, period)

    # Calculate HMA
    hma = 2 * wma_half - wma_full
    hma_final = weighted_moving_average(
        hma, sqrt_period)  # WMA of the difference

    return hma_final


#@njit
def calculate_stickiness_index(data: np.ndarray, window_size: int = 10, short_hma_period: int = 5, score_ema_period: int = 4) -> np.ndarray:
    """
    Calculates the stickiness index based on the area between the Short Hull Moving Average (HMA)
    and the linear regression of recent price data.

    Parameters:
    - data (np.ndarray): Array of price data.
    - window_size (int): The size of the window for linear regression.
    - short_hma_period (int): The period for calculating the Short HMA.
    - score_ema_period (int): The period for applying EMA smoothing to the scores.

    Returns:
    - np.ndarray: Normalized stickiness index between 0 and 1.
    """

    n = len(data)
    if n < window_size:
        # Return an array of zeros for insufficient data
        return np.full(n, 0.0)

    # Calculate Short HMA
    short_hma = hull_moving_average(data, short_hma_period)

    # Initialize scores array
    scores = np.zeros(n)

    # Calculate scores based on area between short HMA and linear regression
    for i in range(window_size - 1, n):
        # Define current window of data using short HMA
        window_data = short_hma[i - window_size + 1:i + 1]
        x = np.arange(window_size)

        # Skip iteration if there are NaN values
        if np.any(np.isnan(window_data)):
            continue

        # Perform manual linear regression on current window
        slope, intercept = manual_linear_regression(x, window_data)

        # Calculate predicted values from linear regression
        predicted_values = slope * x + intercept

        # Calculate absolute area between short HMA and linear regression line over the window
        area_between = np.sum(np.abs(predicted_values - window_data))

        # Assign the area to scores (ensuring it is non-negative)
        scores[i] = area_between

    # Normalize using just the median for a more direct scale
    non_zero_scores = scores[scores > 0]

    if len(non_zero_scores) > 0:
        median_score = np.median(non_zero_scores)
        normalized_scores = np.zeros_like(scores)
        mask = scores > 0
        normalized_scores[mask] = non_zero_scores / median_score
    else:
        normalized_scores = scores

    # Apply manual EMA smoothing
    smoothed_scores = calculate_ema(normalized_scores, score_ema_period)

    # Invert scores using 1 - x method to reflect stickiness
    final_scores = 1 - smoothed_scores

    return final_scores

# TODO: NOT used here ! can be! tells the overall Pigness stickiness of a stock, can be used to classify!


#@njit
def calculate_mean_stickiness(data: np.ndarray, window_size: int = 10, short_hma_period: int = 5, score_ema_period: int = 4, period: int = -1) -> float:
    """
    Calculates the mean stickiness index over a specified period.

    Parameters:
    - data (np.ndarray): Array of price data.
    - window_size (int): The size of the window for linear regression.
    - short_hma_period (int): The period for calculating the Short HMA.
    - score_ema_period (int): The period for applying EMA smoothing to the scores.
    - period (int): The number of recent candles to consider. Default is -1, which uses all available data.

    Returns:
    - float: Mean stickiness index over the specified period.
    """

    stickiness_index = calculate_stickiness_index(
        data, window_size, short_hma_period, score_ema_period)

    if period <= 0 or period > len(stickiness_index):
        period = len(stickiness_index)

    return np.mean(stickiness_index[-period:])


#@njit
def calculate_slope(ema, period):
    n = len(ema)
    slope = np.zeros(n)
    x = np.arange(period)
    x_mean = np.mean(x)
    x_diff = x - x_mean
    x_diff_sq_sum = np.sum(x_diff ** 2)

    for i in range(period - 1, n):
        y = ema[i-period+1:i+1]
        y_mean = np.mean(y)
        slope[i] = np.sum(x_diff * (y - y_mean)) / x_diff_sq_sum

    return slope
