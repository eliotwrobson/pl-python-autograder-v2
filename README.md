# pytest-prairielearn-grader

A pytest plugin for autograding Python code in [PrairieLearn](https://www.prairielearn.com/). Student code runs in isolated subprocess sandboxes with configurable security restrictions, timeouts, and detailed feedback.

## Installation

```bash
pip install pytest-prairielearn-grader
```

For notebook grading support:

```bash
pip install pytest-prairielearn-grader[notebook]
```

## Quick Start

See [quick_start.md](quick_start.md) for a full tutorial with PrairieLearn integration examples.

## Key Features

### Sandboxed Execution

Student code runs in a separate subprocess via Unix sockets, providing:
- Security isolation from the grading harness
- Import whitelist/blacklist enforcement
- Builtin function restrictions
- Timeout enforcement
- Privilege dropping (Unix)

### Student-Friendly Feedback Mode

Control how much information students see when their code fails. Use `@pytest.mark.output(level=...)` per test, or set `output_level` globally in your `ConfigObject`:

```python
from pytest_prairielearn_grader import ConfigObject

autograder_config = ConfigObject(
    output_level="friendly",  # Global default for all tests
)
```

**Output levels:**
| Level | Shows |
|-------|-------|
| `"none"` | Exception class name only (e.g., `AssertionError`) |
| `"message"` | Exception name + first line of message *(default)* |
| `"traceback"` | Full exception with traceback |
| `"friendly"` | Only the exception message text — no class name, no traceback |

Per-test markers override the global setting:

```python
@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test add", points=5)
def test_add(sandbox: StudentFixture) -> None:
    assert_fn_equal(sandbox, "add", args=(2, 3), expected=5)
```

### Assertion Helpers

Student-friendly assertion functions that produce clean, readable failure messages:

```python
from pytest_prairielearn_grader.assertions import assert_equal, assert_fn_equal

@pytest.mark.output(level="friendly")
@pytest.mark.grading_data(name="Test calculation", points=5)
def test_calc(sandbox: StudentFixture) -> None:
    # Produces: "Checking: add(2, 3)\nExpected output: 5\nYour code output: 4\n..."
    assert_fn_equal(sandbox, "add", args=(2, 3), expected=5)
```

Available helpers:
- `assert_equal(actual, expected)` — compare any values
- `assert_approx_equal(actual, expected, rtol=1e-5, atol=1e-8)` — numeric comparison
- `assert_fn_equal(sandbox, func_name, args=..., expected=...)` — call + compare
- `assert_fn_approx_equal(sandbox, func_name, args=..., expected=...)` — call + approx compare
- `assert_true(condition)` / `assert_false(condition)` — boolean checks

### Ungradable Submission Detection

When student code has a `SyntaxError`, the submission is automatically marked as **ungradable** (`"gradable": false` in results). This means the student does not lose a grading attempt and sees a clear error message.

```python
# Opt out if you want syntax errors to score 0 instead:
autograder_config = ConfigObject(
    syntax_errors_ungradable=False,
)
```

The grader also detects test collection failures (grader-side errors) and marks those as ungradable with a message for course staff.

### Test Case Visibility

Forward-compatible support for controlling which test results are shown to students. Add a `visibility` field to `grading_data`:

```python
@pytest.mark.grading_data(name="Hidden edge case", points=3, visibility="hidden")
def test_edge_case(sandbox: StudentFixture) -> None:
    result = sandbox.query_function("solve", edge_input)
    assert result == expected
```

The `visibility` value is passed through to the results JSON per test. Supported values (aligned with [Gradescope conventions](https://gradescope-autograders.readthedocs.io/en/latest/specs/)):
- `"visible"` — always shown (default behavior when omitted)
- `"hidden"` — never shown to students
- `"after_due_date"` — shown after the due date
- `"after_published"` — shown when grades are published

> **Note:** Rendering of visibility is handled by the PrairieLearn platform element, not the grader itself. The grader simply forwards the field.

### ConfigObject

Type-safe, immutable configuration for all autograder settings:

```python
from pytest_prairielearn_grader import ConfigObject

autograder_config = ConfigObject(
    sandbox_timeout=2.0,
    import_whitelist=["numpy", "math"],
    builtin_whitelist=["len", "range", "sum"],
    output_level="friendly",
    syntax_errors_ungradable=True,
    starting_vars={"coefficient": 10},
    names_for_user=["coefficient"],
)
```

See [ConfigObject documentation](src/pytest_prairielearn_grader/config.py) for all options.

## Results JSON Format

The autograder produces `autograder_results.json` with the following structure:

```json
{
    "gradable": true,
    "score": 0.85,
    "tests": [
        {
            "test_id": "test_student.py::test_function[student_code]",
            "name": "Test Function",
            "max_points": 5,
            "points": 5.0,
            "points_frac": 1.0,
            "outcome": "passed",
            "message": ""
        }
    ]
}
```

When a submission is ungradable:

```json
{
    "gradable": false,
    "format_errors": ["SyntaxError: invalid syntax (line 3)"],
    "message": "Your code could not be parsed. Please fix the syntax errors and resubmit.",
    "tests": []
}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
uv run pytest tests -p no:prairielearn-grader

# Run specific scenario
uv run pytest tests/test_autograder_scenarios.py -k "test_friendly_feedback" -v

# Format
ruff format src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type check
mypy src/
```

## Docker Images

- `eliotwrobson/grader-python-pytest:latest` — full image with numpy, pandas, matplotlib, sympy
- `eliotwrobson/grader-python-pytest:lite` — minimal image with core dependencies only

## Related Issues

- [PrairieLearn #11137 — Redesign of Python Autograder](https://github.com/PrairieLearn/PrairieLearn/issues/11137)
- [PrairieLearn #13739 — New Python autograder tracking issue](https://github.com/PrairieLearn/PrairieLearn/issues/13739)
- [PrairieLearn #12113 — Customizable external grader test case visibility](https://github.com/PrairieLearn/PrairieLearn/issues/12113)
- [PrairieLearn #9636 — Mark submission as ungradable](https://github.com/PrairieLearn/PrairieLearn/issues/9636)
- [PrairieLearn #14143 — OOM/SIGKILL handling](https://github.com/PrairieLearn/PrairieLearn/issues/14143)
