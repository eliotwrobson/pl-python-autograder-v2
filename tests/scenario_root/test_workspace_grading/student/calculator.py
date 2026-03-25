"""Simple calculator module — a student workspace project."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


# Module-level constant the tests can also query
PI_APPROX = 3.14159
