"""
Workspace grading scenario — demonstrates the workspace_sandbox fixture.

The student workspace lives in the adjacent 'student/' directory and contains:
    calculator.py          — a simple calculator module
    utils/helpers.py       — utility helpers in a sub-package

Tests use dotted module paths to call functions and query variables from the
student's project, exactly as they would in a real PrairieLearn workspace question.
"""

import pytest

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import WorkspaceFixture

autograder_config = ConfigObject(
    sandbox_timeout=5.0,
    workspace_mode=True,
    # workspace_student_dir is intentionally omitted here; the fixture resolves
    # to the adjacent 'student/' directory automatically.
)


@pytest.mark.grading_data(name="Add two numbers", points=2)
def test_add(workspace_sandbox: WorkspaceFixture) -> None:
    result = workspace_sandbox.query_function("calculator.add", 3, 4)
    assert result == 7


@pytest.mark.grading_data(name="Subtract two numbers", points=2)
def test_subtract(workspace_sandbox: WorkspaceFixture) -> None:
    result = workspace_sandbox.query_function("calculator.subtract", 10, 3)
    assert result == 7


@pytest.mark.grading_data(name="Multiply two numbers", points=2)
def test_multiply(workspace_sandbox: WorkspaceFixture) -> None:
    result = workspace_sandbox.query_function("calculator.multiply", 3, 4)
    assert result == 12


@pytest.mark.grading_data(name="Divide raises on zero denominator", points=2)
def test_divide_by_zero(workspace_sandbox: WorkspaceFixture) -> None:
    response = workspace_sandbox.query_function_raw("calculator.divide", 1, 0)
    assert response["status"] == "exception"
    assert response["exception_name"] == "ValueError"


@pytest.mark.grading_data(name="Query module-level constant", points=1)
def test_query_constant(workspace_sandbox: WorkspaceFixture) -> None:
    pi = workspace_sandbox.query("calculator.PI_APPROX")
    assert abs(pi - 3.14159) < 1e-5


@pytest.mark.grading_data(name="Clamp helper from sub-package", points=2)
def test_clamp(workspace_sandbox: WorkspaceFixture) -> None:
    result = workspace_sandbox.query_function("utils.helpers.clamp", 15, 0, 10)
    assert result == 10


@pytest.mark.grading_data(name="Query constant from sub-package", points=1)
def test_epsilon(workspace_sandbox: WorkspaceFixture) -> None:
    eps = workspace_sandbox.query("utils.helpers.EPSILON")
    assert eps == 1e-9
