"""
Test scenario for module sandbox with multiple student code files.
This tests that different student code files get separate cached instances.
"""

from pytest_pl_grader.fixture import StudentFixture


def test_module_sandbox_counter_1(module_sandbox: StudentFixture) -> None:
    """Test counter functionality - should start at 0."""
    result = module_sandbox.query_function("get_counter")
    assert result == 0


def test_module_sandbox_counter_2(module_sandbox: StudentFixture) -> None:
    """Test counter increment - should share state with previous test."""
    module_sandbox.query_function("increment_counter")
    result = module_sandbox.query_function("get_counter")
    assert result == 1


def test_module_sandbox_counter_3(module_sandbox: StudentFixture) -> None:
    """Test another counter increment - should share state with previous tests."""
    module_sandbox.query_function("increment_counter")
    result = module_sandbox.query_function("get_counter")
    assert result == 2