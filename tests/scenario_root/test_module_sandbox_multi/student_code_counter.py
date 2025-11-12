# Multiple student code files for testing module sandbox caching
# File 1: Basic counter implementation
counter = 0

def get_counter() -> int:
    global counter
    return counter

def increment_counter() -> None:
    global counter
    counter += 1

def reset_counter() -> None:
    global counter
    counter = 0