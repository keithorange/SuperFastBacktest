import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


def generate_price_series(start_price, volatility, trend, length):
    """Generate a price series with given characteristics."""
    returns = np.random.normal(trend, volatility, length)
    price_series = start_price * np.exp(np.cumsum(returns))
    return price_series


def scale_series(series, offset=1000):
    """Scale a series while maintaining its relative movements and adding an offset."""
    min_val = series.min()
    max_val = series.max()

    # Scale linearly based on original range
    scaled = (series - min_val) / (max_val - min_val)  # Scale to 0-1
    return scaled * (max_val - min_val) + offset  # Scale back and add offset


# Generate different price series
np.random.seed(42)  # For reproducibility
length = 252  # One year of trading days

assets = {
    "Penny Stock": generate_price_series(0.5, 0.03, 0.0002, length),
    "Mid-range Stock": generate_price_series(50, 0.015, 0.0001, length),
    "High-priced Stock": generate_price_series(500, 0.01, 0.00005, length),
    "Volatile Crypto": generate_price_series(100, 0.05, 0.0003, length)
}

# Scale the assets
scaled_assets = {name: scale_series(prices) for name, prices in assets.items()}

# Plotting
fig = plt.figure(figsize=(20, 15))
gs = GridSpec(2, 2, figure=fig)

for i, (name, prices) in enumerate(assets.items()):
    ax = fig.add_subplot(gs[i])
    # ax.plot(prices, label='Original', color='blue')
    ax.plot(scaled_assets[name], label='Scaled', color='red')
    ax.set_title(f"{name}")
    ax.set_ylabel("Price")

    # # Set y-axis limits for better visibility
    # ax.set_ylim(bottom=0)  # Ensure y-axis starts from 0 for better visibility

    ax.legend()

plt.tight_layout()
plt.show()

# Print some statistics
for name, prices in assets.items():
    original_returns = (prices[-1] / prices[0] - 1) * 100
    scaled_returns = (scaled_assets[name][-1] /
                      scaled_assets[name][0] - 1) * 100
    print(f"{name}:")
    print(f"  Original price range: {prices.min():.2f} to {prices.max():.2f}")
    print(f"  Original return: {original_returns:.2f}%")
    print(f"  Scaled price range: {scaled_assets[name].min():.2f} to {
          scaled_assets[name].max():.2f}")
    print(f"  Scaled return: {scaled_returns:.2f}%")
    print()
