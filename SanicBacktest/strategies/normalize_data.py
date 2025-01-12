import numpy as np
import pandas as pd
from typing import Dict, Tuple
import hashlib
from datetime import datetime, timedelta

class FastCache:
    """Ultra-fast memory cache with minimal overhead"""
    
    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
        self.max_size = max_size
    
    def _make_key(self, df: pd.DataFrame, **kwargs) -> str:
        """Fast key generation focusing only on essential data characteristics"""
        # Get basic data fingerprint

        key_parts = [
            str(df.shape),
            str(df.index[0]),
            str(df.index[-1]),
            str(sum(df.iloc[0].values)),  # First row sum as quick fingerprint
            str(sum(df.iloc[-1].values))  # Last row sum as quick fingerprint
        ]
        
        # Add kwargs to key
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
            
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()
    
    def get(self, df: pd.DataFrame, cache_hours: float = 1.0, **kwargs) -> pd.DataFrame:
        """Get from cache if exists and valid"""
        key = self._make_key(df, **kwargs)
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(hours=cache_hours):
                return data
            
            # Clear expired entry
            del self.cache[key]
        return None
    
    def set(self, df: pd.DataFrame, normalized_df: pd.DataFrame, **kwargs) -> None:
        """Set cache entry with minimal overhead"""
        key = self._make_key(df, **kwargs)
        
        # Simple LRU - if full, remove random 10% of entries
        if len(self.cache) >= self.max_size:
            keys = list(self.cache.keys())[:self.max_size // 10]
            for k in keys:
                del self.cache[k]
                
        self.cache[key] = (normalized_df, datetime.now())

# Global cache instance
_FAST_CACHE = FastCache()

def normalize_price_data_for_trading(data: pd.DataFrame, 
                                   center: float = 100, 
                                   range_size: float = 50, 
                                   window_size: int =1000,#1000,#2000, worked #500 worked
                                   global_normalization: bool = False,
                                   get_from_cache_1h: bool = True) -> pd.DataFrame:
    
    """
    Fast normalized price data with simple caching
    
    # Start of function
    This function normalizes price data for trading purposes.
    It can use caching to speed up repeated calculations.
    """


    if not get_from_cache_1h:
        return _normalize_price_data_implementation(
            data.copy(), center, range_size, window_size, global_normalization
        )
    
    # Try cache
    result = _FAST_CACHE.get(
        data,
        cache_hours=24 * 1000, # DISABLED!,
        center=center,
        range_size=range_size,
        window_size=window_size,
        global_normalization=global_normalization
    )
    
    if result is not None:
        return result
    
    # Compute if not cached
    result = _normalize_price_data_implementation(
        data.copy(), center, range_size, window_size, global_normalization
    )
    
    # Cache result
    _FAST_CACHE.set(
        data,
        result,
        center=center,
        range_size=range_size,
        window_size=window_size,
        global_normalization=global_normalization
    )
    
    # End of normalization data processing

    
    return result
    # End of function


import numpy as np
import pandas as pd

def _normalize_price_data_implementation(data: pd.DataFrame,
                                       center: float,
                                       range_size: float,
                                       window_size: int,
                                       global_normalization: bool) -> pd.DataFrame:
    """Vectorized price data normalization implementation with strict shape preservation"""
    
    price_cols = list(set(data.columns) & {'Open', 'High', 'Low', 'Close'})
    if not price_cols:
        raise ValueError(f"No OHLC columns found in data! Columns are {list(data.columns)}")

    result = data.copy()
    original_index = data.index
    
    offset = center - range_size / 2

    if global_normalization:
        global_min = data['Close'].min()
        global_max = data['Close'].max()
        
        if global_max == global_min:
            return data.copy()

        scale_factor = range_size / (global_max - global_min)

        for col in price_cols:
            result[col] = (data[col] - global_min) * scale_factor + offset
    else:
        # Vectorized rolling min/max calculation using pandas, based on Close prices
        window_mins = data['Close'].rolling(window=window_size, min_periods=1).min()
        window_maxs = data['Close'].rolling(window=window_size, min_periods=1).max()
        
        # Calculate scale factors safely using vectorized operations
        diff = window_maxs - window_mins
        scale_factors = np.where(diff != 0, range_size / diff, 0)
        
        for col in price_cols:
            result[col] = (data[col] - window_mins) * scale_factors + offset
        
        # Handle cases where max equals min
        equal_cases = diff == 0
        for col in price_cols:
            result.loc[equal_cases, col] = center

    if 'Volume' in data.columns:
        if global_normalization:
            vol_min = data['Volume'].min()
            vol_max = data['Volume'].max()
        else:
            # Vectorized volume normalization using pandas
            vol_mins = data['Volume'].rolling(window=window_size, min_periods=1).min()
            vol_maxs = data['Volume'].rolling(window=window_size, min_periods=1).max()
            vol_min = vol_mins
            vol_max = vol_maxs

        vol_range = np.maximum(vol_max - vol_min, 1e-8)
        result['Volume'] = (data['Volume'] - vol_min) / vol_range * range_size + offset

    assert result.shape == data.shape, f"Shape changed during normalization: {data.shape} -> {result.shape}"
    assert result.index.equals(original_index), "Index changed during normalization"
    
    return result
