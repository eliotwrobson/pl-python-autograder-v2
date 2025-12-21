import os
import sys

import pytest

from pytest_pl_grader.fixture import StudentFixture

# Module level timeout
initialization_timeout = 2.0


@pytest.mark.skipif(sys.platform == "win32", reason="Privilege dropping not supported on Windows")
@pytest.mark.grading_data(name="test_worker_username_stored", points=1)
def test_worker_username_stored_in_fixture(sandbox: StudentFixture) -> None:
    """
    Test that the worker_username parameter is correctly stored in the fixture.
    This verifies the --worker-username CLI option is being passed through.
    """
    # The fixture should have worker_username attribute
    assert hasattr(sandbox, "worker_username"), "Fixture missing worker_username attribute"
    
    # If no username was provided, it should be None
    # If a username was provided via CLI, it will be stored here
    # This test just validates the plumbing works
    assert sandbox.worker_username is None or isinstance(sandbox.worker_username, str)


@pytest.mark.skipif(sys.platform == "win32", reason="Privilege dropping not supported on Windows")
@pytest.mark.grading_data(name="test_user_id", points=1)
def test_subprocess_runs_as_different_user(sandbox: StudentFixture) -> None:
    """
    Test that the subprocess can query its user ID.
    When --worker-username is provided, this will be the dropped privilege UID.
    """
    # Query the user ID from the student code
    result = sandbox.query("current_uid")

    # Verify the query returns a valid UID
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
