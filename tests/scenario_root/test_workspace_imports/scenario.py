"""
Workspace import restriction scenario.

Tests that:
  1. Local workspace modules can import each other without appearing in the whitelist.
  2. Local sub-packages can be imported without appearing in the whitelist.
  3. External library imports that are in the whitelist still work normally.
  4. External library imports that are NOT in the whitelist (or are blacklisted)
     are still blocked, even inside workspace module code.

The ConfigObject uses import_whitelist=["math"] so only 'math' is permitted as an
external import.  The default blacklist (os, sys, subprocess, pathlib, shutil) applies.
Workspace-local modules should bypass both restrictions automatically.
"""

import pytest

from pytest_prairielearn_grader import ConfigObject
from pytest_prairielearn_grader.fixture import WorkspaceFixture

autograder_config = ConfigObject(
    workspace_mode=True,
    sandbox_timeout=10.0,
    import_whitelist=["math"],
    # import_blacklist intentionally omitted — the default blacklist applies
)


@pytest.mark.grading_data(name="Local cross-module import bypasses whitelist", points=2)
def test_local_dep_bypass_whitelist(workspace_sandbox: WorkspaceFixture) -> None:
    """
    uses_local_dep.py does `from local_dep import LOCAL_CONSTANT` at the top level.
    'local_dep' is NOT in the import_whitelist, but it is a workspace-local file, so
    it should be importable without any whitelist entry.
    """
    value = workspace_sandbox.query("uses_local_dep.IMPORTED_VALUE")
    assert value == 42


@pytest.mark.grading_data(name="Whitelisted external import works", points=2)
def test_whitelisted_external_import(workspace_sandbox: WorkspaceFixture) -> None:
    """
    uses_math.py does `import math` at the top level.  'math' is in the whitelist,
    so the import should succeed.
    """
    floor_val = workspace_sandbox.query("uses_math.FLOOR_VAL")
    assert floor_val == 3


@pytest.mark.grading_data(name="Local sub-package import bypasses whitelist", points=2)
def test_local_subpkg_bypass_whitelist(workspace_sandbox: WorkspaceFixture) -> None:
    """
    uses_subpkg.py does `from subpkg.util import UTIL_VAL` at the top level.
    The 'subpkg' package is a workspace-local directory, so it should be importable
    without a whitelist entry.
    """
    val = workspace_sandbox.query("uses_subpkg.IMPORTED_UTIL")
    assert val == 99


@pytest.mark.grading_data(name="Non-whitelisted external import is blocked", points=2)
def test_non_whitelisted_external_blocked(workspace_sandbox: WorkspaceFixture) -> None:
    """
    bad_func.py defines get_cwd() which does `import os` at call time.
    'os' is in the default blacklist, so calling the function should raise ImportError
    even though it's inside a workspace module.
    """
    response = workspace_sandbox.query_function_raw("bad_func.get_cwd")
    assert response["status"] == "exception"
    assert response["exception_name"] == "ImportError"
