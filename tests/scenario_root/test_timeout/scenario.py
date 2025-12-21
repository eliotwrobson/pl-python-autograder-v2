# Module-level initialization timeout (used as default when no marker is present)
initialization_timeout = 0.5

import pytest

from pytest_pl_grader.fixture import FeedbackFixture
from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="initialization_timeout", points=2)
@pytest.mark.sandbox_timeout(0.05)
def test_query(sandbox: StudentFixture) -> None:
    assert sandbox.query("x") == 5


@pytest.mark.grading_data(name="module_level_timeout", points=2)
def test_query_with_module_timeout(sandbox: StudentFixture) -> None:
    """Test that uses module-level initialization_timeout (0.5s) instead of marker."""
    # Student code sleeps 0.1s, module timeout is 0.5s, so this should pass
    assert sandbox.query("x") == 5


@pytest.mark.grading_data(name="marker_overrides_module", points=2)
@pytest.mark.sandbox_timeout(0.08)
def test_marker_overrides_module_timeout(sandbox: StudentFixture) -> None:
    """Test that marker timeout (0.08s) overrides module-level timeout (0.5s)."""
    # Student code sleeps 0.1s, marker timeout is 0.08s (overrides 0.5s module)
    # This should timeout, proving the marker (0.08s) is used instead of module default (0.5s)
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
