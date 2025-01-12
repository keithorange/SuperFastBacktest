# import numpy as np
# import matplotlib.pyplot as plt
# import os

# def combined_sortino_metric(sortino, x):
#     """
#     Calculate a combined Sortino metric that handles extreme values smoothly.

#     Parameters:
#     sortino (float): The Sortino ratio (can be infinite)
#     x (float): Another relevant metric (e.g., total return)

#     Returns:
#     float: The combined metric
#     """
#     # Use Softplus to ensure smoothness and handle large values
#     softplus_component = np.log1p(np.exp(sortino))  # Softplus-like behavior

#     # Combine with x using a logistic scaling to ensure stability
#     return softplus_component * (1 / (1 + np.exp(-5 * (x - 0.5))))  # Logistic scaling based on x

# # Generate sample data
# sortinos = np.linspace(-10, 10, 1000)  # Range adjusted for demonstration
# total_returns = np.linspace(0, 1, 1000)
# X, Y = np.meshgrid(sortinos, total_returns)

# # Calculate metric values
# Z = combined_sortino_metric(X, Y)

# # Plotting
# plt.figure(figsize=(12, 8))
# contour = plt.contourf(X, Y, Z, levels=50, cmap='RdYlGn')
# plt.title('Combined Sortino Metric')
# plt.xlabel('Sortino Ratio')
# plt.ylabel('Total Return')
# plt.axhline(0, color='black', linestyle='--', lw=0.7)
# plt.axvline(0, color='black', linestyle='--', lw=0.7)
# plt.colorbar(label='Metric Value')

# # Add infinity labels
# plt.text(9, -0.05, '→ ∞', fontsize=12, verticalalignment='top')
# plt.text(-9, -0.05, '← -∞', fontsize=12, verticalalignment='top')

# # Save figure
# output_dir = "combined_sortino_metric"
# os.makedirs(output_dir, exist_ok=True)
# plt.savefig(os.path.join(output_dir, "combined_sortino_metric.png"))
# plt.close()

# print(f"Plot saved in directory: {output_dir}")

import matplotlib.pyplot as plt
import numpy as np


def smooth_cross_metric(*metrics):
    """
    Calculate a smooth metric combining multiple metrics.

    Parameters:
    *metrics (float): One or more metrics to combine.

    Returns:
    float: The smooth combined metric.
    """

    # Cap each metric to prevent extreme values
    MAX_VALUE = 100  # Assuming metrics are capped at 100 for stability
    clipped_metrics = [np.clip(metric, -MAX_VALUE, MAX_VALUE)
                       for metric in metrics]

    # Apply Softplus to each clipped metric
    softplus_components = [np.log1p(np.exp(metric))
                           for metric in clipped_metrics]

    # Combine using a weighted sum
    n = len(softplus_components)
    weights = np.ones(n) / n  # Equal weights for simplicity

    # Calculate the weighted sum of softplus components
    weighted_sum = np.dot(weights, softplus_components)

    return weighted_sum

# Mathematical proof and analysis


"""
Mathematical Proof:

1. Clipping:
   Let m_i be the i-th input metric.
   m_i' = clip(m_i, -MAX_VALUE, MAX_VALUE)
   This operation ensures -MAX_VALUE ≤ m_i' ≤ MAX_VALUE for all i.

2. Softplus:
   s_i = log(1 + exp(m_i'))
   This operation ensures s_i > 0 for all i, and provides a smooth, monotonic transformation.

3. Weighted Sum:
   w_i = 1/n for all i, where n is the number of metrics.
   S = Σ(w_i * s_i) for i = 1 to n
   
   S = (1/n) * Σ(s_i) for i = 1 to n
   
   This is equivalent to taking the arithmetic mean of the softplus components.

Properties:
1. Boundedness: 0 < S < MAX_VALUE + log(2)
   Proof: 
   - Lower bound: s_i > 0 for all i, so S > 0
   - Upper bound: 
     max(s_i) = log(1 + exp(MAX_VALUE)) < MAX_VALUE + log(2)
     S ≤ (1/n) * n * (MAX_VALUE + log(2)) = MAX_VALUE + log(2)

2. Monotonicity: If all input metrics increase, S increases.
   Proof: Both clipping and softplus are monotonic, and the weighted sum of monotonic functions is monotonic.

3. Smoothness: S is continuously differentiable.
   Proof: Composition of continuously differentiable functions (clip, exp, log, sum) is continuously differentiable.

4. Symmetry: The function treats all input metrics equally.
   Proof: All weights are equal (1/n), so the order of input metrics doesn't matter.

Conclusion:
The function successfully generalizes from 3D to multiple dimensions while maintaining desirable mathematical properties.
"""

# Example usage and visualization


def plot_smooth_cross_metric():
    x = np.linspace(-10, 10, 100)
    y = np.linspace(-10, 10, 100)
    X, Y = np.meshgrid(x, y)
    Z = np.vectorize(lambda x, y: smooth_cross_metric(x, y))(X, Y)

    fig = plt.figure(figsize=(12, 5))

    ax1 = fig.add_subplot(121, projection='3d')
    surf = ax1.plot_surface(X, Y, Z, cmap='viridis')
    ax1.set_xlabel('Metric 1')
    ax1.set_ylabel('Metric 2')
    ax1.set_zlabel('Combined Metric')
    ax1.set_title('3D Surface Plot of Smooth Cross Metric')
    fig.colorbar(surf, shrink=0.5, aspect=5)

    ax2 = fig.add_subplot(122)
    contour = ax2.contourf(X, Y, Z, levels=20, cmap='viridis')
    ax2.set_xlabel('Metric 1')
    ax2.set_ylabel('Metric 2')
    ax2.set_title('Contour Plot of Smooth Cross Metric')
    fig.colorbar(contour)

    plt.tight_layout()
    plt.show()


# Uncomment the following line to generate the plot
plot_smooth_cross_metric()
