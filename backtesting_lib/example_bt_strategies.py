import random
import sys
import os
import json
import numpy as np
import vectorbt as vbt

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting_lib.backtester import run_backtesting, analyze_results, analyze_symbol_results, sort_strategies_by_performance, save_results, save_aggregated_results, save_symbol_results
from backtesting_lib.asset_names import popular_assets, cryptocurrencies, us_market_stocks
from backtesting_lib.result_printer import ResultPrinter
from strategies import strategy_modules, param_grids

def load_strategy_class(strategy_name):
    """Load the strategy class from the strategy module."""
    module = strategy_modules[strategy_name]
    strategy_class_name = ''.join([part.capitalize() for part in strategy_name.split('_')])
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
                save_results(aggregated_performance[strategy][interval], strategy, interval)

def print_results(aggregated_performance, sorted_strategies):
    """Print the results using the ResultPrinter."""
    result_printer = ResultPrinter(aggregated_performance)
    result_printer.print_detailed_summary()
    result_printer.print_summary(sorted_strategies)
    result_printer.print_concise_summary(aggregated_performance)

def main():
    """Main function to backtest multiple strategies on selected stock symbols."""
    symbols = cryptocurrencies
    random.seed(421)
    random.shuffle(symbols)
    n = len(symbols)  # Example number of symbols
    symbols = symbols[:n]
    num_candles = 200000
    intervals = ['5m', '15m',]
    SHOULD_PLOT = False

    strategy_params = {name: {} for name in param_grids.keys()}  # default params == {}
   
    #strategies = list(strategy_params.keys())
    
    strategies = ['grover_llorens_activator', 'ut_bot_strategy', 'heikin_ashi_color_change_strategy']
    

    all_results, symbol_interval_results = run_backtesting(
        symbols, num_candles, intervals, SHOULD_PLOT, strategies, strategy_params
    )
    
    aggregated_performance = analyze_results(all_results)
    symbol_performance = analyze_symbol_results(symbol_interval_results)
    
    save_aggregated_results(aggregated_performance)
    save_symbol_results(symbol_performance)
    
    sorted_strategies = sort_strategies_by_performance(aggregated_performance)
    print_results(aggregated_performance, sorted_strategies)

if __name__ == "__main__":
    main()


# import random
# import sys
# import os
# import json
# import numpy as np
# import vectorbt as vbt

# # Add the parent directory to the system path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from backtesting_lib.backtester import run_backtesting, analyze_results, sort_strategies_by_performance, save_results, save_aggregated_results
# from backtesting_lib.asset_names import popular_assets, cryptocurrencies, us_market_stocks
# from backtesting_lib.result_printer import ResultPrinter
# from strategies import strategy_modules, param_grids

# def load_strategy_class(strategy_name):
#     """Load the strategy class from the strategy module."""
#     module = strategy_modules[strategy_name]
#     strategy_class_name = ''.join([part.capitalize() for part in strategy_name.split('_')])
#     strategy_class = getattr(module, strategy_class_name)
#     return strategy_class

# def test_all_strategies(data, strategy_tuples):
#     """Test all strategies on the given data."""
#     results = {}
#     for strategy_name, params in strategy_tuples:
#         strategy_class = load_strategy_class(strategy_name)
#         strategy_instance = strategy_class(data, **params)
#         result = strategy_instance.run()
#         results[f"{strategy_name}_{json.dumps(params)}"] = result
#     return results

# def save_all_results(aggregated_performance, intervals, strategies):
#     """Save the results for each strategy and interval."""
#     for interval in intervals:
#         for strategy in strategies:
#             if interval in aggregated_performance.get(strategy, {}):
#                 save_results(aggregated_performance[strategy][interval], strategy, interval)

# def print_results(aggregated_performance, sorted_strategies):
#     """Print the results using the ResultPrinter."""
#     result_printer = ResultPrinter(aggregated_performance)
#     result_printer.print_detailed_summary()
#     result_printer.print_summary(sorted_strategies)
#     result_printer.print_concise_summary(aggregated_performance)

# def main():
#     """Main function to backtest multiple strategies on selected stock symbols."""
#     symbols = popular_assets
#     random.seed(420)
#     random.shuffle(symbols)
#     n = 20#len(symbols)
    
    
#     """
#     Concise Strategy Performance Summary:
# Strategy             Overall Mean         5m Return (%)        1m Return (%)        15m Return (%)       
# fractal_breakout_strategy 2.09                 1.94                 -1.51                5.84                 
# stb_gianno_nano_strategy 1.69                 3.17                 -1.37                3.28                 
# chandelier_exit_strategy 1.67                 3.74                 -2.92                4.18                 
# renko_strategy       1.41                 3.50                 -2.38                3.12                 
# atr_god_strategy     1.34                 3.54                 -2.99                3.48                 
# trailing_sl_strategy 1.33                 3.59                 -3.01                3.42                 
# bollinger_bands_strategy 1.22                 2.40                 -1.41                2.67                 
# macd_reloaded_strategy 1.07                 1.98                 -2.23                3.47                 
# wave_trend_strategy  1.01                 2.09                 -2.39                3.35                 
# heikin_ashi_psar_strategy 0.96                 2.51                 -2.99                3.36                 
# supertrend_strategy  0.91                 1.33                 -2.18                3.59                 
# super_guppy_strategy 0.80                 2.03                 -1.65                2.02                 
# trend_ma_strategy    0.70                 1.15                 -2.12                3.08                 
# eurusd_strategy      0.65                 2.68                 -1.95                1.22                 
# atr_trailing_stop_strategy 0.64                 1.34                 -2.16                2.74                 
# trend_ribbon_strategy 0.34                 0.37                 -1.65                2.30                 
# crazy_scalping_strategy 0.25                 0.63                 -0.02                0.15                 
# uhl_ma_system        0.21                 2.55                 -2.06                0.14                 
# hullma_strategy      0.03                 1.58                 -3.22                1.72                 
# turtle_trading_strategy 0.00                 0.00                 0.00                 0.00                 
# pivot_of_pivot_reversal_strategy 0.00                 0.00                 0.00                 0.00                 
# ichimoku_kinko_hyo_strategy 0.00                 0.00                 0.00                 0.00                 
# flexi_supertrend_strategy 0.00                 0.00                 0.00                 0.00                 
# darvas_box_strategy  -0.21                0.62                 -2.11                0.86                 
# bull_bear_fear_strategy -0.49                0.76                 -3.66                1.41                 
# heikin_ashi_color_change_strategy -0.67                -1.74                -2.94                2.68                 
# ut_bot_strategy      -0.68                0.01                 -3.91                1.87                 
# grover_llorens_activator -1.62                -2.30                -4.15                1.58      
#     """
    
#     symbols=symbols[:n]
#     num_candles = 20000000
    
    
#     intervals = [
#         #'1m', 
#         '5m',
#         '15m',
#         '1h',
#         #'4h'
#         ]
#     SHOULD_PLOT = False

#     # # Commented out for potential future use
#     strategy_params = {name: {} for name in param_grids.keys()} # default params == {}
   
#     # Define strategy parameters
#     # strategy_params = {
#     #     'heikin_ashi_color_change_strategy': {},
#     #     'grover_llorens_activator': {},
#     #     'ut_bot_strategy': {},
#     #     'bull_bear_fear_strategy': {},
#     #     'supertrend_strategy': {},
#     #     'atr_trailing_stop_strategy': {},
#     #     'hullma_strategy': {},
#     #     'darvas_box_strategy': {},
#     # }

   
#     strategies = list(strategy_params.keys())


#     all_results = run_backtesting(
#         symbols,
#         num_candles,
#         intervals,
#         SHOULD_PLOT,
#         strategies,
#         strategy_params=strategy_params,
#         parallelize_strategies=True,
#         parallelize_symbols=True,
#         max_workers_strategies=1, # > 1 glitchy!
#         max_workers_symbols=120
#     )
    
#     aggregated_performance = analyze_results(all_results)
#     save_all_results(aggregated_performance, intervals, [s[0] for s in strategies])
#     save_aggregated_results(aggregated_performance)

#     sorted_strategies = sort_strategies_by_performance(aggregated_performance)
#     print_results(aggregated_performance, sorted_strategies)

# if __name__ == "__main__":
#     main()






