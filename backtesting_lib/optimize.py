import itertools
import numpy as np
from backtesting_lib.backtester import run_backtesting, analyze_results, sort_strategies_by_performance, save_results, save_aggregated_results
from tqdm import tqdm

def optimize_strategy_params(strategy_name, symbols, num_candles, interval, param_grid, data_dict, should_plot=False, max_workers_strategies=4, max_workers_symbols=6):
    """
    Perform grid search optimization for strategy parameters.

    Parameters:
    - strategy_name (str): The name of the strategy to optimize.
    - symbols (list): List of symbols to backtest on.
    - num_candles (int): Number of candles for backtesting.
    - interval (str): Data interval.
    - param_grid (dict): Dictionary where keys are parameter names and values are lists of parameter values to test.
    - data_dict (dict): Pre-loaded data for all symbols.
    - should_plot (bool): Whether to plot the strategy performance.
    - max_workers_strategies (int): Number of workers for parallelizing strategies.
    - max_workers_symbols (int): Number of workers for parallelizing symbols.

    Returns:
    - sorted_results (list): Sorted list of all parameter sets and their performance.
    """
    param_names = list(param_grid.keys())
    param_combinations = list(itertools.product(*param_grid.values()))

    all_results = []

    for param_comb in tqdm(param_combinations, desc='Optimizing Parameters'):
        params = dict(zip(param_names, param_comb))
        strategy_params = {strategy_name: params}

        all_results_dict = run_backtesting(
            symbols,
            num_candles,
            interval,
            should_plot,
            [strategy_name],
            strategy_params,
            data_dict=data_dict,  # Pass pre-loaded data
            parallelize_strategies=True,
            parallelize_symbols=True,
            max_workers_strategies=max_workers_strategies,
            max_workers_symbols=max_workers_symbols
        )

        aggregated_performance = analyze_results(all_results_dict)
        sorted_strategies = sort_strategies_by_performance(aggregated_performance)

        total_return = sorted_strategies[0][1]['overall_mean']
        all_results.append((params, sorted_strategies[0][1]))

        # Save intermediate results
        save_results(aggregated_performance[strategy_name], strategy_name, interval)

    # Sort all results by overall_mean in descending order
    sorted_results = sorted(all_results, key=lambda x: x[1]['overall_mean'], reverse=True)
    return sorted_results
