import numpy as np

from pytest_prairielearn_grader.fixture import StudentFixture


def test_random(sandbox: StudentFixture) -> None:
    # Check that variables we set are unaltered
    assert sandbox.query_setup("a") == 42
    assert sandbox.query_setup("b")["c"] == 1
    assert sandbox.query_setup("weird_func")(10) == 30

    assert sandbox.query("c") == 42
    assert sandbox.query("a") == 10
    assert sandbox.query("b")["c"] == 50
    assert sandbox.query("d") == 11

    sandbox.query("numpy_array")

    np.testing.assert_allclose(
        sandbox.query("numpy_array"),
        np.array([[0.68381872, 0.96876697, 0.87395366], [0.68631014, 0.18857604, 0.03678025], [0.35185975, 0.51566197, 0.14740928]]),
    )
