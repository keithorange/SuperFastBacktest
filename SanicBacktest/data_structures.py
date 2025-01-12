
from scipy import integrate
from typing import Callable, Optional, List, Dict, Any, Sequence, Union
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

import pandas as pd


 
class Trade:
    def __init__(self, entry_price: float, entry_date: pd.Timestamp,
                 entry_fee: float, is_long: bool,
                 collateral: float, leverage: float):
        # Calculate the total position value and size at entry
        position_value=collateral * leverage
        
        self._data = {
            'collateral': collateral,
            'leverage': leverage,
            'position_value':position_value,
            'position_size': position_value / entry_price,
            'entry_price': entry_price,
            'entry_date': entry_date,
            'is_long': is_long,
            'exit_price': None,
            'exit_date': None,
            'exit_index': 0,
            'current_value': position_value,  # Initialize with full leveraged value
            'unrealized_profit': 0,
            'realized_profit': 0,
            'entry_fee': entry_fee,
            'exit_fee': 0,
            'total_fee': entry_fee,
            'duration': 0,
        }

    

    def calculate_effective_liquidation_price(self) -> float:
        """Calculate price that would result in exact maximum loss"""
        max_loss_pct = 1 - 1/self._data['leverage']
        if self._data['is_long']:
            return self._data['entry_price'] * (1 - max_loss_pct)
        else:
            return self._data['entry_price'] * (1 + max_loss_pct)   


    def get_position_size(self) -> float:
        """Returns the position size in base currency units (e.g., BTC)"""
        return self._data['position_size']  # Use pre-calculated position size

    def calculate_pnl(self, current_price: float) -> float:
        """Calculate PnL for the position at current price"""
        if self._data['is_long']:
            price_change = current_price - self._data['entry_price']
        else:
            price_change = self._data['entry_price'] - current_price
            
        return self._data['position_size'] * price_change

    def close(self, exit_price: float, exit_date: pd.Timestamp, fee_rate: float, exit_index: int) -> None:
        """Close the position and calculate final PnL with proper fee handling"""
        # Calculate gross profit/loss
        gross_profit = self.calculate_pnl(exit_price)
        
        # Calculate exit fee based on remaining position value
        exit_position_value = self._data['position_size'] * exit_price
        exit_fee = min(
            exit_position_value * fee_rate,
            max(0, gross_profit - self._data['entry_fee'])  # Can't take more fees than remaining value
        )
        
        duration = (exit_date - self._data['entry_date']).total_seconds() / 60

        self._data.update({
            'exit_price': exit_price,
            'exit_date': exit_date,
            'exit_index': exit_index,
            'exit_fee': exit_fee,
            'total_fee': self._data['entry_fee'] + exit_fee,
            'realized_profit': gross_profit - self._data['entry_fee'] - exit_fee,
            'duration': duration,
        })


    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

class Portfolio:
    def __init__(self, initial_cash: float, allow_unlimited_trading: bool = True):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.equity = initial_cash
        self.long_open_trades: List[Trade] = []
        self.short_open_trades: List[Trade] = []
        self.long_closed_trades: List[Trade] = []
        self.short_closed_trades: List[Trade] = []
        self.collateral_in_use = 0
        self.completed_trade_value = 0.0
        self.num_exit_signals = 0
        self.allow_unlimited_trading = allow_unlimited_trading
        self.liquidation_callback = None  # Will be set by backtest

        

    def set_liquidation_callback(self, callback):
        """Allow backtest to register a callback for liquidation events"""
        self.liquidation_callback = callback



        
    def force_liquidate_trade(self, trade: Trade, current_price: float, 
                        current_date: pd.Timestamp, fee_rate: float, 
                        exit_index: int) -> None:
        """Force liquidate a trade with exact collateral loss"""
        is_long = trade["is_long"]
        
        # Key fix: Loss should exactly equal collateral!
        liquidation_value = 0  # At liquidation, we lose exactly collateral
        
        # Use trade's calculated liquidation price
        effective_price = trade.calculate_effective_liquidation_price()
        
        # Close at exact liquidation price
        trade.close(effective_price, current_date, fee_rate, exit_index)
        
        # Update portfolio state - CRITICAL FIX: we lose exactly collateral
        self.cash += liquidation_value  # Will be 0 as we lost full collateral
        self.collateral_in_use -= trade["collateral"]
        
        # Move trade to closed list
        if is_long:
            self.long_closed_trades.append(trade)
            self.long_open_trades.remove(trade)
        else:
            self.short_closed_trades.append(trade)
            self.short_open_trades.remove(trade)

        if self.liquidation_callback:
            self.liquidation_callback(exit_index, is_long)

    def update_values(self, current_price: float, fee_rate: float) -> None:
        """Update portfolio values and check for liquidations with exact precision"""
        self.equity = self.cash + self.collateral_in_use
        
        all_trades = self.long_open_trades + self.short_open_trades
        if not all_trades:
            return

        # Vectorized calculations
        entry_prices = np.array([trade["entry_price"] for trade in all_trades])
        position_sizes = np.array([trade.get_position_size() for trade in all_trades])
        is_long = np.array([trade["is_long"] for trade in all_trades])
        
        # Use the effective liquidation prices
        liquidation_prices = np.array([trade.calculate_effective_liquidation_price() for trade in all_trades])


        # Calculate PnL and check liquidations
        price_diffs = np.where(is_long, current_price - entry_prices, entry_prices - current_price)
        unrealized_pnls = price_diffs * position_sizes
        position_values = position_sizes * current_price

        # Update equity and trade values
        self.equity += np.sum(unrealized_pnls)
        
        for i, trade in enumerate(all_trades):
            trade["current_value"] = position_values[i]
            trade["unrealized_profit"] = unrealized_pnls[i] - trade["entry_fee"]

        # Liquidation check with exact price matching
        # if current_date and exit_index:
        # Strict liquidation check - if we hit OR PASS the liquidation price
        liquidation_mask = np.where(is_long, 
                                current_price <= liquidation_prices,  # Long positions
                                current_price >= liquidation_prices)  # Short positions

        # Process liquidations immediately when detected
        trades_to_liquidate = [(trade, i) for i, (trade, should_liquidate) 
                            in enumerate(zip(all_trades, liquidation_mask)) 
                            if should_liquidate]


        # Sort by how far past liquidation to handle worst cases first
        trades_to_liquidate.sort(key=lambda x: abs(current_price - x[0].calculate_effective_liquidation_price()))

                    
        for trade, _ in trades_to_liquidate:
            self.force_liquidate_trade(trade, current_price, current_date, fee_rate, exit_index)

    def enter_trade(self, entry_price: float, entry_date: pd.Timestamp, 
                   collateral: float, leverage: float, fee_rate: float, is_long: bool) -> bool:
        """Enter a new trade with proper leverage handling"""
        position_value = collateral * leverage
        
        # Calculate fee based on full leveraged position value
        fee = position_value * fee_rate
        total_cost = collateral + fee  # Only need collateral + fees from cash
        
        if self.allow_unlimited_trading or (self.cash - self.collateral_in_use) >= total_cost:
            trade = Trade(
                entry_price=entry_price,
                entry_date=entry_date,
                entry_fee=fee,
                is_long=is_long,
                collateral=collateral,
                leverage=leverage
            )
            
            if is_long:
                self.long_open_trades.append(trade)
            else:
                self.short_open_trades.append(trade)
                
            self.collateral_in_use += collateral
            self.cash -= total_cost
            
            return True
            
        return False



    def exit_long_trades(self, exit_price: float, exit_date: pd.Timestamp, fee_rate: float, exit_index: int) -> None:
        had_trade = False
        
        for trade in list(self.long_open_trades):
            had_trade = True
            
            # Close trade - this calculates final PnL and fees
            trade.close(exit_price, exit_date, fee_rate, exit_index)
            
            # Return collateral plus profits/losses to cash
            self.cash += trade["collateral"] + trade["realized_profit"]
            self.collateral_in_use -= trade["collateral"]
            self.completed_trade_value += trade["realized_profit"]
            
            # Move trade to closed trades list
            self.long_closed_trades.append(trade)
            self.long_open_trades.remove(trade)
        
        if had_trade:
            self.num_exit_signals += 1

    def exit_short_trades(self, exit_price: float, exit_date: pd.Timestamp, fee_rate: float, exit_index: int) -> None:
        had_trade = False
        
        for trade in list(self.short_open_trades):
            had_trade = True
            
            
            # Close trade - this calculates final PnL and fees
            trade.close(exit_price, exit_date, fee_rate, exit_index)
            
            # Return collateral plus profits/losses to cash
            self.cash += trade["collateral"] + trade["realized_profit"]
            self.collateral_in_use -= trade["collateral"]
            self.completed_trade_value += trade["realized_profit"]
            
            # Move trade to closed trades list
            self.short_closed_trades.append(trade)
            self.short_open_trades.remove(trade)
        
        if had_trade:
            self.num_exit_signals += 1

    def exit_all_trades(self, exit_price: float, exit_date: pd.Timestamp, fee_rate: float, exit_index: int) -> None:
        if self.long_open_trades:
            self.exit_long_trades(exit_price, exit_date, fee_rate,  exit_index)
        if self.short_open_trades:
            self.exit_short_trades(exit_price, exit_date, fee_rate,  exit_index)



class TradingUtils:
    @staticmethod
    def get_interval_seconds(interval):
        if interval.lower() == '1d':
            return 86400  # 1 day in seconds
        elif interval.lower() == '1h':
            return 60 * 60
        elif interval.lower() == '15m':
            return 900  # 15 minutes in seconds
        elif interval.lower() == '5m':
            return 300  # 5 minutes in seconds
        elif interval.lower() == '1m':
            return 60  # 1 minute in seconds
        else:
            raise ValueError(f"Unsupported interval: {interval}")

    @classmethod
    def candles_in_a_day(cls, interval):
        # Trading hours from 9:30 AM to 4:30 PM = 7 hours
        trading_hours = 7 * 60 * 60  # Convert hours to seconds

        # Get the interval in seconds
        interval_seconds = cls.get_interval_seconds(interval)

        # Calculate the number of candles in a trading day
        num_candles = trading_hours // interval_seconds

        return num_candles


class EarningsCache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def _get_cache_path(self, symbol: str) -> Path:
        return self.cache_dir / f"earnings_{symbol}.json"

    def _generate_dates_range(self, start_date: datetime, end_date: datetime, interval: str) -> pd.DatetimeIndex:
        """Generate a range of dates based on the interval."""
        if interval.endswith('m'):
            freq = f'{interval[:-1]}T'  # Convert '5m' to '5T' for pandas
        elif interval.endswith('h'):
            freq = f'{interval[:-1]}H'
        else:
            freq = 'D'  # Default to daily

        # Generate business days only
        return pd.date_range(
            start=start_date,
            end=end_date,
            freq=freq,
            tz='UTC'
        )

    @lru_cache(maxsize=None)
    def get_earnings_dates(self, symbol: str) -> Optional[pd.DatetimeIndex]:
        """Get earnings dates with error handling and fallback options."""
        cache_path = self._get_cache_path(symbol)

        # Try to load from cache first
        try:
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                    if cache_data['cache_date'] == date.today().isoformat():
                        dates = pd.to_datetime(cache_data['earnings_dates'])
                        if len(dates) > 0:
                            return dates
        except Exception as e:
            self.logger.warning(f"Failed to load cache for {symbol}: {str(e)}")

        # Fetch from Yahoo Finance
        try:
            stock_info = yf.Ticker(symbol)
            earnings_dates = stock_info.earnings_dates

            if earnings_dates is None or len(earnings_dates) == 0:
                self.logger.warning(f"No earnings dates found for {symbol}")
                # Return empty DatetimeIndex instead of None
                return pd.DatetimeIndex([], tz='UTC')

            # Save to cache
            with open(cache_path, 'w') as f:
                json.dump({
                    'cache_date': date.today().isoformat(),
                    'earnings_dates': earnings_dates.index.strftime('%Y-%m-%d').tolist()
                }, f)

            return earnings_dates.index

        except Exception as e:
            self.logger.error(f"Failed to fetch earnings dates for {
                              symbol}: {str(e)}")
            # Return empty DatetimeIndex instead of None
            return pd.DatetimeIndex([], tz='UTC')

    def get_dates_from_date_str(self, date_str: str, interval: str = "1d") -> np.ndarray:
        """Convert date string to array of dates based on interval."""
        try:
            # Parse the input date
            end_date = datetime.strptime(date_str, '%Y-%m-%d')
            # Start date is 1 year before
            start_date = end_date - timedelta(days=365)

            # Generate dates range
            dates = self._generate_dates_range(start_date, end_date, interval)
            return dates.to_numpy()

        except Exception as e:
            self.logger.error(f"Failed to generate dates range: {str(e)}")
            # Return empty array instead of None
            return np.array([], dtype='datetime64[ns]')

    @lru_cache(maxsize=None)
    def prepare_earnings_exit_signals(
        self,
        symbol: str,
        interval: str,
        date_str: str
    ) -> np.ndarray:
        """Prepare earnings exit signals with proper error handling."""
        try:
            earnings_dates = self.get_earnings_dates(symbol)
            dates = self.get_dates_from_date_str(date_str, interval)

            if len(dates) == 0:
                return np.array([], dtype=bool)

            candles_in_a_day = TradingUtils.candles_in_a_day(interval)

            return self._calculate_earnings_exit_signals(
                dates,
                earnings_dates,
                n=candles_in_a_day,
                m=candles_in_a_day
            )

        except Exception as e:
            self.logger.error(
                f"Failed to prepare earnings exit signals: {str(e)}")
            # Return empty array instead of None
            return np.array([], dtype=bool)

    def _calculate_earnings_exit_signals(
        self,
        dates: np.ndarray,
        earnings_dates: pd.DatetimeIndex,
        n: int = 0,
        m: int = 0
    ) -> np.ndarray:
        """Calculate earnings exit signals with proper date handling."""
        # Handle empty inputs
        if len(dates) == 0 or len(earnings_dates) == 0:
            return np.zeros(len(dates), dtype=bool)

        exit_signals = np.zeros(len(dates), dtype=bool)

        # Convert dates to datetime64[ns] if they aren't already
        dates_ns = pd.to_datetime(dates).values
        earnings_ns = pd.to_datetime(earnings_dates).values

        # Convert to dates only (no time component) for comparison
        dates_days = dates_ns.astype('datetime64[D]')
        earnings_days = earnings_ns.astype('datetime64[D]')

        # Vectorized operation to find indices where dates match earnings dates
        for earnings_day in earnings_days:
            matches = dates_days == earnings_day
            match_indices = np.where(matches)[0]

            for idx in match_indices:
                # Mark the current day
                exit_signals[idx] = True
                # Mark n candles before
                if idx >= n:
                    exit_signals[idx-n:idx] = True
                # Mark m candles after
                if idx + 1 < len(dates) and m > 0:
                    end_idx = min(idx + m + 1, len(dates))
                    exit_signals[idx+1:end_idx] = True

        return exit_signals