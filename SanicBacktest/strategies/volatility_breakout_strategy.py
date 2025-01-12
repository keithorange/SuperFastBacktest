from typing import Tuple
import pandas as pd
import numpy as np
import pandas_ta as pta
from .exit_helpers import apply_trailing_stop_ema


def volatility_breakout_strategy(
    df: pd.DataFrame,
    vol_window: int = 20,
    price_window: int = 10,
    std_dev_threshold: float = 2.0,
    momentum_period: int = 5,
    smooth_period: int = 3,
    use_strategy_exits: bool = True,
    # Entry condition multipliers
    c1: float = 1.0,  # Volatility expansion multiplier
    c2: float = 1.0,  # Price momentum multiplier
    c3: float = 1.0,  # Volume surge multiplier
    c4: float = 1.0,  # Trend alignment multiplier
    # Exit condition multipliers
    c5: float = 1.0,  # Volatility contraction multiplier
    c6: float = 1.0,  # Momentum reversal multiplier
    c7: float = 1.0,  # Volume decline multiplier
    c8: float = 1.0,  # Price reversal multiplier
    c9: float = 1.0,  # Moving average cross multiplier
    tsl_ema_period: int = 5,
    tsl_params: list = [(5, 0), (0.5, 1), (0.1, 3)]
) -> Tuple[pd.Series, pd.Series]:
    """
    Volatility Breakout Strategy with Fully Parameterized Entry/Exit Conditions

    Mathematical Edge:
    1. Volatility clustering (Mandelbrot's observation)
    2. Price momentum persistence in breakout direction
    3. Volume-price confirmation principle

    Mathematical Basis:
    For price series P(t), strategy uses:
    1. Volatility: σ(t) = std(returns(t-n:t))
    2. Z-score: z(t) = (σ(t) - μ(σ)) / std(σ)
    3. Momentum: M(t) = P(t)/P(t-n) - 1
    """
    vol_window = int(vol_window)
    price_window = int(price_window)
    momentum_period = int(momentum_period)
    smooth_period = int(smooth_period)

    # Calculate returns and smooth price
    returns = df['Close'].pct_change()
    smooth_price = pta.ema(df['Close'], length=smooth_period)

    # Volatility metrics
    rolling_vol = returns.rolling(vol_window).std()
    vol_mean = rolling_vol.rolling(vol_window).mean()
    vol_std = rolling_vol.rolling(vol_window).std()
    vol_zscore = (rolling_vol - vol_mean) / vol_std

    # Price momentum
    price_momentum = smooth_price.pct_change(momentum_period)
    price_ma = pta.ema(df['Close'], length=price_window)

    # Volume analysis (if volume data available)
    if 'Volume' in df.columns:
        volume_ma = df['Volume'].rolling(vol_window).mean()
        volume_ratio = df['Volume'] / volume_ma
    else:
        volume_ratio = pd.Series(1, index=df.index)

    # Trend metrics
    trend_direction = (smooth_price > price_ma).astype(int)

    # Entry conditions with parameterized constants
    entries = (
        (vol_zscore > std_dev_threshold * c1) &          # Volatility expansion
        (price_momentum > 0 * c2) &                      # Positive momentum
        (volume_ratio > 1.0 * c3) &                      # Above average volume
        (trend_direction * c4)                           # Trend alignment
    )

    # Initialize exits
    exits = pd.Series(False, index=df.index)

    # Strategy-specific exits if enabled
    if use_strategy_exits:
        exits = (
            # Volatility contraction
            (vol_zscore < -std_dev_threshold * c5) |
            # Momentum reversal
            (price_momentum < 0 * c6) |
            # Volume decline
            (volume_ratio < 0.7 * c7) |
            # Price reversal
            (smooth_price < price_ma * c8) |
            # Moving average cross
            ((smooth_price / price_ma - 1) < -0.01 * c9)
        )

    # Apply trailing stop loss
    exits |= apply_trailing_stop_ema(
        df, entries, exits,
        tsl_params=tsl_params
    )

    return entries, exits


# # Parameter space for hyperoptimization
# strategy_name = 'volatility_breakout_strategy'
# param_space = {
#     'vol_window': hp.quniform('vol_window', 10, 50, 1),
#     'price_window': hp.quniform('price_window', 5, 30, 1),
#     'std_dev_threshold': hp.uniform('std_dev_threshold', 1.0, 3.0),
#     'momentum_period': hp.quniform('momentum_period', 3, 15, 1),
#     'smooth_period': hp.quniform('smooth_period', 2, 10, 1),
#     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
#     # Entry condition multipliers
#     'c1': hp.uniform('c1', 0.1, 3.0),
#     'c2': hp.uniform('c2', 0.1, 3.0),
#     'c3': hp.uniform('c3', 0.1, 3.0),
#     'c4': hp.uniform('c4', 0.1, 3.0),
#     # Exit condition multipliers
#     'c5': hp.uniform('c5', 0.1, 3.0),
#     'c6': hp.uniform('c6', 0.1, 3.0),
#     'c7': hp.uniform('c7', 0.1, 3.0),
#     'c8': hp.uniform('c8', 0.1, 3.0),
#     'c9': hp.uniform('c9', 0.1, 3.0),
#     'tsl_ema_period': hp.quniform('tsl_ema_period', 3, 15, 1),
#     'tsl_params': create_tsl_hyperopt_space(),
# }


# def check_constraints(params, verbose=False):
#     """Check constraints for Volatility Breakout Strategy parameters."""
#     if verbose:
#         print(f"Checking constraints for params: {params}")

#     # Ensure momentum period is less than price window
#     if params['momentum_period'] >= params['price_window']:
#         if verbose:
#             print("momentum_period must be less than price_window")
#         return {'loss': float('inf'), 'status': 'fail'}

#     # Ensure smooth period is less than momentum period
#     if params['smooth_period'] >= params['momentum_period']:
#         if verbose:
#             print("smooth_period must be less than momentum_period")
#         return {'loss': float('inf'), 'status': 'fail'}

#     return None
