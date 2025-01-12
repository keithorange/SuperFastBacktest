import numpy as np
import matplotlib.pyplot as plt


def emphasized_lower_mean(x, factor=2):
    x = np.array(x)
    if len(x) == 0:
        return np.nan
    adjusted_x = x - np.min(x)
    weights = 1 / (adjusted_x + 1) ** factor
    weighted_mean = np.sum(x * weights) / np.sum(weights)
    return weighted_mean


# Factors to test
factors = [1, 1.25, 1.5, 1.75, 2]

# Different distributions to test
distributions = [
    ("Normal", np.random.normal(0, 50, 10000)),
    ("Right-skewed", np.random.lognormal(0, 1, 10000) * 20 - 50),
    ("Left-skewed", -np.random.lognormal(0, 1, 10000) * 20 + 50),
    ("Bimodal", np.concatenate(
        [np.random.normal(-50, 20, 5000), np.random.normal(50, 20, 5000)])),
    ("Uniform", np.random.uniform(-100, 100, 10000))
]

# Create subplots
fig, axs = plt.subplots(len(distributions), len(factors), figsize=(
    20, 5*len(distributions)), sharex='col', sharey='row')
fig.suptitle(
    'Effect of Different Factors on Emphasized Lower Mean for Various Distributions', fontsize=16)

for i, (dist_name, data) in enumerate(distributions):
    arithmetic_mean = np.mean(data)

    for j, factor in enumerate(factors):
        result = emphasized_lower_mean(data, factor)

        # Plot histogram
        axs[i, j].hist(data, bins=50, edgecolor='black', alpha=0.7)
        axs[i, j].axvline(result, color='r', linestyle='dashed',
                          linewidth=2, label='Emphasized Lower Mean')
        axs[i, j].axvline(arithmetic_mean, color='g',
                          linestyle='dashed', linewidth=2, label='Arithmetic Mean')

        if i == 0:
            axs[i, j].set_title(f'Factor: {factor}')
        if j == 0:
            axs[i, j].set_ylabel(f'{dist_name}\nFrequency')

        # Add text annotations for both means
        axs[i, j].text(0.95, 0.95, f'ELM: {result:.2f}',
                       verticalalignment='top', horizontalalignment='right',
                       transform=axs[i, j].transAxes, color='red', fontsize=8)
        axs[i, j].text(0.95, 0.85, f'AM: {arithmetic_mean:.2f}',
                       verticalalignment='top', horizontalalignment='right',
                       transform=axs[i, j].transAxes, color='green', fontsize=8)

# Add legend to the last subplot
handles, labels = axs[-1, -1].get_legend_handles_labels()
fig.legend(handles, labels, loc='lower center', ncol=2)

# Adjust layout and display
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()
