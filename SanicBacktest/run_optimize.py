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


from hyperopt import hp
import logging

import numpy as np
from financial_metrics import _more_tb, _speedy_fn
from optimize import optimize_strategy_params
from data_handler import download_data
from asset_names import *
import sys
import os
import json
from helpers import play_notification_sound
import random
from hyperopt import hp

from strategies.exit_helpers import create_tsl_hyperopt_space
# Ensure the correct path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_metrics import *

# # Configure logging
# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)



def main():
    # symbols = forex
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


        df = df.tail(20000)
        print(f""" NOTE      # TODO: TAKING ONLY few rows
        df = df.head(20000)

# # """)

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


    interval = '5s'#'1h'#'1m'  # changed to 5m form 1h!  #15m is glitched idk why!!! TODO:


    # data_interval_dict = {
    #     interval: {
    #         symbol: download_data(symbol, num_candles, interval) for symbol in symbols
    #     }
    # }

    # Parameter space for hyperoptimization
    strategy_name = 'greasy_pig_strategy_long'
    param_space = {
        'ema_period': hp.quniform('ema_period', 3, 80, 1),
        'slope_period': hp.quniform('slope_period', 3, 40, 1),
        'straightness_threshold': hp.uniform('straightness_threshold', 0.0, 1.0),
        # Corrected range
        'slope_threshold': hp.uniform('slope_threshold', -1.0, 1.0),
        # in %
        'trend_score_window_size': hp.quniform('trend_score_window_size', 4, 60, 1),
        'trend_score_smoothing_period': hp.quniform('trend_score_smoothing_period', 2, 30, 1),
        # More focused range
        'trend_ema_period': hp.quniform('trend_ema_period', 5, 120, 1),
        # Shorter windows for responsiveness
        'trend_ema_slope_period': hp.quniform('trend_ema_slope_period', 5, 60, 1),
        # Tighter threshold range
        'trend_ema_threshold': hp.uniform('trend_ema_threshold', -1, 1),



        'max_deviation_percentage': hp.uniform('max_deviation_percentage', -20, 20),
        
        'use_heikin_ashi': hp.choice('use_heikin_ashi', [True, False]),
        # disabled, tsl will suffice
        'use_tp': hp.choice('use_tp', [True, False]),
        'take_profit_percentage': hp.uniform('take_profit_percentage', 0.4, 40),
        'tsl_params': create_tsl_hyperopt_space(),


        # NOTE: leverage is used in def backtest_strategy_for_symbol
        'leverage': hp.quniform('leverage', 1, 1000, 1),
    }

    print(f" $$$$ FIX LEVERAGE HYPEROPT PARAMS TO 1-> 1000")

    # # # Updated parameter space
    # strategy_name = 'hma_dip_detector_strategy'
    # param_space = {
    #     'long_ma_period': hp.quniform('long_ma_period', 12, 200, 1),
    #     'short_ma_period': hp.quniform('short_ma_period', 4, 50, 1),
    #     'short_ma_type': hp.choice('short_ma_type', ['HMA', 'EMA']),
    #     'slope_period': hp.quniform('slope_period', 3, 50, 1),
    #     'accel_period': hp.quniform('accel_period', 3, 50, 1),
    #     'dip_threshold': hp.uniform('dip_threshold', -1.0, 1.0),
    #     'hma_slope_min_threshold': hp.uniform('hma_slope_min_threshold', -1.0, 1.0),
    #     'hma_slope_max_threshold': hp.uniform('hma_slope_max_threshold', -1.0, 1.0),
    #     'hma_accel_threshold': hp.uniform('hma_accel_threshold', -1.0, 1.0),
    #     'use_heikin_ashi': hp.choice('use_heikin_ashi', [True, False]),
    #     'use_rsi_filter': hp.choice('use_rsi_filter', [False]), # NOTE: turned off! #[True, False]),
    #     # 'rsi_period': hp.quniform('rsi_period', 7, 50, 1),
    #     # 'rsi_oversold': hp.uniform('rsi_oversold', 5, 50),
    #     'use_bb_squeeze': hp.choice('use_bb_squeeze', [False]), # NOTE: turned off! #[True, False]),
    #     # 'bb_length': hp.quniform('bb_length', 6, 50, 1),
    #     # 'bb_std': hp.uniform('bb_std', 1.0, 3.0),
    #     # 'bb_squeeze_threshold': hp.uniform('bb_squeeze_threshold', 0.00, 0.5),
    #     'c1': hp.uniform('c1', 0.0, 4.0),

    #     'use_tp': hp.choice('use_tp', [True, False]),
    #     'take_profit_percentage': hp.uniform('take_profit_percentage', 0.5, 20),
    #     'tsl_params': create_tsl_hyperopt_space(),
    # }

    # # Updated parameter space for Adaptive Mean Reversion
    # strategy_name = 'adaptive_mean_reversion'
    # param_space = {
    #     # Lookback period for rolling mean and std dev
    #     'lookback': hp.quniform('lookback', 4, 100, 1),
    #     # Rolling window for realized volatility calculation
    #     'vol_window': hp.quniform('vol_window', 4, 50, 1),
    #     # Confidence level for dynamic Bollinger Bands
    #     'confidence_level': hp.uniform('confidence_level', 0.5, 0.999),
    #     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
    #     'c1': hp.uniform('c1', 0.0, 4.0),
    #     'c2': hp.uniform('c2', 0.0, 4.0),
    #     'c3': hp.uniform('c3', 0.0, 4.0),
    #     'c4': hp.uniform('c4', 0.0, 4.0),
    #     'c5': hp.uniform('c5', 0.5, 10.0),

    #     # Period for EMA in trailing stop loss
    #        'tsl_params': create_tsl_hyperopt_space(),
    # }

    # # # Parameter space for hyperoptimization
    # strategy_name = 'calculus_trend_strategy'
    # param_space = {
    #     'velocity_period': hp.quniform('velocity_period', 3, 40, 1),
    #     'accel_period': hp.quniform('accel_period', 2, 30, 1),
    #     'smooth_period': hp.quniform('smooth_period', 2, 20, 1),
    #     'fast_period': hp.quniform('fast_period', 4, 30, 1),
    #     'slow_period': hp.quniform('slow_period', 10, 120, 1),
    #     # 'min_velocity': hp.loguniform('min_velocity', np.log(0.00001), np.log(0.1)),
    #     'min_velocity': hp.uniform('min_velocity', 0.0, 0.5),
    #     # 'min_accel': hp.loguniform('min_accel', np.log(0.00001), np.log(0.1)),
    #     'min_accel': hp.uniform('min_accel', 0.0, 0.5),

    #     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
    #     'c1': hp.uniform('c1', 0.0, 4.0),
    #     'c2': hp.uniform('c2', 0.0, 4.0),
    #     'c3': hp.uniform('c3', 0.0, 4.0),
    #     'c4': hp.uniform('c4', 0.0, 4.0),
    #     'c5': hp.uniform('c5', 0.0, 4.0),
    #     'tsl_params': create_tsl_hyperopt_space(),

    # }

    # # Parameter space for hyperoptimization
    # strategy_name = 'volatility_breakout_strategy'
    # param_space = {
    #     'vol_window': hp.quniform('vol_window', 4, 80, 1),
    #     'price_window': hp.quniform('price_window', 4, 80, 1),
    #     'std_dev_threshold': hp.uniform('std_dev_threshold', 0.1, 4.0),
    #     'momentum_period': hp.quniform('momentum_period', 3, 40, 1),
    #     'smooth_period': hp.quniform('smooth_period', 2, 40, 1),
    #     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
    #     # Entry condition multipliers
    #     'c1': hp.uniform('c1', 0.0, 4.0),
    #     'c2': hp.uniform('c2', 0.0, 4.0),
    #     'c3': hp.uniform('c3', 0.0, 4.0),
    #     'c4': hp.uniform('c4', 0.0, 4.0),
    #     # Exit condition multipliers
    #     'c5': hp.uniform('c5', 0.0, 4.0),
    #     'c6': hp.uniform('c6', 0.0, 4.0),
    #     'c7': hp.uniform('c7', 0.0, 4.0),
    #     'c8': hp.uniform('c8', 0.0, 4.0),
    #     'c9': hp.uniform('c9', 0.0, 4.0),
    #     'tsl_params': create_tsl_hyperopt_space(),
    # }

    # # Parameter space for hyperoptimization
    # strategy_name = 'statistical_divergence_strategy'
    # param_space = {
    #     'decomp_window': hp.quniform('decomp_window', 4, 80, 1),
    #     'vol_window': hp.quniform('vol_window', 5, 60, 1),
    #     'zscore_window': hp.quniform('zscore_window', 5, 100, 1),
    #     'entry_threshold': hp.uniform('entry_threshold', 0.2, 3.0),
    #     'smooth_period': hp.quniform('smooth_period', 2, 20, 1),
    #     'use_strategy_exits': hp.choice('use_strategy_exits', [True, False]),
    #     'c1': hp.uniform('c1', 0.0, 4.0),
    #     'c2': hp.uniform('c2', 0.0, 4.0),
    #     'c3': hp.uniform('c3', 0.0, 0.5),
    #     'c4': hp.uniform('c4', 0.0, 4.0),
    #     'c5': hp.uniform('c5', 0.0, 4.0),
    #      'tsl_params': create_tsl_hyperopt_space(),

    # }

    # # NOTE: USE THIS TO SETUP DEFAULT VALUES #TODO: idk if it works here

    # # Function to set default values

    # ### PUT DEFAULT VALUES DICT HERE ###
    # default_values = {'accel_period': 27, 'bb_length': 31, 'bb_squeeze_threshold': 0.3825867906836435, 'bb_std': 2.921547652038045, 'c1': 2.2984462836685733, 'dip_threshold': 0.12028859711796501, 'hma_accel_threshold': -0.18034517593660818, 'hma_slope_max_threshold': 0.8318641197503228, 'hma_slope_min_threshold': 0.4005848071305464, 'long_ma_period': 172,
    #                   'rsi_oversold': 22.884904759569327, 'rsi_period': 8, 'short_ma_period': 23, 'short_ma_type': 'HMA', 'slope_period': 14, 'tsl_params': ((2.782313374492307, 0, 13.0), (2.6822089058272023, 1.3805480026219583, 11.0), (1.2803832968341775, 2.801869655887615, 3.0)), 'use_bb_squeeze': True, 'use_heikin_ashi': True, 'use_rsi_filter': True}

    # def set_default(space, default_values):
    #     for key, value in default_values.items():
    #         if key in space:
    #             # if key == 'use_strategy_exits':
    #             #     space[key] = hp.choice(key, [value, not value])
    #             # elif key == 'tsl_params':
    #             #     # NOTE: We don't modify the tsl_params space, allowing it to be optimized
    #             #     continue
    #             # else:
    #             space[key] = hp.choice(key, [value])
    #     return space

    # # Apply default values to the parameter space
    # param_space = set_default(param_space, default_values)

    # CONSTAIN

    def check_constraints(params, verbose=False):
        """Check all constraints for the given parameters."""
        if verbose:
            print(f"Checking constraints for params: {params}")

        ############## PUT STRATEGY SPECIFIC CONSTRAINS HERE! ########################


# # statistical_divergence_strategy
#         # Ensure zscore_window is greater than decomp_window
#         if params['zscore_window'] <= params['decomp_window']:
#             if verbose:
#                 print("zscore_window must be greater than decomp_window")
#             return {'loss': float('inf'), 'status': 'fail'}

#         # Ensure decomp_window is greater than vol_window
#         if params['decomp_window'] <= params['vol_window']:
#             if verbose:
#                 print("decomp_window must be greater than vol_window")
#             return {'loss': float('inf'), 'status': 'fail'}

# # volatility_breakout_strategy
#         # Ensure momentum period is less than price window
#         if params['momentum_period'] >= params['price_window']:
#             if verbose:
#                 print("momentum_period must be less than price_window")
#             return {'loss': float('inf'), 'status': 'fail'}

#         # Ensure smooth period is less than momentum period
#         if params['smooth_period'] >= params['momentum_period']:
#             if verbose:
#                 print("smooth_period must be less than momentum_period")
#             return {'loss': float('inf'), 'status': 'fail'}

# # #calculus_trend_strategy
#         # Ensure fast period is less than slow period
#         if params['fast_period'] >= params['slow_period']:
#             if verbose:
#                 print("fast_period must be less than slow_period")
#         #     return {'loss': float('inf'), 'status': 'fail'}

#         # # Ensure velocity period is greater than acceleration period
#         # if params['velocity_period'] <= params['accel_period']:
#         #     if verbose:
#         #         print("velocity_period must be greater than accel_period")
#             return {'loss': float('inf'), 'status': 'fail'}


# #    hma_dip_detector_strategy
#             # Ensure hma_slope_max_threshold > hma_slope_min_threshold
#             if params['hma_slope_max_threshold'] <= params['hma_slope_min_threshold']:
#                 if verbose:
#                     print(
#                         "hma_slope_max_threshold must be greater than hma_slope_min_threshold")
#                 return {'loss': float('inf'), 'status': 'fail'}

#         # Ensure short_ma_period < long_ma_period
#         if params['short_ma_period'] >= params['long_ma_period']:
#             if verbose:
#                 print("short_ma_period must be less than long_ma_period")
#             return {'loss': float('inf'), 'status': 'fail'}

        ############ DONT TOUCH! TRAILING STOP LOSS CONSTRAINS HERE! ####################

        tsl_params = params['tsl_params']
        if not tsl_params:
            if verbose:
                logger.error("tsl_params is empty.")
            return {'loss': float('inf'), 'status': 'fail'}

        for i in range(len(tsl_params)):
            # Ensure each element is a list with exactly three elements
            if isinstance(tsl_params[i], (list, tuple)) and len(tsl_params[i]) == 3:
                tsl_pct = tsl_params[i][0]
                activ_pct = tsl_params[i][1]
                ema_period = tsl_params[i][2]
            else:
                if verbose:
                    logger.error(f"Entry {i} does not have exactly three elements: {
                                 tsl_params[i]}")
                return {'loss': float('inf'), 'status': 'fail'}

            # First entry must have activation percentage of 0
            if i == 0 and activ_pct != 0:
                if verbose:
                    logger.error(
                        f"First activation percentage is not 0 (found {activ_pct})")
                return {'loss': float('inf'), 'status': 'fail'}

            # Constraints for subsequent entries
            if i > 0:
                prev_tsl_pct = tsl_params[i - 1][0]
                prev_activ_pct = tsl_params[i - 1][1]
                prev_ema_period = tsl_params[i - 1][2]

                # TSL percentage must decrease
                if tsl_pct >= prev_tsl_pct:
                    if verbose:
                        logger.error(f"Constraint failed at index {i}: tsl_pct ({
                                     tsl_pct}) >= prev_tsl_pct ({prev_tsl_pct})")
                    return {'loss': float('inf'), 'status': 'fail'}

                # Activation percentage must increase
                if activ_pct <= prev_activ_pct:
                    if verbose:
                        logger.error(f"Constraint failed at index {i}: activ_pct ({
                                     activ_pct}) <= prev_activ_pct ({prev_activ_pct})")
                    return {'loss': float('inf'), 'status': 'fail'}

                # EMA period must decrease
                if ema_period >= prev_ema_period:
                    if verbose:
                        logger.error(f"Constraint failed at index {i}: ema_period ({
                                     ema_period}) >= prev_ema_period ({prev_ema_period})")
                    return {'loss': float('inf'), 'status': 'fail'}

        if verbose:
            logger.info("All constraints passed.")
        return None

################################################################################
################################################################################

    """
    Best Hyperopt Loss Functions:
    - perfect_sharpe
    - tradex_sharpe

    - Murke (custom: Burke & Martin Fusion)
        * perfect_murke
        * tradex_murke

        
    - better_profit
    - tradex_profit

    -tradex_citrus

    tradex_sharptino
    DONT USE SPEEDY -> REMOVE IT! If you want short trades use tradex -> shortness as consequence of many!
    """
    
    N_PARALLEL = 10# ~10 MAX! > 20 and insta-crash!

    # """You can Hyperopt using REWARD for EACH backtest/chart OR for ALL aggregated equity curve!"""
    # """
    # Option 1:  EACH backtest/chart NOTE: does NOT work well!!!
    #     sorting_metric = 'expectancy'
    # """
    # sorting_metric = 'total_return'
    
    """
    Option 2: ALL aggregated equity curve!
    """

    def calculate_returns_from_snapshots(normalized_equity_curve_snapshots):
        equity_curve = np.array(normalized_equity_curve_snapshots)
        change_indices = np.where(np.diff(equity_curve) != 0)[0] + 1
        unique_indices = np.unique(np.concatenate(([0], change_indices, [len(equity_curve) - 1])))
        unique_equity_values = equity_curve[unique_indices]
        
        # Avoid division by zero
        returns = np.diff(unique_equity_values) / np.maximum(unique_equity_values[:-1], 1e-8)
        
        return returns.tolist()


    def MY_SHARED_REWARD_FUNC_ON_EQUITY(normalized_equity_curve, metrics):
        """ will take normalized_equity_curve_snapshots equity curve! u can change it to be continous too, or remove all shared to get other! 
        
        ** NOTE:HOWEVER u must take returns! USE diff()"""


        # Calculate returns
        valid_indices = np.isfinite(normalized_equity_curve[:-1]) & (normalized_equity_curve[:-1] != 0)
        returns_from_equity = np.zeros_like(normalized_equity_curve[:-1])
        returns_from_equity[valid_indices] = np.diff(normalized_equity_curve)[valid_indices] / normalized_equity_curve[:-1][valid_indices]



        returns = metrics["trade_returns"]
        profit = better_profit_term(returns, metrics)
        e, m = returns, metrics

        if profit == 0:
            return -1e16
        

        def profit_reward(returns, metrics):
            bpt= better_profit_term(returns, metrics)

            return bpt
        
        bpt = better_profit_term(returns, metrics)

        def expectancy_reward(returns, metrics):
            expectancy = calculate_expectancy(returns)
            if profit >= 0:
                # NOTE: DO NOT use _more_tb !
                return expectancy * len(returns)
            else:
                return expectancy

        def modian_reward(returns, metrics):
            mean = np.mean(returns)
            median = np.median(returns)
            modian = (mean + median) / 2
            if profit >= 0:
                # NOTE: DO NOT use _more_tb !
                return modian * len(returns)
            else:
                return modian


        def chosen_reward(returns, metrics):
            # USE ** 2 ! finds better results than linear!
            return signed_power(perfect_burke(returns, metrics), 1.2)
        

        # USE PROFIT FOR TURBOWAVE  
        # print(metrics)

        ret_x_expec =  metrics["total_return"]  * np.abs(metrics["expectancy"])
        # diff for pos and neg
        if ret_x_expec <0:
            return ret_x_expec
        
        # rew = signed_power(ret_x_expec, 4) * np.log1p(metrics["total_trades"]) / (1+np.log1p(metrics["avg_hold_time"])) # WORKS! PERFECT BUT CONSERVATIVE FOR QUICK-> LOW DD!


        """
        NOTE:
            using 'returns_from_equity' in ratios results in smoother/nicer equity curve
            using raw returns will mean the time when you're HOLDING may be dangerous and turbulent
        """


        # IF PROFIT NEG, DONT COMBINE WITH ANYTHING!
        if metrics["total_return"] < 0:
            return metrics["total_return"]
        

        # rew = np.log1p(metrics["num_wins"]) * signed_power(perfect_sharpe(returns_from_equity, m), 2) 

        # rew =signed_power(perfect_sharpe(returns, metrics) , 5)  * np.log1p(metrics["total_trades"]) / (1+np.log1p(metrics["avg_hold_time"]))
        # rew = abs(rew) * metrics["total_return"] # works!

        # rew = perfect_murke(returns_from_equity, metrics)   # WORKS PERFECT ! TURBOWAVE A+
        # rew = perfect_murke(metrics["trade_returns"], metrics) # WORKS PERFECT ! TURBOWAVE A+




        # rew = signed_power( metrics["total_return"] , 3) * np.log1p(metrics["num_wins"])
        rew = metrics["total_return"]
        
        # rew = abs(perfect_murke(returns_from_equity, m)) * (metrics["total_return"]**2) * np.log1p(metrics["total_trades"]) / (1+(np.log1p(metrics["avg_hold_time"]) * calculate_avg_drawdown(returns_from_equity))) # WORKS! 

        

        # rew = signed_power(  metrics["total_return"], 5) / (1+ calculate_max_drawdown(returns_from_equity))


        # force a trade
        return -1e16 if rew==0 else rew
    
        # can have 0's
        return rew

    
        # turn equity graph INTO returns list! NO equity !        
    # better_profit_term#lambda e, m: -1e20 if better_profit_term(e, m) ==0 else     better_profit_term(e, m)                                                     #_more_tb(e, m, perfect_sharpe(e, m), trade_boost_exp=0.5)
    # _speedy_fn(e, m, lambda e,m: 
    # )


    reward_equity_func = MY_SHARED_REWARD_FUNC_ON_EQUITY
    
                             

    best_params, best_performance, top_results = optimize_strategy_params(
        strategy_name,
        symbols,
        num_candles,
        interval,
        param_space,
        data_interval_dict=data_interval_dict,
        should_plot=True, 
        max_workers_strategies=N_PARALLEL,
        max_workers_symbols=N_PARALLEL,
        max_evals=1000000,
        revert_loss_to_reward=True,
        check_constraints=check_constraints,

        # sorting_metric_key=sorting_metric,
        reward_equity_func=reward_equity_func,
        should_normalize_data=True, 
    )

    # print(f"\nBest Parameters for {strategy_name}")
    # print(best_params)

    # print(f"\nBest Performance for {strategy_name}:")
    # print(f" {sorting_metric} {best_performance[sorting_metric]:.2f}")

    # Save results
    results = {
        strategy_name: {
            'best_params': best_params,
            'best_performance': best_performance,
            'top_results': top_results
        }
    }

    with open(f'{strategy_name}_{interval}_optimized_strategy_results.json', 'w') as f:
        json.dump(results, f, indent=2)



if __name__ == "__main__":
    main()



