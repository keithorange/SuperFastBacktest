from typing import Tuple
import pandas as pd
import numpy as np
import pandas_ta as pta
from .exit_helpers import apply_trailing_stop_ema


def calculus_trend_strategy(
    df: pd.DataFrame,
    velocity_period: int = 5,      # Period for price velocity calculation
    accel_period: int = 3,         # Period for acceleration calculation
    smooth_period: int = 3,        # Period for smoothing price
    fast_period: int = 13,         # Fast EMA for crossover confirmation
    slow_period: int = 48,         # Slow EMA for trend direction
    min_velocity: float = 0.001,   # Minimum velocity threshold
    min_accel: float = 0.0002,     # Minimum acceleration threshold
    use_strategy_exits: bool = False,
    c1: float = 1.0,  # Velocity multiplier
    c2: float = 1.0,  # Acceleration multiplier
    c3: float = 1.0,  # Trend alignment multiplier
    c4: float = 1.0,  # Exit velocity multiplier
    c5: float = 1.0,  # Exit acceleration multiplier
    tsl_params: list = [(5, 0, 12), (0.5, 1, 12), (0.1, 3, 12)]
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculus-Based Price Action Trend Strategy

    Mathematical Edge Components:
    1. First derivative (velocity) identifies trend initiation
    2. Second derivative (acceleration) confirms trend momentum
    3. Price-EMA crossover validates trend direction
    4. Multiple timeframe confluence reduces false signals

    Mathematical Proof:
    For price function P(t), strategy uses:
    1. Velocity: v(t) = dP/dt ≈ (P(t) - P(t-1))/Δt
    2. Acceleration: a(t) = d²P/dt² ≈ (v(t) - v(t-1))/Δt
    3. Trend Alignment: P(t) > EMA(P(t)) indicates uptrend

    Component Synergy:
    - Velocity catches early trend moves
    - Acceleration confirms trend strength
    - EMA crossover reduces false signals
    - Multi-timeframe validation reduces whipsaws
    """

    # Smooth price data to reduce noise
    smooth_price = pta.ema(df['Close'], length=smooth_period)

    # Calculate first derivative (velocity)
    velocity = smooth_price.diff(velocity_period) / velocity_period
    velocity_smoothed = pta.ema(velocity, length=velocity_period)

    # Calculate second derivative (acceleration)
    acceleration = velocity.diff(accel_period) / accel_period
    accel_smoothed = pta.ema(acceleration, length=accel_period)

    # Calculate EMAs for trend confirmation
    fast_ema = pta.ema(df['Close'], length=fast_period)
    slow_ema = pta.ema(df['Close'], length=slow_period)

    # Calculate trend alignment
    price_above_fast = df['Close'] > fast_ema
    fast_above_slow = fast_ema > slow_ema

    # Entry conditions with parameterized constants
    entries = (
        (velocity_smoothed > min_velocity * c1) &         # Strong upward velocity
        (accel_smoothed > min_accel * c2) &              # Positive acceleration
        (price_above_fast & fast_above_slow) * c3        # Trend alignment
    )

    # Initialize exits
    exits = pd.Series(False, index=df.index)

    # Strategy-specific exits if enabled
    if use_strategy_exits:
        exits = (
            (velocity_smoothed < -min_velocity * c4) |    # Velocity reversal
            (accel_smoothed < -min_accel * c5)           # Acceleration reversal
        )

    # Apply trailing stop loss
    exits |= apply_trailing_stop_ema(
        df, entries, exits,
        tsl_params=tsl_params,
    )

    return entries, exits


# # Parameter space for hyperoptimization
# strategy_name = 'calculus_trend_strategy'
# param_space = {
#     'velocity_period': hp.quniform('velocity_period', 3, 20, 1),
#     'accel_period': hp.quniform('accel_period', 2, 10, 1),
#     'smooth_period': hp.quniform('smooth_period', 2, 10, 1),
#     'fast_period': hp.quniform('fast_period', 8, 21, 1),
#     'slow_period': hp.quniform('slow_period', 30, 89, 1),
#     'min_velocity': hp.loguniform('min_velocity', np.log(0.0001), np.log(0.01)),
#     'min_accel': hp.loguniform('min_accel', np.log(0.00001), np.log(0.001)),
#     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
#     'c1': hp.uniform('c1', 0.1, 3.0),
#     'c2': hp.uniform('c2', 0.1, 3.0),
#     'c3': hp.uniform('c3', 0.1, 3.0),
#     'c4': hp.uniform('c4', 0.1, 3.0),
#     'c5': hp.uniform('c5', 0.1, 3.0),
#     'tsl_params': create_tsl_hyperopt_space(),
# }


# def check_constraints(params, verbose=False):
#     """Check constraints for Calculus Trend Strategy parameters."""
#     if verbose:
#         print(f"Checking constraints for params: {params}")

#     # Ensure fast period is less than slow period
#     if params['fast_period'] >= params['slow_period']:
#         if verbose:
#             print("fast_period must be less than slow_period")
#         return {'loss': float('inf'), 'status': 'fail'}

#     # Ensure velocity period is greater than acceleration period
#     if params['velocity_period'] <= params['accel_period']:
#         if verbose:
#             print("velocity_period must be greater than accel_period")
#         return {'loss': float('inf'), 'status': 'fail'}

#     return None
