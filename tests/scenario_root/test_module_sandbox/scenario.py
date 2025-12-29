# Test scenario for parameterized module-scoped sandbox fixture
import pytest

from pytest_prairielearn_grader.fixture import DataFixture
from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="test_module_shared_counter_1", points=1)
def test_module_shared_counter_1(module_sandbox: StudentFixture) -> None:
    """Test that increments a counter and checks its value."""
    # Call increment function and check result
    # student_code.py starts at 0, student_code_variant.py starts at 100
    result = module_sandbox.query_function("increment_counter")
    # Should be 1 for student_code.py and 101 for student_code_variant.py
    assert result in [1, 101], f"Expected counter to be 1 or 101, got {result}"


@pytest.mark.grading_data(name="test_module_shared_counter_2", points=1)
def test_module_shared_counter_2(module_sandbox: StudentFixture) -> None:
    """Test that counter persists between tests (demonstrating shared module scope)."""
    # Call increment function again - should be 2 or 102 if module scope is shared
    result = module_sandbox.query_function("increment_counter")
    assert result in [2, 102], f"Module scope not shared - expected counter to be 2 or 102, got {result}"


@pytest.mark.grading_data(name="test_module_shared_counter_3", points=1)
def test_module_shared_counter_3(module_sandbox: StudentFixture) -> None:
    """Test that counter continues to increment (further demonstrating shared state)."""
    # Call increment function one more time
    result = module_sandbox.query_function("increment_counter")
    assert result in [3, 103], f"Module scope not maintained - expected counter to be 3 or 103, got {result}"


@pytest.mark.grading_data(name="test_basic_functionality", points=1)
def test_basic_functionality(module_sandbox: StudentFixture, data_json: DataFixture) -> None:
    """Test basic functionality using data.json parameters."""
    # Test basic variable access - should be BASE_VALUE from data.json
    result = module_sandbox.query("test_variable")
    expected_value = data_json["params"]["base_value"]
    assert result == expected_value, f"Expected {expected_value}, got {result}"

    # Test function call with data.json multiplier
    result = module_sandbox.query_function("test_function", 10)
    expected_result = 10 * data_json["params"]["multiplier"]
    assert result == expected_result, f"Expected {expected_result} (10 * {data_json['params']['multiplier']}), got {result}"


@pytest.mark.grading_data(name="test_function_with_output", points=1)
def test_function_with_output(module_sandbox: StudentFixture, data_json: DataFixture) -> None:
    """Test that stdout is properly captured from module sandbox."""
    # Call function that produces output
    module_sandbox.query_function("test_function_with_print")

    # Check the accumulated stdout
    stdout_content = module_sandbox.get_accumulated_stdout()
    assert "Hello from test function!" in stdout_content, f"Expected stdout containing 'Hello from test function!', got: {stdout_content}"
    assert "Setup complete!" in stdout_content, f"Expected stdout containing setup message, got: {stdout_content}"

    # Check for the data.json message in stdout
    expected_message = data_json["params"]["greeting_message"]
    assert expected_message in stdout_content, f"Expected stdout containing '{expected_message}', got: {stdout_content}"


@pytest.mark.grading_data(name="test_data_json_integration", points=1)
def test_data_json_integration(module_sandbox: StudentFixture, data_json: DataFixture) -> None:
    """Test that data.json values are properly accessible through setup_code."""
    # Test student functions that return data.json values
    result = module_sandbox.query_function("get_data_value")
    expected_value = data_json["params"]["base_value"]
    assert result == expected_value, f"Expected student function to return {expected_value}, got {result}"

    result = module_sandbox.query_function("get_message_from_data")
    expected_message = data_json["params"]["greeting_message"]
    assert result == expected_message, f"Expected student function to return '{expected_message}', got {result}"


@pytest.mark.grading_data(name="test_setup_code_integration", points=1)
def test_setup_code_integration(module_sandbox: StudentFixture) -> None:
    """Test that setup_code.py functions are accessible."""
    # Test function that uses setup_code function
    result = module_sandbox.query_function("use_setup_function")
    assert result == "Setup value from setup_code.py", f"Expected setup function result, got {result}"


@pytest.mark.grading_data(name="test_array_processing", points=1)
def test_array_processing(module_sandbox: StudentFixture, data_json: DataFixture) -> None:
    """Test processing of array data from data.json."""
    result = module_sandbox.query_function("test_array_processing")
    expected_sum = sum(data_json["params"]["test_array"])
    assert result == expected_sum, f"Expected sum of {data_json['params']['test_array']} = {expected_sum}, got {result}"


@pytest.mark.grading_data(name="test_setup_function_usage", points=1)
def test_setup_function_usage(module_sandbox: StudentFixture, data_json: DataFixture) -> None:
    """Test using functions defined in setup_code.py."""
    result = module_sandbox.query_function("multiply_using_setup", 5)
    expected_result = 5 * data_json["params"]["multiplier"]
    assert result == expected_result, f"Expected {expected_result} (5 * {data_json['params']['multiplier']}), got {result}"
