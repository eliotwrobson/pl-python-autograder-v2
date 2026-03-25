"""
Tests that the autograder correctly handles the Docker production layout, where
run.sh places the student submission directory inside 'student/' rather than
scattering files at the data directory root.

Resulting directory structure (mirrors what run.sh produces):

    test_docker_layout.py          <- test file
    test_docker_layout/
        student/
            student_code.py        <- moved from /grade/student/ by run.sh
        setup_code.py              <- from /grade/tests/ (not present here)
        data.json                  <- from /grade/tests/ (not present here)

The plugin's _find_student_files fallback discovers student_code.py inside the
student/ subdirectory automatically when no files match the pattern at the root.
"""

import pytest

from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="Query variable from student subdir", points=2)
def test_query_variable(sandbox: StudentFixture) -> None:
    assert sandbox.query("ANSWER") == 42


@pytest.mark.grading_data(name="Call function from student subdir", points=2)
def test_call_function(sandbox: StudentFixture) -> None:
    result = sandbox.query_function("double", 21)
    assert result == 42
