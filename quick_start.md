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

### Accessing `data.json` Parameters

Inside `setup_code.py`, you can access parameters from `data.json` via the special `__data_params` variable, which contains the `params` dict (i.e., `data.json["params"]`):

```python
# Access parameters passed from PrairieLearn
coefficient = __data_params["coefficient"]
matrix_size = __data_params["matrix_size"]
```

### Example `setup_code.py`

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
Raises a `RuntimeError` if the variable doesn't exist.

**Example:**

```python
@pytest.mark.grading_data(name="Check Variable", points=2)
def test_variable(sandbox: StudentFixture) -> None:
    coefficient = sandbox.query("coefficient")
    assert coefficient > 0, "Coefficient must be positive"
```

### 2. Query Functions

```python
result = sandbox.query_function("function_name", arg1, arg2, kwarg1=value1)
```

Calls a function defined in the student code with the given arguments and **returns the value directly**.

- **On success**: Returns the function's return value
- **On error**: Raises a `RuntimeError` with details about the exception

**Example:**

```python
@pytest.mark.grading_data(name="Test Function", points=5)
def test_function(sandbox: StudentFixture) -> None:
    # Function returns value directly
    result = sandbox.query_function("calculate", 10, 20)
    assert result == 30, f"Expected 30, got {result}"

    # With keyword arguments
    result = sandbox.query_function("process", x=5, y=10)
    assert result == expected_value
```

**Error handling:**

```python
@pytest.mark.grading_data(name="Test with Error Handling", points=3)
def test_with_error_handling(sandbox: StudentFixture) -> None:
    try:
        result = sandbox.query_function("risky_function", data)
        assert result == expected_value
    except RuntimeError as e:
        # The error message includes the original exception details
        pytest.fail(f"Function raised an error: {e}")
```

**Testing for specific exceptions with `query_function_raw`:**

When you need to verify that student code raises a specific exception (e.g., testing input validation),
use `query_function_raw` to inspect the response directly:

```python
@pytest.mark.grading_data(name="Test Exception Handling", points=3)
def test_raises_value_error(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    """Test that student code properly validates input and raises ValueError."""
    # Call function with invalid input - use query_function_raw to get the full response
    response = sandbox.query_function_raw("validate_input", -1)

    # Check that an exception was raised
    assert response["status"] == "exception", "Function should raise an exception for negative input"
    feedback.set_score(0.5)

    # Verify it's the correct exception type
    assert response["exception_name"] == "ValueError", \
        f"Expected ValueError, got {response['exception_name']}"
    feedback.set_score(0.75)

    # Optionally check the error message
    assert "negative" in response["exception_message"].lower(), \
        "Error message should mention negative values"
    feedback.set_score(1.0)
```

The `query_function_raw` response contains:

- `status`: One of `"success"`, `"exception"`, `"timeout"`, or `"not_found"`
- `value`: The return value (when status is `"success"`)
- `stdout` / `stderr`: Captured output from the function call
- `exception_name`: The exception class name (e.g., `"ValueError"`)
- `exception_message`: The exception message string
- `traceback`: Full traceback string for debugging

### 3. Get Captured Output

```python
output = sandbox.get_accumulated_stdout()
```

Retrieves stdout captured from student code execution across all function calls.

**Example:**

```python
@pytest.mark.grading_data(name="Test Output", points=2)
def test_output(sandbox: StudentFixture) -> None:
    sandbox.query_function("print_greeting", "Alice")
    output = sandbox.get_accumulated_stdout()
    assert "Hello, Alice!" in output, "Greeting not found in output"
```

### 4. Function Timeout

Control execution time for individual function calls:

```python
# Set a 2-second timeout for this specific function call
result = sandbox.query_function("slow_computation", data, query_timeout=2.0)
```

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

### Configuration with ConfigObject

For complex test scenarios, you can use the `ConfigObject` class to configure all autograder settings
in a single, type-safe, immutable object. This is especially useful when you need to override multiple
settings or want better IDE support with autocomplete and type checking.

**Key Features:**

- **Type-safe**: All parameters are type-checked with validation
- **Immutable**: Configuration cannot be modified after creation (frozen dataclass)
- **Keyword-only**: Must use explicit parameter names for clarity
- **Comprehensive**: Supports all security and execution settings

#### Basic Usage

Import and create a `ConfigObject` at the module level in your `test_student.py`:

```python
from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import StudentFixture
import pytest

# Module-level configuration - detected automatically by the plugin
autograder_config = ConfigObject(
    sandbox_timeout=2.0,
    import_whitelist=["numpy", "pandas"],
    builtin_whitelist=["len", "range", "sum", "print"],
    starting_vars={"coefficient": 10, "threshold": 5.0},
    names_for_user=["coefficient", "threshold"],
)

@pytest.mark.grading_data(name="Test with Config", points=5)
def test_with_config(sandbox: StudentFixture) -> None:
    # Configuration is automatically applied
    result = sandbox.query_function("process", data)
    assert result == expected_value
```

#### ConfigObject Parameters

All parameters are optional with sensible defaults:

- **`sandbox_timeout`** (float, default=1.0): Timeout in seconds for sandbox initialization and operations
- **`import_whitelist`** (list[str] | None): Allowed import modules (whitelist mode)
- **`import_blacklist`** (list[str] | None): Blocked import modules (blacklist mode)
- **`builtin_whitelist`** (list[str] | None): Allowed builtin functions
- **`names_for_user`** (list[str] | None): List of variable names to inject into student code
- **`student_code_pattern`** (str, default="student_code\*.py"): Glob pattern for finding student files
- **`starting_vars`** (dict[str, Any], default={}): Dictionary of variable values to provide for injection

**How variable injection works**:

- Only variables listed in `names_for_user` are injected into the student code namespace
- Values are resolved in this priority order:
  1. **Highest**: Variables defined in `setup_code.py` execution
  2. **Medium**: Values from `ConfigObject.starting_vars`
  3. **Lowest**: Values from `data.json` params
- If `names_for_user` is not specified, no variables are injected (prevents variable leaking)
- `starting_vars` provides values but does NOT automatically inject them - variables must still be listed in `names_for_user`

#### Configuration Priority

When `ConfigObject` is defined, it overrides all other configuration sources:

1. **Highest priority**: `ConfigObject` (when `autograder_config` variable exists)
2. **Medium priority**: Module-level variables (e.g., `sandbox_timeout = 2.0`)
3. **Lowest priority**: `data.json` params from PrairieLearn

```python
# This ConfigObject overrides everything
autograder_config = ConfigObject(
    sandbox_timeout=3.0,  # Overrides module-level timeout
    import_whitelist=["numpy"],  # Overrides data.json import_whitelist
    starting_vars={"x": 10},  # Overrides data.json params["x"]
    names_for_user=["x"],
)

# This module-level timeout is ignored when ConfigObject is present
sandbox_timeout = 1.0
```

#### Complete Example

```python
from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import StudentFixture, FeedbackFixture
import pytest

# Comprehensive configuration
autograder_config = ConfigObject(
    # Execution settings
    sandbox_timeout=2.5,

    # Security: only allow scientific computing libraries
    import_whitelist=["numpy", "scipy", "matplotlib"],

    # Allow specific builtins for data processing
    builtin_whitelist=["len", "range", "sum", "min", "max", "sorted"],

    # Provide test data
    starting_vars={
        "input_data": [1, 2, 3, 4, 5],
        "multiplier": 2.5,
        "threshold": 10,
    },

    # Explicitly list what gets injected
    names_for_user=["input_data", "multiplier", "threshold"],
)

@pytest.mark.grading_data(name="Test Processing", points=10)
def test_data_processing(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    # All configuration from ConfigObject is automatically applied
    result = sandbox.query_function("process_data")

    assert len(result) > 0, "Result should not be empty"
    feedback.set_score(0.5)

    assert result == expected_output, "Incorrect processing result"
    feedback.set_score(1.0)
```

#### Validation

`ConfigObject` validates all parameters at creation time:

```python
# ✓ Valid configuration
config = ConfigObject(
    sandbox_timeout=2.0,
    import_whitelist=["numpy"],
)

# ✓ Valid: can combine whitelist and blacklist
config = ConfigObject(
    import_whitelist=["numpy", "matplotlib"],
    import_blacklist=["matplotlib.pyplot"]  # Block pyplot specifically
)

# ✗ Error: timeout must be positive
config = ConfigObject(sandbox_timeout=-1.0)  # ValueError

# ✗ Error: must use keyword arguments
config = ConfigObject(2.0)  # TypeError

# ✗ Error: names_for_user must contain strings
config = ConfigObject(names_for_user=[123, 456])  # ValueError
```

### Security: Import and Builtin Restrictions

Control which Python modules and builtin functions students can use in their code. This is crucial for:

- **Security**: Preventing access to file system, network, or system operations
- **Pedagogical constraints**: Requiring students to implement functionality from scratch
- **Resource management**: Blocking operations that consume excessive resources

#### Import Control

Restrict which Python modules students can import using whitelists or blacklists.

**Import Whitelist**: Only allow specific modules:

```python
# In server.py (PrairieLearn question)
def generate(data):
    data["params"]["import_whitelist"] = ["numpy", "math", "statistics"]
    # Only numpy, math, and statistics can be imported
    # Attempting to import any other module raises ImportError
```

**Import Blacklist**: Block specific modules while allowing all others:

```python
# In server.py
def generate(data):
    data["params"]["import_blacklist"] = ["os", "subprocess", "sys"]
    # os, subprocess, and sys cannot be imported
    # All other modules are allowed
```

**Combining Whitelist and Blacklist**: Use both for fine-grained control (blacklist checked first):

```python
# In server.py
def generate(data):
    # Allow scientific libraries but block specific dangerous submodules
    data["params"]["import_whitelist"] = ["numpy", "scipy", "matplotlib"]
    data["params"]["import_blacklist"] = ["matplotlib.pyplot"]  # Block pyplot even though matplotlib is allowed
    # Result: numpy, scipy, and matplotlib are allowed, but matplotlib.pyplot is blocked
```

**Example student code with import whitelist:**

```python
# data.json has "import_whitelist": ["numpy", "math"]

import numpy as np  # ✓ Allowed
import math  # ✓ Allowed
from numpy import array  # ✓ Allowed

import os  # ✗ ImportError: Module 'os' is not allowed to be imported
import pandas  # ✗ ImportError: Module 'pandas' is not allowed to be imported
```

**Example with import inside function:**

```python
def my_function():
    import os  # ✗ This will raise ImportError when the function is called
    return os.getcwd()
```

**Note**: Blacklist is checked first, then whitelist. If a whitelist is specified, only those modules (minus any in blacklist) can be imported. If only a blacklist is specified, those modules are blocked but all others are allowed.

#### Builtin Function Control

Python's builtin functions (like `open()`, `eval()`, `exec()`) are automatically restricted to a safe subset. The autograder provides **only safe builtins by default**, including:

- Standard types: `int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, `set`, `frozenset`
- Type checking: `isinstance`, `issubclass`, `type`
- Iteration: `iter`, `next`, `enumerate`, `zip`, `range`, `reversed`, `sorted`, `filter`, `map`
- Math: `abs`, `min`, `max`, `sum`, `round`, `pow`, `divmod`
- Conversion: `chr`, `ord`, `bin`, `oct`, `hex`, `hash`
- Common functions: `len`, `print`, `repr`, `getattr`, `hasattr`, `format`
- Python exceptions (for proper error handling)

**Dangerous builtins automatically blocked** include: `open`, `eval`, `exec`, `compile`, `__import__`, `input`, `exit`, `quit`, and others that could compromise security.

**Builtin Whitelist**: Grant access to additional builtin functions:

```python
# In server.py
def generate(data):
    data["params"]["builtin_whitelist"] = ["dict", "sorted", "enumerate"]
    # Students can now use dict(), sorted(), and enumerate() in addition to safe defaults
    # This is useful when you want to allow specific advanced builtins
```

**Example with builtin whitelist:**

```python
# data.json has "builtin_whitelist": ["dict"]

# Safe builtins work normally:
my_list = [1, 2, 3]  # ✓ list is safe by default
length = len(my_list)  # ✓ len is safe by default
print(length)  # ✓ print is safe by default

# Whitelisted builtins work:
my_dict = dict(a=1, b=2)  # ✓ dict is in whitelist

# Dangerous builtins are blocked:
f = open("file.txt")  # ✗ NameError: 'open' is not defined
result = eval("1+1")  # ✗ NameError: 'eval' is not defined
```

#### Combining Security Features

You can combine import and builtin restrictions for comprehensive control:

```python
# In server.py
def generate(data):
    # Allow only numpy and math imports
    data["params"]["import_whitelist"] = ["numpy", "math"]

    # Allow dict builtin for student convenience
    data["params"]["builtin_whitelist"] = ["dict"]

    # Now students can:
    # - Import numpy and math
    # - Use dict() plus safe builtins
    # - Cannot import other modules
    # - Cannot use dangerous builtins like open(), eval()
```

#### PrairieLearn Server.py Configuration

In your PrairieLearn question's `server.py`, add these parameters during the `generate()` step:

```python
import prairielearn as pl

def generate(data):
    # Set up question parameters
    data["params"]["n"] = 5
    data["params"]["A"] = pl.to_json(np.random.rand(5, 5))

    # Configure security restrictions
    data["params"]["import_whitelist"] = ["numpy", "numpy.linalg"]
    data["params"]["builtin_whitelist"] = ["dict", "sorted"]

    # Define variables accessible to student code
    data["params"]["names_for_user"] = [
        {"name": "n", "description": "Matrix dimension", "type": "integer"},
        {"name": "A", "description": "Input matrix", "type": "numpy array"}
    ]
```

These parameters are automatically passed to the autograder via `/grade/data/data.json` and enforced during student code execution.

#### Testing Import/Builtin Restrictions Locally

To test your restrictions in the test scenarios:

```python
# tests/test_student.py
import pytest
from pytest_prairielearn_grader.fixture import StudentFixture

@pytest.mark.grading_data(name="Test with restrictions", points=5)
def test_security(sandbox: StudentFixture) -> None:
    """Test that imports are properly restricted."""
    # If student code tries to import blocked modules,
    # the sandbox will raise an ImportError during initialization
    result = sandbox.query_function("safe_function", data)
    assert result == expected
```

```python
# data.json
{
  "params": {
    "import_whitelist": ["numpy", "math"],
    "builtin_whitelist": ["dict"],
    "names_for_user": [...]
  }
}
```

#### Common Use Cases

**1. Force students to implement algorithms from scratch:**

```python
# Require students to implement their own sorting
data["params"]["import_whitelist"] = []  # No imports allowed
data["params"]["builtin_whitelist"] = []  # No additional builtins beyond safe defaults
# Students must implement sorting without sorted() or external libraries
```

**2. Allow numerical computing but block system access:**

```python
# Scientific computing course
data["params"]["import_whitelist"] = ["numpy", "scipy", "matplotlib", "pandas"]
# Safe builtins are automatically enforced (no open, eval, etc.)
```

**3. Block dangerous operations explicitly:**

```python
# Block system and file operations
data["params"]["import_blacklist"] = ["os", "sys", "subprocess", "pathlib", "shutil"]
# All other imports allowed, but dangerous ones explicitly blocked
```

### Timeout Configuration

Control execution time limits for sandbox initialization and function calls to prevent infinite loops or slow student code.

**Important**: Timeouts apply to:

- **Sandbox initialization** (loading and executing student code at startup)
- **Function calls** via `sandbox.query_function()` with `query_timeout` parameter

Variable queries via `sandbox.query()` do not have timeouts since they're simple lookups.

#### Module-level Default Timeout

Set a default timeout for sandbox initialization in all tests in a file:

```python
# At the top of test_student.py (before imports)
initialization_timeout = 2.0  # 2 second timeout for initialization

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

    # This function call uses the default timeout (no per-function limit)
    result2 = sandbox.query_function("another_compute", data)
    assert result2 == expected_value2
```

**Using ConfigObject for timeouts:**

```python
from pytest_prairielearn_grader import ConfigObject

autograder_config = ConfigObject(
    sandbox_timeout=3.0,  # Sets initialization timeout
)

@pytest.mark.grading_data(name="Test", points=1)
def test_with_config_timeout(sandbox: StudentFixture) -> None:
    # Initialized with 3 second timeout from ConfigObject
    result = sandbox.query_function("process", query_timeout=1.0)
    assert result == expected
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
    output = sandbox.get_accumulated_stdout()
    assert "Hello, Alice!" in output, "Greeting message not found in output"
```

### Student-Friendly Feedback Mode

By default, when a test fails, students see the Python exception class name, a "failed with an
exception:" prefix, and (depending on the output level) a full traceback. This is useful for
debugging but can be intimidating for introductory-level students.

The **friendly** output level suppresses all traceback noise and shows only the human-readable
assertion message. Combine it with the built-in assertion helpers to produce clean, structured
feedback like:

```
Checking: add(2, 3)
Expected output: 5
Your code output: -1
The expected and actual output do not match.
```

#### Enabling Friendly Output

Apply `@pytest.mark.output(level="friendly")` to individual tests:

```python
import pytest
from pytest_prairielearn_grader.fixture import StudentFixture
from pytest_prairielearn_grader.assertions import assert_fn_equal, assert_equal

@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test addition", points=5)
def test_add(sandbox: StudentFixture) -> None:
    assert_fn_equal(sandbox, "add", args=(2, 3), expected=5)
```

Or apply it to every test in a file with a module-level `pytestmark`:

```python
import pytest

pytestmark = pytest.mark.output(level="friendly")
```

Or set it globally via `ConfigObject` (recommended for intro courses):

```python
from pytest_prairielearn_grader import ConfigObject

autograder_config = ConfigObject(
    output_level="friendly",  # All tests use friendly output by default
)
```

With the `ConfigObject` approach, individual tests can still override with
`@pytest.mark.output(level="traceback")` if needed.

**All output levels:**

| Level | Shows to student |
|-------|-----------------|
| `"none"` | Exception class name only (e.g., `AssertionError`) |
| `"message"` | Exception name + first line of message *(default when unset)* |
| `"traceback"` | Exception name + message + full traceback |
| `"friendly"` | Only the exception message text — no class name, no traceback |

#### Assertion Helpers

The `pytest_prairielearn_grader.assertions` module provides helpers that produce the
structured "Checking / Expected / Your output" messages. They raise `AssertionError`
with the formatted message, which the friendly output level then shows as-is.

**`assert_equal(actual, expected, *, msg=None, description=None)`**

Compare two values for equality:

```python
value = sandbox.query("x")
assert_equal(value, 42, description="variable 'x'")
# On failure:
#   Checking: variable 'x'
#   Expected output: 42
#   Your code output: 99
#   The expected and actual output do not match.
```

**`assert_approx_equal(actual, expected, *, rtol=1e-5, atol=1e-8, msg=None, description=None)`**

Compare numeric values with tolerance:

```python
result = sandbox.query_function("compute_pi")
assert_approx_equal(result, 3.14159, rtol=1e-3, description="compute_pi()")
```

**`assert_true(condition, *, msg=None)` / `assert_false(condition, *, msg=None)`**

Check boolean conditions with a clean message:

```python
result = sandbox.query_function("is_valid", data)
assert_true(result, msg="Expected is_valid() to return True for valid input.")
```

**`assert_fn_equal(sandbox, func_name, *, args=(), kwargs=None, expected, msg=None, query_timeout=1.0)`**

Call a student function and compare its return value — the most common helper. It
automatically generates the description from the function call:

```python
assert_fn_equal(sandbox, "add", args=(2, 3), expected=5)
# On failure:
#   Checking: add(2, 3)
#   Expected output: 5
#   Your code output: -1
#   The expected and actual output do not match.
```

**`assert_fn_approx_equal(sandbox, func_name, *, args=(), kwargs=None, expected, rtol=1e-5, atol=1e-8, msg=None, query_timeout=1.0)`**

Same as `assert_fn_equal` but uses approximate comparison:

```python
assert_fn_approx_equal(sandbox, "compute_area", args=(3.0,), expected=28.274, rtol=1e-2)
```

#### Combining with Partial Credit

Friendly mode works seamlessly with `FeedbackFixture`:

```python
@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Multi-step", points=10)
def test_multi_step(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    # Step 1: basic check
    assert_fn_equal(sandbox, "initialize", expected=0)
    feedback.set_score(0.5)

    # Step 2: harder check — if this fails, student keeps 50%
    assert_fn_equal(sandbox, "compute", args=(10,), expected=100)
    feedback.set_score(1.0)
```

#### When to Use Friendly Mode

- **Introductory courses**: Students who haven't seen Python tracebacks benefit from simpler messages.
- **Lite image questions**: Pairs well with the `:lite` Docker image for intro CS courses.
- **Standardized feedback**: When you want all failure messages to follow a consistent format.

For advanced courses, the default output levels (`message` or `traceback`) may be more appropriate
since students can learn from reading full tracebacks.

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

In your PrairieLearn question's `info.json`, specify the grader image:

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

### Choosing an Image

Two image variants are published. Pick the smallest one that includes what your question needs — a smaller image means faster cold-start pull times and a reduced security surface.

| Tag       | Size (approx.) | Includes                                                                                                                                                                                 | Best for                                                                                        |
| --------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `:latest` | ~400–500 MB    | Full scientific stack: `numpy`, `pandas`, `scipy`, `matplotlib` + `matplotcheck2`, `seaborn`, `bokeh`, `scikit-learn`, `scikit-image`, `sympy`, `networkx`, `nltk`, `nbformat`, and more | Any course that needs scientific computing, data science, plotting, or Jupyter notebook grading |
| `:lite`   | ~60–80 MB      | Grader core only: `pytest-prairielearn-grader`, `Pygments`, `beautifulsoup4`, `defusedxml`, `requests`                                                                                   | Introductory CS courses where student code uses only the Python standard library                |

To use the lite image, change the `image` field:

```json
"externalGradingOptions": {
  "enabled": true,
  "image": "eliotwrobson/grader-python-pytest:lite",
  "timeout": 30
}
```

> **Note:** If a student's code imports a package that isn't present in the image (e.g., `numpy` in `:lite`), it will raise an `ImportError` and the test will fail with an exception. Make sure the image you choose contains everything both your test code and the expected student solution require.

Pinned version tags (e.g., `:v1.2.3` and `:v1.2.3-lite`) are also published alongside each release if you need a reproducible build.

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
8. **Configure security restrictions**: Use `import_whitelist` and `builtin_whitelist` in `server.py`
   to control what modules and functions students can access, preventing security issues and
   enforcing pedagogical constraints

---

## Ungradable Submission Detection

When student code has a **SyntaxError** (e.g., missing colons, unmatched brackets, bad indentation),
the grader automatically marks the submission as **ungradable**. This means:

- The student does **not** lose a grading attempt
- They see a clear message: *"Your code could not be parsed. Please fix the syntax errors and resubmit."*
- The `format_errors` field in results contains the specific error

This is especially useful for introductory courses where students may accidentally submit code
with trivial syntax mistakes.

### How It Works

The grader detects `SyntaxError` during sandbox initialization (when `compile()` is called on
student code). Instead of failing all tests with 0%, it produces:

```json
{
  "gradable": false,
  "format_errors": ["SyntaxError: invalid syntax (student_code.py, line 3)"],
  "message": "Your code could not be parsed. Please fix the syntax errors and resubmit.",
  "tests": [...]
}
```

PrairieLearn's external grading framework handles the `"gradable": false` field — the student's
submission panel shows the format errors without consuming an attempt.

### Disabling Ungradable Detection

If you prefer syntax errors to score 0% (counting as a normal attempt), opt out in your config:

```python
from pytest_prairielearn_grader import ConfigObject

autograder_config = ConfigObject(
    syntax_errors_ungradable=False,  # SyntaxError → 0% instead of ungradable
)
```

### Grader-Side Errors

The grader also detects when **test files themselves** fail to collect (e.g., import errors in
your test code, missing dependencies). These are marked as ungradable with a message directing
course staff to check the logs — students are never penalized for grader bugs.

---

## Test Case Visibility

You can mark individual test cases with a `visibility` field that is forwarded to the results JSON.
This allows the PrairieLearn platform element to decide what to show students based on timing or
instructor preference.

```python
@pytest.mark.grading_data(name="Basic test", points=2, visibility="visible")
def test_basic(sandbox: StudentFixture) -> None:
    assert_fn_equal(sandbox, "add", args=(1, 2), expected=3)


@pytest.mark.grading_data(name="Hidden edge case", points=3, visibility="hidden")
def test_edge_case(sandbox: StudentFixture) -> None:
    """Student won't see this test's result."""
    assert_fn_equal(sandbox, "add", args=(-1, -2), expected=-3)


@pytest.mark.grading_data(name="Post-deadline test", points=5, visibility="after_due_date")
def test_advanced(sandbox: StudentFixture) -> None:
    """Only shown after the assignment deadline."""
    assert_fn_equal(sandbox, "solve", args=(complex_input,), expected=complex_output)
```

**Supported visibility values** (aligned with [Gradescope conventions](https://gradescope-autograders.readthedocs.io/en/latest/specs/)):

| Value | Behavior |
|-------|----------|
| `"visible"` | Always shown *(default when omitted)* |
| `"hidden"` | Never shown to students |
| `"after_due_date"` | Shown after the assignment's due date |
| `"after_published"` | Shown when grades are explicitly published |

> **Note:** The grader simply forwards the `visibility` field in the per-test results JSON.
> Rendering logic (hiding/showing) is handled by the PrairieLearn platform element, not the grader.

---

## Jupyter Notebook Grading

PrairieLearn supports JupyterLab as a workspace environment
(`prairielearn/workspace-jupyterlab-python`), and students commonly submit `.ipynb` files from
other IDE-based workspaces too. The autograder handles notebooks natively: it extracts the Python
source from the relevant code cells, concatenates them into a single script, and executes that
script in the sandbox exactly like a normal `.py` submission. Every fixture, query method, and
partial credit feature works identically — no special test-writing API is needed.

> **Optional dependency**: Notebook support requires `nbformat`.
> Install it with `pip install 'pytest-prairielearn-grader[notebook]'`.
> The core package deliberately does **not** depend on `nbformat` so that grader images without
> Jupyter installed remain lightweight.

### Telling the Grader to Look for Notebooks

The only required change is updating `student_code_pattern` in your `ConfigObject` to match
`.ipynb` files:

```python
from pytest_prairielearn_grader import ConfigObject

autograder_config = ConfigObject(
    student_code_pattern="student_code*.ipynb",
    sandbox_timeout=5.0,
)
```

All code cells are extracted in notebook order and concatenated, so functions and variables
defined in earlier cells are available in later ones — exactly as they are when the notebook is
executed top-to-bottom in JupyterLab.

### Filtering Cells with `notebook_cell_tag`

Real student notebooks often contain scratch work, exploratory plots, and print statements that
you don't want to run during grading. Use `notebook_cell_tag` to restrict extraction to only the
cells the student intended to submit:

```python
autograder_config = ConfigObject(
    student_code_pattern="student_code*.ipynb",
    notebook_cell_tag="#grade",   # only cells whose first line starts with "#grade"
    sandbox_timeout=5.0,
)
```

A code cell is included if and only if its **first non-empty line starts with the tag string**.
All other cells — including cells that would raise errors or produce unwanted side effects — are
silently skipped.

**Student notebook example:**

```python
# Cell 1 — scratch work (NOT included, no tag)
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
plt.show()

# Cell 2 — graded solution (included, starts with #grade)
#grade
def solve(A, b):
    import numpy as np
    return np.linalg.solve(A, b)

# Cell 3 — another graded cell (included, starts with #grade)
#grade
x = solve([[1, 0], [0, 2]], [3, 8])
```

Only cells 2 and 3 are extracted and run. Cell 1 is completely ignored, so the `plt.show()` call
never reaches the sandbox.

> `notebook_cell_tag=None` (the default) includes **all** code cells. Use this when you control
> the notebook template and don't need students to tag their answers.

### `info.json` for a JupyterLab Notebook Question

```json
{
  "uuid": "...",
  "title": "Linear Algebra — Notebook Submission",
  "topic": "...",
  "tags": ["..."],
  "type": "v3",
  "singleVariant": true,
  "gradingMethod": "External",
  "workspaceOptions": {
    "image": "prairielearn/workspace-jupyterlab-python",
    "port": 8080,
    "home": "/home/user",
    "gradedFiles": ["notebook.ipynb"]
  },
  "externalGradingOptions": {
    "enabled": true,
    "image": "eliotwrobson/grader-python-pytest:latest",
    "timeout": 60
  }
}
```

> Set `singleVariant: true` so the workspace — and any work saved in it — persists across
> multiple submission attempts.

### Writing Tests for Notebook Submissions

Tests are written the same way as for any other submission type. There is nothing
notebook-specific in the test file beyond `student_code_pattern` (and optionally
`notebook_cell_tag`) in the `ConfigObject`:

```python
import pytest
import numpy as np

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import FeedbackFixture, StudentFixture

autograder_config = ConfigObject(
    student_code_pattern="notebook*.ipynb",
    notebook_cell_tag="#grade",
    sandbox_timeout=10.0,
)


@pytest.mark.grading_data(name="solve() is correct", points=5)
def test_solve(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    A = [[2, 1], [1, 3]]
    b = [5, 10]
    feedback.set_score(0.0)

    result = sandbox.query_function("solve", A, b)
    feedback.set_score(0.5)

    expected = np.linalg.solve(A, b)
    assert np.allclose(result, expected), f"Expected {expected}, got {result}"
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="result variable is set", points=2)
def test_result_variable(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.0)
    x = sandbox.query("x")
    assert x is not None, "Variable 'x' was not defined"
    feedback.set_score(1.0)
```

### ConfigObject Settings for Notebooks

| Parameter              | Type          | Default              | Description                                                                                       |
| ---------------------- | ------------- | -------------------- | ------------------------------------------------------------------------------------------------- |
| `student_code_pattern` | `str`         | `"student_code*.py"` | Glob pattern — change to `"*.ipynb"` or `"notebook*.ipynb"` to match notebook files.              |
| `notebook_cell_tag`    | `str \| None` | `None`               | First-line tag for cell filtering. `None` = all cells. Cannot be used with `workspace_mode=True`. |
| `sandbox_timeout`      | `float`       | `1.0`                | Increase to 5–15 s for notebooks with heavy imports or large cell computations.                   |

### Production vs. Local Development

In production PrairieLearn, the submitted `gradedFiles` end up in `/grade/student/`. The grader
searches for matching files there automatically. For local development, place the notebook in the
scenario data directory next to your test file:

```
questions/my_notebook_question/
└── tests/
    ├── test_student.py
    └── test_student/
        └── notebook.ipynb     # local stand-in for the student's submission
```

---

## Workspace Grading

PrairieLearn workspace questions give students a full IDE (VS Code, JupyterLab, etc.) running in a
browser. When a student clicks **Submit**, PrairieLearn copies the files listed in `gradedFiles`
out of their workspace container and into `/grade/student/`, preserving all directory structure.

The `workspace_sandbox` fixture is designed specifically for this use case. Unlike the regular
`sandbox` fixture (which `exec`s a single file), the workspace fixture adds the student's project
directory to `sys.path` and lets tests interact with the project using Python's normal import
machinery — exactly the same way you would test a local Python package.

### Why a separate fixture?

|              | `sandbox`                          | `workspace_sandbox`                      |
| ------------ | ---------------------------------- | ---------------------------------------- |
| Student code | Single file                        | Multi-file project                       |
| Startup      | `exec` the file                    | Set `sys.path`, import on demand         |
| Querying     | Flat variable/function names       | Dotted module paths (`"models.predict"`) |
| Use case     | `pl-file-editor`, `pl-file-upload` | Workspace questions                      |

### File Structure

For a PrairieLearn workspace question the grader sees this layout at runtime:

```
/grade/
├── data/
│   └── data.json          # question parameters
├── student/               # gradedFiles copied from student's workspace
│   ├── calculator.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py
│   └── main.py
└── tests/                 # copies of your question's tests/ directory
    ├── setup_code.py      # (optional)
    └── test_student.py
```

For **local development**, mirror this by creating a `student/` sub-directory next to your test
file. The fixture finds it automatically without any configuration:

```
questions/my_workspace_question/
├── info.json
├── question.html
└── tests/
    ├── test_student.py        # your test file
    ├── setup_code.py          # (optional)
    └── test_student/          # ← mirrors the data directory layout
        └── student/           # ← local stand-in for /grade/student
            ├── calculator.py
            └── utils/
                ├── __init__.py
                └── helpers.py
```

### `info.json` Configuration

```json
{
  "uuid": "...",
  "title": "Calculator Project",
  "topic": "...",
  "tags": ["..."],
  "type": "v3",
  "singleVariant": true,
  "gradingMethod": "External",
  "workspaceOptions": {
    "image": "prairielearn/workspace-vscode-python",
    "port": 8080,
    "home": "/home/user",
    "gradedFiles": ["calculator.py", "utils/*.py", "utils/__init__.py"]
  },
  "externalGradingOptions": {
    "enabled": true,
    "image": "eliotwrobson/grader-python-pytest:latest",
    "timeout": 30
  }
}
```

**Key points:**

- `gradedFiles` controls which files are copied from the workspace into `/grade/student/`.
  Use glob patterns (`utils/*.py`) to capture whole directories.
- `singleVariant: true` prevents the workspace from resetting between attempts.

### Writing Tests

Use `workspace_sandbox` and query student code with **dotted module paths**:

```python
from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import WorkspaceFixture
import pytest

autograder_config = ConfigObject(
    workspace_mode=True,
    sandbox_timeout=10.0,
)

@pytest.mark.grading_data(name="Add two numbers", points=2)
def test_add(workspace_sandbox: WorkspaceFixture) -> None:
    result = workspace_sandbox.query_function("calculator.add", 3, 4)
    assert result == 7


@pytest.mark.grading_data(name="Clamp from sub-package", points=2)
def test_clamp(workspace_sandbox: WorkspaceFixture) -> None:
    result = workspace_sandbox.query_function("utils.helpers.clamp", 15, 0, 10)
    assert result == 10


@pytest.mark.grading_data(name="Module-level constant", points=1)
def test_constant(workspace_sandbox: WorkspaceFixture) -> None:
    pi = workspace_sandbox.query("calculator.PI_APPROX")
    assert abs(pi - 3.14159) < 1e-5
```

The dotted path is split on the **last dot**: `"calculator.add"` imports the module `calculator`
and calls `getattr(calculator, "add")`. This means:

| Query string                | Module imported   | Attribute retrieved |
| --------------------------- | ----------------- | ------------------- |
| `"calculator.add"`          | `calculator`      | `add`               |
| `"utils.helpers.clamp"`     | `utils.helpers`   | `clamp`             |
| `"models.nn.Model.predict"` | `models.nn.Model` | `predict`           |

### Querying Variables vs. Functions

Both `query` and `query_function` understand dotted paths:

```python
# Query a module-level variable
eps = workspace_sandbox.query("utils.helpers.EPSILON")

# Query a class defined in a module
result = workspace_sandbox.query_function("models.Classifier.predict", X_test)

# query_function_raw — inspects the full response without raising
response = workspace_sandbox.query_function_raw("calculator.divide", 1, 0)
assert response["status"] == "exception"
assert response["exception_name"] == "ValueError"
```

### Optional: Entry-Point Execution

Some workspace questions have a `main.py` that sets up global state before tests run. Use
`workspace_exec_entry` to `exec` it at sandbox startup:

```python
autograder_config = ConfigObject(
    workspace_mode=True,
    workspace_exec_entry="main.py",  # exec'd from workspace root at startup
    sandbox_timeout=15.0,
)

# Now the sandbox namespace includes everything main.py defined at module level
def test_global_state(workspace_sandbox: WorkspaceFixture) -> None:
    db = workspace_sandbox.query("database")  # flat name - set by main.py via exec
    assert db is not None
```

Without `workspace_exec_entry` (the default), no file is executed at startup and all access
goes through the import machinery.

### ConfigObject Settings for Workspaces

| Parameter               | Type                | Default      | Description                                                                                                   |
| ----------------------- | ------------------- | ------------ | ------------------------------------------------------------------------------------------------------------- |
| `workspace_mode`        | `bool`              | `False`      | Enable workspace grading mode                                                                                 |
| `workspace_student_dir` | `str \| None`       | `None`       | Path to student project root. Defaults to `student/` next to tests. Set to `"/grade/student"` for production. |
| `workspace_exec_entry`  | `str \| None`       | `None`       | Relative path (from workspace root) to an entry-point file to `exec` at startup.                              |
| `sandbox_timeout`       | `float`             | `1.0`        | Timeout for sandbox startup (increase for larger projects).                                                   |
| `import_whitelist`      | `list[str] \| None` | `None`       | Allowed imports. `None` = allow all.                                                                          |
| `import_blacklist`      | `list[str] \| None` | default list | Blocked imports.                                                                                              |

### Production vs. Local Development

The `workspace_student_dir` path differs between environments:

```python
# Production (running on PrairieLearn): set an absolute path
autograder_config = ConfigObject(
    workspace_mode=True,
    workspace_student_dir="/grade/student",
)

# Local dev: omit the field — the fixture finds student/ automatically
autograder_config = ConfigObject(
    workspace_mode=True,
    # workspace_student_dir defaults to student/ next to your test file
)
```

A common pattern is to use an environment variable so one config works in both environments:

```python
import os

autograder_config = ConfigObject(
    workspace_mode=True,
    workspace_student_dir=os.environ.get("STUDENT_DIR"),  # None → auto-detect locally
    sandbox_timeout=10.0,
)
```

### Security Notes

- The default `import_blacklist` (`["os", "sys", "subprocess", "pathlib", "shutil"]`) is
  applied in workspace mode too. If the student's project legitimately uses `pathlib` for
  internal file operations, add it to `import_whitelist` explicitly.
- `sys.path` inside the subprocess is modified to include `workspace_student_dir`, so all
  relative imports within the project work naturally.
- Each call to `workspace_sandbox.query_function` runs in the same subprocess, so module-level
  state (caches, open files) persists across calls within a test — exactly like normal Python.

### Complete Example

**`tests/test_student.py`:**

```python
import pytest

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import FeedbackFixture, WorkspaceFixture

autograder_config = ConfigObject(
    workspace_mode=True,
    sandbox_timeout=10.0,
    import_whitelist=["math", "statistics"],
)


@pytest.mark.grading_data(name="add() returns correct value", points=3)
def test_add(workspace_sandbox: WorkspaceFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.0)

    response = workspace_sandbox.query_function_raw("calculator.add", 2, 3)
    assert response["status"] != "not_found", "calculator.add is not defined"
    feedback.set_score(0.5)

    assert response["status"] == "success", (
        f"calculator.add raised {response['exception_name']}: {response['exception_message']}"
    )
    feedback.set_score(0.8)

    assert response["value"] == 5, f"Expected 5, got {response['value']}"
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="divide() raises ValueError on zero", points=2)
def test_divide_guard(workspace_sandbox: WorkspaceFixture) -> None:
    response = workspace_sandbox.query_function_raw("calculator.divide", 10, 0)
    assert response["status"] == "exception", "divide() should raise on zero denominator"
    assert response["exception_name"] == "ValueError"


@pytest.mark.grading_data(name="PI_APPROX constant exists", points=1)
def test_constant(workspace_sandbox: WorkspaceFixture) -> None:
    pi = workspace_sandbox.query("calculator.PI_APPROX")
    assert isinstance(pi, float), "PI_APPROX should be a float"
    assert abs(pi - 3.14) < 0.01
```

**Student workspace (`student/calculator.py`):**

```python
PI_APPROX = 3.14159

def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```
