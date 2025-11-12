# Setup code for module sandbox test
# This code runs before the student code and can access data.json parameters

# Access parameters from data.json
MULTIPLIER = __data_params["multiplier"]
BASE_VALUE = __data_params["base_value"]
SETUP_CONSTANT = "Setup complete!"
GREETING_MESSAGE = __data_params["greeting_message"]
TEST_ARRAY = __data_params["test_array"]


def get_setup_value():
    """Function available to both test and student code."""
    return "Setup value from setup_code.py"


def multiply_by_setup_value(x):
    """Function that uses the data.json multiplier."""
    return x * MULTIPLIER
