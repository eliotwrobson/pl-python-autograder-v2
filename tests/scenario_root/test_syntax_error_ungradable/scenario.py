import pytest

from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="Test variable x", points=2)
def test_query_variable(sandbox: StudentFixture) -> None:
    """This test should not actually run since student code has a syntax error."""
    assert sandbox.query("x") == 42


@pytest.mark.grading_data(name="Test add function", points=3)
def test_add_function(sandbox: StudentFixture) -> None:
    """This test should not actually run since student code has a syntax error."""
    result = sandbox.query_function("add", 2, 3)
    assert result == 5
