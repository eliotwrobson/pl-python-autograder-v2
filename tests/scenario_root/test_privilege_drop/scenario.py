import pwd
import sys

import pytest

from pytest_prairielearn_grader.fixture import StudentFixture

# Module level timeout
initialization_timeout = 2.0


@pytest.mark.skipif(sys.platform == "win32", reason="Privilege dropping not supported on Windows")
@pytest.mark.grading_data(name="test_privilege_drop_to_worker_user", points=1)
def test_subprocess_runs_as_worker_user(sandbox: StudentFixture) -> None:
    """
    Test that the subprocess runs as the correct user when --worker-username is provided.
    This verifies that privilege dropping to the specified user actually occurred.
    """
    # Query the user ID from the student code subprocess
    subprocess_uid = sandbox.query("current_uid")

    assert isinstance(subprocess_uid, int), f"Expected int, got {type(subprocess_uid)}"
    assert subprocess_uid >= 0, f"UID should be non-negative, got {subprocess_uid}"

    # If a worker username was provided, verify the subprocess runs as that user
    if sandbox.worker_username is not None:
        try:
            expected_uid = pwd.getpwnam(sandbox.worker_username).pw_uid
        except KeyError:
            pytest.skip(f"User '{sandbox.worker_username}' does not exist on system")

        assert subprocess_uid == expected_uid, (
            f"Subprocess should run as user '{sandbox.worker_username}' (UID {expected_uid}), " f"but is running as UID {subprocess_uid}"
        )


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
