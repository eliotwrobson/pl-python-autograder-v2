"""Utility helpers — a second module in the student workspace."""


def clamp(value, lo, hi):
    """Clamp *value* to the range [lo, hi]."""
    return max(lo, min(hi, value))


def is_even(n):
    return n % 2 == 0


EPSILON = 1e-9
