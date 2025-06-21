import pytest

from pl_pytest_autograder.fixture import FeedbackFixture
from pl_pytest_autograder.fixture import StudentFixture


@pytest.mark.grading_data(name="initialization_timeout", points=2)
@pytest.mark.sandbox_timeout(0.05)
def test_query(sandbox: StudentFixture) -> None:
    assert sandbox.query("x") == 5


@pytest.mark.grading_data(name="function_timeout", points=2)
@pytest.mark.sandbox_timeout(0.5)
def test_query_slow(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    assert sandbox.query("x") == 5
    assert sandbox.query_function("f_fast", 2, y=3, query_timeout=0.2) == 5
    feedback.set_score(0.1)
    assert sandbox.query_function("f_slow", 2, y=3, query_timeout=0.2) == 5


@pytest.mark.grading_data(name="function_timeout", points=2)
@pytest.mark.sandbox_timeout(0.5)
def test_query_fast(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    assert sandbox.query("x") == 5
    assert sandbox.query_function("f_fast", 2, y=3, query_timeout=0.5) == 5
    feedback.set_score(0.1)
    assert sandbox.query_function("f_slow", 2, y=3, query_timeout=0.5) == 5
