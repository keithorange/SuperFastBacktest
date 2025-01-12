# SanicBacktest

![sanic](sanic.jpg)

PyStratForge 🐍📈🎯
PyStratForge 🐍📈🎯PyStratForge 🐍📈🎯PyStratForge 🐍📈🎯PyStratForge 🐍📈🎯PyStratForge 🐍📈🎯PyStratForge 🐍📈🎯

PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"PepeProfitForge 🐸💹🛠️
"Crafting Winning Trade Strategies at Sonic Speed"

SanicBacktest is a high-performance, flexible backtesting and strategy optimization package for quantitative trading strategies. It leverages the power of vectorbt for fast computations and supports parallel processing for efficient backtesting across multiple symbols and timeframes.

## Features

- Fast backtesting using vectorbt
- Strategy parameter optimization through grid search
- Support for multiple symbols and timeframes
- Parallel processing for improved performance
- Flexible strategy implementation
- Comprehensive performance metrics
- Easy-to-use results analysis and visualization

## Installation

```bash
git clone https://github.com/yourusername/SanicBacktest.git
cd SanicBacktest
pip install -r requirements.txt
```

## Quick Start

Here's a simple example of how to use SanicBacktest:

```python
from backtester import run_backtesting, aggregate_strategy_performance, sort_strategies_by_performance
from data_handler import download_data

# Define symbols and parameters
symbols = ['AAPL', 'GOOGL', 'MSFT']
num_candles = 1000
interval = '1h'

# Define strategy parameters
strategy_params = {
    'bollinger_bands_strategy': {
        'length': 55,
        'mult': 2.0,
        'show': 'Both'
    }
}

# Run backtesting
results, symbol_results = run_backtesting(
    symbols,
    num_candles,
    interval,
    plot=False,
    strategies=['bollinger_bands_strategy'],
    strategy_params=strategy_params
)

# Analyze results
aggregated_performance = aggregate_strategy_performance(results)
sorted_strategies = sort_strategies_by_performance(aggregated_performance)

# Print results
from result_printer import ResultPrinter
printer = ResultPrinter(aggregated_performance)
printer.print_concise_summary(aggregated_performance)
```

## Writing a Custom Strategy

To create a custom strategy, define a function that takes a DataFrame of OHLC data and returns entry and exit signals. Here's an example of a Bollinger Bands strategy:

```python
import pandas as pd
import pandas_ta as ta

def bollinger_bands_strategy(data, length=55, mult=1.0, show='Both'):
    """
    Bollinger Bands Breakout Strategy.
    """
    # Calculate Bollinger Bands
    bb = ta.bbands(data['Close'], length=length, std=mult)
    data['Upper'] = bb['BBU_55_1.0']
    data['Lower'] = bb['BBL_55_1.0']

    # Generate long and short signals
    data['Long'] = data['Close'] > data['Upper']
    data['Short'] = data['Close'] < data['Lower']

    # Generate entry and exit signals
    data['LongSignal'] = data['Long'] & ~data['Long'].shift(1).fillna(False)
    data['ShortSignal'] = data['Short'] & ~data['Short'].shift(1).fillna(False)

    # Filter based on 'show' parameter
    if show == 'Longs Only':
        data['ShortSignal'] = False
    elif show == 'Shorts Only':
        data['LongSignal'] = False

    entries = data['LongSignal']
    exits = data['ShortSignal']

    return entries, exits
```

## Strategy Optimization

You can optimize strategy parameters using the `optimize_strategy_params` function:

```python
from optimizer import optimize_strategy_params

param_grid = {
    'length': [20, 55, 100],
    'mult': [1.0, 2.0, 3.0],
    'show': ['Longs Only', 'Shorts Only', 'Both']
}

optimized_results = optimize_strategy_params(
    'bollinger_bands_strategy',
    symbols,
    num_candles,
    interval,
    param_grid,
    data_dict=None,  # Pre-load data if desired
    should_plot=False
)

# Print optimized results
for params, performance in optimized_results[:5]:
    print(f"Parameters: {params}")
    print(f"Performance: {performance['overall_mean']:.2f}")
    print("---")
```

## Performance

SanicBacktest is designed for high performance:

- Uses vectorbt for fast vectorized operations
- Supports parallel processing for multiple symbols and strategies
- Efficiently handles large datasets and parameter grids

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---
