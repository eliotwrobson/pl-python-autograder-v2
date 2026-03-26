"""
Notebook cell-tag filtering scenario.

Demonstrates ``notebook_cell_tag``:  only code cells whose first line starts
with the tag string are extracted and executed.

The notebook contains:
  - An untagged code cell that ``raise``s ``ValueError``.  If the filter is
    broken and this cell runs, the sandbox initialization fails and every test
    errors — giving a clear signal the filtering did not work.
  - A tagged code cell (first line: ``#grade``) that defines ``x = 99`` and
    ``multiply(a, b)``.

Because both tests pass, we know:
  - The ``#grade`` cell executed (answers are accessible).
  - The untagged crashing cell was excluded (no initialization error).
"""

import pytest

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import FeedbackFixture
from pytest_prairielearn_grader.fixture import StudentFixture

autograder_config = ConfigObject(
    student_code_pattern="student_code*.ipynb",
    notebook_cell_tag="#grade",
    sandbox_timeout=5.0,
)


@pytest.mark.grading_data(name="Check tagged variable x", points=2)
def test_variable(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.0)
    assert sandbox.query("x") == 99
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="Check tagged multiply function", points=3)
def test_multiply(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.0)
    result = sandbox.query_function("multiply", 3, 4)
    assert result == 12
    feedback.set_score(1.0)
