# Test scenario for module-scoped sandbox fixture
import pytest

from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="test_module_shared_counter_1", points=1)
def test_module_shared_counter_1(module_sandbox: StudentFixture) -> None:
    """Test that increments a counter and checks its value."""
    # Call increment function and check result
    result = module_sandbox.query_function("increment_counter")
    assert result == 1, f"Expected counter to be 1, got {result}"


@pytest.mark.grading_data(name="test_module_shared_counter_2", points=1)
def test_module_shared_counter_2(module_sandbox: StudentFixture) -> None:
    """Test that counter persists between tests (demonstrating shared module scope)."""
    # Call increment function again - should be 2 if module scope is shared
    result = module_sandbox.query_function("increment_counter")
    assert result == 2, f"Module scope not shared - expected counter to be 2, got {result}"


@pytest.mark.grading_data(name="test_module_shared_counter_3", points=1)
def test_module_shared_counter_3(module_sandbox: StudentFixture) -> None:
    """Test that counter continues to increment (further demonstrating shared state)."""
    # Call increment function one more time
    result = module_sandbox.query_function("increment_counter")
    assert result == 3, f"Module scope not maintained - expected counter to be 3, got {result}"


@pytest.mark.grading_data(name="test_basic_functionality", points=1)
def test_basic_functionality(module_sandbox: StudentFixture) -> None:
    """Test basic functionality to ensure the module sandbox works like regular sandbox."""
    # Test basic variable access
    result = module_sandbox.query("test_variable")
    assert result == 42, f"Expected 42, got {result}"

    # Test function call
    result = module_sandbox.query_function("test_function", 10)
    assert result == 20, f"Expected 20, got {result}"


@pytest.mark.grading_data(name="test_function_with_output", points=1)
def test_function_with_output(module_sandbox: StudentFixture) -> None:
    """Test that stdout is properly captured from module sandbox."""
    # Call function that produces output
    module_sandbox.query_function("test_function_with_print")

    # Check the accumulated stdout
    stdout_content = module_sandbox.get_accumulated_stdout()
    assert "Hello from test function!" in stdout_content, f"Expected stdout containing 'Hello from test function!', got: {stdout_content}"