from typing import Tuple
import pandas as pd
import numpy as np
import pandas_ta as pta
from .exit_helpers import apply_trailing_stop_ema


def statistical_divergence_strategy(
    df: pd.DataFrame,
    decomp_window: int = 20,       # Window for price decomposition
    vol_window: int = 10,          # Window for volatility calculation
    zscore_window: int = 63,       # Window for zscore calculation
    entry_threshold: float = 2.0,   # Standard deviations for entry
    smooth_period: int = 3,        # Smoothing period for signals
    use_strategy_exits: bool = True,
    c1: float = 1.0,  # Zscore threshold multiplier
    c2: float = 1.0,  # Volatility filter multiplier
    c3: float = 1.0,  # Mean reversion strength multiplier
    c4: float = 1.0,  # Exit zscore multiplier
    c5: float = 1.0,  # Exit volatility multiplier
    tsl_ema_period: int = 5,
    tsl_params: list = [(5, 0), (0.5, 1), (0.1, 3)]
) -> Tuple[pd.Series, pd.Series]:
    """
    Statistical Arbitrage Divergence Strategy

    Mathematical Edge:
    1. Price series P(t) can be decomposed into trend μ(t) and residual ε(t):
       P(t) = μ(t) + ε(t)
    2. Residuals follow Ornstein-Uhlenbeck process:
       dε(t) = -θε(t)dt + σdW(t)
    3. Mean reversion strength θ increases with deviation magnitude

    Trading Edge:
    1. Exploits temporary statistical divergences
    2. Uses volatility regime filtering
    3. Adaptive thresholds based on market conditions
    """
    decomp_window, vol_window, zscore_window, smooth_period = int(
        decomp_window), int(vol_window), int(zscore_window), int(smooth_period)

    # Smooth price for noise reduction
    smooth_price = pta.ema(df['Close'], length=smooth_period)

    # Decompose price into trend and residual
    trend = smooth_price.rolling(window=decomp_window).mean()
    residual = smooth_price - trend

    # Calculate rolling statistics
    rolling_mean = residual.rolling(window=zscore_window).mean()
    rolling_std = residual.rolling(window=zscore_window).std()
    zscore = (residual - rolling_mean) / rolling_std

    # Calculate volatility metrics
    returns = smooth_price.pct_change()
    volatility = returns.rolling(window=vol_window).std()
    vol_zscore = (volatility - volatility.rolling(window=zscore_window).mean()) / \
        volatility.rolling(window=zscore_window).std()

    # Calculate mean reversion strength (theta)
    # Using AR(1) coefficient as proxy for mean reversion strength
    residual_lag = residual.shift(1)
    rolling_cov = (
        residual * residual_lag).rolling(window=decomp_window).mean()
    rolling_var = (residual_lag ** 2).rolling(window=decomp_window).mean()
    theta = 1 - (rolling_cov / rolling_var)

    # Enhanced mean reversion signal
    mr_signal = -zscore * theta

    # Entry conditions with parameterized constants
    entries = (
        (zscore < -entry_threshold * c1) &           # Statistical deviation
        (vol_zscore < entry_threshold * c2) &        # Low volatility regime
        # Strong mean reversion potential
        (mr_signal > c3)
    )

    # Initialize exits
    exits = pd.Series(False, index=df.index)

    # Strategy-specific exits if enabled
    if use_strategy_exits:
        exits = (
            (zscore > -entry_threshold/2 * c4) |     # Residual normalization
            (vol_zscore > entry_threshold * c5)      # Volatility spike
        )

    # Apply trailing stop loss
    exits |= apply_trailing_stop_ema(
        df, entries, exits,
        tsl_params=tsl_params
    )

    return entries, exits


# # Parameter space for hyperoptimization
# strategy_name = 'statistical_divergence_strategy'
# param_space = {
#     'decomp_window': hp.quniform('decomp_window', 10, 50, 1),
#     'vol_window': hp.quniform('vol_window', 5, 30, 1),
#     'zscore_window': hp.quniform('zscore_window', 20, 100, 1),
#     'entry_threshold': hp.uniform('entry_threshold', 1.0, 3.0),
#     'smooth_period': hp.quniform('smooth_period', 2, 10, 1),
#     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
#     'c1': hp.uniform('c1', 0.1, 3.0),
#     'c2': hp.uniform('c2', 0.1, 3.0),
#     'c3': hp.uniform('c3', 0.0, 0.5),
#     'c4': hp.uniform('c4', 0.1, 3.0),
#     'c5': hp.uniform('c5', 0.1, 3.0),
#     'tsl_ema_period': hp.quniform('tsl_ema_period', 3, 15, 1),
#     'tsl_params': create_tsl_hyperopt_space(),
# }


# def check_constraints(params, verbose=False):
#     """Check constraints for Statistical Divergence Strategy parameters."""
#     if verbose:
#         print(f"Checking constraints for params: {params}")

#     # Ensure zscore_window is greater than decomp_window
#     if params['zscore_window'] <= params['decomp_window']:
#         if verbose:
#             print("zscore_window must be greater than decomp_window")
#         return {'loss': float('inf'), 'status': 'fail'}

#     # Ensure decomp_window is greater than vol_window
#     if params['decomp_window'] <= params['vol_window']:
#         if verbose:
#             print("decomp_window must be greater than vol_window")
#         return {'loss': float('inf'), 'status': 'fail'}

#     return None
