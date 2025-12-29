# Quick Start Guide

This is a quick start guide for using the new Python autograder for PrairieLearn. This guide
covers the basic usage and functionality with examples. The grader uses the Docker image
`eliotwrobson/grader-python-pytest:latest` which is powered by the `pytest-prairielearn-grader`
pytest plugin.

The following discussion is based on converted example questions in PrairieLearn.
For a real example, see: https://github.com/PrairieLearn/PrairieLearn/pull/12603

## Editor Setup

Install the required packages in your Python environment for IDE support (e.g., VS Code with Pylance):

```bash
pip install pytest pytest-prairielearn-grader
```

This enables IDE features like autocomplete, type checking, and inline documentation when writing test cases.

## File Structure

The required file structure for a PrairieLearn question using this grader is:

```
- info.json
- question.html
- tests/
  ├── initial_code.py      (optional: starter code for students)
  ├── setup_code.py        (optional: test setup and parameters)
  └── test_student.py      (required: test cases)
```

**Important**: The file editor element in `question.html` should have `file-name="student_code.py"`.
The autograder looks for `student_code.py` by default. You can customize this by setting
`student_code_pattern = "your_filename.py"` at the global scope of `test_student.py`.

## Setup Code (`setup_code.py`)

The `setup_code.py` file defines variables and functions that are available to the student
code. Only variables listed in the `names_for_user` entry in `data.json` (via the
`pl-external-grader-variables` element) are accessible to the student.

Example `setup_code.py`:

```python
import numpy as np
import numpy.linalg as la


def not_allowed(*args, **kwargs):
    raise RuntimeError("Usage of this function is not allowed in this question.")


# Set up parameters
n = np.random.randint(4, 16)

# Generate a random full-rank matrix
X = la.qr(np.random.random_sample((n, n)))[0]
D = np.diag(np.random.random_sample(n) * 10 + 1)
A = X.T @ D @ X

b = np.random.random(n)

# Block certain functions
la.inv = not_allowed
la.pinv = not_allowed
```

In this example, only `A`, `b`, and `n` (specified in `names_for_user`) are accessible in the
student code. The function blocking demonstrates how to prevent students from using certain
library functions.

## Test Cases (`test_student.py`)

Test cases use pytest fixtures provided by the `pytest-prairielearn-grader` package.

### Basic Example

```python
import numpy as np
import numpy.linalg as la
import pytest
from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="x", points=1)
def test_array_all_close(sandbox: StudentFixture) -> None:
    """Test that student's solution x solves the linear system."""
    correct_x = la.solve(sandbox.query("A"), sandbox.query("b"))
    np.testing.assert_allclose(
        sandbox.query("x"), correct_x, err_msg="x is not correct"
    )
```

### Test Markers

The `@pytest.mark.grading_data` decorator specifies test metadata:

- `name`: Test name displayed to students
- `points`: Maximum points for the test
- `include_stdout_feedback`: (Optional, default=`True`) Whether to include student code's stdout in feedback

Example with stdout control:

```python
@pytest.mark.grading_data(name="Test Output", points=2, include_stdout_feedback=True)
def test_with_output(sandbox: StudentFixture) -> None:
    result = sandbox.query_function("process_data", data)
    assert result == expected_value
    # Student's print statements will appear in feedback
```

### Available Fixtures

Three fixtures are provided by the `pytest-prairielearn-grader` package:

1. **`sandbox: StudentFixture`**: Provides sandboxed access to student code. Use this to query variables
   and call functions from the student's submission.

2. **`module_sandbox: StudentFixture`**: Similar to `sandbox`, but maintains state across all tests in
   a module. Useful when you want student code initialization to persist between tests (e.g., testing
   stateful classes or persistent data structures).

3. **`feedback: FeedbackFixture`**: Manages partial credit and custom feedback messages for students.

4. **`data_json: DataFixture`**: Provides access to parameters from PrairieLearn's `data.json` file
   (generated via `pl-external-grader-variables` and other elements).

For implementation details, see the [fixture source code](https://github.com/eliotwrobson/pl-python-autograder-v2/blob/main/src/pytest_prairielearn_grader/fixture.py).

## Querying Student Code

The `sandbox` fixture provides methods to interact with student code:

### 1. Query Variables

```python
value = sandbox.query("variable_name")
```

Retrieves the value of a variable defined in the student code or `setup_code.py`.
Raises an error if the variable doesn't exist.

### 2. Query Functions

```python
result = sandbox.query_function("function_name", arg1, arg2, kwarg1=value1)
```

Calls a function defined in the student code with the given arguments.
Returns a `StudentFunctionResponse` object with:

- `status`: `SUCCESS`, `EXCEPTION`, `TIMEOUT`, or `NOT_FOUND`
- `value`: The return value (if successful)
- `stdout`/`stderr`: Captured output
- `exception_name`, `exception_message`, `traceback`: Error details (if exception occurred)

Example checking function response:

```python
response = sandbox.query_function("calculate", x, y)
if response.status == "SUCCESS":
    assert response.value == expected_result
else:
    pytest.fail(f"Function failed: {response.exception_message}")
```

### 3. Get Captured Output

```python
output = sandbox.get_stdout()
```

Retrieves stdout captured from student code execution.

**Note**: Student code must define the queried symbols, and return values must be JSON-serializable.
Supported types include: `int`, `float`, `str`, `list`, `dict`, `bool`, `None`, numpy arrays, pandas DataFrames,
and matplotlib figures.

## Partial Credit and Feedback

Tests flow linearly, allowing partial credit after certain assertions pass. When an assertion
fails, the student receives the last partial credit value set before the failure.

```python
@pytest.mark.grading_data(name="Multi-step Test", points=10)
def test_with_partial_credit(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    # Check basic requirements (worth 30%)
    result = sandbox.query("data_loaded")
    assert result is not None, "Data must be loaded"
    feedback.set_score(0.3)

    # Check intermediate computation (worth 60%)
    intermediate = sandbox.query("processed_data")
    assert len(intermediate) > 0, "Data processing failed"
    feedback.set_score(0.6)

    # Check final result (worth 100%)
    final = sandbox.query("final_result")
    assert final == expected_value, "Final result incorrect"
    feedback.set_score(1.0)

    # Add custom feedback
    feedback.add_message("Excellent work! All steps completed correctly.")
```

**Key Methods**:

- `feedback.set_score(fraction)`: Set partial credit (0.0 to 1.0)
- `feedback.set_score_final(fraction)`: Set final score (prevents further updates)
- `feedback.add_message(msg)`: Add custom feedback message

## Advanced Features

### Timeout Configuration

Control execution time limits for sandbox initialization and function calls to prevent infinite loops or slow student code.

**Important**: Timeouts apply to:

- **Sandbox initialization** (loading and executing student code at startup)
- **Function calls** via `sandbox.query_function()`

Variable queries via `sandbox.query()` do not have timeouts since they're simple lookups.

#### Module-level Default Timeout

Set a default timeout for sandbox initialization in all tests in a file:

```python
# At the top of test_student.py (before imports)
sandbox_timeout = 2.0  # 2 second timeout for initialization

import pytest
from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="Test 1", points=1)
def test_with_default_timeout(sandbox: StudentFixture) -> None:
    # The sandbox was initialized with 2 second timeout
    # Now we can safely query variables and call functions
    result = sandbox.query_function("compute_result")
    assert result == 5
```

#### Per-test Timeout Override

Override the default initialization timeout with the `@pytest.mark.sandbox_timeout` marker:

```python
@pytest.mark.grading_data(name="Fast Test", points=1)
@pytest.mark.sandbox_timeout(0.5)  # 0.5 second initialization timeout
def test_with_custom_timeout(sandbox: StudentFixture) -> None:
    # This sandbox was initialized with 0.5 second timeout
    result = sandbox.query_function("quick_computation")
    assert result == 5
```

#### Per-function Timeout

Set timeout for individual function calls using the `query_timeout` parameter:

```python
@pytest.mark.grading_data(name="Function Test", points=2)
def test_function_timeout(sandbox: StudentFixture) -> None:
    # This specific function call has a 1 second timeout
    result = sandbox.query_function("compute", data, query_timeout=1.0)
    assert result == expected_value

    # This function call uses the default timeout
    result2 = sandbox.query_function("another_compute", data)
    assert result2 == expected_value2
```

### Module-Scoped Sandbox

Use `module_sandbox` instead of `sandbox` when you want student code state to persist
across multiple tests:

```python
@pytest.mark.grading_data(name="Initialize", points=1)
def test_initialization(module_sandbox: StudentFixture) -> None:
    """First test initializes state."""
    result = module_sandbox.query_function("initialize_counter")
    assert result == 0


@pytest.mark.grading_data(name="Increment 1", points=1)
def test_increment_1(module_sandbox: StudentFixture) -> None:
    """State persists - counter should be 1."""
    result = module_sandbox.query_function("increment_counter")
    assert result == 1


@pytest.mark.grading_data(name="Increment 2", points=1)
def test_increment_2(module_sandbox: StudentFixture) -> None:
    """State still persists - counter should be 2."""
    result = module_sandbox.query_function("increment_counter")
    assert result == 2
```

**Use Cases for `module_sandbox`**:

- Testing stateful classes or modules
- Expensive initialization that should only run once
- Testing persistent data structures (databases, file systems, etc.)
- Simulating multi-step workflows

**Important**: With `module_sandbox`, student code is loaded once and shared across all tests
in the module. Use regular `sandbox` for independent test execution.

### Capturing and Testing Output

Control whether student code output appears in feedback:

```python
@pytest.mark.grading_data(name="With Output", points=2, include_stdout_feedback=True)
def test_with_output(sandbox: StudentFixture) -> None:
    """Student's print statements will appear in feedback."""
    result = sandbox.query_function("process_data")
    # Any print() calls in student code are captured and shown
    assert result == expected


@pytest.mark.grading_data(name="Without Output", points=2, include_stdout_feedback=False)
def test_without_output(sandbox: StudentFixture) -> None:
    """Student's print statements will NOT appear in feedback."""
    result = sandbox.query_function("process_data")
    assert result == expected


@pytest.mark.grading_data(name="Manual Output Check", points=2)
def test_output_manually(sandbox: StudentFixture) -> None:
    """Manually inspect and test stdout."""
    sandbox.query_function("print_greeting", "Alice")
    output = sandbox.get_stdout()
    assert "Hello, Alice!" in output, "Greeting message not found in output"
```

### Testing Matplotlib Plots

The grader supports automatic serialization and deserialization of matplotlib figures:

```python
import matplotlib
matplotlib.use("Agg")  # Non-GUI backend for server environments

import pytest
from matplotlib.figure import Figure
from matplotcheck.base import PlotTester
from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="Plot Test", points=5)
def test_student_plot(sandbox: StudentFixture) -> None:
    """Test that student creates a correct plot."""
    # Student function returns a matplotlib figure
    plot = sandbox.query_function("create_plot", data)

    assert isinstance(plot, Figure)
    assert len(plot.axes) == 1

    # Use matplotcheck for detailed plot testing
    ax = plot.axes[0]
    pt = PlotTester(ax)

    # Check plot properties
    pt.assert_plot_type("line")
    pt.assert_axis_label_contains(axis="x", strings_expected=["Time"])
    pt.assert_axis_label_contains(axis="y", strings_expected=["Value"])
    pt.assert_title_contains(["Data Visualization"])
```

The grader automatically serializes/deserializes:

- Matplotlib figures
- NumPy arrays
- Pandas DataFrames
- Standard Python types (int, float, str, list, dict, bool, None)

## More Examples

To see more examples of what is possible in these test files, look at the test cases in
[this folder](https://github.com/eliotwrobson/pl-python-autograder-v2/tree/main/tests/scenario_root). Each test file is called `scenario.py`.

## PrairieLearn Configuration

In your PrairieLearn question's `info.json`, specify the grader:

```json
{
  "title": "Your Question Title",
  "topic": "Your Topic",
  "tags": ["your-tags"],
  "type": "v3",
  "gradingMethod": "External",
  "externalGradingOptions": {
    "enabled": true,
    "image": "eliotwrobson/grader-python-pytest:latest",
    "timeout": 30
  }
}
```

## Tips and Best Practices

1. **Use descriptive test names**: The `name` in `@pytest.mark.grading_data` is shown to students
2. **Provide clear error messages**: Use informative assertion messages to guide students
3. **Test incrementally**: Break complex problems into smaller tests with partial credit
4. **Control output visibility**: Use `include_stdout_feedback=False` for tests where student output
   would be confusing or reveal answers
5. **Set appropriate timeouts**: Prevent infinite loops while allowing reasonable execution time
6. **Use `module_sandbox` sparingly**: Only when you need persistent state across tests
7. **Block prohibited functions**: Use the setup code to prevent students from using disallowed functions
   (like in the `la.inv = not_allowed` example above)
