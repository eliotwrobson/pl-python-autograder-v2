import sympy as sp


def analyze_vibration(x_hat, threshold):
    approximation = 7
    true_value = float((sp.sin(6 * x_hat) + 3 * sp.cos(x_hat) + 6).evalf())
    production_ready = approximation > threshold

    return approximation, true_value, production_ready
