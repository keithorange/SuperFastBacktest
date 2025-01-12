# Ultra-Short-Term Scalping Strategies (Extremely tight stops, rapid adjustments)
from numba import jit, njit
import pandas_ta as pta
import pandas_ta as ta
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib

from hyperopt import hp

matplotlib.use('Agg')  # Use the 'Agg' backend

# print("NOTE: using SIMPLE tsl 2 part for testing hyperopt")

def create_tsl_hyperopt_space(max_tsl=50, min_activ_pct=0.1, max_activ_pct=50, max_ema_period=40, use_3part=True):
    """
    Create a hyperopt space for trailing stop strategies with constraints.

    The trailing stop loss percentage ranges from 0% to max_tsl.
    The activation profit percentage ranges from 0% to max_activ_pct.
    The EMA period ranges from 5 to max_ema_period.

    Parameters:
    - max_tsl (float): Maximum trailing stop loss percentage (default is 1%).
    - min_activ_pct (float): Minimum activation profit percentage (default is 0.3%).
    - max_activ_pct (float): Maximum activation profit percentage (default is 3%).
    - max_ema_period (int): Maximum EMA period (default is 30).
    - use_3part (bool): Whether to use 3 parts or 2 parts (default is True).
    """

    first_tsl = [hp.uniform('tsl_pct_1', 0, max_tsl), 0,
                 hp.quniform('ema_period_1', 3, max_ema_period, 1)]
    second_tsl = [hp.uniform('tsl_pct_2', 0, max_tsl),
                  hp.uniform('activ_pct_2', min_activ_pct, max_activ_pct),
                  hp.quniform('ema_period_2', 3, max_ema_period, 1)]
    third_tsl = [hp.uniform('tsl_pct_3', 0, max_tsl),
                 hp.uniform('activ_pct_3', min_activ_pct, max_activ_pct),
                 hp.quniform('ema_period_3', 3, max_ema_period, 1)]

    # USES A 3 part LIST with TSL, activation %, and EMA period
    if use_3part:
        return [first_tsl, second_tsl, third_tsl]
    else:
        return [first_tsl, second_tsl]


def get_stop_pct(current_profit, tsl_params):
    """
    Get the appropriate stop percentage based on current profit.
    Now handles 3-element lists where the third element is the EMA period.
    """
    for stop, profit, _ in reversed(tsl_params):
        if current_profit >= profit:
            return stop
    # Return the initial stop if no profit threshold is met
    return tsl_params[0][0]


# def apply_trailing_stop_ema(data, entry_signals, exit_signals, tsl_params, price_column='Close', plot=False):
#     """
#     Apply trailing stop using EMA.
#     tsl_params: List of [tsl_pct, activ_pct, ema_period] lists
#     """
#     # Validate all parameters are provided
#     if not all(len(params) == 3 for params in tsl_params):
#         raise ValueError(
#             "Each TSL parameter set must have [tsl_pct, activ_pct, ema_period]")

#     # Calculate EMA using the first set's period
#     ema_period = int(tsl_params[0][2])
#     value_column = data[price_column].ewm(span=ema_period, adjust=False).mean()

#     prices = data[price_column].values
#     values = value_column.values

#     in_position = False
#     entry_price = np.nan
#     highest_value = np.nan
#     stop_price = np.nan

#     trade_entries = []
#     trade_exits = []

#     for i in range(len(data)):
#         if entry_signals.iloc[i] and not in_position:
#             # Enter position
#             in_position = True
#             entry_price = prices[i]
#             highest_value = values[i]
#             trade_entries.append((i, prices[i]))

#             # Set initial stop price
#             stop_price = entry_price * (1 - tsl_params[0][0] / 100)

#         elif in_position:
#             # Update highest value
#             if values[i] > highest_value:
#                 highest_value = values[i]

#                 # Find appropriate parameters based on current profit
#                 current_profit = (highest_value / entry_price - 1) * 100

#                 # Get appropriate stop percentage based on profit level
#                 for tsl_pct, activ_pct, ema_period in reversed(tsl_params):
#                     if current_profit >= activ_pct:
#                         new_stop_price = highest_value * (1 - tsl_pct / 100)
#                         stop_price = max(stop_price, new_stop_price)
#                         break

#             # Check for exit
#             if prices[i] <= stop_price or exit_signals.iloc[i]:
#                 exit_signals.iloc[i] = True
#                 in_position = False
#                 trade_exits.append((i, prices[i]))

#                 # Reset tracking variables
#                 entry_price = np.nan
#                 highest_value = np.nan
#                 stop_price = np.nan

#     return exit_signals.copy()


#@njit
def apply_trailing_stop_ema_fast(prices, values, entry_signals, exit_signals, tsl_params):
    """
    Apply trailing stop using EMA (optimized version).
    tsl_params: 2D array of [tsl_pct, activ_pct, ema_period] lists
    """
    n = len(prices)
    in_position = False
    entry_price = 0.0
    highest_value = 0.0
    stop_price = 0.0

    for i in range(n):
        if entry_signals[i] and not in_position:
            # Enter position
            in_position = True
            entry_price = prices[i]
            highest_value = values[i]

            # Set initial stop price
            stop_price = entry_price * (1 - tsl_params[0, 0] / 100)

        elif in_position:
            # Update highest value
            if values[i] > highest_value:
                highest_value = values[i]

                # Find appropriate parameters based on current profit
                current_profit = (highest_value / entry_price - 1) * 100

                # Get appropriate stop percentage based on profit level
                for j in range(len(tsl_params) - 1, -1, -1):
                    if current_profit >= tsl_params[j, 1]:
                        new_stop_price = highest_value * \
                            (1 - tsl_params[j, 0] / 100)
                        stop_price = max(stop_price, new_stop_price)
                        break

            # Check for exit
            if prices[i] <= stop_price or exit_signals[i]:
                exit_signals[i] = True
                in_position = False

                # Reset tracking variables
                entry_price = 0.0
                highest_value = 0.0
                stop_price = 0.0

    return exit_signals


def apply_trailing_stop_ema(data, entry_signals, exit_signals, tsl_params, price_column='Close', plot=False):
    """
    Apply trailing stop using EMA.
    tsl_params: List of [tsl_pct, activ_pct, ema_period] lists
    """
    # Validate all parameters are provided
    if not all(len(params) == 3 for params in tsl_params):
        raise ValueError(
            "Each TSL parameter set must have [tsl_pct, activ_pct, ema_period]")

    # Calculate EMA using the first set's period
    ema_period = int(tsl_params[0][2])
    value_column = data[price_column].ewm(span=ema_period, adjust=False).mean()

    prices = data[price_column].values
    values = value_column.values

    # Convert tsl_params to a numpy array for use in the JIT-compiled function
    tsl_params_array = np.array(tsl_params)

    # Convert input signals to numpy arrays if they're pandas Series
    entry_signals_array = entry_signals.values if isinstance(
        entry_signals, pd.Series) else entry_signals
    exit_signals_array = exit_signals.values if isinstance(
        exit_signals, pd.Series) else exit_signals

    # Call the optimized function
    exit_signals_array = apply_trailing_stop_ema_fast(
        prices, values, entry_signals_array, exit_signals_array, tsl_params_array)

    # Convert the result back to a pandas Series if the input was a Series
    if isinstance(exit_signals, pd.Series):
        exit_signals = pd.Series(exit_signals_array, index=exit_signals.index)
    else:
        exit_signals = exit_signals_array

    return exit_signals


#@njit
def _apply_take_profit_helper(entry_values, exit_values, entry_signals, exit_signals, take_profit_percentage):
    """
    Helper function to apply take profit logic.

    Parameters:
    entry_values (array): Array of values used for entry (could be prices or EMA)
    exit_values (array): Array of values used for exit (typically prices)
    entry_signals (array): Boolean array indicating entry signals
    exit_signals (array): Boolean array indicating exit signals
    take_profit_percentage (float): Take profit percentage (e.g., 5 for 5%)

    Returns:
    array: Updated exit signals
    """
    n = len(entry_values)
    in_position = False
    take_profit = 0.0

    for i in range(n):
        if entry_signals[i] and not in_position:
            # Enter position
            in_position = True
            entry_value = entry_values[i]
            take_profit = entry_value * (1 + (take_profit_percentage / 100))
        elif in_position:
            # Check for take profit exit
            if exit_values[i] >= take_profit:
                exit_signals[i] = True
                in_position = False
                take_profit = 0.0

    return exit_signals


def _ensure_numpy_array(data):
    """Convert input to numpy array if it's a pandas Series."""
    if hasattr(data, 'to_numpy'):
        return data.to_numpy(), data.index
    return np.array(data), None

def _wrap_result(result, index):
    """Wrap the result in a pandas Series if an index was provided."""
    if index is not None:
        return pd.Series(result, index=index)
    return result


def apply_take_profit(entry_values, exit_values, entry_signals, exit_signals, take_profit_percentage):
    """Generic function to apply take profit logic."""
    entry_values_np, index = _ensure_numpy_array(entry_values)
    exit_values_np, _ = _ensure_numpy_array(exit_values)
    entry_signals_np, _ = _ensure_numpy_array(entry_signals)
    exit_signals_np, _ = _ensure_numpy_array(exit_signals)

    result = _apply_take_profit_helper(
        entry_values_np, exit_values_np, entry_signals_np, exit_signals_np, take_profit_percentage
    )

    return _wrap_result(result, index)

def apply_take_profit_prices(prices, entry_signals, exit_signals, take_profit_percentage):
    """Apply a simple take profit calculation based on a percentage of the entry price."""
    return apply_take_profit(prices, prices, entry_signals, exit_signals, take_profit_percentage)

def apply_take_profit_ema_entry(prices, ema, entry_signals, exit_signals, take_profit_percentage):
    """Apply a take profit calculation based on a percentage of the EMA at entry,
    but use actual prices for exit determination."""
    return apply_take_profit(ema, prices, entry_signals, exit_signals, take_profit_percentage)

def calculate_returns(data, trade_entries, trade_exits, price_column='Close'):
    returns = []
    for entry, exit in zip(trade_entries, trade_exits):
        entry_price = data[price_column].iloc[entry[0]]
        exit_price = data[price_column].iloc[exit[0]]
        returns.append((exit_price / entry_price) - 1)

    cumulative_returns = pd.Series(index=data.index, dtype=float)
    cumulative_returns.iloc[0] = 0

    current_return = 0
    for i, (entry, exit) in enumerate(zip(trade_entries, trade_exits)):
        current_return += returns[i]
        cumulative_returns.iloc[entry[0]:exit[0]+1] = current_return

    cumulative_returns = cumulative_returns.fillna(method='ffill').fillna(0)
    return cumulative_returns


def calculate_drawdowns(returns):
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown


def plot_trailing_stop(data, trade_entries, trade_exits, stop_levels, stop_changes, tsl_params, price_column='Close', plot_dir='trailing_stop_plots'):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(
        20, 15), gridspec_kw={'height_ratios': [2, 1]})

    # Plot price and stop levels on the first subplot
    ax1.plot(data.index, data[price_column], label='Price', color='blue')

    for entry in trade_entries:
        ax1.plot(data.index[entry[0]], entry[1], '^', markersize=10,
                 color='lime', label='Entry' if entry == trade_entries[0] else '')
    for exit in trade_exits:
        ax1.plot(data.index[exit[0]], exit[1], 'v', markersize=10,
                 color='red', label='Exit' if exit == trade_exits[0] else '')

    stop_x, stop_y = zip(*stop_levels)
    ax1.plot(data.index[list(stop_x)], stop_y, '--',
             color='purple', label='Stop Level', linewidth=2)

    last_stop_pct = None
    for i, stop_price, stop_pct in stop_changes:
        if stop_pct != last_stop_pct:
            ax1.plot(data.index[i], stop_price, 'o',
                     markersize=6, color='orange')
            ax1.annotate(f"{stop_pct*100:.2f}%", (data.index[i], stop_price), textcoords="offset points",
                         xytext=(0, 10), ha='center', va='bottom', fontsize=8, color='black', weight='bold', rotation=90)
            last_stop_pct = stop_pct

    ax1.set_title(f"Trailing Stop Strategy Test\nStrategy: {
                  tsl_params}")
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True)

    # Calculate and plot returns and drawdowns on the second subplot
    strategy_returns = calculate_returns(
        data, trade_entries, trade_exits, price_column)
    market_returns = data[price_column].pct_change().cumsum()
    drawdowns = calculate_drawdowns(strategy_returns)

    ax2.plot(data.index, strategy_returns,
             label='Strategy Returns', color='green')
    ax2.plot(data.index, market_returns,
             label='Market Returns', color='blue', alpha=0.5)
    ax2.plot(data.index, drawdowns, label='Drawdowns', color='red', alpha=0.5)

    ax2.set_title('Strategy Performance')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Returns / Drawdowns')
    ax2.legend()
    ax2.grid(True)

    # Add some performance metrics as text
    total_return = strategy_returns.iloc[-1]
    sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * \
        np.sqrt(252) if len(strategy_returns) > 1 else 0
    max_drawdown = drawdowns.min()

    metrics_text = f'Total Return: {total_return:.2%}\nSharpe Ratio: {
        sharpe_ratio:.2f}\nMax Drawdown: {max_drawdown:.2%}'
    ax2.text(0.02, 0.98, metrics_text, transform=ax2.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save the plot
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    strategy_name = '_'.join(
        [f"{stop}_{profit}" for stop, profit in tsl_params])
    filename = f"trailing_stop_{strategy_name}.png"
    filepath = os.path.join(plot_dir, filename)
    plt.savefig(filepath)
    plt.close(fig)  # Close the figure to free up memory

    print(f"Plot saved to {filepath}")
