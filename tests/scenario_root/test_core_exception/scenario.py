import pytest

from pl_pytest_autograder.fixture import FeedbackFixture
from pl_pytest_autograder.fixture import StudentFixture


@pytest.mark.grading_data(name="test_exception", points=2)
def test_core_exception(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.1)
    assert sandbox.query("x") == 1
