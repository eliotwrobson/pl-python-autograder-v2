import time

time.sleep(0.1)  # Simulate a long-running import

x = 5


def f_slow(x, *, y):
    # Simulate slow running function
    time.sleep(0.4)
    return x + y


def f_fast(x, *, y):
    # Simulate slow running function
    time.sleep(0.1)
    return x + y
