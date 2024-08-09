import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import vectorbt as vbt
import time


CACHE_DIR = 'data_cache'

class DataCache:
    @staticmethod
    def save_to_cache(data, symbol, interval, num_candles):
        os.makedirs(CACHE_DIR, exist_ok=True)
        file_path = os.path.join(CACHE_DIR, f"{symbol}_{interval}_{num_candles}.pkl")
        data.to_pickle(file_path)

    @staticmethod
    def load_from_cache(symbol, interval, num_candles):
        file_path = os.path.join(CACHE_DIR, f"{symbol}_{interval}_{num_candles}.pkl")
        if os.path.exists(file_path):
            return pd.read_pickle(file_path)
        return None

class CachedData:
    @classmethod
    def download_symbol(cls, symbol, interval, num_candles, redownload=False):
        def load_from_cache(care_about_time=True):
            # get from cache 
            cached_data = DataCache.load_from_cache(symbol, interval, num_candles)
            if cached_data is not None:
                if not care_about_time:
                    return cached_data
                
                # Check if the cached data is recent enough
                last_timestamp = cached_data.index[-1]
                if last_timestamp.tzinfo is not None:
                    last_timestamp = last_timestamp.tz_convert(None)
                current_time = datetime.now()
                if current_time.tzinfo is not None:
                    current_time = current_time.replace(tzinfo=None)
                interval_seconds = cls.get_interval_seconds(interval)
                if (current_time - last_timestamp).total_seconds() < interval_seconds:
                    return cached_data
        
        def get_dates():
            end_date = datetime.now()
            # Determine the start date based on the interval
            if interval.lower() == '1d':
                start_date = end_date - timedelta(days=360*5)
            elif interval.lower() == '1h':
                start_date = end_date - timedelta(days=179)
            elif interval.lower() in ['5m', '15m']:
                start_date = end_date - timedelta(days=59)
            elif interval.lower() == '1m':
                start_date = end_date - timedelta(days=6)
            
            else:
                raise ValueError(f"Unsupported interval: {interval}")
            return start_date, end_date
                    
        if not redownload:
            cached_data =  load_from_cache()
            if cached_data is not None and not cached_data.empty:
                return cached_data
            
            

        start_date, end_date = get_dates()
        data = yf.download(symbol, interval=interval, start=start_date, end=end_date)
        # data = vbt.YFData.download(
        #     symbol,
        #     start=start_date,
        #     end=end_date,
        #     missing_index='drop',
        #     interval=interval
        #     )
        if data.empty:
            print(f"Downloaded data for {symbol} is empty. Skipping.")
            print(f"Interned Failed? Coul NOT download from YFinance! Using Cached DF!")
            return load_from_cache(care_about_time=False) # return wahtever one we have we offlien

        if 'Close' not in data.columns:
            raise KeyError(f"'Close' column not found in the data for {symbol}")
        data = data.iloc[-num_candles:]
        DataCache.save_to_cache(data, symbol, interval, num_candles)
        return data


    @staticmethod
    def get_interval_seconds(interval):
        if interval.lower() == '1d':
            return 86400  # 1 day in seconds
        elif interval.lower() == '1h':
            return 60*60
        elif interval.lower() == '15m':
            return 900  # 15 minutes in seconds
        elif interval.lower() == '5m':
            return 300  # 5 minutes in seconds
        elif interval.lower() == '1m':
            return 60  # 1 minute in seconds
        else:
            raise ValueError(f"Unsupported interval: {interval}")

    @classmethod
    def download(cls, symbols, interval, num_candles,redownload=False):
        data = {}
        for symbol in symbols:
            downloaded_data = cls.download_symbol(symbol, interval, num_candles, redownload)
            if not downloaded_data.empty:
                data[symbol] = downloaded_data
        return data

def download_data(symbol, num_candles, interval, redownload=False, max_retries=10):
    for attempt in range(max_retries):
        data = CachedData.download([symbol], interval=interval, num_candles=num_candles, redownload=redownload)
        if symbol in data:
            return data[symbol]
        time.sleep(1)  # Wait for 1 second before retrying
    raise KeyError(f"Data for {symbol} not found after {max_retries} attempts.")
