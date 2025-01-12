import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
import math

def calculate_ratios(returns, risk_free_rate=0.02):
    excess_returns = returns - risk_free_rate
    sharpe = np.mean(excess_returns) / np.std(returns) if np.std(returns) != 0 else 0
    downside_returns = np.minimum(excess_returns, 0)
    sortino = np.mean(excess_returns) / np.std(downside_returns) if np.std(downside_returns) != 0 else np.inf

    threshold = risk_free_rate
    gains = np.sum(returns[returns > threshold] - threshold)
    losses = np.abs(np.sum(returns[returns <= threshold] - threshold))
    omega = gains / losses if losses != 0 else np.inf

    cumulative_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (running_max - cumulative_returns) / running_max
    max_drawdown = np.max(drawdowns)
    calmar = np.mean(excess_returns) / max_drawdown if max_drawdown != 0 else np.inf

    return sharpe, sortino, omega, calmar

def generate_balance(days, seed=None, target_final_value=2000):
    if seed is not None:
        np.random.seed(seed)

    trend = np.random.choice(['up', 'down', 'sideways'])
    if trend == 'up':
        base = np.linspace(0, 1, days)
    elif trend == 'down':
        base = np.linspace(1, 0, days)
    else:
        base = np.ones(days)

    seasonality = np.sin(np.linspace(0, 8*np.pi, days)) * 0.2

    shocks = np.zeros(days)
    num_shocks = np.random.randint(1, 8)
    for _ in range(num_shocks):
        shock_idx = np.random.randint(0, days)
        shock_magnitude = np.random.uniform(-0.5, 0.5)
        shocks[shock_idx:] += shock_magnitude

    combined = base + seasonality + shocks
    noise = np.random.normal(0, 0.05, days)
    final = combined + noise

    balance = 1000 * np.exp(final)
    balance = np.maximum(balance, 1)

    # Adjust the balance to reach the target final value
    scaling_factor = target_final_value / balance[-1]
    balance *= scaling_factor

    return balance

def plot_charts(balances, ratios, final_totals, custom_scores, title, num_charts):
    num_cols = min(5, num_charts)
    num_rows = math.ceil(num_charts / num_cols)

    plt.figure(figsize=(4*num_cols, 4*num_rows))
    for i, (balance, (sharpe, sortino, omega, calmar), final_total, custom_score) in enumerate(zip(balances, ratios, final_totals, custom_scores)):
        if i >= num_charts:
            break
        ax = plt.subplot(num_rows, num_cols, i+1)
        ax.plot(balance)
        ax.set_title(f'Chart {i+1}')
        ax.set_xlabel('Days')
        ax.set_ylabel('Balance')
        ax.text(0.05, 0.05,
                f'Final: ${final_total:.0f}\nSharpe: {sharpe:.2f}\nSortino: {sortino:.2f}\nOmega: {omega:.2f}\nCalmar: {calmar:.2f}\nCustom: {custom_score:.2f}',
                transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8))
    plt.tight_layout()
    plt.suptitle(title, fontsize=16)
    plt.show()

def custom_score(final_total, omega):
    return final_total * (omega ** 3)

def plot_top_charts(balances, ratios, final_totals, custom_scores, title, num_charts_to_show):
    num_cols = min(5, num_charts_to_show)
    num_rows = math.ceil(num_charts_to_show / num_cols)

    plt.figure(figsize=(4*num_cols, 4*num_rows))
    for i in range(num_charts_to_show):
        ax = plt.subplot(num_rows, num_cols, i+1)
        ax.plot(balances[i])
        ax.set_title(f'Chart {i+1}')
        ax.set_xlabel('Days')
        ax.set_ylabel('Balance')
        sharpe, sortino, omega, calmar = ratios[i]
        ax.text(0.05, 0.05,
                f'Final: ${final_totals[i]:.0f}\nSharpe: {sharpe:.2f}\nSortino: {sortino:.2f}\nOmega: {omega:.2f}\nCalmar: {calmar:.2f}\nCustom: {custom_scores[i]:.2f}',
                transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8))
    plt.tight_layout()
    plt.suptitle(title, fontsize=16)
    plt.show()


import numpy as np

def smooth_sortino_metric(sortino, x, k=1000):
    """
    Calculate a smooth metric combining Sortino ratio and another metric.

    Parameters:
    sortino (float): The Sortino ratio
    x (float): Another relevant metric (e.g., total return)
    k (float): A large constant to control sensitivity (default: 1000)

    Returns:
    float: The smooth combined metric
    """
    return x * np.tanh(sortino / k)

def custom_score(final_total, sortino, omega, k=1000):
    total_return = (final_total - 1000) / 1000 * 100  # Assuming initial balance is 1000
    smooth_sortino_returns = smooth_sortino_metric(sortino, total_return, k)
    return smooth_sortino_returns * (omega ** 2)

def run_analysis(num_charts, days, num_charts_to_show, target_final_value):
    balances = []
    all_ratios = []
    final_totals = []
    custom_scores = []

    for i in range(num_charts):
        balance = generate_balance(days, seed=i, target_final_value=target_final_value)
        returns = np.diff(balance) / balance[:-1]
        ratios = calculate_ratios(returns)
        balances.append(balance)
        all_ratios.append(ratios)
        final_total = balance[-1]
        final_totals.append(final_total)

        # Calculate custom score using smooth Sortino metric
        sharpe, sortino, omega, calmar = ratios
        custom_scores.append(custom_score(final_total, sortino, omega))

    print(f"Generated {num_charts} charts")


    # sort_criteria = ['Sharpe', 'Sortino', 'Omega', 'Calmar', 'Final Total', 'Custom Score']
    sort_criteria = ['Sortino', 'Custom Score']

    for criterion in sort_criteria:
        if criterion == 'Final Total':
            sorted_indices = sorted(range(num_charts), key=lambda k: final_totals[k], reverse=True)
        elif criterion == 'Custom Score':
            sorted_indices = sorted(range(num_charts), key=lambda k: custom_scores[k], reverse=True)
        else:
            index = sort_criteria.index(criterion)
            sorted_indices = sorted(range(num_charts), key=lambda k: all_ratios[k][index], reverse=True)

        top_indices = sorted_indices[:num_charts_to_show]
        sorted_balances = [balances[j] for j in top_indices]
        sorted_ratios = [all_ratios[j] for j in top_indices]
        sorted_final_totals = [final_totals[j] for j in top_indices]
        sorted_custom_scores = [custom_scores[j] for j in top_indices]
        plot_top_charts(sorted_balances, sorted_ratios, sorted_final_totals, sorted_custom_scores,
                        f"Top {num_charts_to_show} Portfolio Balance Charts Sorted by {criterion} ({days} days)", num_charts_to_show)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate and analyze portfolio balance charts.")
    parser.add_argument("--num_charts_to_gen", type=int, default=200, help="Number of charts to generate")
    parser.add_argument("--days", type=int, default=100, help="Number of days for each chart")
    parser.add_argument("--num_charts_to_show", type=int, default=20, help="Number of top charts to display")
    parser.add_argument("--target_final_value", type=float, default=2000, help="Target final value for all charts")
    args = parser.parse_args()

    run_analysis(args.num_charts_to_gen, args.days, args.num_charts_to_show, args.target_final_value)
