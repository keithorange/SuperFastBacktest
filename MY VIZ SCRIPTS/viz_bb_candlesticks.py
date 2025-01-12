import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

# Fetch data
ticker = "NVDA"
data = yf.download(ticker, start="2023-01-01", end="2023-12-31")


def plot_candlestick(ax, df, open_col, high_col, low_col, close_col, width=0.8, colorup='g', colordown='r'):
    for i, (idx, row) in enumerate(df.iterrows()):
        color = colorup if row[close_col] >= row[open_col] else colordown
        rect = Rectangle((i - width/2, min(row[open_col], row[close_col])),
                         width, abs(row[close_col] - row[open_col]),
                         facecolor=color, edgecolor=color)
        ax.add_patch(rect)
        ax.plot([i, i], [row[low_col], row[high_col]],
                color='black', linewidth=1)


def bollinger_bands(df, window=20, num_std=2):
    bb = df.copy()
    bb['SMA'] = df['Close'].rolling(window=window).mean()
    bb['STD'] = df['Close'].rolling(window=window).std()
    bb['Upper'] = bb['SMA'] + (num_std * bb['STD'])
    bb['Lower'] = bb['SMA'] - (num_std * bb['STD'])
    bb['BB_Open'] = (df['Open'] - bb['Lower']) / (bb['Upper'] - bb['Lower'])
    bb['BB_High'] = (df['High'] - bb['Lower']) / (bb['Upper'] - bb['Lower'])
    bb['BB_Low'] = (df['Low'] - bb['Lower']) / (bb['Upper'] - bb['Lower'])
    bb['BB_Close'] = (df['Close'] - bb['Lower']) / (bb['Upper'] - bb['Lower'])
    return bb


# Apply candlestick calculations
regular = data[['Open', 'High', 'Low', 'Close']]
bollinger_data = bollinger_bands(data)

# Plotting
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 20))
fig.suptitle(
    f"{ticker} Regular Candlesticks with Bollinger Bands vs Bollinger Band Relative Candlesticks", fontsize=16)

# Plot regular candlesticks with Bollinger Bands
ax1.set_title("Regular Candlesticks with Bollinger Bands")
plot_candlestick(ax1, regular, 'Open', 'High', 'Low', 'Close')
ax1.plot(range(len(bollinger_data)),
         bollinger_data['Upper'], 'r--', alpha=0.5, label='Upper BB')
ax1.plot(range(len(bollinger_data)),
         bollinger_data['SMA'], 'g--', alpha=0.5, label='SMA')
ax1.plot(range(len(bollinger_data)),
         bollinger_data['Lower'], 'r--', alpha=0.5, label='Lower BB')
ax1.set_xlim(0, len(regular))
ax1.set_ylabel('Price')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend()

# Plot Bollinger Band Relative candlesticks
ax2.set_title("Bollinger Band Relative Candlesticks")
plot_candlestick(ax2, bollinger_data, 'BB_Open',
                 'BB_High', 'BB_Low', 'BB_Close')
ax2.set_xlim(0, len(bollinger_data))
ax2.set_ylabel('Relative Price')
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='Lower Band')
ax2.axhline(y=0.5, color='g', linestyle='--',
            alpha=0.5, label='Middle Band (SMA)')
ax2.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='Upper Band')
ax2.legend()

# Set x-axis labels
for ax in (ax1, ax2):
    ax.set_xlabel('Date')
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: data.index[int(
        x)].strftime('%Y-%m-%d') if x >= 0 and x < len(data.index) else ''))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

plt.tight_layout()
plt.show()
