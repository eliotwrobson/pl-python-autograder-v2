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
