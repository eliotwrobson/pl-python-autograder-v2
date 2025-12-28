# Pytest PrairieLearn Grader - AI Coding Agent Instructions

## Project Overview

**pytest-prairielearn-grader** is a pytest plugin for autograding Python code, designed for integration with PrairieLearn. It executes student code in isolated sandbox environments and provides detailed feedback and scoring.

**Key Architecture**: Test harnesses run in the main process, while student code executes in separate subprocesses via Unix sockets, enabling security isolation and timeout enforcement.

## Core Components

### 1. Sandboxed Execution (`StudentFixture`)

- **Location**: [src/pytest_prairielearn_grader/fixture.py](src/pytest_prairielearn_grader/fixture.py)
- **How it works**: Tests use the `sandbox` or `module_sandbox` fixtures to interact with student code
- **Key methods**:
  - `sandbox.query(var_name)` - retrieve variables from student code
  - `sandbox.query_function(func_name, *args, **kwargs)` - execute functions in student code
  - `sandbox.get_stdout()` - capture student code output
- **Important**: Student code runs in subprocess via `_student_code_runner.py`; results are JSON-serialized through socket communication

### 2. Student Code Runner Process

- **Location**: [src/pytest_prairielearn_grader/\_student_code_runner.py](src/pytest_prairielearn_grader/_student_code_runner.py)
- **Role**: Runs in isolated subprocess, executes student code, enforces security/timeouts
- **Socket Protocol**: Receives JSON requests (setup, query, function calls), returns JSON responses
- **Security Features**:
  - Import whitelist/blacklist enforcement
  - Builtin function restrictions
  - Privilege dropping (Unix only)
  - Timeout enforcement via asyncio

### 3. Test Execution & Grading

- **Location**: [src/pytest_prairielearn_grader/plugin.py](src/pytest_prairielearn_grader/plugin.py)
- **Custom Pytest Plugin**: Registers fixtures and collects grading metadata
- **Fixtures**:
  - `sandbox` (function-scoped): Isolated per test, supports parameterization
  - `module_sandbox` (module-scoped): Reused across module, single student code only
  - `feedback` (function-scoped): Manages partial credit and messages
  - `data_json` (module-scoped): Loads test parameters from `data.json`

### 4. Test Scenario Structure

- **Location**: [tests/scenario_root/](tests/scenario_root/)
- **Pattern**: Each test scenario has a directory `test_*` containing:
  - `scenario.py` - test code using autograder fixtures
  - `data.json` - parameters passed to student code
  - `setup_code.py` - initialization code for student sandbox
  - `student_code_*.py` - various student code variants for testing
  - `expected_outcome.json` - expected pytest results for validation

## Critical Developer Workflows

### Running Tests

```bash
# Run all scenario tests
pytest tests/test_autograder_scenarios.py -v

# Run specific scenario
pytest tests/test_autograder_scenarios.py::test_autograder_scenario_with_pytester[test_quiz_2_1] -v

# Run with output capture disabled (see prints)
pytest tests/test_autograder_scenarios.py -s
```

### Running a Single Scenario Directly

```bash
# Copy scenario files, run: cd tests/scenario_root/test_quiz_2_1 && pytest test_quiz_2_1.py -v
```

### Linting & Type Checking

```bash
# Format with ruff
ruff format src/ tests/

# Check with ruff
ruff check src/ tests/ --fix

# Type check
mypy src/
```

## Key Design Patterns & Conventions

### 1. Grading Data Marks

```python
@pytest.mark.grading_data(name="Test Name", points=5, include_stdout_feedback=False)
def test_something(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    # name: displayed to student
    # points: max points for this test
    # include_stdout_feedback: whether to capture student stdout
```

### 2. Partial Credit Pattern

```python
def test_multi_step(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.5)  # 50% credit if next assert fails
    assert step_one_passes()  # if fails here, student gets 50%

    feedback.set_score(0.8)   # 80% credit if next assert fails
    assert step_two_passes()   # if fails here, student gets 80%

    feedback.set_score(1.0)   # 100% if all pass
```

### 3. Function Query Pattern

```python
# In test:
result = sandbox.query_function("student_func", arg1, arg2, timeout=5)

# Query returns StudentFunctionResponse with:
# - status: SUCCESS, EXCEPTION, TIMEOUT, NOT_FOUND
# - value: JSON-deserialized return value
# - stdout/stderr: captured output
# - exception_name/message/traceback: if exception occurred
```

### 4. Data Configuration Pattern

```python
# data.json structure:
{
  "params": {
    "sin_coefficient": 2.5,
    "cos_coefficient": 1.3,
    "names_for_user": [
      {"name": "sin_coefficient", "type": "float", "description": "..."},
      {"name": "array_data", "type": "ndarray", "description": "..."}
    ],
    "import_whitelist": ["numpy", "math"],
    "builtin_whitelist": ["len", "range", "sum"]
  }
}

# In setup_code.py, define variables; they're injected if in names_for_user
```

### 5. Serialization

- Uses `dill` for complex Python objects (numpy arrays, pandas DataFrames, matplotlib plots)
- Base64-encoded in JSON for transport
- See [src/pytest_prairielearn_grader/json_utils.py](src/pytest_prairielearn_grader/json_utils.py) for custom serialization

## Important Integration Points

### PrairieLearn Integration

- Test file must be named `tests/test_*.py`
- Student code file is expected as `student_code.py` (configurable via `student_code_pattern` global variable)
- Output is collected as JSON with test results, scores, and messages
- Exit codes: 0 = success, non-zero = test execution failures

### Command Line Options

- `--worker-username`: Identifies which student submission is running (used for privilege dropping)
- `--output-json`: Path where JSON results are written
- Custom pytest options (e.g., `-v`, `-s`) work normally

## Common Pitfalls & Solutions

| Issue                                      | Solution                                                                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------- |
| "Student code server process terminated"   | Check for unhandled exceptions in setup_code or timeout too short                     |
| Function not found errors                  | Ensure function is defined in student_code.py, not just setup_code.py                 |
| Timeout errors on network tests            | Increase timeout via `@pytest.mark.sandbox_timeout(N)`                                |
| Serialization fails                        | Use `dill`-compatible types (check json_utils.py for supported types)                 |
| Module sandbox with multiple student codes | Use regular `sandbox` fixture instead; module_sandbox requires single student_code.py |

## Files to Reference When Extending

- **Adding new fixture**: [src/pytest_prairielearn_grader/plugin.py#L195-L210](src/pytest_prairielearn_grader/plugin.py#L195-L210)
- **New query type**: [src/pytest_prairielearn_grader/utils.py](src/pytest_prairielearn_grader/utils.py) (define TypedDict) + [src/pytest_prairielearn_grader/\_student_code_runner.py](src/pytest_prairielearn_grader/_student_code_runner.py) (handle message)
- **Custom marks**: [src/pytest_prairielearn_grader/utils.py#L5-L20](src/pytest_prairielearn_grader/utils.py#L5-L20) (define enum) + [src/pytest_prairielearn_grader/plugin.py](src/pytest_prairielearn_grader/plugin.py) (use in marker parsing)
- **Test examples**: [tests/scenario_root/](tests/scenario_root/) (all subdirectories follow same pattern)

## Python Version & Dependencies

- **Minimum Python**: 3.11
- **Key dependencies**: pytest, dill, prettytable
- **Dev dependencies**: numpy, pandas, mypy, ruff, matplotlib, sympy
- **Code style**: Ruff with specific rules configured in pyproject.toml (140 char line length, specific linters enabled)
