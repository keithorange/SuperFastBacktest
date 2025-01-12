import re
from scipy import integrate
from typing import Callable, Optional, List, Dict, Any, Sequence, Tuple, Union
import logging
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
import yfinance as yf
import math
import random
from matplotlib.gridspec import GridSpec
import traceback
import pandas as pd
import numpy as np
import concurrent.futures
import importlib
from tqdm import tqdm
import os
import json
from strategies.normalize_data import normalize_price_data_for_trading
from data_handler import download_data
import matplotlib.pyplot as plt
import seaborn as sns

from helpers import *
from data_structures import *
from financial_metrics import *

def handle_trade_exits(portfolio: Portfolio, current_price: float, current_date: pd.Timestamp, fees: float, exit_index: int, is_long: bool) -> bool:
    if is_long:
        portfolio.exit_long_trades(current_price, current_date, fees, exit_index)
    else:
        portfolio.exit_short_trades(current_price, current_date, fees, exit_index)

    return True


def handle_trade_entries(portfolio: Portfolio, current_price: float, current_date: pd.Timestamp,
                         collateral: float, leverage: float, fees: float,
                         stop_when_broke: bool, is_long: bool) -> bool:
    # Check if we have enough free cash for the collateral
    if portfolio.cash >= collateral or (not stop_when_broke):
        return portfolio.enter_trade(current_price, current_date, collateral, leverage, fees, is_long)

    return False


# First fix: Time-based exit logic
def check_exit_time_range(current_date, exit_start_time, exit_end_time):
    """Improved exit time range checker that handles overnight periods"""
    if not (exit_start_time and exit_end_time):
        return False
        
    current_time = current_date.time()
    
    # Handle overnight period (e.g., 22:00 to 16:55 next day)
    if exit_start_time > exit_end_time:
        # During overnight period
        return current_time >= exit_start_time or current_time <= exit_end_time
    else:
        # During same day period
        return exit_start_time <= current_time <= exit_end_time


# Create a global instance of Earnigns Hours cache (NYSE/NASDAQ etc earnings reports!)
earnings_cache = EarningsCache()


"""TODO: MAKE FASTER! SPEED UP LIKE CRAZY!"""
def backtest_strategy(
    # normalized_data: pd.DataFrame, # use NORMALIZED data ONLY to FEED into strategy and get OUTPUT signals
    raw_data: pd.DataFrame, # use RAW DATA for ALL CALCULATIONS and REWARDS!
    long_entries: pd.Series,
    long_exits: pd.Series,
    short_entries: pd.Series,
    short_exits: pd.Series,
    symbol: str,
    init_cash: float,
    interval: str,
    leverage: float = 10,#60.0,  # TODO: fix bug! 
    entry_signal_stacking: bool = False,
    max_concurrent_trades: int = 1,
    use_fixed_size: bool = True,
    trade_size: float = 0.1,
    fees: float = 0.0004, # 2x per trade (happens 1x per buy, 1x per sell) costs (fees + slippage + spread etc.)
    include_uncompleted: bool = True,
    use_equity_curve: bool = True,
    random_exit_probability: float = 0,
    exit_on_next_candle: bool = True,
    exit_on_end_of_day: bool = False,
    exit_before_earnings_report: bool = False,
    exit_before_weekend: bool = False,
    exit_time_range: Optional[Tuple[str, str]] = ("18:55", "21:00"),  # (start_time, end_time) "18:59", # TODO: HARDCODED FOR TURBOWAVE, has "resetting period each day" where resets to 1000 and have warmup time
) -> Dict[str, Any]:

    print(f"**NOTE: enabled exiting at specific time: {exit_time_range}")
    """
    Modified version that separates normalized data (for signal generation) 
    from raw data (for profit/metrics calculation)
    """
    WAIT_AFTER_EXIT_N_CANDLES = 1
    WAIT_AFTER_ENTRY_N_CANDLES = 1

   # Near the top of the function, after other initializations
    exit_start_time = exit_end_time = None
    if exit_time_range:
        try:
            exit_start_time = datetime.strptime(exit_time_range[0], "%H:%M").time()
            exit_end_time = datetime.strptime(exit_time_range[1], "%H:%M").time()
        except (ValueError, IndexError):
            raise ValueError("exit_time_range must be a tuple of two times in 'HH:MM' format")

    # In backtest_strategy()
    def handle_exit(portfolio, price, date, index, is_long, reason="signal"):
        """Modified to handle both position types properly"""
        nonlocal active_long_trades, active_short_trades, exit_long_occurred, exit_short_occurred
        nonlocal candles_since_last_long_exit, candles_since_last_short_exit

        # Check which position types need to be exited
        has_long = bool(portfolio.long_open_trades)
        has_short = bool(portfolio.short_open_trades)
        
        if has_long and is_long:
            handle_trade_exits(portfolio, price, date, fees, index, is_long)
            filled_long_exits[index] = 1
            active_long_trades = 0
            candles_since_last_long_exit = 0
            exit_long_occurred = True
            
        if has_short and not is_long:
            handle_trade_exits(portfolio, price, date, fees,  index, is_long)
            filled_short_exits[index] = 1
            active_short_trades = 0
            candles_since_last_short_exit = 0
            exit_short_occurred = True

    def handle_liquidation(exit_index: int, is_long: bool) -> None:
        """Callback to handle trade liquidation events"""
        nonlocal active_long_trades, active_short_trades
        nonlocal candles_since_last_long_exit, candles_since_last_short_exit
        
        if is_long:
            active_long_trades -= 1
            candles_since_last_long_exit = 0
            filled_long_exits[exit_index] = 1
        else:
            active_short_trades -= 1
            candles_since_last_short_exit = 0
            filled_short_exits[exit_index] = 1

            

    portfolio = Portfolio(init_cash)
    portfolio.set_liquidation_callback(handle_liquidation)
    close_prices_raw = raw_data['Close'].values


    dates = raw_data.index.to_numpy()

    # Force convert entries and exits to pandas Series
    if not isinstance(long_entries, pd.Series):
        long_entries = pd.Series(long_entries, index=raw_data.index)
    if not isinstance(long_exits, pd.Series):
        long_exits = pd.Series(long_exits, index=raw_data.index)
    if not isinstance(short_entries, pd.Series):
        short_entries = pd.Series(short_entries, index=raw_data.index)
    if not isinstance(short_exits, pd.Series):
        short_exits = pd.Series(short_exits, index=raw_data.index)
    
    # force them all to be floats not bools
    long_entries = long_entries.astype(bool)
    long_exits = long_exits.astype(bool)
    short_entries = short_entries.astype(bool)
    short_exits = short_exits.astype(bool)

    # Initialize tracking arrays

    equity_curve = np.zeros(len(close_prices_raw))
    equity_curve[0] = init_cash

    filled_long_entries = np.zeros(len(close_prices_raw))
    filled_long_exits = np.zeros(len(close_prices_raw))
    unfilled_long_entries = np.zeros(len(close_prices_raw))
    unfilled_long_exits = np.zeros(len(close_prices_raw))

    filled_short_entries = np.zeros(len(close_prices_raw))
    filled_short_exits = np.zeros(len(close_prices_raw))
    unfilled_short_entries = np.zeros(len(close_prices_raw))
    unfilled_short_exits = np.zeros(len(close_prices_raw))


    position_long_sizes = np.zeros(len(close_prices_raw))
    concurrent_long_trades = np.zeros(len(close_prices_raw))

    position_short_sizes = np.zeros(len(close_prices_raw))
    concurrent_short_trades = np.zeros(len(close_prices_raw))

    active_long_trades = 0
    active_short_trades = 0

    candles_since_last_long_exit = 2*WAIT_AFTER_EXIT_N_CANDLES
    candles_since_last_long_entry = 2*WAIT_AFTER_ENTRY_N_CANDLES
    candles_since_last_short_exit = 2*WAIT_AFTER_EXIT_N_CANDLES
    candles_since_last_short_entry = 2*WAIT_AFTER_ENTRY_N_CANDLES

    if not entry_signal_stacking:
        max_concurrent_trades = 1

    previous_date = None
    end_of_day_exited = False

    if exit_before_earnings_report:
        today = date.today().isoformat()
        earnings_exit_signals = earnings_cache.prepare_earnings_exit_signals(symbol, interval, today)

    if exit_before_weekend:
        weekend_exit_signals = get_weekend_exit_signals(dates)


    for i in range(len(close_prices_raw)):
        current_price_raw = close_prices_raw[i]
        current_date = dates[i]

        # Update portfolio state and equity curve at the start of each iteration
        # In backtest_strategy main loop:
        portfolio.update_values(current_price_raw, fee_rate=fees, 
                            current_date=current_date, exit_index=i)

        # Handle liquidation case
        if i > 0 and previous_equity == 0:
            portfolio.equity = 0

        # Update equity curve
        equity_curve[i] = portfolio.equity

        # Store previous equity for next iteration
        previous_equity = portfolio.equity


        entry_long_occurred = False
        exit_long_occurred = False
        entry_short_occurred = False
        exit_short_occurred = False
        
        is_end_of_day_exit_time = False
        is_random_exit = False

        # Inside the main loop, update the check for exit time
        # Improved exit time check
        is_in_exit_time_range = check_exit_time_range(
            current_date,
            exit_start_time,
            exit_end_time
        )

        # Force exit if in exit time range and have open positions
        if is_in_exit_time_range and (portfolio.long_open_trades or portfolio.short_open_trades):
            handle_exit(portfolio, current_price_raw, current_date, i, True)
            handle_exit(portfolio, current_price_raw, current_date, i, False)


        # Check for end of day
        if exit_on_end_of_day and i < len(close_prices_raw) - 1:
            next_date = dates[i + 1]
            if current_date.date() != next_date.date():
                is_end_of_day_exit_time = True

        if exit_before_weekend:
            is_end_of_day_exit_time |= weekend_exit_signals[i]

        if exit_before_earnings_report:
            is_end_of_day_exit_time |= earnings_exit_signals[i]

        if random.random() < random_exit_probability:
            is_random_exit = True

        # if on LAST CANDLE! (show_uncompleted == True), EXIT ALL POSITIONS!
        # In the main loop, near the end:
        # Check if we're in the last 3 candles of the data (IF USING EXIT ON NEXT CANDLE!)
        if i >= len(close_prices_raw) - 3 and include_uncompleted:
            long_exits.iloc[i] = True
            short_exits.iloc[i] = True

        if any(long_entries) or any(short_entries):
            pass

        # Combined exit handling for all exit conditions
        if i > 0:

            # Check exit conditions
            if (long_exits.iloc[i-1 if exit_on_next_candle else i] or
                short_exits.iloc[i-1 if exit_on_next_candle else i] or
                is_end_of_day_exit_time or 
                is_random_exit or
                is_in_exit_time_range):
                # (include_uncompleted and i == len(close_prices_raw) - 1) handled above nautrally):
                
                is_in_long = long_exits.iloc[i-1 if exit_on_next_candle else i]==1
                if portfolio.long_open_trades + portfolio.short_open_trades:
                    handle_exit(portfolio, current_price_raw, current_date, i, is_long=is_in_long)

                    if is_end_of_day_exit_time:
                        end_of_day_exited = True
                else:
                    if is_in_long:
                        unfilled_long_exits[i] = 1
                    else: 
                        unfilled_short_exits[i] = 1

        # Common conditions
        is_trade_allowed = (
            i > 0 and
            not exit_long_occurred and
            not exit_short_occurred and 
            not is_end_of_day_exit_time and
            not is_random_exit and
            not is_in_exit_time_range and
            not (end_of_day_exited and current_date.date() == previous_date)
        )

        # Handle entries for long trades
        allow_entry_long = (
            is_trade_allowed and
            long_entries.iloc[i] and  
            not entry_long_occurred and
            active_long_trades < max_concurrent_trades and
            candles_since_last_long_exit >= WAIT_AFTER_EXIT_N_CANDLES and
            candles_since_last_long_entry >= WAIT_AFTER_ENTRY_N_CANDLES 
        )

        # Handle entries for short trades
        allow_entry_short = (
            is_trade_allowed and
            short_entries.iloc[i] and  # Check for short entry condition
            not entry_short_occurred and
            active_short_trades < max_concurrent_trades and# Limit on concurrent short trades
            candles_since_last_short_exit >= WAIT_AFTER_EXIT_N_CANDLES and
            candles_since_last_short_entry >= WAIT_AFTER_ENTRY_N_CANDLES 
        )

        is_long_entry = long_entries.iloc[i] == 1

        if (allow_entry_long or allow_entry_short):
            # Apply leverage to trade size for position sizing
            collateral = trade_size * portfolio.initial_cash if use_fixed_size else trade_size*portfolio.cash # either fixed of current % !
            if handle_trade_entries(
                portfolio=portfolio,
                current_price=current_price_raw,
                current_date=current_date,
                collateral=collateral,  # Pass raw size $
                leverage=leverage,  # Pass leverage separately
                fees=fees,
                stop_when_broke=False, #if False then KEEP TRADING WITH NEGATIVE BALANCE
                is_long=is_long_entry
            ):
            
                if is_long_entry:
                    active_long_trades += 1  # ADD THIS!
                    filled_long_entries[i] = 1
                    entry_long_occurred = True
                    candles_since_last_long_entry = 0
                else:
                    active_short_trades += 1  # ADD THIS!
                    filled_short_entries[i] = 1
                    entry_short_occurred = True
                    candles_since_last_short_entry = 0

            else:
                if is_long_entry:
                    unfilled_long_entries[i] = 1
                else:
                    unfilled_short_entries[i] = 1


        # Update portfolio and equity curve
        previous_equity = portfolio.equity
        # In backtest_strategy main loop:
        portfolio.update_values(current_price_raw, fee_rate=fees, 
                            current_date=current_date, exit_index=i)
        
        # Ensure equity doesn't mysteriously recover after liquidation
        if previous_equity == 0:
            portfolio.equity = 0
            
        # Update other tracking metrics
        position_long_sizes[i] = sum(trade.get_position_size() for trade in portfolio.long_open_trades)
        position_short_sizes[i] = sum(trade.get_position_size() for trade in portfolio.short_open_trades)

        concurrent_long_trades[i] = active_long_trades
        concurrent_short_trades[i] = active_short_trades

        candles_since_last_long_entry += 1
        candles_since_last_long_exit += 1

        candles_since_last_short_entry += 1
        candles_since_last_short_exit += 1
        previous_date = current_date.date()

        if i > 0 and current_date.date() != dates[i-1].date():
            end_of_day_exited = False

    # DONE MAIN LOOP! DO ANY ADDITIONAL PROCEESSING BELOW!

    # Final equity curve updates
    def combine_signals(array1: np.ndarray, array2: np.ndarray) -> np.ndarray:
        """
        Combines exit signals ensuring we don't double count
        """
        # If either array has a signal, that's a snapshot point
        # Using logical_or instead of addition prevents double counting
        return np.logical_or(array1 > 0, array2 > 0).astype(float)

    ## Usage in your code - modified to force last index:
    combined_long_short_exits = combine_signals(filled_long_exits, filled_short_exits)
    combined_long_short_entries = combine_signals(filled_long_entries, filled_short_entries)


    equity_curve_snapshots = take_snapshots_by_indicator(equity_curve, indicator=combined_long_short_exits)

    # Calculate metrics
    finished_trades = portfolio.long_closed_trades + portfolio.short_closed_trades
    
    drawdowns = calculate_drawdowns(equity_curve)
    metrics = calculate_metrics(
        benchmark_prices=close_prices_raw,
        trades=finished_trades,
        num_exit_signals=portfolio.num_exit_signals,
        period_type=interval,
        use_equity_curve=use_equity_curve,
        equity_curve=equity_curve,
        equity_curve_snapshots=equity_curve_snapshots,
    )

    visualization_data = {
        'dates': dates,
        'close_prices': close_prices_raw,
        'equity': equity_curve,
        'equity_curve_snapshots': equity_curve_snapshots,
        'position_long_sizes': position_long_sizes,
        'position_short_sizes': position_short_sizes,
        'filled_long_entries': filled_long_entries,
        'filled_short_entries': filled_short_entries,
        'filled_long_exits': filled_long_exits,
        'filled_short_exits': filled_short_exits,
        'unfilled_long_entries': filled_long_entries,
        'unfilled_short_entries': filled_short_entries,
        'unfilled_long_exits': filled_long_exits,
        'unfilled_short_exits': filled_short_exits,
        'trades': finished_trades,
        'drawdowns': drawdowns,
        'concurrent_long_trades': concurrent_long_trades,
        'concurrent_short_trades': concurrent_short_trades,

    }

    return {
        'metrics': metrics,
        'visualization_data': visualization_data
    }


def load_strategy(strategy_name):
    """Load strategy from file based on specifications: TODO: write specs here..."""
    module = importlib.import_module(f'strategies.{strategy_name}')
    strategy_func = getattr(module, strategy_name)
    return strategy_func

def run_backtesting_for_symbol(symbol, raw_data, normalized_data, plot, interval, strategy_func, strategy_params, **kwargs):
    """Updated version that takes both raw and pre-normalized data"""
    if raw_data.empty:
        print(f"No data available for {symbol}. Skipping backtesting.")
        return symbol, {}

    # Use pre-normalized data for signal generation
    long_entries, long_exits, short_entries, short_exits  = strategy_func(normalized_data, **strategy_params)
    
    # Run backtest using both normalized and raw data
    result = backtest_strategy(
        raw_data=raw_data,               # For profit calculation
        long_entries=long_entries, 
        long_exits=long_exits, 
        short_entries=short_entries,
        short_exits=short_exits,
        symbol=symbol, 
        init_cash=100.0, 
        interval=interval, 
        **kwargs
    )


    if plot: 
        plot_backtest_results(result, symbol, interval)

    return symbol, result['metrics']


def run_backtesting_for_strategy(strategy_name, raw_data_dict, normalized_data_dict, plot, interval, strategy_params, max_workers_symbols, **kwargs):
    """Updated to accept both raw and normalized data dictionaries"""
    strategy_func = load_strategy(strategy_name)
    strategy_results = {}
    symbol_interval_results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_symbols) as executor:
        futures = {
            executor.submit(
                run_backtesting_for_symbol, 
                symbol, 
                raw_data,
                normalized_data_dict[symbol],  # Pass normalized data
                plot, 
                interval, 
                strategy_func, 
                strategy_params,
                **kwargs
            ): symbol
            for symbol, raw_data in raw_data_dict.items()
        }

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f'Running {strategy_name}'):
            symbol, result = future.result()
            strategy_results[symbol] = result
            if symbol not in symbol_interval_results:
                symbol_interval_results[symbol] = []
            symbol_interval_results[symbol].append(result)

    return strategy_name, strategy_results, symbol_interval_results

def run_backtesting(symbols, num_candles, intervals, plot, strategies, strategy_params=None,
                    parallelize_strategies=True,
                    max_workers_strategies=50, max_workers_symbols=50,
                    data_interval_dict=None, pushback_data_pct=0,
                    should_normalize_data=True,
                    **kwargs):
    """
    Run backtesting on multiple symbols and strategies.

    Parameters:
    -----------
    ...

    data_interval_dict : dict, optional
        A dictionary containing pre-loaded OHLCV data for each interval and symbol.
        The structure should be:
        {
            'interval1': {
                'symbol1': pd.DataFrame({
                    'open': [...],
                    'high': [...],
                    'low': [...],
                    'close': [...],
                    'volume': [...]
                }),
                'symbol2': pd.DataFrame({...}),
                ...
            },
            'interval2': {...},
            ...
        }
        Each DataFrame should have a DatetimeIndex representing the timestamp of each candle.
        If not provided, data will be downloaded using the download_data function.

    ...

    Returns:
    --------
    tuple
        A tuple containing two dictionaries:
        1. all_results: Strategy results for each interval
        2. symbol_interval_results: Individual symbol results for each strategy and interval
    """
    # ... (rest of the function implementation)

    all_results = {}
    symbol_interval_results = {}

    if type(intervals) == str:
        intervals = [intervals]

    for interval in intervals:
        # Download or use provided raw data
        if not data_interval_dict:
            raw_data_dict = {
                symbol: download_data(symbol, num_candles, interval) 
                for symbol in symbols
            }
        else:
            raw_data_dict = data_interval_dict[interval]

        # Apply pushback_data_pct if needed
        if pushback_data_pct > 0:
            for symbol in raw_data_dict:
                total_data_length = len(raw_data_dict[symbol])
                keep_length = int(total_data_length * (1 - pushback_data_pct))
                raw_data_dict[symbol] = raw_data_dict[symbol][:keep_length]

        # Create normalized data dictionary once
        normalized_data_dict = {
            symbol: normalize_price_data_for_trading(data.copy()) if should_normalize_data else data.copy()
            for symbol, data in raw_data_dict.items()
        }

        interval_results = {}

        if parallelize_strategies:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_strategies) as executor:
                futures = {
                    executor.submit(
                        run_backtesting_for_strategy, 
                        strategy, 
                        raw_data_dict,
                        normalized_data_dict,  # Pass normalized data dict
                        plot,
                        interval, 
                        strategy_params[strategy],
                        max_workers_symbols,
                        **kwargs
                    ): strategy
                    for strategy in strategies
                }
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
                strategy_name, strategy_results, symbol_results = run_backtesting_for_strategy(
                    strategy, 
                    raw_data_dict,
                    normalized_data_dict,  # Pass normalized data dict
                    plot, 
                    interval,
                    strategy_params[strategy], 
                    max_workers_symbols,
                    **kwargs
                )
                interval_results[strategy_name] = strategy_results
                for symbol, result_list in symbol_results.items():
                    if symbol not in symbol_interval_results:
                        symbol_interval_results[symbol] = {}
                    if strategy_name not in symbol_interval_results[symbol]:
                        symbol_interval_results[symbol][strategy_name] = []
                    symbol_interval_results[symbol][strategy_name].extend(result_list)

        all_results[interval] = interval_results

    return all_results, symbol_interval_results


"""NEW CODE!!"""



from reward_functions import AGGREGATE_MEAN_FUNC


def aggregate_results(metrics_list: List[Dict], mean_func: Callable = AGGREGATE_MEAN_FUNC) -> Dict:
    """
    Efficiently aggregate metrics using vectorized operations.

    Corollary: While lower-priority mean could theoretically find better minima by emphasizing certain regions, the practical impossibility of stable training makes it inferior for neural network optimization. USE np.mean()

    """
    # Initialize default values for Mean, Min, Max
    default_metrics = {'Mean': 0.0, 'Min': 0.0, 'Max': 0.0}

    if not metrics_list:
        return default_metrics
    
    metrics_df = pd.DataFrame(metrics_list)
    
    if metrics_df.empty:
        return default_metrics
    
    # Get only numeric columns
    numeric_cols = metrics_df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        return default_metrics
    
    try:
        aggregated_means = metrics_df[numeric_cols].agg(mean_func)
        min_values = metrics_df[numeric_cols].min()
        max_values = metrics_df[numeric_cols].max()
        
        return {
            'Mean': aggregated_means.to_dict(),
            'Min': min_values.to_dict(),
            'Max': max_values.to_dict()
        }
    except Exception as e:
        print(f"Error during aggregation: {e}")
        return default_metrics
    
def aggregate_strategy_performance(
    all_results: Dict,
    mean_func: Callable = AGGREGATE_MEAN_FUNC,
    # use other mean funcs for (equity curves speicfially!)
    metric_functions: Dict[str, Callable] = {
        'normalized_equity_curve': np.mean,
        'normalized_equity_curve_snapshots': np.mean,
        'original_equity_curve': np.mean,
        'original_equity_curve_snapshots': np.mean,

    },
    default_value=0
) -> Dict:
    """
    Aggregate strategy performance across all intervals using vectorized operations.
    Automatically detects and handles array metrics by checking value types.
    
    Parameters:
    -----------
    all_results : Dict
        The results to aggregate
    mean_func : Callable
        Default aggregation function for metrics without specific functions
    metric_functions : Dict[str, Callable]
        Dictionary mapping metric names to their specific aggregation functions
        e.g., {'normalized_equity_curve': np.mean}
    default_value : Any
        Default value for missing metrics
    """
    strategy_performance = {}
    metric_functions = metric_functions or {}
    
    # Initialize default values for strategies
    default_strategy_result = {
        'overall': {'Mean': 0.0, 'Min': 0.0, 'Max': 0.0}
    }
    
    if not all_results:
        return {}
    
    def is_array_like(value) -> bool:
        """Helper function to detect array-like objects"""
        return isinstance(value, (list, np.ndarray)) or (
            isinstance(value, pd.Series) and len(value) > 1
        )
    
    def get_aggregation_func(metric_name: str) -> Callable:
        """Get the appropriate aggregation function for a metric"""
        return metric_functions.get(metric_name, mean_func)

    def safe_apply_along_axis(array_agg_func, stacked):
        def _apply_func(x):
            return array_agg_func(pd.Series(x)) if not np.isnan(x).all() else np.nan

        if stacked.shape[0] > 0 and stacked.shape[1] > 0:
            return np.apply_along_axis(_apply_func, axis=0, arr=stacked)
        else:
            return np.array([])  # or some other appropriate default value

    
    # Process each strategy and interval
    for interval, interval_results in all_results.items():
        for strategy, symbol_results in interval_results.items():
            if not symbol_results:  # Skip empty results
                continue
            
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {}
            
            # Convert to list safely
            metrics_list = list(symbol_results.values())
            if metrics_list:
                # Create a copy of metrics without array data
                scalar_metrics_list = []
                arrays_dict = {}
                
                # Detect array metrics from first non-empty result
                first_metrics = next((m for m in metrics_list if m), {})
                array_metrics = [
                    key for key, value in first_metrics.items()
                    if value is not None and is_array_like(value)
                ]
                
                # Separate arrays and scalar metrics
                for metrics in metrics_list:
                    scalar_metrics = metrics.copy()
                    
                    # Extract arrays, remove from scalar metrics
                    for array_metric in array_metrics:
                        if array_metric in scalar_metrics:
                            array_data = scalar_metrics.pop(array_metric)
                            if array_data is not None:
                                # Initialize array dict if needed
                                if array_metric not in arrays_dict:
                                    arrays_dict[array_metric] = []
                                    
                                # Ensure array is numpy array and has no NaN values
                                arr = np.array(array_data)
                                if not np.isnan(arr).any():  # Only include non-NaN arrays
                                    arrays_dict[array_metric].append(arr)
                    
                    scalar_metrics_list.append(scalar_metrics)
                
                # Aggregate scalar metrics normally
                result = aggregate_results(scalar_metrics_list, mean_func)
                
                # Aggregate arrays by applying appropriate mean_func across corresponding indices
                for array_metric, arrays in arrays_dict.items():
                    if arrays:
                        # Get specific aggregation function for this metric
                        array_agg_func = get_aggregation_func(array_metric)
                        
                        # Find minimum and maximum lengths
                        min_len = min(len(arr) for arr in arrays)
                        max_len = max(len(arr) for arr in arrays)
                        
                        if min_len != max_len:
                            # Trim all arrays to the shortest length to ensure proper alignment
                            arrays = [arr[:min_len] for arr in arrays]
                        
                        # Stack arrays directly without padding
                        stacked = np.stack(arrays)
                        averaged = safe_apply_along_axis(array_agg_func, stacked)

                        
                        # Ensure no NaN values in final result
                        if np.isnan(averaged).any():
                            # Forward fill NaN values
                            mask = np.isnan(averaged)
                            idx = np.where(~mask, np.arange(mask.shape[0]), 0)
                            np.maximum.accumulate(idx, out=idx)
                            averaged = averaged[idx]
                            
                            # If still have NaN at the end, backward fill
                            if np.isnan(averaged[-1]):
                                averaged = pd.Series(averaged).fillna(method='bfill').values
                        
                        result[array_metric] = averaged
                
                strategy_performance[strategy][interval] = result
    
    # Calculate overall metrics for each strategy
    for strategy in list(strategy_performance.keys()):
        interval_metrics = [
            metrics for interval, metrics in strategy_performance[strategy].items()
            if interval != 'overall' and metrics.get('Mean')
        ]
        
        if not interval_metrics:
            strategy_performance[strategy]['overall'] = default_strategy_result['overall']
            continue
        
        # Get all metrics keys from the first interval
        metric_keys = set(interval_metrics[0]['Mean'].keys())
        
        # Calculate overall metrics using vectorized operations
        overall_metrics = {}
        
        # Detect array metrics from first interval
        first_interval = next(iter(interval_metrics))
        array_metrics = [
            key for key in first_interval.keys()
            if key in first_interval and is_array_like(first_interval[key])
        ]
        
        # Handle array metrics first
        for array_metric in array_metrics:
            arrays = []
            for interval in interval_metrics:
                if array_metric in interval and interval[array_metric] is not None:
                    arrays.append(interval[array_metric])
            
            if arrays:
                # Get specific aggregation function for this metric
                array_agg_func = get_aggregation_func(array_metric)
                
                # Find minimum length to ensure proper alignment
                min_len = min(len(arr) for arr in arrays)
                
                # Trim all arrays to minimum length
                arrays = [arr[:min_len] for arr in arrays]
                
                # Stack and average using appropriate function
                stacked = np.stack(arrays)
                averaged = safe_apply_along_axis(array_agg_func, stacked)
                
                # Handle any remaining NaN values
                if np.isnan(averaged).any():
                    averaged = pd.Series(averaged).fillna(method='ffill').fillna(method='bfill').values
                
                overall_metrics[array_metric] = averaged
        
        # Handle scalar metrics
        for metric in metric_keys:
            if metric not in array_metrics:
                values = []
                for interval in interval_metrics:
                    try:
                        value = interval['Mean'][metric]
                        values.append(value)
                    except KeyError:
                        print(f"Metric '{metric}' not found in interval results.")
                
                if values:
                    # Use specific aggregation function if available
                    metric_agg_func = get_aggregation_func(metric)
                    overall_metrics[metric] = metric_agg_func(pd.Series(values))
                else:
                    overall_metrics[metric] = default_value
        
        strategy_performance[strategy]['overall'] = overall_metrics
    
    return strategy_performance 

def analyze_symbol_results_per_strategy(
    symbol_interval_results: Dict,
    mean_func: Callable = AGGREGATE_MEAN_FUNC
) -> Dict:
    """
    Analyze results per strategy with vectorized operations where possible.
    """
    if not symbol_interval_results:
        return {}
    
    strategy_performance = {}
    
    # Process each symbol and strategy
    for symbol, strategy_results in symbol_interval_results.items():
        for strategy, results in strategy_results.items():
            if strategy not in strategy_performance:
                strategy_performance[strategy] = []
            
            # Handle None values and empty results
            valid_results = []
            for result in results:
                if result is None:
                    result = {'total_return': 0.0}  # Default values for None
                valid_results.append(result)
            
            if valid_results:
                # Create DataFrame for vectorized operations
                results_df = pd.DataFrame(valid_results)
                if not results_df.empty:
                    # Get numeric columns
                    numeric_cols = results_df.select_dtypes(include=[np.number]).columns
                    
                    # Aggregate metrics
                    aggregated_result = results_df[numeric_cols].agg(mean_func).to_dict()
                    aggregated_result['symbol'] = symbol
                    
                    strategy_performance[strategy].append(aggregated_result)
    
    # Sort results by total_return for each strategy
    for strategy in strategy_performance:
        if strategy_performance[strategy]:
            strategy_performance[strategy].sort(
                key=lambda x: x.get('total_return', 0),
                reverse=True
            )
    
    return strategy_performance

def sort_strategies_by_performance(aggregated_performance, metric, reverse=True):
    """
    Sorts strategies based on a specified performance metric.

    :param aggregated_performance: Dictionary of aggregated performance metrics for each strategy
    :param metric: The metric to sort by (default is 'omega_ratio')
    :param reverse: If True, sort in descending order (default); if False, sort in ascending order
    :return: List of tuples (strategy_name, performance_metrics) sorted by the specified metric
    """
    sorted_strategies = sorted(aggregated_performance.items(),
                               key=lambda x: x[1]['overall'][metric],
                               reverse=reverse)
    return sorted_strategies



def save_results(results, strategy_name, interval, output_dir='backtesting_results'):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{strategy_name}_{interval}_results.json"
    filepath = os.path.join(output_dir, filename)

    # Convert only leaf values to strings
    results = convert_leaf_values_to_string(results)

    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results for {strategy_name} ({interval}) saved to {filepath}")


def save_aggregated_results(aggregated_results, output_dir='backtesting_results'):
    os.makedirs(output_dir, exist_ok=True)
    filename = "aggregated_results.json"
    filepath = os.path.join(output_dir, filename)

    # Convert only leaf values to strings
    aggregated_results = convert_leaf_values_to_string(aggregated_results)

    with open(filepath, 'w') as f:
        json.dump(aggregated_results, f, indent=2)

    print(f"Aggregated results saved to {filepath}")


def save_symbol_results(symbol_results, output_dir='backtesting_results'):
    os.makedirs(output_dir, exist_ok=True)
    filename = "symbol_results.json"
    filepath = os.path.join(output_dir, filename)

    # Convert only leaf values to strings
    symbol_results = convert_leaf_values_to_string(symbol_results)

    with open(filepath, 'w') as f:
        json.dump(symbol_results, f, indent=2)

    print(f"Symbol results saved to {filepath}")

def plot_backtest_results(result, symbol, interval, save_to_file=True):

    # if save_to_file:
    #     plot_dir = 'backtest_plots'
    #     os.makedirs(plot_dir, exist_ok=True)
    #     base_filename = f"{symbol}_{interval}"
        
    #     # NOTE: ONLY SAVE THE BEST IMAGE (WILL BE FASTER!)
    #     # Fast check for the best metric value
    #     best_metric = float('-inf')
    #     for filename in os.listdir(plot_dir):
    #         if filename.startswith(base_filename) and filename.endswith('_backtest_results.png'):
    #             match = re.search(r'%=(-?\d+\.?\d*)', filename)
    #             if match:
    #                 try:
    #                     file_metric = float(match.group(1))
    #                     best_metric = max(best_metric, file_metric)
    #                 except ValueError:
    #                     print(f"Warning: Could not convert percentage to float in filename: {filename}")
    #             else:
    #                 print(f"Warning: No percentage found in filename: {filename}")

    #     # If current result is not better, return early
    #     if result['metrics']['total_return'] <= best_metric:
    #         return


    # PLOT ALL POSITIVE RESULTS
    if result['metrics']['total_return'] <= 0:
        return


    try:
        metrics = result['metrics']
        vdata = result['visualization_data']

        # Check if there were any trades
        if all(vdata['equity'] == vdata['equity'][0]):
            log_dir = 'backtest_plots'
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'no_trades_log.txt')
            with open(log_file, 'a') as f:
                f.write(f"{symbol},{interval}\n")
            return  # Exit the function without plotting

        # plt.style.use('seaborn-v0_8-darkgrid')
        # sns.set_palette("muted")

        # Rest of your existing code, but with these modifications:
        plt.style.use('fast')  # Use fast style
        fig = plt.figure(figsize=(15, 35), dpi=100)  # Reduced size and DPI


        fig.canvas.draw()
        gs = GridSpec(10, 2, figure=fig, height_ratios=[2, 1, 1, 1, 1, 1, 1, 1, 1, 0.5])

        x_axis = np.arange(len(vdata['close_prices']))

        # Plot 1: Asset price with entry/exit signals
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(x_axis, vdata['close_prices'], color='grey', linewidth=1, label='Close Price')

        # Plot filled entries and exits
        ax1.scatter(np.where(vdata['filled_long_entries'] == 1)[0], vdata['close_prices'][vdata['filled_long_entries'] == 1],
                    color='green', marker='^', s=50, alpha=1, label='Filled Long Entries')
        ax1.scatter(np.where(vdata['filled_long_exits'] == 1)[0], vdata['close_prices'][vdata['filled_long_exits'] == 1],
                    color='red', marker='v', s=50, alpha=1, label='Filled Long Exits')
        ax1.scatter(np.where(vdata['filled_short_entries'] == 1)[0], vdata['close_prices'][vdata['filled_short_entries'] == 1],
                    color='blue', marker='v', s=50, alpha=1, label='Filled Short Entries')
        ax1.scatter(np.where(vdata['filled_short_exits'] == 1)[0], vdata['close_prices'][vdata['filled_short_exits'] == 1],
                    color='orange', marker='^', s=50, alpha=1, label='Filled Short Exits')

        # Plot unfilled entries and exits
        ax1.scatter(np.where(vdata['unfilled_long_entries'] == 1)[0], vdata['close_prices'][vdata['unfilled_long_entries'] == 1],
                    color='green', marker='^', s=50, alpha=0.3, label='Unfilled Long Entries')
        ax1.scatter(np.where(vdata['unfilled_long_exits'] == 1)[0], vdata['close_prices'][vdata['unfilled_long_exits'] == 1],
                    color='red', marker='v', s=50, alpha=0.3, label='Unfilled Long Exits')
        ax1.scatter(np.where(vdata['unfilled_short_entries'] == 1)[0], vdata['close_prices'][vdata['unfilled_short_entries'] == 1],
                    color='blue', marker='v', s=50, alpha=0.3, label='Unfilled Short Entries')
        ax1.scatter(np.where(vdata['unfilled_short_exits'] == 1)[0], vdata['close_prices'][vdata['unfilled_short_exits'] == 1],
                    color='orange', marker='^', s=50, alpha=0.3, label='Unfilled Short Exits')

        ax1.set_ylabel('Price')
        ax1.set_title(f"{symbol} Price Chart with Entry/Exit Signals")
        ax1.legend()

        # Plot 2: Portfolio Value (Equity)
        ax2 = fig.add_subplot(gs[1, :], sharex=ax1)
        ax2.plot(x_axis, vdata['equity'], color='blue', linewidth=2)
        ax2.set_ylabel('Portfolio Value')
        ax2.set_title('Strategy Equity Performance')

        # Plot 3: Collected Profits
        ax3 = fig.add_subplot(gs[2, :], sharex=ax1)
        ax3.plot(x_axis, vdata['equity_curve_snapshots'], color='green', linewidth=2)
        ax3.set_ylabel('Collected Profits')
        ax3.set_title('Collected Profits Over Time')

        # Plot 4: Drawdowns
        ax4 = fig.add_subplot(gs[3, :], sharex=ax1)
        ax4.fill_between(x_axis, vdata['drawdowns'], alpha=0.3)
        ax4.set_ylabel('Drawdown (%)')
        ax4.set_title('Drawdowns Over Time')

        # Plot 5: Position Sizes
        ax5 = fig.add_subplot(gs[4, :], sharex=ax1)
        ax5.plot(x_axis, vdata['position_long_sizes'], color='green', linewidth=2, label='Long Positions')
        ax5.plot(x_axis, -np.array(vdata['position_short_sizes']), color='red', linewidth=2, label='Short Positions')
        ax5.set_ylabel('Position Size')
        ax5.set_title('Long and Short Position Sizes Over Time')
        ax5.legend()

        # Plot 6: Concurrent Trades
        ax6 = fig.add_subplot(gs[5, :], sharex=ax1)
        ax6.plot(x_axis, vdata['concurrent_long_trades'], color='green', linewidth=2, label='Long Trades')
        ax6.plot(x_axis, vdata['concurrent_short_trades'], color='red', linewidth=2, label='Short Trades')
        ax6.set_ylabel('Number of Trades')
        ax6.set_title('Concurrent Long and Short Trades')
        ax6.legend()

        # Plot 7: Individual Trade Returns
        ax7 = fig.add_subplot(gs[6, :])
        long_returns = [trade['realized_profit'] / (trade.get_position_size() * trade['entry_price']) 
                        for trade in vdata['trades'] if trade['is_long']]
        short_returns = [trade['realized_profit'] / (trade.get_position_size() * trade['entry_price']) 
                        for trade in vdata['trades'] if not trade['is_long']]
        
        ax7.bar(range(len(long_returns)), long_returns, color='green', alpha=0.5, label='Long Trades')
        ax7.bar(range(len(long_returns), len(long_returns) + len(short_returns)), short_returns, color='red', alpha=0.5, label='Short Trades')
        ax7.set_xlabel('Trade Number')
        ax7.set_ylabel('Return (%)')
        ax7.set_title('Individual Trade Returns')
        ax7.legend()


        # Plot 8: Trade Duration vs Profit
        ax8 = fig.add_subplot(gs[7, 0])
        long_durations = [trade['duration'] for trade in vdata['trades'] if trade['is_long']]
        long_profits = [trade['realized_profit'] for trade in vdata['trades'] if trade['is_long']]
        short_durations = [trade['duration'] for trade in vdata['trades'] if not trade['is_long']]
        short_profits = [trade['realized_profit'] for trade in vdata['trades'] if not trade['is_long']]
        ax8.scatter(long_durations, long_profits, color='green', alpha=0.5, label='Long Trades')
        ax8.scatter(short_durations, short_profits, color='red', alpha=0.5, label='Short Trades')
        ax8.set_xlabel('Trade Duration (days)')
        ax8.set_ylabel('Profit')
        ax8.set_title('Trade Duration vs Profit')
        ax8.legend()

        # Plot 9: Trade Returns Distribution
        ax9 = fig.add_subplot(gs[7, 1])
        sns.histplot(long_returns, kde=True, color='green', alpha=0.5, label='Long Trades', ax=ax9)
        sns.histplot(short_returns, kde=True, color='red', alpha=0.5, label='Short Trades', ax=ax9)
        ax9.set_xlabel('Trade Return (%)')
        ax9.set_ylabel('Frequency')
        ax9.set_title('Distribution of Trade Returns')
        ax9.legend()

        # Format x-axis to show dates at regular intervals
        date_ticks = np.linspace(0, len(x_axis) - 1, 10, dtype=int)
        for ax in [ax1, ax2, ax3, ax4, ax5, ax6]:
            ax.set_xlim(0, len(x_axis) - 1)
            ax.set_xticks(date_ticks)
            ax.set_xticklabels([vdata['dates'][i].strftime('%Y-%m-%d') for i in date_ticks],
                              rotation=45, ha='right')

        # Add overall title
        plt.suptitle(f"{symbol} Strategy Performance ({interval})", fontsize=20, y=0.995)

        # Adjust layout and display
        plt.tight_layout()
        plt.subplots_adjust(top=0.95, bottom=0.05, hspace=0.4)

        # Force draw before saving
        fig.canvas.draw()

        if save_to_file:
            # Save with percentage in filename
            filename = f"{symbol}_{interval}_%={result['metrics']['total_return']}_backtest_results.png"
            filepath = os.path.join(plot_dir, filename)
            fig.savefig(filepath, dpi=100)


            # NOTE: ONLY SAVE THE BEST IMAGE (WILL BE FASTER!)
            # Save as BEST
            best_filename = f"{symbol}_{interval}_BEST.png"
            best_filepath = os.path.join(plot_dir, best_filename)
            fig.savefig(best_filepath, dpi=100)

            # Save metrics to a separate text file
            metrics_text = "\n".join([
                f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"
                for k, v in result['metrics'].items()
                if isinstance(v, (int, float))
            ])
            metrics_filename = f"{symbol}_{interval}_%={result['metrics']['total_return']}_metrics.txt"
            metrics_filepath = os.path.join(plot_dir, metrics_filename)
            with open(metrics_filepath, 'w') as f:
                f.write(metrics_text)

        else:
            plt.show()

        # Clean up
        plt.close(fig)

    except Exception as e:
        print(f"Error in plotting: {str(e)}")
        traceback.print_exc()
        plt.close('all')



# def plot_backtest_results(result, symbol, interval, save_to_file=True):
#     try:
#         metrics = result['metrics']
#         vdata = result['visualization_data']

#         # Check if there were any trades
#         if all(vdata['equity'] == vdata['equity'][0]):
#             # No trades were made, log this information
#             log_dir = 'backtest_plots'
#             os.makedirs(log_dir, exist_ok=True)
#             log_file = os.path.join(log_dir, 'no_trades_log.txt')
            
#             with open(log_file, 'a') as f:
#                 f.write(f"{symbol},{interval}\n")
            
#             return  # Exit the function without plotting

#         # Set up the plot style
#         plt.style.use('seaborn-v0_8-darkgrid')
#         sns.set_palette("muted")

#         # Create figure and draw it immediately
#         fig = plt.figure(figsize=(20, 40))
#         fig.canvas.draw()  # Force initial draw
#         gs = GridSpec(8, 2, figure=fig, height_ratios=[2, 1, 1, 1, 1, 1, 1, 0.5])

#         # Generate continuous x-axis values
#         x_axis = np.arange(len(vdata['close_prices']))

#         # Plot 1: Asset price with entry/exit signals
#         ax1 = fig.add_subplot(gs[0, :])
#         ax1.plot(x_axis, vdata['close_prices'], color='grey', linewidth=1, label='Close Price')

#         # Define indices for long and short entries/exits
#         long_entry_indices = np.where(vdata['long_entries'] == 1)[0]
#         long_exit_indices = np.where(vdata['long_exits'] == 1)[0]
#         short_entry_indices = np.where(vdata['short_entries'] == 1)[0]
#         short_exit_indices = np.where(vdata['short_exits'] == 1)[0]

#         # Add long entry signals
#         ax1.scatter(long_entry_indices, vdata['close_prices'][long_entry_indices],
#                    color='green', marker='^', s=50, alpha=1, label='Long Entries')

#         # Add long exit signals
#         ax1.scatter(long_exit_indices, vdata['close_prices'][long_exit_indices],
#                    color='red', marker='v', s=50, alpha=1, label='Long Exits')

#         # Add short entry signals
#         ax1.scatter(short_entry_indices, vdata['close_prices'][short_entry_indices],
#                    color='blue', marker='v', s=50, alpha=1, label='Short Entries')

#         # Add short exit signals
#         ax1.scatter(short_exit_indices, vdata['close_prices'][short_exit_indices],
#                    color='orange', marker='^', s=50, alpha=1, label='Short Exits')

#         ax1.set_ylabel('Price')
#         ax1.set_title(f"{symbol} Price Chart with Entry/Exit Signals")
#         ax1.legend()


#         # Plot 2: Portfolio Value (Equity)
#         ax2 = fig.add_subplot(gs[1, :], sharex=ax1)
#         ax2.plot(x_axis, vdata['equity'], color='blue', linewidth=2)
#         ax2.set_ylabel('Portfolio Value')
#         ax2.set_title('Strategy Equity Performance')

#         # Plot 3: Collected Profits
#         ax3 = fig.add_subplot(gs[2, :], sharex=ax1)
#         ax3.plot(x_axis, vdata['equity_curve_snapshots'], color='green', linewidth=2)
#         ax3.set_ylabel('Collected Profits')
#         ax3.set_title('Collected Profits Over Time')

#         # Plot 4: Drawdowns
#         ax4 = fig.add_subplot(gs[3, :], sharex=ax1)
#         ax4.fill_between(x_axis, vdata['drawdowns'], alpha=0.3)
#         ax4.set_ylabel('Drawdown (%)')
#         ax4.set_title('Drawdowns Over Time')

#         # Plot 5: Individual Trade Returns
#         ax5 = fig.add_subplot(gs[4, :])
#         trade_returns = [trade['realized_profit'] / (trade['size'] * trade['entry_price']) 
#                         for trade in vdata['trades']]
#         ax5.bar(range(len(trade_returns)), trade_returns)
#         ax5.set_xlabel('Trade Number')
#         ax5.set_ylabel('Return (%)')
#         ax5.set_title('Individual Trade Returns')

#         # Plot 6: Total Concurrent Trades
#         ax6 = fig.add_subplot(gs[5, :], sharex=ax1)
#         ax6.plot(x_axis, vdata['concurrent_trades'], color='brown', linewidth=2)
#         ax6.set_ylabel('Number of Trades')
#         ax6.set_title('Total Concurrent Trades')

#         # Plot 7: Trade Duration vs Profit
#         ax7 = fig.add_subplot(gs[6, 0])
#         trade_durations = [trade['duration'] for trade in vdata['trades']]
#         trade_profits = [trade['realized_profit'] for trade in vdata['trades']]
#         ax7.scatter(trade_durations, trade_profits, alpha=0.5)
#         ax7.set_xlabel('Trade Duration (days)')
#         ax7.set_ylabel('Profit')
#         ax7.set_title('Trade Duration vs Profit')

#         # Plot 8: Trade Returns Distribution
#         ax8 = fig.add_subplot(gs[6, 1])
#         sns.histplot(trade_returns, kde=True, ax=ax8)
#         ax8.set_xlabel('Trade Return (%)')
#         ax8.set_ylabel('Frequency')
#         ax8.set_title('Distribution of Trade Returns')

#         # Format x-axis to show dates at regular intervals
#         date_ticks = np.linspace(0, len(x_axis) - 1, 10, dtype=int)
#         for ax in [ax1, ax2, ax3, ax4, ax6]:
#             ax.set_xlim(0, len(x_axis) - 1)
#             ax.set_xticks(date_ticks)
#             ax.set_xticklabels([vdata['dates'][i].strftime('%Y-%m-%d') for i in date_ticks],
#                               rotation=45, ha='right')

#         # Add overall title
#         plt.suptitle(f"{symbol} Strategy Performance ({interval})", fontsize=20, y=0.995)

#         metrics_text = "\n".join([
#             f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"
#             for k, v in metrics.items()
#             if isinstance(v, (int, float))  # Only include numeric values
#         ])

#         props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
#         fig.text(0.5, 0.02, metrics_text, fontsize=12,
#                 verticalalignment='bottom', horizontalalignment='center',
#                 bbox=props, transform=fig.transFigure)

#         # Adjust layout and display
#         plt.tight_layout()
#         plt.subplots_adjust(top=0.95, bottom=0.1, hspace=0.4)

#         # Force draw before saving
#         fig.canvas.draw()

#         if save_to_file:
#             plot_dir = 'backtest_plots'
#             os.makedirs(plot_dir, exist_ok=True)
#             filename = f"{symbol}_{interval}_backtest_results.png"
#             filepath = os.path.join(plot_dir, filename)
            
#             # Use Figure's savefig method directly instead of plt.savefig
#             fig.savefig(filepath, dpi=300, bbox_inches='tight')
#         else:
#             plt.show()

#         # Clean up
#         plt.close(fig)

#     except Exception as e:
#         print(f"Error in plotting: {str(e)}")
#         traceback.print_exc()
        
#         # Make sure to clean up even if there's an error
#         plt.close('all')
