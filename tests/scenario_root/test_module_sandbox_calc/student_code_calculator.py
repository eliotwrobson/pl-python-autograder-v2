# Multiple student code files for testing module sandbox caching
# File 2: Calculator implementation
calculator_state = {"total": 0.0}

def add(value: float) -> float:
    calculator_state["total"] += value
    return calculator_state["total"]

def subtract(value: float) -> float:
    calculator_state["total"] -= value
    return calculator_state["total"]

def get_total() -> float:
    return calculator_state["total"]

def clear() -> None:
    calculator_state["total"] = 0.0