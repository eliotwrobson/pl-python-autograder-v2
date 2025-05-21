import time

x = 5


def fib(n):
    if n <= 1:
        return n + 1
    if n == 8:
        time.sleep(20)
    if n == 7:
        1 / 0

    return fib(n - 1) + fib(n - 2)
