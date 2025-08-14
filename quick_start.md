# Quick start guide

This is a quick start guide for using the new Python autograder. This will be
go over a simple example in PL to explain the basic usage and functionality. This
will be using the grader image `eliotwrobson/grader-python-v2`. This grader image
is powered by the autograder pytest extension code here.

The following discussion is based on the converted example question here:
https://github.com/PrairieLearn/PrairieLearn/pull/12603

## File structure

The required file structure for a PL question using this grader image is below

```
- info.json
- question.html
- tests
  ├── initial_code.py
  ├── setup_code.py
  └── test_student.py
```

Importantly, the file editor element in question.html should have the file name set to
`student_code.py`. The file name read by the autograder will be `student_code.py`. This
can be changed by setting `student_code_pattern = "file_name.py"` at the global scope of
the `test_student.py` file. This filename is hardcoded.

## `setup_code.py`

```python
import numpy as np
import numpy.linalg as la


def not_allowed(*args, **kwargs):
    raise RuntimeError("Usage of this function is not allowed in this question.")


# set up parameters
n = np.random.randint(4, 16)

# generate a random full-rank matrix by generating a random eigenvector basis and nonzero eigenvalues
X = la.qr(np.random.random_sample((n, n)))[0]
D = np.diag(np.random.random_sample(n) * 10 + 1)
A = X.T @ D @ X

b = np.random.random(n)

la.inv = not_allowed
la.pinv = not_allowed
```

Inside the setup code, you are allowed to define different variables for use by the student
submission. Importantly, for a variable to be accessible in the student submission, the variable name must be included in the `names_for_user` entry in the params dictionary. This
is using the same format that is set by the `pl-external-grader-variables` element.

In this example, only `A`, `b`, and `n` are included in the `names_for_user` entry.

## `test_student.py`

```python
import numpy as np
import numpy.linalg as la
import pytest
from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="x", points=1)
def test_array_all_close(sandbox: StudentFixture) -> None:
    correct_x = la.solve(sandbox.query("A"), sandbox.query("b"))
    np.testing.assert_allclose(
        sandbox.query("x"), correct_x, err_msg="x is not correct"
    )
```

In this example, the name of the test case shown to the student on the frontend is
"x", worth 1 point. This is set with the `pytest.mark.grading_data` decorator. The
`sandbox` fixture is used to query the student code environment for the variables
defined in the `setup_code.py` file, and by the student code.

There are three fixtures defined by the `pytest_pl_grader` package:

1. `StudentFixture`: This fixture provides a sandboxed environment for the student code to run in. It allows the test to query the student code for variables and functions defined in the `setup_code.py` file. To use this fixture, simply include a parameter in your test function called `sandbox`.

2. `FeedbackFixture`: This fixture provides a way to give feedback to the student on their code submissions, including hints and error messages. To use this fixture, include a parameter in your test function called `feedback`.

3. `DataFixture`: This fixture provides access to supplemental data included in the test case by PL in the `data.json` file. To use this fixture, include a parameter in your test function called `data_json`.

To look at the code for each fixture, see the [file defining these fixtures](https://github.com/eliotwrobson/pl-python-autograder-v2/blob/main/src/pytest_pl_grader/fixture.py).

### Testing flow

Tests in this package are designed to flow in a linear way, where partial credit can be
given after certain asserts pass. Once an assert fails, the amount of partial credit awarded
will be the last value given before the failure, and the failure message in the assert will
be given as feedback. To set partial credit, simply call `feedback.set_score(<points>)`, where
`<points>` is in the range [0, 1]. To set custom feedback, set `feedback.add_message(<message>)`.

## More examples

To see more examples of what is possible in these test files, look at the test cases in
[this folder](https://github.com/eliotwrobson/pl-python-autograder-v2/tree/main/tests/scenario_root). Each test file is called `scenario.py`.
