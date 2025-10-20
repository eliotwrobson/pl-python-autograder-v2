from pytest_pl_grader.fixture import StudentFixture


def test_random(sandbox: StudentFixture) -> None:
    # Check that variables we set are unaltered
    assert sandbox.query_setup("a") == 42
    assert sandbox.query_setup("b")["c"] == 1

    assert sandbox.query("c") == 42
    assert sandbox.query("a") == 10
    assert sandbox.query("b")["c"] == 50
