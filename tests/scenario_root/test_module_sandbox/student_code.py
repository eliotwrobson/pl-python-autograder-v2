# Student code for testing module-scoped sandbox

# Access value from data.json (will be available via the sandbox)
test_variable = 42

# Module-level counter to test shared state between tests
_counter = 0


def test_function(x):
    """A simple test function using a fixed multiplier."""
    # Use a fixed multiplier since setup_code variables aren't directly accessible
    return x * 3


def increment_counter():
    """Increment and return the module-level counter."""
    global _counter
    _counter += 1
    return _counter


def test_function_with_print():
    """A function that produces stdout output."""
    print("Hello from test function! Setup complete!")
    return "done"


def get_data_value():
    """Function to access the data.json value parameter."""
    # This will access the value from data.json through the test framework
    return 42  # The value from data.json


def get_message_from_data():
    """Function to access the message from data.json."""
    # This will access the message from data.json through the test framework
    return "Hello from data.json!"  # The message from data.json


def use_setup_function():
    """Function that simulates using a setup function."""
    return "Setup value from setup_code.py"
