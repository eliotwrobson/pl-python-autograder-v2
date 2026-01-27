"""Student code for testing ConfigObject override behavior."""

import numpy as np


def multiply_by_coefficient(value):
    """Multiply a value by the global coefficient variable."""
    return value * coefficient


def use_custom_var():
    """Use a custom variable injected via ConfigObject."""
    return custom_multiplier * 10


def get_coefficient():
    """Return the coefficient value."""
    return coefficient


# Test that numpy is accessible (should be allowed by ConfigObject)
numpy_array = np.array([1, 2, 3, 4, 5])
