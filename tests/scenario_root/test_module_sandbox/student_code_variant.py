# Student code variant for testing parameterized module-scoped sandbox
# This variant has a different counter starting point to demonstrate separate state

# Access value from setup_code which gets it from data.json
test_variable = BASE_VALUE

# Module-level counter starting at 100 (different from student_code.py)
_counter = 100


def test_function(x):
    """A simple test function using the data.json multiplier."""
    # Use the MULTIPLIER from setup_code.py (which gets it from data.json)
    return x * MULTIPLIER


def increment_counter():
    """Increment and return the module-level counter (starts at 100)."""
    global _counter
    _counter += 1
    return _counter


def test_function_with_print():
    """A function that produces stdout output using setup_code values."""
    print(f"Hello from test function! {SETUP_CONSTANT}")
    print(f"Message: {GREETING_MESSAGE}")
    return "done"


def get_data_value():
    """Function to access the data.json base_value parameter."""
    return BASE_VALUE


def get_message_from_data():
    """Function to access the message from data.json."""
    return GREETING_MESSAGE


def use_setup_function():
    """Function that uses a function from setup_code.py."""
    return get_setup_value()


def test_array_processing():
    """Function that processes the test array from data.json."""
    # Calculate sum manually since sum() builtin might not be available
    total = 0
    for item in TEST_ARRAY:
        total += item
    return total


def multiply_using_setup(x):
    """Function that uses the setup function to multiply."""
    return multiply_by_setup_value(x)
