from datetime import datetime
import os
from hyperopt import hp, fmin, STATUS_OK, Trials, early_stop
from hyperopt.pyll.base import Apply
from matplotlib import pyplot as plt
from backtester import run_backtesting, aggregate_strategy_performance, sort_strategies_by_performance, convert_leaf_values_to_string
import json

from hyperopt import rand, tpe, STATUS_OK, STATUS_FAIL
import numpy as np
from hyperopt.base import miscs_update_idxs_vals
from hyperopt import rand, tpe, atpe


class RandomFollowedByTPEAlgo:
    def __init__(self, r_count, tpe_count, initial_r):
        self.r_count = r_count
        self.tpe_count = tpe_count
        self.initial_r = initial_r
        self.random_algo = rand.suggest
        """
        ATPE vs TPE:
        - Adaptive search strategy
        - Faster convergence
        - Better for complex spaces
        - Easy TPE replacement
        """
        """
        NOTE: if you use 'hyperopt' fresh, it will break atpe ! u need to make code change!
            https://github.com/hyperopt/hyperopt/pull/861/files/a7922ea76a69dd486be93e140c4420baf166eda7
            #value = random.randint(min, max)
            value = random.randint(min, max - 1)' 
        """
        self.tpe_algo = atpe.suggest# use ATPE may be better #tpe.suggest
        self.current_trial = 0

    def suggest(self, new_ids, domain, trials, seed):
        self.current_trial = len(trials.trials)
        
        if self.current_trial < self.initial_r:
            return self.random_algo(new_ids, domain, trials, seed)
        
        cycle_length = self.r_count + self.tpe_count
        cycle_position = (self.current_trial - self.initial_r) % cycle_length
        
        if cycle_position < self.r_count:
            return self.random_algo(new_ids, domain, trials, seed)
        else:
            return self.tpe_algo(new_ids, domain, trials, seed)

# TODO: find optimal params! 
#  (r_count=10, tpe_count=20, initial_r=10):
def get_random_followed_by_tpe_algo(r_count=1, tpe_count=4, initial_r=0):

    """
    Factory function to create an algorithm that does initial random trials,
    then cycles between X random trials followed by Y TPE trials.
    
    Args:
        r_count: Number of random trials in each cycle after initial phase
        tpe_count: Number of TPE trials in each cycle
        initial_r: Number of initial random trials before cycling begins
    
    Returns:
        suggest: The suggestion function for hyperopt
    """
    algo = RandomFollowedByTPEAlgo(r_count=r_count, tpe_count=tpe_count, initial_r=initial_r)
    return algo.suggest


# Example usage:
"""
from hyperopt import fmin, hp, Trials

def objective(params):
    x = params['x']
    y = params['y']
    return {'loss': x**2 + y**2, 'status': STATUS_OK}

space = {
    'x': hp.uniform('x', -10, 10),
    'y': hp.uniform('y', -10, 10),
}

cycling_algo = get_cycling_hybrid_algo(initial_random=50, cycle_length=100, random_fraction=0.3)

trials = Trials()
best = fmin(
    fn=objective,
    space=space,
    algo=cycling_algo,
    max_evals=500,
    trials=trials
)
"""

def is_hyperopt_object(obj):
    """Check if an object is a hyperopt space object."""
    return hasattr(obj, 'pos_args') and hasattr(obj, 'named_args')


def get_hyperopt_choices(space):
    """Extract choices from a hyperopt choice object."""
    if isinstance(space, dict):
        return list(space.values())
    elif hasattr(space, 'pos_args'):
        return space.pos_args[1]
    return []


def remove_duplicate_params(param_space):
    """Remove duplicate parameter combinations from the param space."""
    unique_params = set()
    filtered_space = {}

    for key, space in param_space.items():
        if is_hyperopt_object(space):
            if hasattr(space, 'pos_args') and len(space.pos_args) > 1 and isinstance(space.pos_args[1], (list, tuple)):
                # This is likely a hp.choice object
                filtered_options = []
                for option in get_hyperopt_choices(space):
                    option_hash = params_to_hashable(option) if isinstance(
                        option, dict) else str(option)
                    if option_hash not in unique_params:
                        unique_params.add(option_hash)
                        filtered_options.append(option)
                filtered_space[key] = hp.choice(key, filtered_options)
            else:
                # For other hyperopt objects, keep them as is
                filtered_space[key] = space
        else:
            # For non-hyperopt objects, keep them as is
            filtered_space[key] = space

    return filtered_space


def params_to_hashable(params):
    """Convert params dict to a hashable representation."""
    def convert_value(value):
        if isinstance(value, (int, float, bool, str)):
            return value
        elif isinstance(value, list):
            return tuple(convert_value(v) for v in value)
        elif isinstance(value, dict):
            return tuple(sorted((k, convert_value(v)) for k, v in value.items()))
        else:
            return str(value)

    return json.dumps(convert_value(params), sort_keys=True)




import matplotlib.pyplot as plt
import os
from datetime import datetime
import re

def plot_equity_curve(equity_curve, equity_curve_snapshots, strategy_name, interval, iteration, sorting_metric, metric_value, save_path):

    base_filename = f'{strategy_name}_equity_{interval}_score'

    # NOTE: ONLY SAVE THE BEST IMAGE (WILL BE FASTER!)
    # Read existing files and find the best metric value
    best_metric = float('-inf')
    for filename in os.listdir(save_path):
        if filename.startswith(base_filename) and filename.endswith('.png'):
            match = re.search(r'score=(-?\d+\.?\d*)', filename)
            if match:
                try:
                    file_metric = float(match.group(1))
                    best_metric = max(best_metric, file_metric)
                except ValueError:
                    print(f"Warning: Could not convert score to float in filename: {filename}")
            else:
                print(f"Warning: No score found in filename: {filename}")


    # # Early return if the current metric is not the best
    # if metric_value <= best_metric:
    #     return None
        
    # plt.figure(figsize=(12, 10))
    plt.figure(figsize=(8, 6), dpi=60)  # Reduced from 12,10 and using lower DPI
    plt.style.use('fast')  # Use fast style



    title = f"{strategy_name} - {interval}\n{sorting_metric}: {metric_value}, Iteration: {iteration}"
    plt.suptitle(title, fontsize=14, y=0.98)

    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(equity_curve, linewidth=2, color='blue')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.set_ylabel('Equity Curve')
    
    ax2 = plt.subplot(2, 1, 2)
    ax2.plot(equity_curve_snapshots, linewidth=2, color='orange')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.set_ylabel('Equity Curve Snapshots')
    ax2.set_xlabel('Time')

    plt.tight_layout()
    plt.subplots_adjust(top=0.93, hspace=0.2)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    plt.figtext(0.99, 0.01, f'Generated: {timestamp}', 
                ha='right', va='bottom', fontsize=8, style='italic')

    os.makedirs(save_path, exist_ok=True)
    
    

    # Speed optimization 9: Lower DPI for saving
    current_filename = f"{base_filename}={metric_value}.png"  # Reduced precision
    plt.savefig(os.path.join(save_path, current_filename), 
                dpi=60)  # Lower quality compression


    # NOTE: ONLY SAVE THE BEST IMAGE (WILL BE FASTER!)
    best_filename = f"{base_filename}_BEST.png"
    plt.savefig(os.path.join(save_path, best_filename), 
                dpi=60)

    plt.close()


def convert_leaf_values_to_string(data):
    """
    Convert leaf values to strings with numpy array handling.
    """
    import numpy as np
    
    if isinstance(data, dict):
        return {k: convert_leaf_values_to_string(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_leaf_values_to_string(v) for v in data]
    elif isinstance(data, np.ndarray):
        return convert_leaf_values_to_string(data.tolist())
    elif isinstance(data, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, 
                         np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
        return str(int(data))
    elif isinstance(data, (np.float_, np.float16, np.float32, np.float64)):
        return str(float(data))
    elif isinstance(data, (int, float, bool)):
        return str(data)
    else:
        return data

def optimize_strategy_params(
    strategy_name, 
    symbols, 
    num_candles, 
    interval, 
    param_space, 
    data_interval_dict, 
    should_plot=False, 
    max_workers_strategies=100, 
    max_workers_symbols=100, 
    sorting_metric_key=None,
    reward_equity_func=None,
    top_n=100000, 
    max_evals=1000, 
    revert_loss_to_reward=True, 
    check_constraints=None,
    should_normalize_data=False
):
    """
    Perform Hyperopt optimization for strategy parameters with support for custom equity curve reward functions.
    Now includes equity curve plotting functionality and proper numpy array handling.
    """
    top_results = []
    tested_params = set()
    param_space = remove_duplicate_params(param_space)
    on_iteration = 0


    # Track best metric value
    best_metric_value = float('-inf') if revert_loss_to_reward else float('inf')
    
    
    # Create plot directory
    plot_dir = f'HYPEROPT/{interval}/equity_curves'
    os.makedirs(plot_dir, exist_ok=True)

    def objective(params):
        nonlocal top_results, tested_params, on_iteration, best_metric_value
        on_iteration += 1

        # Process parameters
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, Apply):
                processed_params[key] = value.eval()
            elif isinstance(value, (int, float, bool, str)):
                processed_params[key] = value
            elif isinstance(value, list):
                processed_params[key] = [tuple(item) if isinstance(item, list) else item for item in value]
            else:
                processed_params[key] = value[0] if isinstance(value, list) else value

        # Convert specific parameters to integers
        for key in processed_params.keys():
            if any(substring in key for substring in ['_period', '_index', '_length']):
                processed_params[key] = int(processed_params[key])

        # Check constraints
        if check_constraints:
            constraint_result = check_constraints(processed_params)
            if constraint_result:
                return constraint_result

        # Handle duplicate params
        params_hash = params_to_hashable(processed_params)
        if params_hash in tested_params:
            return {'loss': float('inf'), 'status': STATUS_OK, 'params': processed_params}
        tested_params.add(params_hash)

        # Run backtesting
        strategy_params = {strategy_name: processed_params}
        all_results_dict, symbol_interval_result = run_backtesting(
            symbols,
            num_candles,
            interval,
            should_plot,
            [strategy_name],
            strategy_params,
            data_interval_dict=data_interval_dict,
            parallelize_strategies=True,
            max_workers_strategies=max_workers_strategies,
            max_workers_symbols=max_workers_symbols,
            should_normalize_data=should_normalize_data # NOTE: NORMALIZE IF NEEDED
        )
        
        # Get aggregated performance
        aggregated_performance = aggregate_strategy_performance(all_results_dict)
        overall_results = aggregated_performance[strategy_name]['overall']
        
        # Get equity curve and calculate metric
        normalized_equity_curve = overall_results['normalized_equity_curve'] # use the returns version (u can also use raw with intial capital)
        normalized_equity_curve_snapshots = overall_results['normalized_equity_curve_snapshots'] # use the returns version (u can also use raw with intial capital)
        
        if reward_equity_func is not None and normalized_equity_curve is not None:
            # NOTE: CUSTOM REWARD FUNCTION
            # Use SNAPSHOTS or CONTINOUS!?!?! Your Choice? RN is Continuous
            sorting_metric = reward_equity_func(normalized_equity_curve, overall_results)
            metric_name = 'reward_equity_func'
        else:
            sorting_metric = overall_results[sorting_metric_key]
            metric_name = sorting_metric_key

        # Handle no trades case
        if overall_results["total_trades"] == 0:
            print(f"No trades at all! Using default negative value")
            sorting_metric = -1e12


        # NOTE: I am ALREADY plotting backtesting! This is JUST equity curves, backtesting is FULL plot!
        # # DRAW all BALANCE/TRADES in ONE equity curve!
        # plot_equity_curve(
        #     equity_curve=normalized_equity_curve,
        #     equity_curve_snapshots=normalized_equity_curve_snapshots,
        #     strategy_name=strategy_name,
        #     interval=interval,
        #     iteration=on_iteration,
        #     sorting_metric=metric_name,
        #     metric_value=sorting_metric,
        #     save_path=plot_dir
        # )


        # Create result dictionary
        new_result = {
            'params': processed_params,
            'performance': overall_results,
            metric_name: sorting_metric
        }

        # Update and save results
        if not any(params_to_hashable(result['params']) == params_hash for result in top_results):
            top_results.append(new_result)
            top_results.sort(key=lambda x: x[metric_name], reverse=revert_loss_to_reward)
            top_results = top_results[:top_n]

            try:
                # Save JSON results with numpy handling
                serializable_top_results = convert_leaf_values_to_string(top_results)
                with open(f'HYPEROPT/{interval}/{strategy_name}_hyperopt.json', 'w') as f:
                    json.dump(serializable_top_results, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to save JSON results: {e}")

        # Save detailed results to txt file
        with open(f'HYPEROPT/{interval}/{strategy_name}_BEST_PARAMS.txt', 'w') as f:
            f.write(f"""
---------------------------------------------------
Optimized Strategy Parameters
---------------------------------------------------

Strategy Name: {strategy_name}
Symbols: [\"{'\", \"'.join(symbols)}\"]
Interval: {interval}
Parameter Space: {param_space}
On Iteration: {on_iteration}
Metric Type: {'Custom Reward Function' if reward_equity_func is not None else sorting_metric_key}

---------------------------------------------------

Top {top_n} Results Sorted by '{metric_name}':

---------------------------------------------------

""")
            for i, result in enumerate(top_results, 1):
                metric_value = result[metric_name]
                f.write(f"# {i}. {metric_name} = {metric_value:.20f}\n")
                f.write(f"{result['params']}\n\n")

        # Calculate loss for hyperopt
        loss = sorting_metric * (-1 if revert_loss_to_reward else 1)
        return {
            'loss': loss, 
            'status': STATUS_OK, 
            'params': processed_params, 
            'performance': overall_results
        }

    # Run optimization
    trials = Trials()
    """
        max_queue_len: Controls the size of the trial queue in Hyperopt's optimization process.

        Key points:
        1. Larger values (e.g., 100, 200, 500) can improve performance on complex problems.
        2. Enhances exploration-exploitation balance in the search space.
        3. Helps overcome local optima and adapts better to complex, non-linear landscapes.
        4. Improves performance of algorithms like TPE by providing more data for modeling.
        5. Reduces sensitivity to noise in individual trial evaluations.
        6. Increases computational overhead and memory usage.

        In practice, larger values often lead to better solutions, especially in high-dimensional
        or complex optimization tasks. While the default is often small (e.g., 1 or 10), 
        using larger values like 100, 200, or even 500 can be beneficial for challenging problems.
        The optimal value depends on your specific optimization task and available computational resources.

        Note: Yes, you can use a large value. The trade-off is between potential performance 
        improvements and increased computational resources. Experiment with different values 
        to find the best balance for your specific use case.
        """

    best = fmin(
        algo=get_random_followed_by_tpe_algo(),
        fn=objective,
        space=param_space,
        max_evals=max_evals,
        trials=trials,

        max_queue_len=40#40#10 # TODO: try 100,200, 500, 50 # WAS 40 BEFORE high???
        
    )

    best_params = trials.best_trial['result']['params']
    best_performance = trials.best_trial['result']['performance']

    return best_params, best_performance, top_results