"""
Data Preprocessing for Backtesting

This function prepares financial data for backtesting. Key steps:

1. Load data (e.g., from JSON, CSV, API)
2. Convert to pandas DataFrame with DatetimeIndex
3. Ensure OHLCV columns (Open, High, Low, Close, Volume)
4. Convert index to timezone-aware datetime (default: America/New_York)

Specifications:
- Input: Raw data source (file path, API response, etc.)
- Output: Dict[str, Dict[str, pd.DataFrame]]
  Format: {interval: {symbol: dataframe}}
- DataFrame requirements:
  - Index: timezone-aware DatetimeIndex
  - Columns: ['Open', 'High', 'Low', 'Close', 'Volume']
  - All columns should be numeric (float or int)

Example output DataFrame index:
Timestamp('YYYY-MM-DD HH:MM:SS-0500', tz='America/New_York')

Adjust timezone as needed for different markets.
Ensure compatibility with backtesting engine's datetime handling.
"""


import pandas as pd
from backtester import run_backtesting, aggregate_strategy_performance, sort_strategies_by_performance, save_results, save_aggregated_results, save_symbol_results, analyze_symbol_results_per_strategy
from strategies import strategy_modules, param_grids
from asset_names import *
import random
import sys
import os
import json
from helpers import play_notification_sound


# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_strategy_class(strategy_name):
    """Load the strategy class from the strategy module."""
    module = strategy_modules[strategy_name]
    strategy_class_name = ''.join([part.capitalize()
                                  for part in strategy_name.split('_')])
    strategy_class = getattr(module, strategy_class_name)
    return strategy_class


def test_all_strategies(data, strategy_tuples):
    """Test all strategies on the given data."""
    results = {}
    for strategy_name, params in strategy_tuples:
        strategy_class = load_strategy_class(strategy_name)
        strategy_instance = strategy_class(data, **params)
        result = strategy_instance.run()
        results[f"{strategy_name}_{json.dumps(params)}"] = result
    return results


def save_all_results(aggregated_performance, intervals, strategies):
    """Save the results for each strategy and interval."""
    for interval in intervals:
        for strategy in strategies:
            if interval in aggregated_performance.get(strategy, {}):
                save_results(
                    aggregated_performance[strategy][interval], strategy, interval)


def print_results(aggregated_performance, sorted_strategies):
    print(f"""
    aggregated_performance: {aggregated_performance}

    sorted_strategies: {sorted_strategies}
    """)


def main():
    """Main function to backtest multiple strategies on selected stock symbols."""


    import pandas as pd

    import pandas as pd
    from pytz import timezone

    def load_turbowave_data(filename='turbowave_candles.json'):
        with open(filename, 'r') as f:
            turbowave_data = json.load(f)
        
        df = pd.DataFrame(turbowave_data)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close']]
        
        # Capitalize column names
        df.columns = df.columns.str.capitalize()
        
        # Assuming volume is not present in your data, add a placeholder column
        df['Volume'] = 0
        
        # Convert the index to timezone-aware datetime (America/New_York)
        ny_tz = timezone('America/New_York')
        df.index = df.index.tz_localize('UTC').tz_convert(ny_tz)
        
        data_interval_dict = {'5s': {'TURBOWAVE': df}}
        
        return data_interval_dict


    # Usage example
    data_interval_dict =  load_turbowave_data()

    symbols=['TURBOWAVE']


    n = len(symbols)






    random.seed(333)
    random.shuffle(symbols)
    symbols = symbols[:n]

    num_candles = 1000000

    intervals = ['5s']#['1h']
    SHOULD_PLOT = True

    N_PARALLEL = 2

    strategy_params_tuples = [

        (

            # 'hma_dip_detector_strategy',

            # # # # ########### FOUND ###########


            #######################



            # 'adaptive_mean_reversion',

            # 'calculus_trend_strategy',





            # 'volatility_breakout_strategy',


            # 'statistical_divergence_strategy',


            'greasy_pig_strategy',
    {}



        )]

    strategy_params = {name: {} for name in param_grids.keys()}  # default params == {}

    for (name, params) in strategy_params_tuples:
        strategy_params[name] = params

    # strategy_names = list(strategy_params.keys())  # ALL in dir
    strategy_names = [x[0] for x in strategy_params_tuples]
    # strategy_names = [name for name in param_grids.keys()]

    all_results, symbol_interval_results = run_backtesting(
        symbols, num_candles, intervals, SHOULD_PLOT, strategy_names, strategy_params,
        # full parallelization: USE FULL POWER!!!
        max_workers_strategies=N_PARALLEL, max_workers_symbols=N_PARALLEL,
        data_interval_dict=data_interval_dict, # provide if u have custom data!,
        should_normalize_data=True,
                                                           )

    aggregated_performance = aggregate_strategy_performance(all_results)
    save_aggregated_results(aggregated_performance)

    sorted_strategies = sort_strategies_by_performance(
        aggregated_performance, metric='sharpe_ratio')
    print_results(aggregated_performance, sorted_strategies)

    symbol_performance = analyze_symbol_results_per_strategy(
        symbol_interval_results)
    save_symbol_results(symbol_performance)

    play_notification_sound(sound_name='Submarine')


if __name__ == "__main__":
    main()
