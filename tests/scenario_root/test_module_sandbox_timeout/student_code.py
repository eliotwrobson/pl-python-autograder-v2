import time

# This should cause timeout during initialization
time.sleep(5.0)  # Much longer than the 0.05 timeout

x = 5


def test_function():
    return 42
