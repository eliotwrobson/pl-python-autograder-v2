import platform

pytest_plugins = ("pytester",)
platform  # noqa: B018


def test_help(pytester):
    result = pytester.runpytest_subprocess("--help")
    result.stdout.fnmatch_lines(
        [
            "*",
            "*",
            "benchmark:",
            "  --benchmark-min-time=SECONDS",
            "                        *Default: '0.000005'",
            "  --benchmark-max-time=SECONDS",
            "                        *Default: '1.0'",
            "  --benchmark-min-rounds=NUM",
            "                        *Default: 5",
            "  --benchmark-timer=FUNC",
            "  --benchmark-calibration-precision=NUM",
            "                        *Default: 10",
            "  --benchmark-warmup=[KIND]",
            "  --benchmark-warmup-iterations=NUM",
            "                        *Default: 100000",
            "  --benchmark-disable-gc",
            "  --benchmark-skip      *",
            "  --benchmark-only      *",
            "  --benchmark-save=NAME",
            "  --benchmark-autosave  *",
            "  --benchmark-save-data",
            "  --benchmark-json=PATH",
            "  --benchmark-compare=[NUM|_ID]",
            "  --benchmark-compare-fail=EXPR?[[]EXPR?...[]]",
            "  --benchmark-cprofile=COLUMN",
            "  --benchmark-storage=URI",
            "                        *Default: 'file://./.benchmarks'.",
            "  --benchmark-verbose   *",
            "  --benchmark-sort=COL  *",
            "  --benchmark-group-by=LABEL",
            "                        *Default: 'group'",
            "  --benchmark-columns=LABELS",
            "  --benchmark-histogram=[FILENAME-PREFIX]",
            "*",
        ]
    )


def test_groups(testdir):
    test = testdir.makepyfile(
        """
import time
import pytest

def test_fast(benchmark):
    benchmark(lambda: time.sleep(0.000001))
    assert 1 == 1

def test_slow(benchmark):
    benchmark(lambda: time.sleep(0.001))
    assert 1 == 1

@pytest.mark.benchmark(group="A")
def test_slower(benchmark):
    benchmark(lambda: time.sleep(0.01))
    assert 1 == 1

@pytest.mark.benchmark(group="A", warmup=True)
def test_xfast(benchmark):
    benchmark(lambda: None)
    assert 1 == 1
"""
    )
    result = testdir.runpytest_subprocess("-vv", "--doctest-modules", test)
    result.stdout.fnmatch_lines(
        [
            "*collected 5 items",
            "*",
            "test_groups.py::*test_groups PASSED*",
            "test_groups.py::test_fast PASSED*",
            "test_groups.py::test_slow PASSED*",
            "test_groups.py::test_slower PASSED*",
            "test_groups.py::test_xfast PASSED*",
            "*",
            "* benchmark: 2 tests *",
            "*",
            "* benchmark 'A': 2 tests *",
            "*",
            "*====== 5 passed * ======*",
        ]
    )
    print(result.stdout)
    assert False
