import pytest

from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="module_initialization_timeout", points=2)
@pytest.mark.sandbox_timeout(0.05)
def test_module_sandbox_with_timeout(module_sandbox: StudentFixture) -> None:
    """Test that module_sandbox respects initialization timeout."""
    # This should fail due to timeout during initialization
    # because student_code.py sleeps for 0.2 seconds but timeout is 0.05 seconds
    assert module_sandbox.query("x") == 5
