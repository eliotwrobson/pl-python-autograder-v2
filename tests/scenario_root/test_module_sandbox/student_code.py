# Student code for testing module-scoped sandbox

test_variable = 42

# Module-level counter to test shared state between tests
_counter = 0


def test_function(x):
    """A simple test function."""
    return x * 2


def increment_counter():
    """Increment and return the module-level counter."""
    global _counter
    _counter += 1
    return _counter


def test_function_with_print():
    """A function that produces stdout output."""
    print("Hello from test function!")
    return "done"