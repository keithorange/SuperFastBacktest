
from scipy import integrate
from typing import Callable, Optional, List, Dict, Any, Sequence, Union
import logging
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
import yfinance as yf
import math
import random
from matplotlib.gridspec import GridSpec
import traceback
import pandas as pd
import numpy as np
import concurrent.futures
import importlib
from tqdm import tqdm
import os
import json
from reward_functions import _remove_zero_scores
from helpers import handle_infs_nans
from strategies.normalize_data import normalize_price_data_for_trading
from data_handler import download_data
import matplotlib.pyplot as plt
import seaborn as sns


NOISE_RANGE = (1e-10, 1e-10) # TINY NOISE to add into denominator etc.

import numpy as np


def calculate_noisy_downside_std(returns, noise_range=NOISE_RANGE):
    """
    Calculate the noisy downside volatility (standard deviation of returns below zero).

    Parameters:
    returns (array-like): Array of portfolio returns
    noise_range (tuple): Range for uniform noise (default is (0.001, 0.0011))

    Returns:
    float: The noisy downside volatility
    """
    # Select only negative returns
    downside_returns = [r for r in returns if r < 0]


    # Calculate downside standard deviation
    if len(downside_returns) > 0:
        pure_downside_vol = np.std(downside_returns, ddof=1)  # Sample standard deviation
    else:
        pure_downside_vol = 0.0  # No negative returns, set to 0

    # Add uniform noise to downside volatility
    noisy_downside_vol = pure_downside_vol + noise_range[0]#.uniform(noise_range[0], noise_range[1])

    # Ensure the result is never less than the minimum noise value
    return max(noisy_downside_vol, noise_range[0])




def calculate_noisy_ulcer(returns, noise_range=NOISE_RANGE):
    """
    Calculate the noisy Ulcer Index.

    Parameters:
    returns (array-like): Array of portfolio returns.
    noise_range (tuple): Range for uniform noise (default is (0.001, 0.0011)).

    Returns:
    float: The noisy Ulcer Index.
    """
    if len(returns) < 1:
        return noise_range[0]
    # Calculate cumulative returns
     # Adjusted drawdown calculation
    drawdowns = calculate_drawdowns(returns)
    # Calculate pure Ulcer Index
    pure_ulcer = linear_power(np.mean(linear_power(returns, 2)), 0.5)
    # Add uniform noise
    noisy_ulcer = pure_ulcer + noise_range[0]#np.random.uniform(noise_range[0], noise_range[1])


    # Apply log1p transformation to compress the value
    final_ulcer_index = np.log1p(noisy_ulcer)


    # Ensure the result is never exactly zero
    return max(final_ulcer_index, noise_range[0])

import numpy as np

def calculate_smart_noisy_std_dev(returns, noise_distance, noise_range=NOISE_RANGE):
    """
    Calculate a smart noisy standard deviation by adding a point at a specified distance.

    Parameters:
    returns (array-like): Array of portfolio returns.
    noise_distance (float): The distance (in standard deviations) to place the new point.
    noise_range (tuple): Range for minimum noise (default is NOISE_RANGE).

    Returns:
    float: The smart noisy standard deviation.
    """
    returns = np.array(returns)
    
    # Calculate mean and standard deviation of original returns
    mean_return = np.mean(returns)
    pure_std_dev = np.std(returns)

    # Determine the new point to add
    new_point = mean_return + (noise_distance * pure_std_dev)

    # Add the new point to the returns
    extended_returns = np.append(returns, new_point)

    # Calculate the new standard deviation
    smart_noisy_std_dev = np.std(extended_returns)

    # Ensure the result is never below the minimum noise
    return max(smart_noisy_std_dev, noise_range[0])



import numpy as np

def calculate_drawdowns(returns, eps=1e-8):
    """
    Calculate drawdowns from a series of returns.

    Args:
        returns: Array of returns
        eps: Small constant to prevent division by zero

    Returns:
        Array of drawdown percentages
    """
    # Calculate cumulative returns
    cumulative_returns = np.cumsum(returns)

    # Calculate running maximum
    running_max = np.maximum.accumulate(cumulative_returns)

    # Calculate raw drawdowns
    drawdowns = running_max - cumulative_returns

    # Calculate drawdowns as percentages
    drawdowns_pct = np.where(
        running_max > cumulative_returns,
        drawdowns / np.maximum(running_max - cumulative_returns, eps),
        0
    )

    return drawdowns_pct

def geometric_mean_plus_one(*args, epsilon=NOISE_RANGE[0]):
    """
    Calculate the geometric mean of the given arguments, adding 1 to each before multiplication
    and subtracting 1 from the final result. Uses epsilon to handle zero values.

    Parameters:
        *args: Any number of numeric arguments
        epsilon: Small value to replace zeros (default: 1e-10)

    Returns:
        float: The calculated geometric mean
    """
    if not args:
        raise ValueError("At least one argument is required")

    # Replace zeros with epsilon and add 1 to each value
    product = np.prod([max(arg, epsilon) + 1 for arg in args])
    return product ** (1 / len(args)) - 1


import numpy as np




def calculate_downwave(returns):
    """
    Calculates the amplitude of drawdowns, combining their spread and intensity:
    1. Max drawdown: Peak intensity
    2. Avg drawdown: Central tendency
    3. Std drawdown: Spread

    Uses geometric mean to synthesize these aspects into a single measure.


    By combining these using the geometric mean, we're essentially creating a single measure that captures:
        How extreme the drawdowns get (max)
        What's typical (avg)
        How much they vary (std)
        It's like we're creating a "super amplitude" that doesn't just look at the peak, but considers the whole "shape" of the drawdown behavior.
        This is analogous to how in signal processing, you might use various measures (peak amplitude, RMS amplitude, crest factor) to fully characterize a waveform. Here, we're doing it all in one shot for drawdowns.
        It's a dope way to compress all that drawdown info into one badass number, just like amplitude does for waves. 🌊📊💯
    """
    max_drawdown = calculate_max_drawdown(returns)
    avg_drawdown = calculate_avg_drawdown(returns)
    std_drawdown = calculate_std_drawdown(returns)

    return geometric_mean_plus_one(max_drawdown, avg_drawdown, std_drawdown)


def calculate_triple_threat_risk(returns, noise_range=NOISE_RANGE):
    """
    Evaluates the 'Triple Threat Risk' metric, combining three key downside risk measures:
    1. Noisy downside volatility
    2. Noisy Ulcer Index
    3. amplitude drawdowns

    This comprehensive risk metric provides a robust assessment of portfolio downside risk,
    accounting for volatility, sustained losses, and significant drawdowns. The 'noisy'
    components add a layer of randomness to mitigate overfitting.

    Parameters:
        returns (array-like): Array of portfolio returns.
        noise_range (tuple): Range for uniform noise (default is (0.001, 0.0011)).

    Returns:
        float: The Triple Threat Risk metric. Higher values indicate higher risk.
    """
    if len(returns) <= 0:
        return noise_range[0]

    # Calculate noisy downside volatility
    noisy_downside_vol = calculate_noisy_downside_std(returns, noise_range)

    # Calculate noisy Ulcer Index
    noisy_ulcer = calculate_noisy_ulcer(returns, noise_range)

    # Calculate smashed drawdowns
    downwave = calculate_downwave(returns)

    # Combine all components using geometric mean
    combined_metric = geometric_mean_plus_one(
        noisy_downside_vol, noisy_ulcer, downwave)

    # Ensure the metric is never exactly zero
    return max(combined_metric, noise_range[0])


def stded_total_return(returns, k=5):
    """
    Parameters:
    - returns: array-like, individual trade returns
    - k: sensitivity factor for standard deviation adjustment

    Returns:
    - ATR: Adjusted Total Return value
    """
    if len(returns) == 0:
        return 0

    # Calculate total return
    total_return = np.sum(returns)

    # Calculate standard deviation of returns
    std_dev = np.std(returns) if len(returns) > 1 else 0

    # # Calculate Adjusted Total Return
    atr = total_return * (1 / (1 + k * std_dev))

    # print(f"total_return={total_return} std_dev={
    #       std_dev} (1 / (1 + k * std_dev))={(1 / (1 + k * std_dev))} atr={atr}")

    return atr


def middle_weighed_return(returns, k=1):
    """
    Calculate the Middle Weighted Return (WR).

    Parameters:
    - returns: array-like, individual trade returns
    - k: sensitivity factor for weighting

    Returns:
    - WR: Weighted Return value
    """

    # # use excess returns to avoid 0s!
    # risk_free_rate = 0.0001

    # # Calculate excess returns
    # excess_returns = returns - risk_free_rate

    # # Filter out non-positive excess returns
    # positive_excess_returns = excess_returns[excess_returns > 0]

    # REMOVE 0'S FROM EQUITY CURVE RETURNS
    returns = returns#eturns[returns != 0]

    if len(returns) == 0:
        return 0

    mean_return = np.mean(returns)
    # median_return = np.median(returns)

    # Calculate average of mean and median
    avg_return = mean_return  # (mean_return + median_return) / 2

    # Calculate WR
    wr = np.sum(returns /
                (1 + k * np.abs(returns - avg_return)))

    # print(f"mean_return={mean_return} median_return={median_return} wr={wr}")

    return wr



def calculate_return_path_lengths(returns, exp_factor: float = 1.0, noise_range=NOISE_RANGE):
    """
    Calculates cumulative lengths of positive and negative return paths with noise.
    Applies the signed power transformation to the returns.
    """
    positive_returns = np.where(returns > 0, returns, 0)
    negative_returns = np.where(returns < 0, -returns, 0)

    # Apply the signed power transformation
    positive_returns = signed_power(positive_returns, exp_factor)
    negative_returns = signed_power(negative_returns, exp_factor)

    total_up = np.sum(positive_returns) + noise_range[0]
    total_down = np.sum(negative_returns) + noise_range[0]

    return abs(total_up), abs(total_down)

def calculate_drawdown_length(returns,exp_factor: float=1.0, noise_range=NOISE_RANGE):
    """
    Calculates the cumulative length of drawdowns.
    """
    return calculate_return_path_lengths(returns,exp_factor,  noise_range)[1]


def calculate_drawup_length(returns, noise_range=NOISE_RANGE):
    """
    Calculates the cumulative length of drawups.
    """
    return calculate_return_path_lengths(returns, noise_range)[0]


def calculate_return_path_areas(returns, noise_range=NOISE_RANGE):
    """
    Calculates areas under the curve for positive and negative return paths with noise.
    """
    positive_returns = np.maximum(returns, 0)
    negative_returns = np.maximum(-returns, 0)

    # Calculate cumulative sums
    cumulative_positive = np.cumsum(positive_returns)
    cumulative_negative = np.cumsum(negative_returns)

    # Calculate areas using trapezoidal rule
    positive_area = integrate.trapezoid(
        cumulative_positive, dx=1) + noise_range[0]#np.random.uniform(*noise_range)
    negative_area = integrate.trapezoid(
        cumulative_negative, dx=1) +noise_range[0]# np.random.uniform(*noise_range)

    return abs(positive_area), abs(negative_area)


def calculate_drawdown_area(returns, noise_range=NOISE_RANGE):
    """
    Calculates the area under the cumulative drawdown curve.
    """
    return calculate_return_path_areas(returns, noise_range)[1]


def calculate_drawup_area(returns, noise_range=NOISE_RANGE):
    """
    Calculates the area under the cumulative drawup curve.
    """
    return calculate_return_path_areas(returns, noise_range)[0]


def calculate_rachev_ratio(returns: np.ndarray, alpha: float = 0.1, lambda_: float = 1) -> float:  # set to 20% tail
    """
    Calculate the Rachev ratio.

    Args:
    returns (np.ndarray): Array of period returns.
    alpha (float): Tail probability level (default: 0.05 for 5% tail).
    lambda_ (float): Risk aversion parameter (default: 1 for risk-neutral).

    Returns:
    float: Rachev ratio
    """

    def calculate_etl() -> float:
        """
        Calculate the Expected Tail Loss (ETL) at a given alpha level.
        """
        sorted_returns = np.sort(returns)
        var = np.percentile(sorted_returns, alpha * 100)
        tail_returns = sorted_returns[sorted_returns <= var]
        if len(tail_returns) == 0:
            return 0
        return -np.mean(tail_returns)

    def calculate_etr() -> float:
        """
        Calculate the Expected Tail Return (ETR) at a given alpha level.
        """
        sorted_returns = np.sort(returns)[::-1]  # Sort in descending order
        var = np.percentile(sorted_returns, alpha * 100)
        tail_returns = sorted_returns[sorted_returns >= var]
        if len(tail_returns) == 0:
            return 0
        return np.mean(tail_returns)

    etr = calculate_etr()
    etl = calculate_etl()

    # Handle the case where etl is zero
    if etl == 0:
        if etr == 0:
            return 1.0  # If both are zero, return 1 (neutral)
        else:
            return float('inf')  # If only etl is zero, return infinity

    return (etr ** lambda_) / (etl ** lambda_)



def calculate_continuous_returns(prices: np.ndarray) -> np.ndarray:
    return np.divide(prices - prices[0], prices[0], out=np.zeros_like(prices), where=prices[0] != 0)


def calculate_annualized_return(returns: np.ndarray, periods_per_year: int) -> float:
    """
    Calculate annualized return using simple arithmetic mean.
    Args:
        returns: Array of period returns
        periods_per_year: Number of periods in a year (e.g., 252 for daily data)
    """
    if len(returns) == 0:
        return 0.0

    # Simple average return per period
    avg_return = np.mean(returns)

    # Annualize by simple multiplication
    return avg_return * periods_per_year


def calculate_profit_factor(trade_returns: np.ndarray, winning_trades: np.ndarray, losing_trades: np.ndarray) -> float:
    """Calculate profit factor with proper edge case handling."""
    gross_profit = np.sum(trade_returns[winning_trades])
    gross_loss = abs(np.sum(trade_returns[losing_trades]))

    epsilon = np.finfo(float).eps
    return gross_profit / (gross_loss + epsilon)


def calculate_returns(prices: np.ndarray) -> np.ndarray:
    """Calculate simple returns."""
    if len(prices) <= 1:
        return np.array([])

    returns = np.diff(prices) / prices[:-1]
    return np.nan_to_num(returns, nan=0.0, posinf=1e6, neginf=-1e6)


def calculate_cumulative_returns(returns: np.ndarray) -> np.ndarray:
    """
    Calculate cumulative returns using simple addition.
    """
    if len(returns) == 0:
        return np.array([])

    return np.cumsum(returns)


def calculate_total_return(returns: np.ndarray) -> float:
    """
    Calculate total return by simply summing all returns.
    """
    if len(returns) == 0:
        return 0.0

    return np.sum(returns)


def calculate_downside_deviation(returns: np.ndarray, threshold: float, periods_per_year: int) -> float:
    """
    Calculate downside deviation with proper edge case handling.
    """
    if len(returns) == 0:
        return 0.0

    downside_returns = np.minimum(returns - threshold, 0)
    mean_squared = np.mean(linear_power(downside_returns, 2)) # +1 so values <1 doesnt shrink!

    # Handle negative numbers inside sqrt
    epsilon = np.finfo(float).eps
    mean_squared_safe = max(mean_squared, epsilon)

    return np.sqrt(mean_squared_safe) * np.sqrt(periods_per_year)


def calculate_max_drawdown(equity_curve: np.ndarray) -> float:
    """Calculate maximum drawdown."""
    drawdowns = calculate_drawdowns(equity_curve)
    return np.max(drawdowns) if len(drawdowns) > 0 else 0.0


def calculate_avg_drawdown(equity_curve: np.ndarray) -> float:
    """Calculate average drawdown."""
    drawdowns = calculate_drawdowns(equity_curve)
    return np.mean(drawdowns) if len(drawdowns) > 0 else 0.0


def calculate_std_drawdown(equity_curve: np.ndarray) -> float:
    """
    Calculate standard deviation of drawdowns using calculate_drawdowns function.
    """
    if len(equity_curve) <= 1:  # Need at least 2 points for std
        return 0.0

    drawdowns = calculate_drawdowns(equity_curve)
    return np.std(drawdowns)





def calculate_volatility(returns: np.ndarray, periods_per_year: int) -> float:
    """Calculate annualized volatility."""
    if len(returns) <= 1:
        return 0.0
    return np.std(returns, ddof=1) * np.sqrt(periods_per_year)


def calculate_alpha(returns: np.ndarray, market_returns: np.ndarray, risk_free_rate: float, periods_per_year: int) -> float:
    """Calculate alpha with proper edge case handling."""
    if len(returns) == 0 or len(market_returns) == 0:
        return 0.0

    excess_return = calculate_annualized_return(
        returns, periods_per_year) - risk_free_rate
    market_excess_return = calculate_annualized_return(
        market_returns, periods_per_year) - risk_free_rate
    beta = calculate_beta(returns, market_returns)

    return excess_return - (beta * market_excess_return)


def calculate_beta(returns: np.ndarray, market_returns: np.ndarray) -> float:
    """Calculate beta using covariance."""
    if len(returns) == 0 or len(market_returns) == 0:
        return 0.0

    covariance = np.cov(returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)

    epsilon = np.finfo(float).eps
    return covariance / (market_variance + epsilon)


def calculate_expectancy(returns: np.ndarray) -> float:
    """Calculate trading expectancy."""


    returns =np.array( returns)

    if len(returns) == 0:
        return 0.0

    wins = returns[returns > 0] * 100
    losses = returns[returns <0] * 100  # turn to pct from 1.0 form

    win_rate = len(wins) / len(returns)
    loss_rate = len(losses) / len(returns)

    avg_win = np.mean(wins) if len(wins) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0

    return (win_rate * avg_win) - (loss_rate * abs(avg_loss))



def calculate_ratio(numerator: float, denominator: float, epsilon=1) -> float:
    return numerator / (denominator + epsilon)

def get_periods_per_year(period_type: str) -> int:
    # period_map = {
    #     '1m': 525600,
    #     '5m': 105120,
    #     '15m': 35040,
    #     '30m': 17520,
    #     '1h': 8760,
    #     '4h': 2190,
    #     '1d': 365,
    #     '1w': 52,
    # }
    # # Default to 252 trading days if period_type is not found
    # return period_map.get(period_type, 252)

    return 252



def get_weekend_exit_signals(dates: np.ndarray) -> np.ndarray:
    # Initialize exit signals array
    exit_signals = np.zeros(len(dates), dtype=int)

    # Convert dates to Pandas DatetimeIndex for easier manipulation
    dates = pd.to_datetime(dates)

    # Loop through the dates
    for i in range(len(dates)):
        # Check if the current date is a Monday
        if dates[i].weekday() == 0:  # 0 corresponds to Monday
            # Look backwards for the last Friday
            for j in range(i - 1, -1, -1):  # Loop backwards from i-1 to 0
                if dates[j].weekday() == 4:  # 4 corresponds to Friday
                    # Mark the last candle on Friday as an exit point
                    exit_signals[j] = 1  # Use assignment instead of comparison
                    break

    return exit_signals

import numpy as np

def signed_power(x, power):
    """
    Applies power function while preserving the sign of x.
    
    Args:
    x (array-like): Input values
    power (float): Power to raise the absolute values to
    
    Returns:
    array-like: Signed power of x
    """
    return np.sign(x) * np.abs(np.power(np.abs(x), power))

def linear_power(x, power, threshold=1.0):
    """
    Applies linear function for values within [-threshold, threshold],
    and power function otherwise.
    
    Args:
    x (array-like): Input values
    power (float): Power to use for values outside the threshold
    threshold (float): Threshold for linear behavior (default 1.0)
    
    Returns:
    array-like: Result of linear-power operation
    """
    return np.where(np.abs(x) <= threshold, x, signed_power(x, power))

def signed_linear_power(x, power, threshold=1.0):
    """
    Ensures sign preservation after linear_power transformation.
    
    Args:
    x (array-like): Input values
    power (float): Power to use for values outside the threshold
    threshold (float): Threshold for linear behavior (default 1.0)
    
    Returns:
    array-like: Result of signed linear-power operation
    """
    sign = np.sign(x)
    return sign * np.abs(linear_power(np.abs(x), power, threshold))


def perfect_sharpe(returns, 
        metrics, noise_distance=0, noise_range=NOISE_RANGE):
    """
    Calculate a modified Sharpe ratio with smart noise addition.

    Parameters:
    noise_distance (float): The distance (in standard deviations) to place the new point.
    noise_range (tuple): Range for minimum noise (default is NOISE_RANGE).

    Returns:
    float: The modified Sharpe ratio.
    """

    # total_return = np.sum(returns)
    # Calculate total return for numerator
    total_return = better_profit_term(returns, metrics)


    # Calculate smart noisy standard deviation for denominator
    smart_noisy_std_dev = calculate_smart_noisy_std_dev(returns, noise_distance, noise_range)

    # Calculate modified Sharpe ratio 
    # Assuming risk-free rate is 0 for simplicity
    modified_sharpe_ratio = total_return / (1 + smart_noisy_std_dev)

    return modified_sharpe_ratio


def perfect_sortino(returns, metrics, noise_range=NOISE_RANGE):
    # Calculate excess returns for numerator
    total_return = better_profit_term(returns, metrics)

    noisy_downside_vol = calculate_noisy_downside_std(returns, noise_range)

    sortino_ratio = total_return / (1+noisy_downside_vol)

    return sortino_ratio


def perfect_sterling(returns, metrics ):

    total_return = better_profit_term(returns, metrics)
    sterling = total_return / (1+calculate_avg_drawdown(returns))
    return sterling

def perfect_burke(returns, metrics, power=2):

    # Calculate total return for numerator
    total_return = better_profit_term(returns, metrics)

    # Calculate noisy drawdowns
    NOISE = 1e-6
    noisy_drawdowns = calculate_drawdowns(returns) + NOISE


    # Calculate the sum of squared drawdowns
    sum_squared_drawdowns = np.sum(noisy_drawdowns ** power)

    # Calculate Burke ratio
    burke_ratio = total_return / (1+np.sqrt(sum_squared_drawdowns))

    return burke_ratio




def perfect_downwave(returns, 
        metrics, noise_range=NOISE_RANGE):
    

    total_return = better_profit_term(returns, metrics)
    downwave = calculate_downwave(returns)

    return total_return / (1+max(downwave, noise_range[0]))

def calculate_triple_threat_ratio(returns, 
        metrics,noise_range=NOISE_RANGE):
    """
    Measures return efficiency against triple risk factors.
    """

    total_return = better_profit_term(returns, metrics)
    downside_stress = calculate_triple_threat_risk(returns, noise_range)

    return (total_return) / (1+downside_stress)




def citrus_ratio(returns, 
        metrics,):
    """BEST RATIO EVER! BEST NUEMRATOR OVER BEST DENOMIATOR! SUPER SECRET RELIGIOUS-INSPIRING FUCKING RATIO!"""

    citrus = geometric_mean_plus_one(calculate_drawdown_length(returns, exp_factor=1.1), calculate_downwave(returns))
    citrus = np.log1p(citrus)
    profit_term = better_profit_term(returns,)
    return profit_term / (1+citrus)


def bananas_ratio(returns, metrics):
    profit_term = better_profit_term(returns,)
    down_term = better_down_term(metrics)
    return profit_term / (1+down_term)

def _profit_punish_loss(r, punish_loss_exp: float = 2):
    r = r * 100

    profits = np.sum(r[r >= 0])
    losses = np.sum(-np.abs(r[r < 0]) ** punish_loss_exp)
    return profits + losses

def _no_long_time_profit(returns, metrics, max_hold_time_mins, max_hold_time_scalar=0):
    returns = returns * 100
    hold_times = metrics["trade_hold_times"]

    # if len(hold_times > 0):
    #     print(f"""
    #         **Returns: {returns}
    #         Hold_times: {hold_times}
    # \n
    #         """)
    
    
    assert len(returns) == len(hold_times)

    total_sum = 0
    for i, return_value in enumerate(returns):
        if hold_times[i] >= max_hold_time_mins:
            total_sum += max_hold_time_scalar*return_value
            # continue
        total_sum += return_value


    return total_sum  # Don't forget to return the result



def calculate_returns_from_snapshots(normalized_equity_curve_snapshots):
    equity_curve = np.array(normalized_equity_curve_snapshots)
    change_indices = np.where(np.diff(equity_curve) != 0)[0] + 1
    unique_indices = np.unique(np.concatenate(([0], change_indices, [len(equity_curve) - 1])))
    unique_equity_values = equity_curve[unique_indices]
    
    # Avoid division by zero
    returns = np.diff(unique_equity_values) / np.maximum(unique_equity_values[:-1], 1e-8)
    
    return returns.tolist()


def better_profit_term(returns, metrics,) -> float:
    total_return = np.sum(returns)

    # mean_trade_returns = (np.mean(returns)*100) * len(returns)
    # expectancy = calculate_expectancy(returns) * 100
    # expectancy_returns =  expectancy* metrics['total_trades']
    # return expectancy_returns

    # rew = expectancy # NOTE: WORKS PERFECTLY! BETTER THAN $$$
    # rew = total_return


    # rew = abs(expectancy * total_return) * np.sign(expectancy)

    rew = metrics["total_return"]

    # print(f"total-return: {rew}")

     # works great! UNLESS OUTLIER BIG TRADES! THEN USE JUST MEDIAN * TRADES    
    # rew = np.power( ((1+abs(expectancy*metrics["total_trades"])) * (1+ abs(total_return))*(1+abs(metrics["median_trade"]))), 1/3 ) * np.sign(total_return)

    # rew = abs(metrics["median_trade"] * metrics["total_trades"] * 100) * np.sign(expectancy)
    # rew = total_return

    # rew = _profit_punish_loss(returns, punish_loss_exp=1)
    
    # rew = _no_long_time_profit(returns, metrics, max_hold_time_mins=60*5*2)

    # rew = np.sign(total_return) * ((1+abs(expectancy)) * (1+ abs(total_return)))# 1/2 ) 
    return rew


def better_down_term(returns, 
        metrics,):
    dt_b = metrics["avg_loss"] * metrics["losing_trades"]
    dt_c = metrics["avg_drawdown"]
    down_term =  (1+abs(dt_b)) * (1+abs(dt_c))

    return (1+down_term)


def _calculate_m_ratio(
        returns, 
        metrics,
                            noise_range: tuple,
                    drawdown_func: Callable[[np.ndarray], np.ndarray],
                    magnitude_func: Callable[[np.ndarray], np.ndarray],
                    duration_func: Callable[[np.ndarray], np.ndarray],
                    # constant to avoid overfitting 
                    constant_drawdown: float = 0.05,
                    constant_duration: int = 10) -> float:
    """
    Helper function to calculate MURKE or Martin ratio with a constant drawdown added and processed through the same functions.
    """
    N = len(returns)
    if N == 0:
        return noise_range[1]
    elif N == 1:
        return returns[0]
        
    total_return = better_profit_term(returns, metrics)
    
    drawdowns = drawdown_func(returns)
    significance_threshold = noise_range[0]
    is_dd = drawdowns > significance_threshold
    
    dd_changes = np.diff(np.concatenate(([0], is_dd.astype(int), [0])))
    dd_starts = np.where(dd_changes == 1)[0]
    dd_ends = np.where(dd_changes == -1)[0] - 1
    
    # Process the constant drawdown through the same functions
    constant_dd_component = magnitude_func(np.array([constant_drawdown])) * duration_func(np.array([constant_duration]))
    
    if len(dd_starts) == 0:
        denominator = constant_dd_component[0]  # Use only the constant component
    else:
        dd_magnitudes = np.array([
            drawdowns[start:end + 1].max()
            for start, end in zip(dd_starts, dd_ends)
        ])
        dd_lengths = dd_ends - dd_starts + 1
        
        calculated_dd = np.sum(magnitude_func(dd_magnitudes) * duration_func(dd_lengths)) / N
        denominator = calculated_dd + constant_dd_component[0]  # Add the constant component
    
    # Wrap in log since massive
    denominator = np.log1p(denominator)
    
    return total_return / (1+denominator)



def perfect_murke(returns, 
        metrics, noise_range=NOISE_RANGE) -> float:
    """
    MURKE ratio with mathematically optimized penalties.
    
    Key changes:
    1. Pure magnitude^2 for quadratic drawdown penalty
    2. sqrt(length) for reduced duration impact
    3. Properly scaled denominators

    NOTE: you can specify the ** x for the dd_len ** a and dd_time ** b ! 
    """
    def murke_drawdown_func(returns):
        return calculate_drawdowns(returns)
    
    def murke_magnitude_func(magnitudes):
        return np.abs(magnitudes) ** 2 # can be 1 for linear, 2 for exp scaling for dd length, 3 etc.
    
    def modified_duration(lengths):
        return np.abs(lengths)**1.1 #** 1
    
    # additional scaleing  so in similar range as 0-100 profit
    return 10* _calculate_m_ratio(returns, metrics,
                                  noise_range,
                        murke_drawdown_func,
                        murke_magnitude_func,
                        modified_duration) 

# Martin ratio function
def perfect_martin(returns, 
        metrics, noise_range=NOISE_RANGE) -> float:
    """
    Martin ratio with consistent N-normalization.
    
    Args:
        returns: Array of returns.
        noise_range: Tuple of (min_noise, max_noise).
    
    Returns:
        Martin ratio.
    """
    
    def martin_drawdown_func(returns):
        return calculate_drawdowns(returns)

    def martin_magnitude_func(magnitudes):
        return magnitudes  # Linear for Martin ratio

    def identity_duration(lengths):
        return lengths

    return _calculate_m_ratio(returns, metrics,
                              noise_range, martin_drawdown_func, 
                            martin_magnitude_func, identity_duration)

def sharptino_ratio(returns, metrics, profit_std_weight=1, loss_std_weight=4, total_std_weight=1):
    """
    Calculates the Sharptino Ratio with adjustable weights for profit, loss, and total standard deviations.
    Handles edge cases like empty profit/loss arrays and zero standard deviations.
    
    :param returns: Array-like, daily portfolio returns.
    :param metrics: Dictionary containing normalized equity curve snapshots.
    :param profit_std_weight: Weight for the standard deviation of profits.
    :param loss_std_weight: Weight for the standard deviation of losses.
    :param total_std_weight: Weight for the total standard deviation.
    :return: Sharptino Ratio value.
    """
    # Take just the raw trade profits (no equity curves...)
    returns = metrics["trade_returns"]
    returns = _remove_zero_scores(returns, radius=1e-10)

    
    if len(returns) == 0:
        return 0.0  # Return 0 if there are no non-zero returns
    
    # Separate profits and losses
    profits = returns[returns > 0]
    losses = returns[returns < 0]
    
    # Calculate standard deviations with safe handling
    std_profit = np.std(profits) if len(profits) > 1 else 0
    std_loss = np.std(losses) if len(losses) > 1 else 0
    std_total = np.std(returns) if len(returns) > 1 else 0
    
    # Handle case where all standard deviations are zero
    if std_profit == 0 and std_loss == 0 and std_total == 0:
        total_return = better_profit_term(returns, metrics)
        return total_return
    
    # Calculate weighted components safely
    weighted_components = []
    if std_profit > 0:
        weighted_components.append(profit_std_weight * std_profit**2)
    if std_loss > 0:
        weighted_components.append(loss_std_weight * std_loss**2)
    if std_total > 0:
        weighted_components.append(total_std_weight * std_total**2)
    
    # Calculate total weights for non-zero components
    total_weights = 0
    if std_profit > 0:
        total_weights += profit_std_weight
    if std_loss > 0:
        total_weights += loss_std_weight
    if std_total > 0:
        total_weights += total_std_weight
    
    # Calculate combined standard deviation safely
    if total_weights == 0:
        combined_std = 0
    else:
        combined_std = np.sqrt(sum(weighted_components) / total_weights)
    
    # Calculate total return
    total_return = better_profit_term(returns, metrics)
    
    # Calculate final Sharptino ratio
    sharptino = total_return / (combined_std)
    
    return sharptino


# # NOTE: disable when # charts > 4, will be impossible to train!
# def _early_tb(
#         returns, 
#         metrics,

#         reward_fn: Union[Callable, float],

#             # disable when using big chart set n > 10
#             enable_early_trades_early_tb=False,
#             min_num_trades=1,
#             etb_init=-1e8,#0.01, # SET HIGHER THAN LOWEST POSSIBLE LOW SCORE WHEN 1+ TRADE
#             #   etb_init=-1e-8, # set super tiny low value just to make trades but doesnt have too
#             #  etb_factor=1e-9,
#                 enable_profit_for_negative_score=False, # NOTE: def worked with murke! BUT, trying False if pos nums & neg profit is much diff!
#                 enable_exp_negative_score=6, # if 0 off
#                 ) -> float:
    
#     """boost first trades"""
#     reward_value = reward_fn(returns, 
#         metrics,)  if callable(reward_fn) else reward_fn

#     profit = better_profit_term(returns, metrics) 
#     if profit <= 0 and enable_profit_for_negative_score :
#         reward_value = profit 

#     if not enable_early_trades_early_tb:
#         return reward_value

#     if  metrics["total_trades"]  < min_num_trades:# or not len(returns):
#         return etb_init 

    
#     if enable_exp_negative_score and profit <= 0:
#         reward_value = signed_power(reward_value, enable_exp_negative_score)
    
#     # returns = returns[returns != 0]  

#     return reward_value + metrics["trades_per_1000_candles"]*1e-8

def _more_tb(
    returns, metrics, 
    reward_fn, 
    trade_boost_exp=0.15,
    tb_only_pos=True,
    wins_only=True,
):
    if wins_only:
        n = metrics["num_wins"]
    else:
        n = metrics["total_trades"]
        
    reward_value = reward_fn(returns, metrics) if callable(reward_fn) else reward_fn
    original_sign = np.sign(reward_value)
    trade_boost = max(1, n)

    if better_profit_term(returns, metrics) <= 0:
        trade_boost = 1

    # New logic: as trade_boost increases, output approaches original reward
    trade_boost_value = signed_power(trade_boost, trade_boost_exp)
    adjustment_factor = 1 / (1 + np.abs(trade_boost_value))
    
    adjusted_reward = reward_value * (1 - adjustment_factor) + reward_value * adjustment_factor

    if tb_only_pos:
        if original_sign > 0:
            return original_sign * np.abs(adjusted_reward)
        else:
            return reward_value  # Return original negative value without modification
    else:
        return original_sign * np.abs(adjusted_reward)  # Apply adjustment to both positive and negative values


def _speedy_fn(
        returns,metrics,
        reward_fn, 
        unspeedify_loss=True, # keep loss raw to prevent it making LOTS of trades to shrink LOSS! (happens IRL)
                ):
    reward_value = reward_fn(returns, 
        metrics,)  if callable(reward_fn) else reward_fn
    
    original_sign = np.sign(reward_value)



    # simpler version
    tht = metrics["total_hold_time"] 
    aht =  metrics["avg_hold_time"]
    mht = metrics["max_hold_time"]
    sht = metrics["std_hold_time"]
    htm = geometric_mean_plus_one(mht, sht)
    htm = signed_power(htm, 2)
    
    htm = np.log1p(htm)

    speedy_reward = reward_value
    if not ( unspeedify_loss and better_profit_term(returns, metrics)<=0):
        speedy_reward = reward_value / (1 + htm)


    # boost by intial trades too! 
    return original_sign * np.abs(speedy_reward)



def calculate_special_sauce_metrics(metrics, trades, benchmark_returns, returns):

    """
    Any of these can be used to hyperpot for optimal trading strategies.

    """
    # Take just the raw trade profits (no equity curves...)
    returns = metrics["trade_returns"]
    returns = _remove_zero_scores(returns, radius=1e-10)
    
    x= {

        # # TODO: DO NOT USE SPEEDY! USE REGULAR

        # "better_profit": (  better_profit_term(returns, metrics)),
        # "speedy_profit": _speedy_fn(returns, metrics, better_profit_term(returns, metrics)),
        # "tradex_profit":_more_tb(returns, metrics, (  better_profit_term(returns, metrics))),

        # "perfect_downwave": (  perfect_downwave),
        # # "speedy_downwave": _speedy_fn(perfect_downwave),

        # "perfect_sharpe": (  perfect_sharpe(returns, metrics)),
        # "tradex_sharpe": _more_tb(returns, metrics, (  perfect_sharpe)),

        # "perfect_sortino": (  perfect_sortino),
        # "tradex_sortino": _more_tb(returns, metrics, (  perfect_sortino)),

        # "sharptino": (  sharptino_ratio(returns, metrics)),
        # "tradex_sharptino": _more_tb(returns, metrics, (  sharptino_ratio)),
        # "speedy_tradex_sharptino": _more_tb(returns, metrics, _speedy_fn(returns, metrics, sharptino_ratio)),

        # "perfect_murke": (  perfect_murke(returns, metrics, )),
        # "speedy_murke": _speedy_fn(returns, metrics, perfect_murke),
        # "tradex_murke": _more_tb(returns, metrics, (perfect_murke)),
        
        # "speedy_tradex_murke": _more_tb(returns, metrics, _speedy_fn(returns, metrics, perfect_murke)),
        # "perfect_martin": (  perfect_martin),
        # "speedy_martin": _speedy_fn(returns, metrics, perfect_martin),
        # "tradex_martin": _more_tb(returns, metrics, (  perfect_martin)),
        # "speedy_tradex_martin": _more_tb(returns, metrics, _speedy_fn(returns, metrics, perfect_martin)),

        # "perfect_sterling": (  perfect_sterling(returns, metrics, )),
        # "perfect_burke": (  perfect_burke(returns, metrics, )),

        # "triple_threat_ratio": (  calculate_triple_threat_ratio),

        # "bananas_ratio": (  bananas_ratio),

        # "citrus_ratio": (  citrus_ratio),
        # "tradex_citrus": _more_tb(returns, metrics, (  citrus_ratio)),
        # "speedy_citrus": _speedy_fn(returns, metrics, citrus_ratio),


    }
    return x

# Smart sign-preserving multiplication of three terms


def calculate_metrics(benchmark_prices: np.ndarray,
                      trades: List[Dict],
                      num_exit_signals: int,
                      equity_curve: np.ndarray,
                      equity_curve_snapshots: np.ndarray,
                      use_equity_curve: bool = True,
                      period_type: str = '5m',
                      risk_free_rate: float = 1e-10) -> Dict[str, float]:
    
    
    # Keep original curves for wallet balance calculations
    original_equity_curve = equity_curve.copy()
    original_equity_curve_snapshots = equity_curve_snapshots.copy()
    
    # Create normalized versions for return calculations
    initial_capital = original_equity_curve[0]
    normalized_equity_curve = original_equity_curve - initial_capital
    normalized_equity_curve_snapshots = original_equity_curve_snapshots - initial_capital



    periods_per_year = get_periods_per_year(period_type)
    # Get snapshot indices

    exit_indices = np.array([trade['exit_index'] for trade in trades])
    exit_indices = np.unique(np.append(exit_indices, len(benchmark_prices) - 1))

    # Calculate continuous benchmark returns
    benchmark_returns_continuous = calculate_continuous_returns(benchmark_prices)

    # Take snapshots of benchmark returns
    benchmark_returns_snapshots = take_snapshots_by_indices(benchmark_returns_continuous, exit_indices)

    # Basic trade statistics
    trade_returns = np.array([trade['realized_profit'] for trade in trades])
    winning_trades = trade_returns > 0
    losing_trades = trade_returns < 0
    total_trades = len(trades)
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    win_rate = num_wins / total_trades if total_trades > 0 else 0

    # any other stats u need to take from trades, take them!
    trade_hold_times = np.array([trade['duration'] for trade in trades])

    # if total_trades:
    #     print(f"ALL TRADES PROFITS: {np.array([trade['profit'] for trade in trades])}")


    # Use normalized curves for returns calculations
    if use_equity_curve:
        benchmark_returns = benchmark_returns_continuous
        # returns = np.diff(normalized_equity_curve) / (normalized_equity_curve[:-1] + initial_capital)
        
        returns = trade_returns # keep simple trade returns, NOT using equity curve idea here!
        drawdowns = calculate_drawdowns(normalized_equity_curve)
    else:
        # valid_snapshots = ~np.isnan(normalized_equity_curve_snapshots)
        # returns = np.diff(normalized_equity_curve_snapshots[valid_snapshots]) / (normalized_equity_curve_snapshots[valid_snapshots][:-1] + initial_capital)
        benchmark_returns = benchmark_returns_snapshots[~np.isnan(benchmark_returns_snapshots)]

        returns = trade_returns # keep simple trade returns, NOT using equity curve idea here!
        drawdowns = calculate_drawdowns(normalized_equity_curve_snapshots)



    max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
    avg_drawdown = np.mean(drawdowns) if len(drawdowns) > 0 else 0
    std_drawdown = np.std(drawdowns) if len(drawdowns) > 0 else 0

    # Total return
    total_return = np.sum(trade_returns) #(original_equity_curve[-1] - original_equity_curve[0]) / original_equity_curve[0]

    # Benchmark return
    benchmark_total_return = benchmark_returns_continuous[-1]

    # Profit factor and average trade metrics
    profit_factor = calculate_profit_factor(trade_returns, winning_trades, losing_trades)
    avg_trade = np.mean(trade_returns) if total_trades > 0 else 0
    avg_win = np.mean(trade_returns[winning_trades]) if num_wins > 0 else 0
    avg_loss = np.mean(trade_returns[losing_trades]) if (total_trades - num_wins) > 0 else 0
    max_win = np.max(trade_returns) if total_trades > 0 else 0
    max_loss = np.min(trade_returns) if total_trades > 0 else 0
    
    # Calculate median trade
    median_trade = np.median(trade_returns) if total_trades > 0 else 0





    def calculate_trade_durations(trades, equity_curve, period_type):
        USE_DURATION_IN_CANDLES = True

        if USE_DURATION_IN_CANDLES:
            trade_durations = []
            for i in range(len(trades)):
                current_trade = trades[i]
                duration = (current_trade['exit_date'] - current_trade['entry_date']).total_seconds() / pd.Timedelta(period_type).total_seconds()
                trade_durations.append(duration)
        else:
            trade_durations = [trade['duration'] for trade in trades]

        total_trades = len(trades)
        
        if total_trades > 0:
            avg_hold_time = np.mean(trade_durations)
            max_hold_time = np.max(trade_durations)
            min_hold_time = np.min(trade_durations)
            std_hold_time = np.std(trade_durations)
            total_hold_time = np.sum(trade_durations)  # Calculate the total hold time
        else:
            avg_hold_time = max_hold_time = min_hold_time = std_hold_time = total_hold_time = 0

        return avg_hold_time, max_hold_time, min_hold_time, std_hold_time, total_hold_time

    # Usage of the function
    avg_hold_time, max_hold_time, min_hold_time, std_hold_time, total_hold_time = calculate_trade_durations(trades, equity_curve, period_type)


    # Trading frequency
    total_candles = len(original_equity_curve)
    trades_per_1000_candles = (num_exit_signals / total_candles) * 1000

    # CAGR (Compound Annual Growth Rate)
    cagr = ((original_equity_curve[-1] / initial_capital) ** (1 / (len(original_equity_curve) / periods_per_year))) - 1


    # Expectancy and risk-reward ratio


    expectancy = calculate_expectancy(trade_returns)
    risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

    total_return_x_expectancy = (1+abs(expectancy)) * (1+ abs(total_return)) * np.sign(total_return)

    metrics = {
        'benchmark_return': benchmark_total_return,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'avg_drawdown': avg_drawdown,
        'std_drawdown': std_drawdown,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        "num_wins": num_wins,
        "num_losses": num_losses,
        'winning_trades': num_wins,
        'losing_trades': total_trades - num_wins,
        'trades_per_1000_candles': trades_per_1000_candles,
        'avg_trade': avg_trade,
        'median_trade': median_trade,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': max_win,
        'max_loss': max_loss,
        'avg_hold_time': avg_hold_time,
        'max_hold_time': max_hold_time,
        'min_hold_time': min_hold_time,
        'std_hold_time': std_hold_time,
        'total_hold_time': total_hold_time,
        'cagr': cagr,
        'expectancy': expectancy,
        'risk_reward_ratio': risk_reward_ratio,
        'total_return_x_expectancy': total_return_x_expectancy,
        
    }

    def fix_inf_nans(m):
        for key in m:
            metrics[key] = handle_infs_nans(metrics[key])

    fix_inf_nans(metrics)

    metrics.update({
        "normalized_equity_curve_snapshots": normalized_equity_curve_snapshots,
        "normalized_equity_curve": normalized_equity_curve,
        "original_equity_curve_snapshots":original_equity_curve_snapshots,
        "original_equity_curve":original_equity_curve,

        # adding in any other stuff rto use
        "trade_returns": trade_returns,
        "trade_hold_times": trade_hold_times,
    })

    # Calculate risk-adjusted metrics
    risk_adjusted_metrics = calculate_risk_adjusted_metrics(
        trade_returns,
        benchmark_returns,
        risk_free_rate,
        periods_per_year,
        equity_curve,
        metrics,
        use_equity_curve
    )
    metrics.update(risk_adjusted_metrics)
    fix_inf_nans(metrics)

    special_sauce_metrics = calculate_special_sauce_metrics(metrics, trades, benchmark_returns, returns)
    metrics.update(special_sauce_metrics)

    fix_inf_nans(metrics)

    return metrics



def calculate_risk_adjusted_metrics(returns: np.ndarray, benchmark_returns: np.ndarray, risk_free_rate: float, periods_per_year: int, equity_curve: np.ndarray, metrics, use_equity_curve: bool = True, ) -> Dict[str, float]:
    """
    Calculate various risk-adjusted performance metrics.

    Args:
    returns (np.ndarray): Array of period returns.
    benchmark_returns (np.ndarray): Array of benchmark returns.
    risk_free_rate (float): Risk-free rate (annualized).
    periods_per_year (int): Number of periods per year.
    equity_curve (np.ndarray): Array representing the equity curve.
    use_equity_curve (bool): If True, use equity curve for certain calculations instead of returns.

    Returns:
    Dict[str, float]: Dictionary of calculated metrics.
    """
    if use_equity_curve:
        period_returns = np.diff(equity_curve) / equity_curve[:-1]
        cumulative_returns = equity_curve / equity_curve[0] - 1
    else:
        period_returns = returns
        cumulative_returns = calculate_cumulative_returns(returns)

    # Ensure benchmark_returns has the same length as period_returns
    if len(benchmark_returns) != len(period_returns):
        benchmark_returns = benchmark_returns[:len(period_returns)]

    annualized_return = calculate_annualized_return(
        period_returns, periods_per_year)
    volatility = calculate_volatility(period_returns, periods_per_year)

    max_drawdown = calculate_max_drawdown(cumulative_returns)
    avg_drawdown = calculate_avg_drawdown(cumulative_returns)
    std_drawdown = calculate_std_drawdown(cumulative_returns)
    ulcer_index = calculate_noisy_ulcer(cumulative_returns)
    # " ULCER INDEX IS WACK! SMASHED DRAWDOWNS IS LITERALLY THE BEST!

    downwave = calculate_downwave(cumulative_returns)
    downwave = max(downwave, 1e-8)

    beta = calculate_beta(period_returns, benchmark_returns)
    alpha = calculate_alpha(
        period_returns, benchmark_returns, risk_free_rate, periods_per_year)
    expectancy = calculate_expectancy(period_returns)

    excess_return = annualized_return - risk_free_rate
    sqrt_periods = np.sqrt(periods_per_year)

    drawdowns = calculate_drawdowns(cumulative_returns)
    squared_drawdowns = np.sum(linear_power(drawdowns, 2)) # added in +1 so <1 dds dont shrink! burke is retarted originally....

    drawdown_resistance = 1 / (1 + downwave)  # Softer penalty

    metrics = {
        'sharpe_ratio': calculate_ratio(excess_return, volatility) * sqrt_periods,
        'alpha_sharpe_ratio': calculate_ratio(alpha, volatility) * sqrt_periods,
        'expectancy_sharpe_ratio': calculate_ratio(expectancy, volatility) * sqrt_periods,

        'sortino_ratio': calculate_ratio(excess_return, calculate_downside_deviation(period_returns, risk_free_rate/periods_per_year, periods_per_year)) * sqrt_periods,
        'alpha_sortino_ratio': calculate_ratio(alpha, calculate_downside_deviation(period_returns - benchmark_returns, 0, periods_per_year)) * sqrt_periods,
        'expectancy_sortino_ratio': calculate_ratio(expectancy, calculate_downside_deviation(period_returns, 0, periods_per_year)) * sqrt_periods,

        'omega_ratio': calculate_ratio(np.sum(np.maximum(period_returns - risk_free_rate/periods_per_year, 0)), np.sum(np.maximum(risk_free_rate/periods_per_year - period_returns, 0))),
        'alpha_omega_ratio': calculate_ratio(np.sum(np.maximum(period_returns - benchmark_returns, 0)), np.sum(np.maximum(benchmark_returns - period_returns, 0))),
        'expectancy_omega_ratio': calculate_ratio(np.sum(np.maximum(period_returns, 0)), np.sum(np.maximum(-period_returns, 0))),

        'calmar_ratio': calculate_ratio(excess_return, max_drawdown),
        'alpha_calmar_ratio': calculate_ratio(alpha, max_drawdown),
        'expectancy_calmar_ratio': calculate_ratio(expectancy, max_drawdown),

        'sterling_ratio': calculate_ratio(excess_return, avg_drawdown),
        'alpha_sterling_ratio': calculate_ratio(alpha, avg_drawdown),
        'expectancy_sterling_ratio': calculate_ratio(expectancy, avg_drawdown),

        'burke_ratio': calculate_ratio(excess_return, np.sqrt(squared_drawdowns)),
        'alpha_burke_ratio': calculate_ratio(alpha, np.sqrt(squared_drawdowns)),
        'expectancy_burke_ratio': calculate_ratio(expectancy, np.sqrt(squared_drawdowns)),

        'martin_ratio': calculate_ratio(excess_return, ulcer_index),
        'alpha_martin_ratio': calculate_ratio(alpha, ulcer_index),
        'expectancy_martin_ratio': calculate_ratio(expectancy, ulcer_index),


        'downwave': calculate_ratio(excess_return, downwave),
        'alpha_downwave': calculate_ratio(alpha, downwave),
        'expectancy_downwave': calculate_ratio(expectancy, downwave),



        'treynor_ratio': calculate_ratio(excess_return, beta) * sqrt_periods,
        'simple_alpha': metrics["total_return"] - metrics["benchmark_return"],
        'alpha': alpha,
        'beta': beta,
        'ulcer_index': ulcer_index,
        'expectancy': expectancy,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'downwave': downwave,
        'drawdown_resistance': drawdown_resistance,
    }

    return metrics


# use for calcualting equity curve snapshots 


def _generate_snapshots(data: np.ndarray, valid_indices: np.ndarray) -> np.ndarray:
    """
    Generates a snapshot array based on valid indices.

    Args:
        data (np.ndarray): The original data array from which snapshots are taken.
        valid_indices (np.ndarray): An array of valid indices where snapshots should be taken.

    Returns:
        np.ndarray: An array where values at valid indices match the original data,
                    and intermediate values are filled with the last snapshot value.
    """
    if len(valid_indices) == 0:
        return np.full_like(data, data[0])
    
    valid_indices = valid_indices.astype(float)

    snapshot_data = np.empty_like(data)
    snapshot_data[0] = data[0]  # Always start with the first value

    last_valid_index = 0
    for i in range(1, len(data)):
        if i in valid_indices:
            snapshot_data[i] = data[i]
            last_valid_index = i
        else:
            snapshot_data[i] = snapshot_data[last_valid_index]

    return snapshot_data

def take_snapshots_by_indices(data: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """
    Generates a snapshot array based on specified indices.

    Args:
        data (np.ndarray): The original data array from which snapshots are taken.
        indices (np.ndarray): An array of indices where snapshots should be taken.

    Returns:
        np.ndarray: An array with snapshots at specified indices.
    """
    indices = indices.astype(float)

    valid_indices = np.unique(indices[(indices >= 0) & (indices < len(data))])

    return _generate_snapshots(data, valid_indices)

def take_snapshots_by_indicator(data: np.ndarray, indicator: np.ndarray) -> np.ndarray:
    """
    Generates a snapshot array based on an indicator array of 0s and 1s.

    Args:
        data (np.ndarray): The original data array from which snapshots are taken.
        indicator (np.ndarray): An array of the same length as `data`, with 1s indicating
                                where snapshots should be taken and 0s otherwise.

    Returns:
        np.ndarray: An array with snapshots at positions indicated by 1s in `indicator`.
    """
    if len(indicator) != len(data):
        raise ValueError("Indicator must be the same length as data.")
    
    indicator = indicator.astype(float)
    
    valid_indices = np.where(indicator == 1)[0]
    return _generate_snapshots(data, valid_indices)
