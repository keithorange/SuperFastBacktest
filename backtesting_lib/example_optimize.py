import sys
import os
from datetime import datetime, timedelta
import json
import numpy as np

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting_lib.backtester import run_backtesting, analyze_results, sort_strategies_by_performance
from backtesting_lib.asset_names import popular_assets, us_market_stocks, cryptocurrencies
from backtesting_lib.result_printer import ResultPrinter
from backtesting_lib.optimize import optimize_strategy_params
from backtesting_lib.data_handler import download_data  # Import the optimization function

import random

def main():
    """
    Main function to backtest and optimize multiple strategies on selected stock symbols.
    """
    
    # Define the list of stock symbols
    symbols = popular_assets  # Using first 20 assets for demonstration
    
    random.seed(420)
    random.shuffle(popular_assets)
    
    # SHUFFLE AND TAKE N
    #n = len(symbols)
    n = 50
    symbols = symbols[:n]
    
    # Define the number of candles for backtesting
    num_candles = 100000
    
    interval = '5m'
    
    # Download data once for all symbols
    data_dict = {symbol: download_data(symbol, num_candles, interval) for symbol in symbols}
    
    # Define strategies to test
    
    #print(f"data_dict={data_dict}")
    
    # Define parameter grid for optimization
        
        
    param_grid = {
        'key_value': [0.5, 1, 3],
        'atr_period': [6, 14, 30],
        'heikin_ashi': [False, True],
        'ema_length': [8, 20, 50]
    }


    strategy_name = 'ut_bot_strategy'

    sorted_results = optimize_strategy_params(
        strategy_name,
        symbols,
        num_candles,
        interval,
        param_grid,
        data_dict=data_dict,  # Pass pre-loaded data
        should_plot=False,
        max_workers_strategies=2,
        max_workers_symbols=120
    )

    best_params = sorted_results[0][0]
    best_performance = sorted_results[0][1]

    print(f"\nBest Parameters for {strategy_name}")
    print(best_params)
    print(f"\nBest Performance for {strategy_name}:")
    print(f"  overall_mean {best_performance['overall_mean']:.2f}")

    # Save all results
    results = {
        strategy_name: {
            'sorted_results': sorted_results
        }
    }

    results_file = 'optimized_strategy_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nOptimization results saved to {results_file}")

if __name__ == "__main__":
    main()
