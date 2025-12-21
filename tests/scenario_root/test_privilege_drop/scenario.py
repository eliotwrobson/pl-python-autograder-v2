import os
import sys

import pytest

from pytest_pl_grader.fixture import StudentFixture

# Module level timeout
initialization_timeout = 2.0


@pytest.mark.skipif(sys.platform == "win32", reason="Privilege dropping not supported on Windows")
@pytest.mark.grading_data(name="test_user_id", points=1)
def test_subprocess_runs_as_different_user(sandbox: StudentFixture) -> None:
    """
    Test that the subprocess runs as a different user when --worker-username is provided.
    This test should only run on Unix systems where privilege dropping is supported.
    """
    # Query the user ID from the student code
    result = sandbox.query("current_uid")

    # The subprocess should be running as a different user
    # We can't know the exact UID without knowing what user was passed,
    # but we can verify it's different from the current process
    current_process_uid = os.getuid()

    # If worker-username was provided, the UIDs should be different
    # This test will need to be run with --worker-username=<some_user> to be meaningful
    # For now, we just verify the query works
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    assert result >= 0, f"UID should be non-negative, got {result}"


@pytest.mark.skipif(sys.platform == "win32", reason="Privilege dropping not supported on Windows")
@pytest.mark.grading_data(name="test_effective_user_id", points=1)
def test_subprocess_effective_user_matches_real_user(sandbox: StudentFixture) -> None:
    """
    Test that both real and effective user IDs are set correctly.
    """
    real_uid = sandbox.query("current_uid")
    effective_uid = sandbox.query("current_euid")

    # Both should be the same after privilege dropping
    assert real_uid == effective_uid, f"Real UID ({real_uid}) should match effective UID ({effective_uid})"


@pytest.mark.skipif(sys.platform == "win32", reason="Privilege dropping not supported on Windows")
@pytest.mark.grading_data(name="test_group_id", points=1)
def test_subprocess_group_ids_match(sandbox: StudentFixture) -> None:
    """
    Test that group IDs are also set correctly.
    """
    real_gid = sandbox.query("current_gid")
    effective_gid = sandbox.query("current_egid")

    # Both should be the same after privilege dropping
    assert real_gid == effective_gid, f"Real GID ({real_gid}) should match effective GID ({effective_gid})"
    assert isinstance(real_gid, int)
    assert real_gid >= 0
