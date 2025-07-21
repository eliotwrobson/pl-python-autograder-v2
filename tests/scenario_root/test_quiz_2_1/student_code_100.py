import numpy as np


def analyze_vibration(x_hat, threshold):
    approximation = 9 + 6 * x_hat - 3 * x_hat * x_hat / 2 - 216 * x_hat * x_hat * x_hat / 6
    true_value = np.sin(6 * x_hat) + 3 * np.cos(x_hat) + 6
    production_ready = approximation > threshold

    return approximation, true_value, production_ready
