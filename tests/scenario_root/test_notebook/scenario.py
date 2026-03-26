"""
Notebook grading scenario — default behavior (all code cells included).

Demonstrates grading a student Jupyter notebook (.ipynb) submission when no
``notebook_cell_tag`` is set.  All code cells in the notebook are extracted
and concatenated, exactly as if they were a single ``.py`` file.

Contrast with ``test_notebook_cell_tag``, which restricts execution to only
the cells tagged with ``#grade``.
"""

import pytest

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import FeedbackFixture
from pytest_prairielearn_grader.fixture import StudentFixture

autograder_config = ConfigObject(
    student_code_pattern="student_code*.ipynb",
    sandbox_timeout=5.0,
)


@pytest.mark.grading_data(name="Check variable x", points=2)
def test_variable(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.0)
    assert sandbox.query("x") == 42
    feedback.set_score(1.0)


@pytest.mark.grading_data(name="Check add function", points=3)
def test_add(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    feedback.set_score(0.0)
    result = sandbox.query_function("add", 3, 4)
    assert result == 7
    feedback.set_score(1.0)
