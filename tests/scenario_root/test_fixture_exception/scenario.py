import pytest
from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.fixture
def ans(sandbox: StudentFixture):
    """
    Fixture that accesses student code and will fail during setup if student code raises an exception.
    This mimics the pattern described in issue #18.
    """
    # This should trigger the TypeError from student code during fixture setup
    return sandbox.query("some_value")


@pytest.mark.grading_data(name="Test with fixture exception", points=1)
@pytest.mark.output("exception_message")
def test_with_fixture_exception(sandbox: StudentFixture, ans) -> None:
    """
    This test uses a fixture that accesses student code.
    If student code raises an exception, it should be properly reported.
    """
    # We shouldn't reach here if the fixture fails
    assert ans == 42
