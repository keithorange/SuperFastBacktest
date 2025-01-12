import os

import numpy as np
mac_sounds = [
    # Basso: A low, deep sound often used for alerts.
    "Basso",

    # Blow: A blowing sound that can be quite startling.
    "Blow",

    # Frog: A ribbit sound that can be amusingly annoying.
    "Frog",

    # Glass: A ringing sound that is sharp and clear.
    "Glass",

    # Hero: A triumphant and loud chime.
    "Hero",

    # Morse: A series of beeps that can be very attention-grabbing.
    "Morse",

    # Ping: A short, high-pitched sound that can be irritating if repeated.
    "Ping",

    # Sosumi: A quirky sound that has become a classic notification tone.
    "Sosumi",

    # Submarine: A deep, echoing sound reminiscent of a submarine horn.
    "Submarine",

    # Tink: A light, bell-like sound that can be quite sharp.
    "Tink"
]

def play_notification_sound(sound_name='Frog'):
    # Path to a built-in sound file (you can change this to any .wav or .mp3 file you have)
    sound_file = f"/System/Library/Sounds/{sound_name}.aiff"  # Built-in sound on macOS
    os.system(f"afplay '{sound_file}'")


def normalize(value, min_val, max_val):
    return max(0, min(1, (value - min_val) / (max_val - min_val)))


def scale_min_value_by_trade_frequency(trade_count, min_trades, min_value=-100000, max_value=10000):
    # Check if inputs are valid
    if min_value >= max_value:
        raise ValueError("min_value must be less than max_value")

    if min_trades <= 0:
        raise ValueError("min_trades must be positive")

    # If we've made enough trades, no restrictions
    if trade_count >= min_trades:
        return None

    # If no trades made, use maximum restriction
    if trade_count == 0:
        return min_value

    # Calculate how far we've progressed
    progress = trade_count / min_trades

    # Scale between min_value and max_value based on progress
    return min_value + (max_value - min_value) * progress

def handle_infs_nans(ratio: float, default_value=-100) -> float:
    if type(ratio) == np.ndarray or type(ratio) == list: # SKIP LISTS/ARRAYS
        return ratio
    # print(f"type(ratio) = {type(ratio) }")
    try:
        return default_value if np.isinf(ratio) or np.isnan(ratio) else ratio
    except:
        return ratio

def signed_square(x):
    """Helper function to compute the signed square of a number."""
    return x * abs(x)

# def sum_signed_squares(numbers):
#     """Compute the sum of signed squares for a list of numbers."""
#     return sum(signed_square(x) for x in numbers)


def sign_preserving_multiply(a, b, c):
    """
    Multiply terms while preserving proper sign behavior:
    - If two negatives multiply to positive, convert back to negative
    - Maintains true directional signals
    """
    ab = a * b
    ab_sign = 1 if ab >= 0 else -1
    bc = b * c
    bc_sign = 1 if bc >= 0 else -1
    ac = a * c
    ac_sign = 1 if ac >= 0 else -1

    # If any two terms multiply to positive due to negative*negative,
    # we should make result negative
    final_sign = -1 if (ab_sign + bc_sign + ac_sign) < 2 else 1

    return final_sign


def convert_leaf_values_to_string(obj):
    if isinstance(obj, dict):
        return {k: convert_leaf_values_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(convert_leaf_values_to_string(v) for v in obj)
    elif isinstance(obj, (int, float, bool, type(None))):
        return obj  # Keep these types as they are
    else:
        return str(obj)  # Convert everything else to string
