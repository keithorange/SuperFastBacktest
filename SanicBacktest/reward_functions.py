
# use this to remove all 0's from scores (useful for excellent SUBSET trading. If you want trades ACROSS ALL, DO NOT USE!)
from typing import Callable, List, Union
import numpy as np

def signed_power(x, power):
    """
    Applies power function while preserving the sign of x.
    
    Args:
    x (array-like): Input values
    power (float): Power to raise the absolute values to
    
    Returns:
    array-like: Signed power of x
    """
    return np.sign(x) * np.abs(np.power(np.abs(x), power))

def linear_power(x, power, threshold=1.0):
    """
    Applies linear function for values within [-threshold, threshold],
    and power function otherwise.
    
    Args:
    x (array-like): Input values
    power (float): Power to use for values outside the threshold
    threshold (float): Threshold for linear behavior (default 1.0)
    
    Returns:
    array-like: Result of linear-power operation
    """
    return np.where(np.abs(x) <= threshold, x, signed_power(x, power))

def signed_linear_power(x, power, threshold=1.0):
    """
    Ensures sign preservation after linear_power transformation.
    
    Args:
    x (array-like): Input values
    power (float): Power to use for values outside the threshold
    threshold (float): Threshold for linear behavior (default 1.0)
    
    Returns:
    array-like: Result of signed linear-power operation
    """
    sign = np.sign(x)
    return sign * np.abs(linear_power(np.abs(x), power, threshold))



def _remove_zero_scores(scores, radius=1e-9):
    """
    Remove scores that are within a specified radius around zero.

    Args:
    scores (array-like): The input array of scores.
    radius (float): The radius around zero within which scores should be removed.

    Returns:
    numpy.ndarray: An array with scores outside the specified radius around zero.

    """

    scores = np.asarray(scores)
    return scores[np.abs(scores) > radius]





def scaled_arithmetic_mean(x, zero_penalty=1, disable_zero_penalty_on_loss=True):
    """
    Calculates a mean that handles zeros based on the zero_penalty factor.
    
    - zero_penalty = 1: Traditional mean (full zero penalty)
    - zero_penalty < 1: Reduces penalty for zeros
    """
    # Convert to numpy array
    x = np.array(x)
    
    # Handle empty case
    if len(x) == 0:
        return 0

    # Get non-zero values
    non_zero_scores = _remove_zero_scores(x)

    # Calculate the number of zeros
    num_zeros = len(x) - len(non_zero_scores)

    # Return the mean of non-zero values (ignoring zeros)
    # If there are no zeros, return the regular mean
    if zero_penalty == 0 or num_zeros == 0:
        return np.mean(non_zero_scores)

    # Calculate the mean of non-zero values
    mean_non_zero = np.mean(non_zero_scores)


    if disable_zero_penalty_on_loss:
        penalty_factor = mean_non_zero
    else:
        # Apply penalty by dividing the sum by the number of zeros multiplied by the penalty
        penalty_factor = mean_non_zero / (1 + num_zeros * zero_penalty)  # Using zero_penalty in the denominator


    return penalty_factor


def arithmetic_mean(scores: Union[List[float], np.ndarray], remove_zeros: bool = False) -> float:
    """Calculate the arithmetic mean of scores."""
    if remove_zeros:
        scores = _remove_zero_scores(np.array(scores))

    if len(scores) == 0:
        return 0.0
    if len(scores) == 1:
        return float(scores[0])
    
    return np.mean(scores)

def median(scores: Union[List[float], np.ndarray], remove_zeros: bool = False) -> float:
    """Calculate the median of scores."""
    if remove_zeros:
        scores = _remove_zero_scores(np.array(scores))

    if len(scores) == 0:
        return 0.0
    if len(scores) == 1:
        return float(scores[0])
    
    return np.median(scores)

def modian(scores: Union[List[float], np.ndarray], alpha: float, remove_zeros: bool = False) -> float:
    """Calculate the modian as a weighted combination of mean and median."""
    if remove_zeros:
        scores = _remove_zero_scores(np.array(scores))

    if len(scores) == 0:
        return 0.0
    if len(scores) == 1:
        return float(scores[0])

    mean_value = arithmetic_mean(scores, remove_zeros)
    median_value = median(scores, remove_zeros)
    return mean_value * alpha + median_value * (1 - alpha)



def scaled_arithmetic_sum(x, zero_penalty=0, disable_zero_penalty_on_loss=True):
    """
    Calculates a sum that handles zeros based on the zero_penalty factor.
    
    - zero_penalty = 0: Regular sum (ignoring zeros)
    - zero_penalty = 1: Full penalty sum (dividing by the number of zeros * zero_penalty)
    """
    # Convert to numpy array
    x = np.array(x)
    
    # Handle empty case
    if len(x) == 0:
        return 0
    
    # Get non-zero values
    non_zero_scores = _remove_zero_scores(x)
    
    # Calculate the number of zeros
    num_zeros = len(x) - len(non_zero_scores)
    
    # Return the sum of non-zero values (ignoring zeros)
    # If there are no zeros, return the regular sum
    if zero_penalty == 0 or num_zeros == 0:
        return np.sum(non_zero_scores)
    
    # Calculate the sum of non-zero values
    sum_non_zero = np.sum(non_zero_scores)
    
    if disable_zero_penalty_on_loss:
        penalty_factor = sum_non_zero
    else:
        # Apply penalty by dividing the sum by the number of zeros multiplied by the penalty
        penalty_factor = sum_non_zero / (1 + num_zeros * zero_penalty)  # Using zero_penalty in the denominator

    
    return penalty_factor

def arithmetic_sum(x, remove_zeros=False):
    if remove_zeros:
        x = _remove_zero_scores(x)

    if len(x) == 0:
        return 0
    if len(x) == 1:
        return x[0]
    
    return np.sum(x)



# OPTION #1 FOR LPM! 

import numpy as np
from typing import Union, List, Sequence


def _validate_and_convert_scores(scores: Union[List[float], np.ndarray, Sequence[float]]) -> np.ndarray:
    if not len(scores): return np.array([])
    original_length = len(scores)
    scores = np.array(scores, dtype=np.float64)
    valid_mask = np.isfinite(scores)
    valid_scores = scores[valid_mask]
    if len(valid_scores) != original_length:
        print(f"⚠️ Warning: Removed {original_length - len(valid_scores)} non-finite values from scores.")
    return valid_scores

def _calculate_weights(valid_scores: np.ndarray, alpha: float, epsilon: float, normalize: bool = True) -> np.ndarray:
    alpha = max(0.0, alpha)
    safe_scores = np.maximum(valid_scores, epsilon)
    transformed_scores = -np.power(safe_scores, 2)
    weights = np.exp(alpha * transformed_scores)
    if normalize:
        total_weights = np.sum(weights)
        weights /= (total_weights if total_weights >= epsilon else epsilon)
    return weights

def _compute_weighted_mean(valid_scores: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(weights * valid_scores))

ALPHA = 10  # 0 == arithmetic mean

def _lower_priority_mean_fn(scores, normalize, alpha=ALPHA, epsilon=1e-10):
    # If only 1 score return it!
    if len(scores) == 1:
        return scores[0]
    
    if alpha == 0: return arithmetic_mean(scores)


    valid_scores = _validate_and_convert_scores(scores)
    weights = _calculate_weights(valid_scores, alpha, epsilon, normalize=normalize)
    return _compute_weighted_mean(valid_scores, weights)

# STYLE 1: both work great! 
def lower_priority_mean_trades_subset(scores, alpha=ALPHA, epsilon=1e-10) -> float:
    return _lower_priority_mean_fn(scores, normalize=True, alpha=alpha, epsilon=epsilon)

def lower_priority_mean_must_trade(scores, alpha=ALPHA, epsilon=1e-10) -> float: # USE THIS! 
    return _lower_priority_mean_fn(scores, normalize=False, alpha=alpha, epsilon=epsilon)



def risk_adjusted_metric(
    scores: Union[List[float], np.ndarray],
    mean_func: Callable = arithmetic_sum, 
    deviation_factor: float = 1.0,
    remove_zeros_from_scores: bool = False,
    remove_zeros_from_dev: bool = True,
) -> float:
    """
    Calculate a risk-adjusted metric of scores.

    This function computes a risk-adjusted metric that penalizes dispersion and
    favors strategies with consistent performance across multiple inputs.
    """
    scores = np.array(scores, dtype=np.float64)

    # Remove zeros from scores if specified
    if remove_zeros_from_scores:
        filtered_scores = _remove_zero_scores(scores)
    else:
        filtered_scores = scores

    # Handle cases with insufficient scores
    if len(filtered_scores) <= 1:
        return float(filtered_scores[0]) if len(filtered_scores) == 1 else 0.0

    # # Remove non-finite values from filtered scores
    # valid_mask = np.isfinite(filtered_scores)
    # if not np.all(valid_mask):
    #     print(f"⚠️ Warning: Removed {np.sum(~valid_mask)} non-finite values")
    #     filtered_scores = filtered_scores[valid_mask]

    center_value = mean_func(filtered_scores)

    # Prepare deviation scores
    if remove_zeros_from_dev:
        deviation_scores = _remove_zero_scores(scores)
    else:
        deviation_scores = scores

    # Handle cases with insufficient scores
    if len(deviation_scores) == 0:
       return center_value
        
    # Calculate absolute deviations using the filtered deviation scores
    abs_deviations = np.abs(deviation_scores - center_value)

    # Calculate dispersion (mean absolute deviation)
    dispersion = np.mean(abs_deviations)

    # Normalize dispersion by the absolute center value
    dispersion = (dispersion / (np.abs(center_value) + 1e-10))

    # Apply power transformation

    numerator =center_value #signed_power(center_value , 2) # profit term
    dispersion = signed_power(dispersion, deviation_factor) # std term

    dispersion = np.log1p(dispersion)


    # Calculate risk-adjusted metric
    result = numerator / (1 + dispersion)

    # # Debug output
    # if not np.allclose(filtered_scores, filtered_scores[0]):
    #     print("### Risk-Adjusted Results ###")
    #     print(f"Scores: {filtered_scores}")
    #     print(f"Center: {center_value:.6f}")
    #     print(f"Dispersion: {dispersion:.6f}")
    #     print(f"Result: {result:.6f}\n")


    return float(result)


# NOTE: DOES NOT HYPEROPT! WEIGHTS JUMP I THINK THATS WHY!
def lower_priority_simple(scores, max_score=None, alpha=2.0, use_sum=True):
    """
    Weighted mean that gives lower priority to worse scores.
    Can use either provided max_score or take max from data.

    USE max_score=None unless you are EXPERT!

    Weight = (max_score - score)^power / sum((max_score - scores)^power)

    Args:
        scores (array-like): Input scores
        max_score (float, optional): If provided, use this as max. If None, use max(scores)
        power (float): Power for weight calculation. 1.0 = linear, >1 = more aggressive
        epsilon (float): Small number for numerical stability
    """
    scores = np.array(scores, dtype=np.float64)

    if len(scores) == 0:
        return 0
    if len(scores) == 1:
        return scores[0]

    # Use provided max_score or take from data
    actual_max = np.max(scores)
    if max_score is None:
        max_score = actual_max
    elif actual_max > max_score:
        print(f"🚨 Score(s) {scores[scores > max_score]} exceeded max_score {max_score}")
        if use_sum:
            return float(np.sum(scores))  # Fallback to arithmetic sum
        else: 
            return float(np.mean(scores))

    # Calculate distances (always positive since we subtract from max)
    distances = max_score - scores

    # Calculate weights
    weights = ((distances) ** alpha)

    if not use_sum:
        weights /= (np.sum(weights)+1e-10)


    result = float(np.sum(scores * weights))
    
    # # Debug output (only if scores differ)
    # if not np.allclose(scores, scores[0]):
    #     print("### Weighted Results ###")
    #     print(f"Scores: {scores}")
    #     print(f"Weights: {weights}")
    #     print(f"Weighted {'Sum' if use_sum else 'Mean'}: {result:.6f}\n")

    return result


import numpy as np
from typing import Union, List, Sequence

def lower_priority_exp(scores: Union[List[float], np.ndarray, Sequence[float]], 
                       alpha: float = 4.0, use_sum:bool=False) -> float:
    """
    Scale-preserving lower priority mean that maintains natural number relationships.
    
    Properties:
    - Preserves natural scale of numbers (no normalization)
    - Works with any range of numbers (negative/positive/zero)
    - Stronger weighting for lower values with higher alpha
    - Hyperproportional (scaling inputs scales output proportionally)
    
    Args:
        scores: Input values to average
        alpha: Weight parameter (>= 0) where higher values mean stronger
               preference for lower values:
               - alpha = 1: mild preference
               - alpha = 4: strong preference
               - alpha = 8: very strong preference
               - alpha = 16: extreme preference
    """
    if not len(scores):
        return np.nan
    
    scores = np.array(scores, dtype=np.float64)
    
    if len(scores) == 1:
        return float(scores[0])
    
    if np.all(scores == scores[0]):
        return float(scores[0])
    
    alpha = max(0.0, alpha)
    
    # Shift scores to positive range if needed (preserves relationships)
    shift = 0
    min_score = np.min(scores)
    if min_score <= 0:
        shift = abs(min_score) + 1  # Ensure all scores > 0
        scores = scores + shift
    
    # Calculate weights using raw scores (no normalization)
    # For negative exponents, larger numbers -> smaller weights
    weights = np.exp(-alpha * scores)
    
    # Sum will never be 0 since all exponents are finite
    weights = weights / (np.sum(weights)+ 1e-10)
    
    # Calculate weighted mean and unshift if needed
    if use_sum:
        result = np.sum(weights * scores)
    else:
        result = np.mean(weights * scores)

        
    if shift > 0:
        result -= shift
        
    return float(result)



small_scaled_arithmetic_sum = lambda x:  scaled_arithmetic_sum(x, zero_penalty=0.1, disable_zero_penalty_on_loss=True) #arithmetic_sum(x)
# 
AGGREGATE_MEAN_FUNC = arithmetic_sum


# AGGREGATE_MEAN_FUNC = lambda x: lower_priority_exp(x, alpha=1, use_sum=True)

print(f"Using AGGREGATE_MEAN_FUNC = { AGGREGATE_MEAN_FUNC.__class__}")
