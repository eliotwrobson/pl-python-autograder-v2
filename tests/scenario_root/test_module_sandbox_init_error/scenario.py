import pytest

from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="Test 1", points=1)
def test_one(module_sandbox: StudentFixture) -> None:
    """This test should fail due to initialization error."""
    result = module_sandbox.query("x")
    assert result == 5


@pytest.mark.grading_data(name="Test 2", points=1)
def test_two(module_sandbox: StudentFixture) -> None:
    """This test should also fail with the same error, but error should only be reported once."""
    result = module_sandbox.query("y")
    assert result == 10


@pytest.mark.grading_data(name="Test 3", points=1)
def test_three(module_sandbox: StudentFixture) -> None:
    """This test should also fail with the same error."""
    result = module_sandbox.query_function("some_func")
    assert result == 42
