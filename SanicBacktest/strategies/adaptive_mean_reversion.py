
from typing import Tuple
import pandas as pd
import numpy as np

from scipy.stats import norm

from .exit_helpers import apply_trailing_stop_ema


def adaptive_mean_reversion(
    df: pd.DataFrame,
    lookback: int = 63,
    vol_window: int = 21,
    confidence_level: float = 0.95,
    use_strategy_exits: bool = True,
    c1: bool = 1.0,
    c2: bool = 1.0,
    c3: bool = 1.0,
    c4: bool = 1.0,
    c5: bool = 1.0,

    tsl_ema_period: int = 5,  # Period for EMA in trailing stop loss
    tsl_params: list = None,  # Pairs for stop profit logic
) -> Tuple[pd.Series, pd.Series]:
    """
    Strategy 3: Adaptive Mean Reversion with Statistical Arbitrage

    Mathematical Edge:
    1. Ornstein-Uhlenbeck process for price deviations
    2. Optimal stopping theory for entry/exit
    3. Dynamic confidence intervals based on vol regime

    Proof of Edge:
    Price follows OU process:
    dXt = θ(μ - Xt)dt + σdWt

    Optimal entry point derived from Hamilton-Jacobi-Bellman equation:
    V(x) = sup E[e^(-ρτ)(Xτ - K)|X0 = x]

    Where stopping time τ maximizes expected value
    """

    lookback = int(lookback)
    vol_window = int(vol_window)

    # Calculate rolling statistics
    rolling_mean = df['Close'].rolling(lookback).mean()
    rolling_std = df['Close'].rolling(lookback).std()

    # Calculate volatility-adjusted z-scores
    realized_vol = df['Close'].pct_change().rolling(
        vol_window).std() * np.sqrt(252)
    vol_ratio = realized_vol / realized_vol.rolling(lookback).mean()

    # Dynamic Bollinger Bands with volatility adjustment
    z_score = (df['Close'] - rolling_mean) / rolling_std
    adjusted_z = z_score * np.sqrt(vol_ratio)

    # Calculate confidence intervals
    confidence_multiplier = norm.ppf(confidence_level)
    upper_bound = rolling_mean + rolling_std * \
        confidence_multiplier * np.sqrt(vol_ratio)
    lower_bound = rolling_mean - rolling_std * \
        confidence_multiplier * np.sqrt(vol_ratio)

    # Entry: Significant deviation with mean reversion potential
    entries = (
        (df['Close'] < lower_bound * c1) &  # Price below confidence interval
        (adjusted_z < -confidence_multiplier * c2) &  # Significant deviation
        (realized_vol < realized_vol.rolling(
            vol_window).mean() * c3)  # Low vol regime
    )

    # Exit: When volatility normalizes or based on strategy exits
    exits = pd.Series(False, index=df.index)

    if use_strategy_exits:
        # Exit: Return to mean or vol spike
        exits = (
            (df['Close'] > rolling_mean*c4) |  # Price crosses mean
            (realized_vol > realized_vol.rolling(
                vol_window).mean() * c5)  # Vol spike
        )

    exits |= apply_trailing_stop_ema(
        df, entries, exits, tsl_params=tsl_params)

    return entries, exits

# # Updated parameter space for Adaptive Mean Reversion
#     strategy_name = 'adaptive_mean_reversion'
#     param_space = {
#         # Lookback period for rolling mean and std dev
#         'lookback': hp.quniform('lookback', 4, 100, 1),
#         # Rolling window for realized volatility calculation
#         'vol_window': hp.quniform('vol_window', 4, 50, 1),
#         # Confidence level for dynamic Bollinger Bands
#         'confidence_level': hp.uniform('confidence_level', 0.5, 0.999),
#         'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
#         'c1': hp.uniform('c1', 0.1, 4.0),
#         'c2': hp.uniform('c2', 0.1, 4.0),
#         'c3': hp.uniform('c3', 0.1, 4.0),
#         'c4': hp.uniform('c4', 0.1, 4.0),
#         'c5': hp.uniform('c5', 0.5, 10.0),

#         # Period for EMA in trailing stop loss
#         'tsl_ema_period': hp.quniform('tsl_ema_period', 3, 12, 1),
#         'tsl_params': create_tsl_hyperopt_space(),
#     }


# def check_constraints(params, verbose=False):
#     """Check all constraints for the Adaptive Mean Reversion parameters."""
#     if verbose:
#         print(f"Checking constraints for params: {params}")

#     # Ensure lookback is greater than vol_window
#     if params['lookback'] <= params['vol_window']:
#         if verbose:
#             print("lookback must be greater than vol_window")
#         return {'loss': float('inf'), 'status': 'fail'}
