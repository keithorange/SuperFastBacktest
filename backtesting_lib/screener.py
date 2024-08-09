import os
import sys
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from importlib import import_module
import mplfinance as mpf

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting_lib.data_handler import download_data
from backtesting_lib.asset_names import popular_assets, cryptocurrencies, us_market_stocks

# Dynamically import all strategy modules from the strategies folder
strategy_path = os.path.join(os.path.dirname(__file__), 'strategies')
strategy_files = [f for f in os.listdir(strategy_path) if f.endswith('.py') and not f.startswith('__')]

strategy_modules = {}
for strategy_file in strategy_files:
    module_name = f"strategies.{strategy_file[:-3]}"
    strategy_modules[strategy_file[:-3]] = import_module(module_name)


class StockScreener:
    def __init__(self, symbols, num_candles, interval='5m', verbose=True):
        self.symbols = symbols
        self.num_candles = num_candles
        self.interval = interval
        self.verbose = verbose
        self.data = self.download_data()

    def download_data(self):
        data = {}
        for symbol in self.symbols:
            if self.verbose:
                print(f"Downloading data for {symbol}...\n")
            stock_data = download_data(symbol, num_candles=self.num_candles, interval=self.interval, redownload=True)
            if stock_data is not None and not stock_data.empty:
                data[symbol] = stock_data
        return data

    def dollar_volume_filter(self, min_dollar_volume):
        filtered_symbols = []
        for symbol, stock_data in self.data.items():
            stock_data['DollarVolume'] = stock_data['Volume'] * stock_data['Close']
            avg_dollar_volume = stock_data['DollarVolume'].mean()
            if avg_dollar_volume >= min_dollar_volume:
                filtered_symbols.append(symbol)
        return filtered_symbols

    def age_filter(self, min_days_listed):
        filtered_symbols = []
        for symbol, stock_data in self.data.items():
            if len(stock_data) >= min_days_listed:
                filtered_symbols.append(symbol)
        return filtered_symbols

    def volatility_filter(self, lookback_days, min_volatility, sort_direction='desc'):
        filtered_symbols = []
        for symbol, stock_data in self.data.items():
            stock_data['Return'] = stock_data['Close'].pct_change()
            rolling_volatility = stock_data['Return'].rolling(lookback_days).std().dropna()
            avg_volatility = rolling_volatility.mean()

            if avg_volatility >= min_volatility:
                filtered_symbols.append(symbol)
        if sort_direction == 'desc':
            filtered_symbols.sort(key=lambda x: self.data[x]['Return'].rolling(lookback_days).std().mean(), reverse=True)
        else:
            filtered_symbols.sort(key=lambda x: self.data[x]['Return'].rolling(lookback_days).std().mean())
        return filtered_symbols

    def strategy_filter(self, strategy_name, n_periods=1, signal_type='entry'):
        filtered_symbols = []
        strategy_func_or_class = self.load_strategy_func_or_class(strategy_name)
        for symbol, stock_data in self.data.items():
            if callable(strategy_func_or_class):
                entries, exits = strategy_func_or_class(stock_data)
            else:
                strategy_instance = strategy_func_or_class(stock_data)
                entries, exits = strategy_instance.run()  # Assuming strategies have a 'run' method returning entries and exits
            signals = entries if signal_type == 'entry' else exits
            if signals.tail(n_periods).any():
                filtered_symbols.append(symbol)
        return filtered_symbols

    def load_strategy_func_or_class(self, strategy_name):
        """Load the strategy function or class from the strategy module."""
        module = strategy_modules[strategy_name]
        strategy_func_or_class_name = ''.join([part.capitalize() for part in strategy_name.split('_')])
        # Check if it's a function
        if hasattr(module, strategy_name):
            return getattr(module, strategy_name)
        # Otherwise, it's a class
        return getattr(module, strategy_func_or_class_name)

    def run_filters(self, filters):
        filtered_symbols = set(self.symbols)
        count = 0
        for filter_func, filter_args in filters:
            input_symbol_count = len(filtered_symbols)
            filtered_symbols &= set(filter_func(**filter_args))
            if self.verbose:
                print(f"({count+1}) Filter {filter_func.__name__} with args {filter_args}:\n    input symbols={input_symbol_count}, output symbols={len(filtered_symbols)}\n")
            count += 1
        return filtered_symbols

    def plot_symbols(self, symbols, use_heikin_ashi=True,num_candles=100000000000):
        plotter = StockPlotter()
        for symbol in symbols:
            if symbol in self.data:
                stock_data = self.data[symbol][-num_candles:]
                plotter.plot_candlestick(stock_data, symbol, use_heikin_ashi)

class StockPlotter:
    def __init__(self):
        pass

    def plot_candlestick(self, data, title, use_heikin_ashi=True):
        data = data.copy()
        data.index.name = 'Date'
        data.reset_index(inplace=True)
        data['Date'] = pd.to_datetime(data['Date'])
        data.set_index('Date', inplace=True)
        
        if use_heikin_ashi:
            ha_data = self.calculate_heikin_ashi(data)
            mpf.plot(
                ha_data,
                type='candle',
                style='charles',
                title=title,
                ylabel='Price',
                volume=True,
                show_nontrading=True
            )
        else:
            mpf.plot(
                data,
                type='candle',
                style='charles',
                title=title,
                ylabel='Price',
                volume=True,
                show_nontrading=True
            )

    def calculate_heikin_ashi(self, data):
        ha_data = data.copy()
        ha_data['Close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4

        ha_data['Open'] = (data['Open'].shift(1) + data['Close'].shift(1)) / 2
        ha_data['High'] = data[['High', 'Open', 'Close']].max(axis=1)
        ha_data['Low'] = data[['Low', 'Open', 'Close']].min(axis=1)

        ha_data.dropna(inplace=True)
        return ha_data

if __name__ == "__main__":
    # Example usage
    symbols = cryptocurrencies
    num_candles = 300
    interval = '5m'
    verbose = True

    screener = StockScreener(symbols, num_candles, interval, verbose)
    hold_n = 1
    filters = [
        # general
        (screener.dollar_volume_filter, {'min_dollar_volume': 10 * 1000}),
        (screener.age_filter, {'min_days_listed': 30}),
        (screener.volatility_filter, {'lookback_days': 10, 'min_volatility': 0.001, 'sort_direction': 'desc'}),
        
        # specific strategies filter for entry signal now
        
        #(screener.strategy_filter, {'strategy_name': 'heikin_ashi_color_change_strategy', 'n_periods': hold_n, 'signal_type': 'entry'}),
        #(screener.strategy_filter, {'strategy_name': 'stb_gianno_nano_strategy', 'n_periods': hold_n, 'signal_type': 'entry'}),
        (screener.strategy_filter, {'strategy_name': 'ut_bot_strategy', 'n_periods': 2, 'signal_type': 'entry'})
    ]
    screened_symbols = screener.run_filters(filters)

    print("Filtered Symbols:", screened_symbols)
    screener.plot_symbols(screened_symbols, num_candles=100)
