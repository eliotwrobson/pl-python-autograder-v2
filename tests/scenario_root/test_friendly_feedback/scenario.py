import pytest

from pytest_prairielearn_grader.assertions import assert_approx_equal
from pytest_prairielearn_grader.assertions import assert_equal
from pytest_prairielearn_grader.assertions import assert_fn_equal
from pytest_prairielearn_grader.fixture import FeedbackFixture
from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test add function", points=2)
def test_fn_equal(sandbox: StudentFixture) -> None:
    """Test assert_fn_equal with friendly output."""
    assert_fn_equal(sandbox, "add", args=(2, 3), expected=5)


@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test variable x", points=1)
def test_equal_variable(sandbox: StudentFixture) -> None:
    """Test assert_equal on a queried variable with friendly output."""
    value = sandbox.query("x")
    assert_equal(value, 42, description="variable 'x'")


@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test multiply function", points=2)
def test_fn_equal_passes(sandbox: StudentFixture) -> None:
    """Test that assert_fn_equal passes when correct."""
    assert_fn_equal(sandbox, "multiply", args=(3, 4), expected=12)


@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test greeting", points=1)
def test_equal_string(sandbox: StudentFixture) -> None:
    """Test assert_equal with string values and custom message."""
    result = sandbox.query_function("greet", "Alice")
    assert_equal(result, "Hello, Alice!", description="greet('Alice')", msg="Greeting format is incorrect.")


@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test approx", points=1)
def test_approx_equal(sandbox: StudentFixture) -> None:
    """Test assert_approx_equal."""
    result = sandbox.query_function("multiply", 1.0, 1.0)
    assert_approx_equal(result, 1.0, description="multiply(1.0, 1.0)")


@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test partial credit with friendly", points=3)
def test_partial_credit_friendly(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that partial credit still works with friendly assertions."""
    # First check passes for both correct and wrong code
    result = sandbox.query_function("multiply", 3, 4)
    assert_equal(result, 12, description="multiply(3, 4)")
    feedback.set_score(0.5)

    # Second check may fail on wrong code
    assert_fn_equal(sandbox, "add", args=(10, 5), expected=15)
    feedback.set_score(1.0)
