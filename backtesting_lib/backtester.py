import vectorbt as vbt
import pandas as pd
import numpy as np
import concurrent.futures
import importlib
from tqdm import tqdm
import os
import json

from backtesting_lib.data_handler import download_data


INIT_CASH = 10000
def backtest_strategy(data, entries, exits, symbol='', init_cash=INIT_CASH,freq='5m', plot=False): # dont use fees broken!
    portfolio = vbt.Portfolio.from_signals(data['Close'], entries, exits, init_cash=init_cash, fees=0, freq=freq)
    
    if plot:
        title = f"{symbol} Strategy Performance"
        fig = portfolio.plot(title=title)
        fig.show()
    
    return portfolio

import numpy as np

def extract_metrics(portfolio):
    stats = portfolio.stats()
    total_profit = portfolio.total_profit()

    # Ensure 'Total Closed Trades' is available in stats
    total_closed_trades = stats.get('Total Closed Trades', 0)
    
    # Calculate profit per trade percentage
    if total_closed_trades > 0:
        total_return_pct = stats['Total Return [%]']
        profit_per_trade_pct = total_return_pct / total_closed_trades
    else:
        profit_per_trade_pct = np.nan

    # Calculate profit per trade
    profit_per_trade_abs = total_profit / total_closed_trades if total_closed_trades != 0 else np.nan

    metrics = {
        'total_return': stats['Total Return [%]'],
        'expectancy': stats['Expectancy'],
        'profit_per_trade_abs': profit_per_trade_abs,
        'profit_per_trade_pct': profit_per_trade_pct,
        'benchmark_return': stats['Benchmark Return [%]'],
        'total_profit': total_profit,
        'max_drawdown': stats['Max Drawdown [%]'],
        'win_rate': stats['Win Rate [%]'],
        'best_trade': stats['Best Trade [%]'],
        'worst_trade': stats['Worst Trade [%]'],
        'total_trades': stats['Total Trades'],
        'total_closed_trades': total_closed_trades,
        'total_open_trades': stats['Total Open Trades'],
    }

    return metrics



def load_strategy(strategy_name):
    module = importlib.import_module(f'backtesting_lib.strategies.{strategy_name}')
    strategy_func = getattr(module, strategy_name)
    return strategy_func

def run_backtesting_for_symbol(symbol, data, plot, strategy_func, strategy_params, **kwargs):
    if data.empty:
        print(f"No data available for {symbol}. Skipping backtesting.")
        return symbol, {}
    
    entries, exits = strategy_func(data, **strategy_params)
    portfolio = backtest_strategy(data, entries, exits, symbol=symbol, plot=plot, **kwargs)
    metrics = extract_metrics(portfolio)
    return symbol, metrics

def run_backtesting_for_strategy(strategy_name, data_dict, plot, strategy_params, max_workers_symbols=6, **kwargs):
    strategy_func = load_strategy(strategy_name)
    strategy_results = {}
    symbol_interval_results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_symbols) as executor:
        futures = {
            executor.submit(run_backtesting_for_symbol, symbol, data, plot, strategy_func, strategy_params, **kwargs): symbol
            for symbol, data in data_dict.items()
        }

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f'Running {strategy_name}'):
            symbol, result = future.result()
            strategy_results[symbol] = result
            if symbol not in symbol_interval_results:
                symbol_interval_results[symbol] = []
            symbol_interval_results[symbol].append(result)

    return strategy_name, strategy_results, symbol_interval_results

def run_backtesting(symbols, num_candles, intervals, plot, strategies, strategy_params=None, parallelize_strategies=True, parallelize_symbols=True, max_workers_strategies=4, max_workers_symbols=6, data_dict=None, **kwargs):
    all_results = {}
    symbol_interval_results = {}

    if type(intervals) == str:
        intervals = [intervals]
    
    for interval in intervals:
        data_dict = {symbol: download_data(symbol, num_candles, interval) for symbol in symbols}
        interval_results = {}
        
        if parallelize_strategies:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_strategies) as executor:
                futures = {executor.submit(run_backtesting_for_strategy, strategy, data_dict, plot, strategy_params[strategy], max_workers_symbols if parallelize_symbols else 1, **kwargs): strategy for strategy in strategies}
                
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc='Running Strategies'):
                    strategy_name, strategy_results, symbol_results = future.result()
                    interval_results[strategy_name] = strategy_results
                    for symbol, result_list in symbol_results.items():
                        if symbol not in symbol_interval_results:
                            symbol_interval_results[symbol] = {}
                        if strategy_name not in symbol_interval_results[symbol]:
                            symbol_interval_results[symbol][strategy_name] = []
                        symbol_interval_results[symbol][strategy_name].extend(result_list)
        else:
            for strategy in tqdm(strategies, desc='Running Strategies'):
                strategy_name, strategy_results, symbol_results = run_backtesting_for_strategy(strategy, data_dict, plot, strategy_params[strategy], max_workers_symbols if parallelize_symbols else 1, **kwargs)
                interval_results[strategy_name] = strategy_results
                for symbol, result_list in symbol_results.items():
                    if symbol not in symbol_interval_results:
                        symbol_interval_results[symbol] = {}
                    if strategy_name not in symbol_interval_results[symbol]:
                        symbol_interval_results[symbol][strategy_name] = []
                    symbol_interval_results[symbol][strategy_name].extend(result_list)
        
        all_results[interval] = interval_results
    
    return all_results, symbol_interval_results

def aggregate_results(metrics_list):
    metrics_df = pd.DataFrame(metrics_list)
    numeric_columns = metrics_df.select_dtypes(include=[np.number]).columns
    aggregated_metrics = {
        'Mean': metrics_df[numeric_columns].mean().to_dict(),
        'Min': metrics_df[numeric_columns].min().to_dict(),
        'Max': metrics_df[numeric_columns].max().to_dict()
    }
    return aggregated_metrics

def analyze_results(all_results):
    strategy_performance = {}
    for interval, interval_results in all_results.items():
        for strategy, symbol_results in interval_results.items():
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {}
            metrics_list = list(symbol_results.values())
            strategy_performance[strategy][interval] = aggregate_results(metrics_list)

    for strategy in strategy_performance:
        interval_returns = []
        for interval in strategy_performance[strategy]:
            if interval != 'overall_mean':
                interval_returns.append(strategy_performance[strategy][interval]['Mean']['total_return'])
        overall_mean = np.mean(interval_returns)
        strategy_performance[strategy]['overall_mean'] = overall_mean

    return strategy_performance

def analyze_symbol_results(symbol_interval_results):
    symbol_performance = {}
    for symbol, strategy_results in symbol_interval_results.items():
        for strategy, results in strategy_results.items():
            if strategy not in symbol_performance:
                symbol_performance[strategy] = []
            metrics_list = [result for result in results if result]  # Filter out empty results
            if metrics_list:
                aggregated_result = aggregate_results(metrics_list)['Mean']
                aggregated_result['symbol'] = symbol
                symbol_performance[strategy].append(aggregated_result)
    
    for strategy, performance_list in symbol_performance.items():
        symbol_performance[strategy] = sorted(performance_list, key=lambda x: x['total_return'], reverse=True)

    return symbol_performance

def sort_strategies_by_performance(aggregated_performance, metric='overall_mean', ascending=False):
    sorted_strategies = sorted(
        aggregated_performance.items(), 
        key=lambda x: x[1][metric], 
        reverse=not ascending
    )
    return sorted_strategies

def save_results(results, strategy_name, interval, output_dir='backtesting_results'):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{strategy_name}_{interval}_results.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results for {strategy_name} ({interval}) saved to {filepath}")

def save_aggregated_results(aggregated_results, output_dir='backtesting_results'):
    os.makedirs(output_dir, exist_ok=True)
    filename = "aggregated_results.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(aggregated_results, f, indent=2)
    
    print(f"Aggregated results saved to {filepath}")

def save_symbol_results(symbol_results, output_dir='backtesting_results'):
    os.makedirs(output_dir, exist_ok=True)
    filename = "symbol_results.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(symbol_results, f, indent=2)
    
    print(f"Symbol results saved to {filepath}")
