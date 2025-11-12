"""
Test scenario for module sandbox with calculator student code.
This tests that different student code files get separate cached instances,
and state is shared within the module.
"""

from pytest_pl_grader.fixture import StudentFixture


def test_module_sandbox_calc_1(module_sandbox: StudentFixture) -> None:
    """Test calculator functionality - should start at 0."""
    result = module_sandbox.query_function("get_total")
    assert result == 0.0


def test_module_sandbox_calc_2(module_sandbox: StudentFixture) -> None:
    """Test calculator add - should share state with previous test."""
    result = module_sandbox.query_function("add", 10.5)
    assert result == 10.5
    
    total = module_sandbox.query_function("get_total")
    assert total == 10.5


def test_module_sandbox_calc_3(module_sandbox: StudentFixture) -> None:
    """Test calculator subtract - should share state with previous tests."""
    result = module_sandbox.query_function("subtract", 3.5) 
    assert result == 7.0
    
    total = module_sandbox.query_function("get_total")
    assert total == 7.0