import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from hyperopt import fmin, tpe, hp, Trials

def normalize_price_data(data, center, range_size, window_size, global_normalization):
    """Normalized price data using only data within the rolling window"""
    price_cols = list(set(data.columns) & {'Open', 'High', 'Low', 'Close'})
    if not price_cols:
        raise ValueError(f"No OHLC columns found in data! columns are {list(data.columns)}")

    result = data.copy()

    if global_normalization:
        # Global normalization logic remains unchanged
        global_min = data[price_cols].min().min()
        global_max = data[price_cols].max().max()
        
        if global_max == global_min:
            return data.copy()

        offset = center - range_size / 2
        scale_factor = range_size / (global_max - global_min)

        for col in price_cols:
            result[col] = (data[col] - global_min) * scale_factor + offset
    else:
        # Rolling window normalization
        window_min_series = []
        window_max_series = []
        
        for i in range(len(data)):
            start_idx = max(0, i - window_size + 1)
            window_data = data.iloc[start_idx:i+1][price_cols]
            window_min = window_data.min().min()
            window_max = window_data.max().max()
            window_min_series.append(window_min)
            window_max_series.append(window_max)
        
        window_mins = pd.Series(window_min_series, index=data.index)
        window_maxs = pd.Series(window_max_series, index=data.index)
        
        offset = center - range_size / 2
        scale_factors = range_size / (window_maxs - window_mins)
        scale_factors = scale_factors.replace([np.inf, -np.inf], 1)  # Handle division by zero
        
        for col in price_cols:
            result[col] = (data[col] - window_mins) * scale_factors + offset

        # Handle the first window_size-1 candles
        for i in range(window_size - 1):
            window_data = data.iloc[:i+1][price_cols]
            window_min = window_data.min().min()
            window_max = window_data.max().max()
            if window_max != window_min:
                scale_factor = range_size / (window_max - window_min)
                for col in price_cols:
                    result.loc[data.index[i], col] = (data.iloc[i][col] - window_min) * scale_factor + offset

    # Normalize volume if present
    if 'Volume' in data.columns:
        if global_normalization:
            vol_min = data['Volume'].min()
            vol_max = data['Volume'].max()
        else:
            vol_rolling = data['Volume'].rolling(window_size, min_periods=1)
            vol_min = vol_rolling.min()
            vol_max = vol_rolling.max()
        
        vol_range = vol_max - vol_min
        vol_range[vol_range == 0] = 1  # Avoid division by zero
        result['Volume'] = (data['Volume'] - vol_min) / vol_range * range_size + offset

    return result

def global_normalization(data, center=100, range_size=50):
    """Apply global normalization to the data."""
    global_min = data.min()
    global_max = data.max()
    offset = center - range_size / 2
    scale_factor = range_size / (global_max - global_min)
    return (data - global_min) * scale_factor + offset


def calculate_returns(data, signals):
    """Calculate cumulative returns based on signals."""
    returns = data.pct_change().fillna(0)  # Calculate returns
    strategy_returns = returns * signals.shift(1).fillna(0)  # Apply signals
    return strategy_returns.cumsum()  # Cumulative returns


def generate_random_signals(num_charts, length):
    """Generate random entry/exit signals for each chart."""
    all_signals = []
    for _ in range(num_charts):
        signals = np.random.choice([-1, 0, 1], size=length)
        all_signals.append(pd.Series(signals))
    return all_signals


def generate_simple_random_walk(num_charts, length, initial_price=10000, step_size=5):
    """
    Generate unique price data using a simple random walk.

    Parameters:
    - num_charts (int): Number of price series to generate.
    - length (int): Length of each price series.
    - initial_price (float): The starting price for each series.
    - step_size (float): The maximum amount by which the price can change each step.

    Returns:
    - list: A list of Pandas DataFrames containing the generated price data.
    """
    #  Create an array for the random changes
    changes = np.random.uniform(-step_size, step_size,
                                size=(num_charts, length - 1))

    # Initialize the prices array
    prices = np.zeros((num_charts, length))

    # Set the initial prices
    prices[:, 0] = initial_price

    # Calculate the cumulative sum of changes along the rows
    # Ensure prices are non-negative and avoid abrupt drops
    for i in range(1, length):
        # Update prices based on previous price and current change
        prices[:, i] = np.maximum(prices[:, i-1] + changes[:, i-1], 0)

        # Optional: Ensure some minimum change to avoid flat lines
        if np.all(changes[:, i-1] <= 0):
            # If all changes are negative or zero, add a small positive change
            prices[:, i] += np.random.uniform(0.1, 1.0, size=num_charts)

    # Convert each row to a DataFrame
    price_data = [pd.DataFrame(prices[i], columns=["Price"])
                  for i in range(num_charts)]

    return price_data


if __name__ == "__main__":
    # Parameters
    num_charts = 2000  # Total number of charts
    length = 1000     # Length of each chart (N)

    price_dfs = generate_simple_random_walk(num_charts, length)
    signals = generate_random_signals(num_charts, length)

    # Define the search space for Hyperopt
    space = hp.quniform('window_size', 30, 1000, 1)

    import numpy as np

    # Assuming all necessary functions (global_normalization, calculate_returns, etc.) are defined above

    # Define the path for the results file
    results_file = 'top_results.json'

    def update_results_file(result_entry):
        """Read current results from file, add new entry, sort by total_cumulative_return, and write back."""
        # Load existing results if the file exists
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                all_results = json.load(f)
        else:
            all_results = []

        # Add the new result entry
        all_results.append(result_entry)

        # Sort by total cumulative return and keep only top N results
        top_n = 100
        sorted_results = sorted(
            all_results, key=lambda x: x['total_cumulative_return'], reverse=True)[:top_n]

        # Write sorted top results back to the file
        with open(results_file, 'w') as f:
            json.dump(sorted_results, f, indent=4)

    def objective(window_size):
        """Objective function for Hyperopt optimization."""
        window_size = int(window_size)
        cumulative_returns_list = []

        # Calculate returns for each chart with its respective signals
        for i in range(num_charts):
            normalized_data = global_normalization(price_dfs[i]['Price'])
            cumulative_returns = calculate_returns(normalized_data, signals[i])
            cumulative_returns_list.append(cumulative_returns)

        # Calculate final returns for all charts
        final_returns = [returns.iloc[-1]
                         for returns in cumulative_returns_list]

        # Mean and std of final cumulative returns
        mean_cumulative_return = np.mean(final_returns)
        std_cumulative_return = np.std(final_returns)

        # Calculate total cumulative return
        total_cumulative_return = np.sum(final_returns)

        # Calculate Sharpe ratio (optional)
        sharpe_ratio = mean_cumulative_return / (std_cumulative_return + 1e-6)

        poodle_ratio = ((total_cumulative_return*abs(total_cumulative_return)) /
                        (np.log1p(1+np.sqrt(1+window_size))*std_cumulative_return))
        # Store the result with parameters inside the objective function
        result_entry = {
            "poodle_ratio": poodle_ratio,
            'window_size': window_size,
            'total_cumulative_return': total_cumulative_return,
            'mean_cumulative_return': mean_cumulative_return,
            'std_cumulative_return': std_cumulative_return,
            'sharpe_ratio': sharpe_ratio
        }

        # Update results file with the new entry
        update_results_file(result_entry)

        # Return negative Sharpe ratio for maximization
        # return -sharpe_ratio

        return -1*poodle_ratio

    # Define the search space for Hyperopt
    space = hp.quniform('window_size', 3, 1000, 1)

    # Run the optimization
    trials = Trials()
    best = fmin(fn=objective,
                space=space,
                algo=tpe.suggest,
                max_evals=1000,
                trials=trials,
                max_queue_len=2)

    best_window_size = int(best['window_size'])
    print(f"Best window size: {best_window_size}")

    # Recalculate cumulative returns again for visualization (same as before)
    cumulative_returns_list = []
    for i in range(num_charts):
        normalized_data = global_normalization(price_dfs[i]['Price'])
        cumulative_returns = calculate_returns(normalized_data, signals[i])
        cumulative_returns_list.append(cumulative_returns)

    # Calculate mean, max, and min cumulative returns for visualization (same as before)
    mean_cumulative_returns = np.mean(cumulative_returns_list, axis=0)
    max_cumulative_returns = np.max(cumulative_returns_list, axis=0)
    min_cumulative_returns = np.min(cumulative_returns_list, axis=0)
    median_cumulative_returns = np.median(cumulative_returns_list, axis=0)

    # Visualize the results (same as before)
    plt.figure(figsize=(12, 6))
    plt.plot(mean_cumulative_returns,
             label='Mean Cumulative Returns', color='blue')
    plt.plot(median_cumulative_returns,
             label='Median Cumulative Returns', color='orange')

    plt.xlabel('Time')
    plt.ylabel('Cumulative Returns')
    plt.title(
        f'Cumulative Returns with Optimal Rolling Window Size ({best_window_size})')
    plt.legend()
    plt.grid()
    plt.show()

    # Plot the optimization process (same as before)
    plt.figure(figsize=(12, 6))
    xs = [t['misc']['vals']['window_size'][0]
          for t in trials.trials]  # Extract window sizes evaluated
    # Extract corresponding objective scores (negated for plotting)
    ys = [-t['result']['loss'] for t in trials.trials]

    plt.scatter(xs, ys, color='blue', label='Objective Scores')
    plt.xlabel('Window Size')
    plt.ylabel('Objective Score (higher is better)')
    plt.title('Hyperopt Optimization Process')
    plt.grid()
    plt.legend()
    plt.show()
