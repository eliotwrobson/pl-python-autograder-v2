# Test scenario for module-scoped sandbox fixture
import pytest

from pytest_pl_grader.fixture import DataFixture
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

    # Test function call with setup_code MULTIPLIER (3)
    result = module_sandbox.query_function("test_function", 10)
    assert result == 30, f"Expected 30 (10 * 3), got {result}"


@pytest.mark.grading_data(name="test_function_with_output", points=1)
def test_function_with_output(module_sandbox: StudentFixture) -> None:
    """Test that stdout is properly captured from module sandbox."""
    # Call function that produces output
    module_sandbox.query_function("test_function_with_print")

    # Check the accumulated stdout
    stdout_content = module_sandbox.get_accumulated_stdout()
    assert "Hello from test function!" in stdout_content, f"Expected stdout containing 'Hello from test function!', got: {stdout_content}"
    assert "Setup complete!" in stdout_content, f"Expected stdout containing setup message, got: {stdout_content}"


@pytest.mark.grading_data(name="test_data_json_integration", points=1)
def test_data_json_integration(module_sandbox: StudentFixture, data_json: DataFixture) -> None:
    """Test that data.json values are accessible."""
    # Test student functions that return hardcoded values (simulating data.json access)
    result = module_sandbox.query_function("get_data_value")
    assert result == 42, f"Expected student function to return 42, got {result}"

    result = module_sandbox.query_function("get_message_from_data")
    assert result == "Hello from data.json!", f"Expected student function to return message, got {result}"

    # Test accessing data.json value through the framework (if available)
    if data_json is not None:
        assert data_json["params"]["value"] == 42, f"Expected data.json value to be 42, got {data_json['params']['value']}"
        assert data_json["params"]["message"] == "Hello from data.json!", (
            f"Expected data.json message, got {data_json['params']['message']}"
        )


@pytest.mark.grading_data(name="test_setup_code_integration", points=1)
def test_setup_code_integration(module_sandbox: StudentFixture) -> None:
    """Test that setup_code.py integration works (simulated)."""
    # Test function that simulates using setup_code function
    result = module_sandbox.query_function("use_setup_function")
    assert result == "Setup value from setup_code.py", f"Expected setup function result, got {result}"
