import math

import numpy as np
import pytest

from pytest_pl_grader.fixture import DataFixture
from pytest_pl_grader.fixture import FeedbackFixture
from pytest_pl_grader.fixture import StudentFixture


def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def f(x, sin_coefficient, cos_coefficient, constant_term):
    return np.sin(sin_coefficient * x) + cos_coefficient * np.cos(x) + constant_term


def taylor_f(x, sin_coefficient, cos_coefficient, constant_term, taylor_degree):
    t0 = constant_term + cos_coefficient
    t1 = sin_coefficient
    t2 = -cos_coefficient
    t3 = -(sin_coefficient**3)
    taylor_sum = t0 + t1 * x + (t2 / factorial(2)) * (x**2) + (t3 / factorial(3)) * (x**3)
    if taylor_degree == 4:
        t4 = cos_coefficient
        taylor_sum += (t4 / factorial(4)) * (x**4)
    return taylor_sum


def analyze_vibration(x_hat, threshold, sin_coefficient, cos_coefficient, constant_term, taylor_degree):
    approximation = taylor_f(x_hat, sin_coefficient, cos_coefficient, constant_term, taylor_degree)
    true_value = f(x_hat, sin_coefficient, cos_coefficient, constant_term)
    production_ready = approximation > threshold
    return approximation, true_value, production_ready


@pytest.mark.grading_data(name="Test analyze_vibration function", points=6)
@pytest.mark.sandbox_timeout(5)
@pytest.mark.parametrize(
    ("i", "x_hat", "threshold"),
    [(1, 0.7235132915688036, 23.137774021447807), (2, 0.23796317102834275, 23.50476117422776)],
)
def test_0(sandbox: StudentFixture, feedback: FeedbackFixture, data_json: DataFixture, i: int, x_hat: float, threshold: float) -> None:
    points = 0

    sin_coefficient = data_json["params"]["sin_coefficient"]
    cos_coefficient = data_json["params"]["cos_coefficient"]
    constant_term = data_json["params"]["constant_term"]
    taylor_degree = data_json["params"]["taylor_degree"]

    feedback.add_message(" ")
    feedback.add_message(f"Test #{i}")

    st_result = sandbox.query_function("analyze_vibration", x_hat, threshold)
    ref_result = analyze_vibration(
        x_hat,
        threshold,
        sin_coefficient,
        cos_coefficient,
        constant_term,
        taylor_degree,
    )

    assert st_result is not None, "Your function did not return any value. Ensure you have a return statement."

    assert isinstance(st_result, list) and len(st_result) == 3, "Your function should return a tuple with exactly three elements."

    points = 0

    if math.isclose(ref_result[0], st_result[0]):
        points += 1

    if math.isclose(ref_result[1], st_result[1]):
        points += 1

    if ref_result[2] == st_result[2]:
        points += 1
        feedback.add_message("'production_ready' looks good")
    else:
        feedback.add_message(f"'production_ready' is incorrect and has type {type(st_result[2])}")

    feedback.set_score_final(points / 3)
