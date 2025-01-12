import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pandas_ta as ta


def fetch_data(tickers, start_date, end_date):
    """
    Fetch historical data for the specified tickers from Yahoo Finance.
    """
    data = {}
    for ticker in tickers:
        df = yf.download(ticker, start=start_date, end=end_date, interval='5m')
        # Filter out weekends (non-trading days)
        df = df[df.index.dayofweek < 5]  # Keep only Monday to Friday
        data[ticker] = df
    return data


def calculate_atr(data, atr_period=14):
    """
    Calculate the Average True Range (ATR) for each asset.
    """
    return ta.atr(data['High'], data['Low'], data['Close'], length=atr_period)


def plot_atr_grid(asset_data, atr_multiplier_list=[1.0, 1.5, 2.0], fixed_stop_pct=0.05):
    """
    Plot the closing price and ATR-based stop-loss lines in a grid format.

    Parameters:
    - asset_data (dict): Dictionary of DataFrames for each ticker.
    - atr_multiplier_list (list): List of multipliers for ATR to show different stop-loss lines.
    - fixed_stop_pct (float): Fixed percentage for static trailing stop loss.
    """

    num_assets = len(asset_data)
    fig, axes = plt.subplots(nrows=num_assets, ncols=1,
                             figsize=(14, 5 * num_assets))

    for ax, (ticker, data) in zip(axes, asset_data.items()):
        # Calculate ATR
        atr_values = calculate_atr(data)

        # Plot closing price
        ax.plot(data['Close'], label='Close Price', color='blue', alpha=0.5)

        # Plot static trailing stop loss based on fixed percentage
        static_stop_loss = data['Close'] * (1 - fixed_stop_pct)
        ax.axhline(y=static_stop_loss.iloc[-1], color='orange',
                   linestyle='--', label=f'Static TSL ({fixed_stop_pct*100:.0f}%)')

        # Plot stop-loss lines based on different ATR multipliers
        for multiplier in atr_multiplier_list:
            stop_loss = data['Close'] - (atr_values * multiplier)
            ax.plot(
                stop_loss, label=f'Stop-Loss Line (ATR x {multiplier})', linestyle='--')

        # Add title and labels
        ax.set_title(f'{ticker} Price and Stop-Loss Lines')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend()

    plt.tight_layout()
    plt.show()


# Main execution
if __name__ == "__main__":

    # Define tickers and date range
    # Example: Penny stocks and larger assets
    tickers = ['VAST.L', 'SNDA.L', 'TPT.L', 'AAPL', 'BTC-USD']
    start_date = '2024-10-01'
    end_date = '2024-10-05'  # Shorter time frame

    # Fetch historical data
    asset_data = fetch_data(tickers, start_date, end_date)

    # Plotting the ATR with the closing price and multiple stop-loss lines
    plot_atr_grid(asset_data)
