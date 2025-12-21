# Module-level initialization timeout (used as default)
INITIALIZATION_TIMEOUT = 0.5

import pytest

from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="uses_module_timeout", points=2)
def test_with_module_timeout(sandbox: StudentFixture) -> None:
    """Test that uses module-level INITIALIZATION_TIMEOUT (0.5s) - should pass."""
    # Student code sleeps 0.15s, module timeout is 0.5s, so this should succeed
    assert sandbox.query("x") == 5


@pytest.mark.grading_data(name="marker_overrides_module", points=2)
@pytest.mark.sandbox_timeout(0.05)
def test_with_marker_override(sandbox: StudentFixture) -> None:
    """Test that marker (0.05s) overrides module-level timeout - should timeout."""
    # Student code sleeps 0.15s, marker timeout is 0.05s, so this should timeout
    assert sandbox.query("x") == 5


@pytest.mark.grading_data(name="explicit_long_timeout", points=2)
@pytest.mark.sandbox_timeout(1.0)
def test_with_explicit_long_timeout(sandbox: StudentFixture) -> None:
    """Test with explicit long timeout (1.0s) - should pass."""
    # Student code sleeps 0.15s, marker timeout is 1.0s, so this should succeed
    assert sandbox.query("x") == 5
