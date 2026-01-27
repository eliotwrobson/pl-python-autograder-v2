"""Test scenario for ConfigObject configuration override functionality.

This test verifies that:
1. ConfigObject can be used to configure the sandbox via module-level autograder_config
2. ConfigObject settings override data.json settings
3. ConfigObject settings override module-level variables
4. All configuration options work correctly through ConfigObject
"""

import pytest

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import FeedbackFixture
from pytest_prairielearn_grader.fixture import StudentFixture

# Module-level timeout that should be overridden by ConfigObject
sandbox_timeout = 0.5

# Module-level ConfigObject that overrides all other configuration
# The plugin automatically detects this variable and uses it
autograder_config = ConfigObject(
    sandbox_timeout=2.0,  # Override module-level timeout
    import_whitelist=["numpy", "pandas"],  # Override data.json whitelist (which allows math)
    import_blacklist=None,  # Override data.json blacklist
    builtin_whitelist=["len", "range", "sum", "print"],  # Override data.json builtin_whitelist
    starting_vars={"coefficient": 10, "custom_multiplier": 3},  # Override data.json coefficient value
    names_for_user=[
        {"name": "coefficient", "type": "int", "description": "Coefficient from ConfigObject"},
        {"name": "custom_multiplier", "type": "int", "description": "Custom variable from ConfigObject"},
    ],  # Override data.json names_for_user to include both variables
    student_code_pattern="student_code.py",  # Explicitly specify which student code file
)


@pytest.mark.grading_data(name="Test ConfigObject overrides data.json", points=10)
def test_config_object_overrides_data_json(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that ConfigObject overrides coefficient from data.json (5 -> 10)."""
    result = sandbox.query("coefficient")
    assert result == 10, f"ConfigObject should override data.json coefficient: expected 10, got {result}"
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="Test ConfigObject custom starting_vars", points=10)
def test_config_object_custom_vars(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that ConfigObject can inject custom variables."""
    result = sandbox.query_function("use_custom_var")
    assert result == 30, f"custom_multiplier should be 3: 3 * 10 = 30, got {result}"
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="Test ConfigObject allows numpy import", points=10)
def test_config_object_import_whitelist(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that ConfigObject import_whitelist allows numpy (overrides data.json which allows math)."""
    result = sandbox.query("numpy_array")
    assert result is not None, "numpy_array should exist"
    assert len(result) == 5, f"numpy_array should have 5 elements, got {len(result)}"
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="Test ConfigObject timeout override", points=10)
def test_config_object_timeout_override(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that ConfigObject timeout overrides module-level timeout.

    This is more of a smoke test - we can't easily verify the timeout value,
    but we can verify that the sandbox works with the ConfigObject timeout.
    """
    result = sandbox.query_function("multiply_by_coefficient", 5)
    assert result == 50, f"5 * 10 = 50, got {result}"
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="Test ConfigObject builtin_whitelist", points=10)
def test_config_object_builtin_whitelist(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that ConfigObject builtin_whitelist works correctly.

    The student code uses len and range which are in the whitelist.
    """
    # Query a simple calculation that would use allowed builtins
    result = sandbox.query_function("multiply_by_coefficient", 3)
    assert result == 30, f"3 * 10 = 30, got {result}"
    feedback.set_score(1.0)
