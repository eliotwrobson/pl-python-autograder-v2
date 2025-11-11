import pytest

from pytest_pl_grader.fixture import FeedbackFixture
from pytest_pl_grader.fixture import StudentFixture


def simple_function_with_print():
    print("Hello from student code!")
    print("This is a second line of output")
    return 42


@pytest.mark.grading_data(name="Test with stdout feedback", points=2, include_stdout_feedback=True)
def test_with_stdout_feedback(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that demonstrates the new stdout feedback feature."""

    # Query a function that produces stdout
    result = sandbox.query_function("simple_function_with_print")

    # The stdout should be automatically added to feedback at the end of the test
    # because include_stdout_feedback=True

    if result == 42:
        feedback.set_score_final(1.0)
        feedback.add_message("Function returned the correct value!")
    else:
        feedback.set_score_final(0.0)
        feedback.add_message("Function returned an incorrect value.")


@pytest.mark.grading_data(name="Test with default stdout feedback", points=2)
def test_with_default_stdout_feedback(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that demonstrates the new default behavior (stdout feedback enabled by default)."""

    # Query a function that produces stdout
    result = sandbox.query_function("simple_function_with_print")

    # The stdout should be automatically added to feedback at the end of the test
    # because include_stdout_feedback defaults to True

    if result == 42:
        feedback.set_score_final(1.0)
        feedback.add_message("Function returned the correct value!")
    else:
        feedback.set_score_final(0.0)
        feedback.add_message("Function returned an incorrect value.")


@pytest.mark.grading_data(name="Test without stdout feedback", points=2, include_stdout_feedback=False)
def test_without_stdout_feedback(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that demonstrates how to explicitly disable stdout feedback."""

    # Query the same function that produces stdout
    result = sandbox.query_function("simple_function_with_print")

    # The stdout should NOT be added to feedback because include_stdout_feedback=False

    if result == 42:
        feedback.set_score_final(1.0)
        feedback.add_message("Function returned the correct value!")
    else:
        feedback.set_score_final(0.0)
        feedback.add_message("Function returned an incorrect value.")
