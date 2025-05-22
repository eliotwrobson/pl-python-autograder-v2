import argparse
import operator
import platform
import subprocess
import sys
import traceback
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from datetime import timezone
from importlib.resources import files
from pathlib import Path
from typing import NamedTuple

import pytest

from . import __version__
from .fixture import BenchmarkFixture
from .session import BenchmarkSession
from .session import PerformanceRegression
from .timers import default_timer
from .utils import NameWrapper
from .utils import consistent_dumps
from .utils import get_commit_info
from .utils import get_current_time
from .utils import get_tag
from .utils import operations_unit
from .utils import parse_columns
from .utils import parse_compare_fail
from .utils import parse_cprofile_loops
from .utils import parse_name_format
from .utils import parse_rounds
from .utils import parse_save
from .utils import parse_seconds
from .utils import parse_sort
from .utils import parse_timer
from .utils import parse_warmup
from .utils import time_unit


class StudentFiles(NamedTuple):
    leading_file: Path | None
    trailing_file: Path | None
    student_code_file: Path


class StudentFixture:
    process: subprocess.Popen | None

    def __init__(self, file_names: StudentFiles) -> None:
        self.leading_file = file_names.leading_file
        self.trailing_file = file_names.trailing_file
        self.student_code_file = file_names.student_code_file

        script_path = str(files("pl_pytest_autograder").joinpath("_student_code_runner.py"))

        self.process = subprocess.Popen(
            [sys.executable, script_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def try_message(self, message: str) -> str:
        import json

        json_message = json.dumps({"message": message})

        stdout, stderr = self.process.communicate(json_message.encode("utf-8"), timeout=2)
        return stdout.decode("utf-8")

    # TODO add functions that let instructors use the student fixture
    # use the stuff pete set up here: https://github.com/reteps/pytest-autograder-prototype
    def _cleanup(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

    def __repr__(self) -> str:
        return f"StudentFixture(leading_file={self.leading_file}, trailing_file={self.trailing_file}, student_code_file={self.student_code_file})"


# TODO rename this!


@pytest.fixture
def benchmark(request: pytest.FixtureRequest) -> Iterable[StudentFixture]:
    fixture = StudentFixture(request.param)
    yield fixture
    fixture._cleanup()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """
    TODO this is where the parameterization inside the folder is happening
    """
    print("HERE in metafunc", type(metafunc))

    # TODO read in student code and leading/trailing code
    # patterns from metafunc by magically named variables
    # in the testing module.
    # print(metafunc.module.__dict__["student_code_name"])

    # 1. Get the module object associated with the test function
    test_module = metafunc.module

    if test_module is None:
        # IN case the test is not in a module (e.g., it is a class method)
        # or a standalone function, you can skip this step
        return

    # print(test_module)
    # 2. Access the __file__ attribute of the module
    # This gives you the string path to the .py file where the test function is defined
    module_filepath_str = test_module.__file__

    # 3. Convert it to a pathlib.Path object for easier manipulation
    module_path = Path(module_filepath_str)

    if "benchmark" in metafunc.fixturenames:
        # Let's assume you have a 'data' directory next to your test file
        data_dir = module_path.parent / module_path.stem

        if data_dir.is_dir():
            print("IN THE DATA DIR")
            # Find a specific data file, e.g., 'test_data.txt'
            leading_file = data_dir / "leading_code.py"
            trailing_file = data_dir / "trailing_code.py"
            # TODO parameterize this accross multiple of these files if the exist
            # conforming to the same naming scheme
            student_code_file = data_dir / "student_code.py"

            file_tup = StudentFiles(leading_file, trailing_file, student_code_file)

            metafunc.parametrize("benchmark", [file_tup], indirect=True)
            # else:
            #    pass
            # pytest.skip(f"Data file '{data_file.name}' not found in '{data_dir}'")
        else:
            pass
            # pytest.skip(f"Data directory '{data_dir}' not found.")


### TODO delete all of the old stuff below here as much as we can ###


def pytest_report_header(config):
    bs = config._benchmarksession

    return (
        "benchmark: {version} (defaults:"
        " timer={timer}"
        " disable_gc={0[disable_gc]}"
        " min_rounds={0[min_rounds]}"
        " min_time={0[min_time]}"
        " max_time={0[max_time]}"
        " calibration_precision={0[calibration_precision]}"
        " warmup={0[warmup]}"
        " warmup_iterations={0[warmup_iterations]}"
        ")"
    ).format(
        bs.options,
        version=__version__,
        timer=bs.options.get("timer"),
    )


def add_display_options(addoption, prefix="benchmark-"):
    addoption(
        f"--{prefix}sort",
        metavar="COL",
        type=parse_sort,
        default="min",
        help="Column to sort on. Can be one of: 'min', 'max', 'mean', 'stddev', 'name', 'fullname'. Default: %(default)r",
    )
    addoption(
        f"--{prefix}group-by",
        metavar="LABEL",
        default="group",
        help="How to group tests. Can be one of: 'group', 'name', 'fullname', 'func', 'fullfunc', "
        "'param' or 'param:NAME', where NAME is the name passed to @pytest.parametrize."
        " Default: %(default)r",
    )
    addoption(
        f"--{prefix}columns",
        metavar="LABELS",
        type=parse_columns,
        default=["min", "max", "mean", "stddev", "median", "iqr", "outliers", "ops", "rounds", "iterations"],
        help="Comma-separated list of columns to show in the result table. Default: "
        "'min, max, mean, stddev, median, iqr, outliers, ops, rounds, iterations'",
    )
    addoption(
        f"--{prefix}name",
        metavar="FORMAT",
        type=parse_name_format,
        default="normal",
        help="How to format names in results. Can be one of 'short', 'normal', 'long', or 'trial'. Default: %(default)r",
    )
    addoption(
        f"--{prefix}time-unit",
        metavar="COLUMN",
        default=None,
        choices=["ns", "us", "ms", "s", "auto"],
        help="Unit to scale the results to. Available units: 'ns', 'us', 'ms', 's'. Default: 'auto'.",
    )


def add_histogram_options(addoption, prefix="benchmark-"):
    filename_prefix = f"benchmark_{get_current_time()}"
    addoption(
        f"--{prefix}histogram",
        action="append",
        metavar="FILENAME-PREFIX",
        nargs="?",
        default=[],
        const=filename_prefix,
        help="Plot graphs of min/max/avg/stddev over time in FILENAME-PREFIX-test_name.svg. If FILENAME-PREFIX contains"
        f" slashes ('/') then directories will be created. Default: {filename_prefix!r}",
    )


def add_csv_options(addoption, prefix="benchmark-"):
    filename_prefix = f"benchmark_{get_current_time()}"
    addoption(
        f"--{prefix}csv",
        action="append",
        metavar="FILENAME",
        nargs="?",
        default=[],
        const=filename_prefix,
        help=f"Save a csv report. If FILENAME contains slashes ('/') then directories will be created. Default: {filename_prefix!r}",
    )


def add_global_options(addoption, prefix="benchmark-"):
    addoption(
        f"--{prefix}storage",
        *[] if prefix else ["-s"],
        metavar="URI",
        default="file://./.benchmarks",
        help="Specify a path to store the runs as uri in form file://path or"
        " elasticsearch+http[s]://host1,host2/[index/doctype?project_name=Project] "
        "(when --benchmark-save or --benchmark-autosave are used). For backwards compatibility unexpected values "
        "are converted to file://<value>. Default: %(default)r.",
    )
    addoption(
        f"--{prefix}netrc",
        nargs="?",
        default="",
        const="~/.netrc",
        help="Load elasticsearch credentials from a netrc file. Default: %(default)r.",
    )
    addoption(
        f"--{prefix}verbose",
        *[] if prefix else ["-v"],
        action="store_true",
        default=False,
        help="Dump diagnostic and progress information.",
    )
    addoption(
        f"--{prefix}quiet",
        *[] if prefix else ["-q"],
        action="store_true",
        default=False,
        help="Disable reporting. Verbose mode takes precedence.",
    )
    if not prefix:
        addoption(
            "--import-mode",
            default="prepend",
            choices=["prepend", "append", "importlib"],
            dest="importmode",
            help="How to attempt loading hooks from conftest. Akin to pytest's --import-mode. Default: %(default)r.",
        )


def pytest_addoption(parser):
    group = parser.getgroup("benchmark")
    group.addoption(
        "--benchmark-min-time",
        metavar="SECONDS",
        type=parse_seconds,
        default="0.000005",
        help="Minimum time per round in seconds. Default: %(default)r",
    )
    group.addoption(
        "--benchmark-max-time",
        metavar="SECONDS",
        type=parse_seconds,
        default="1.0",
        help="Maximum run time per test - it will be repeated until this total time is reached. It may be "
        "exceeded if test function is very slow or --benchmark-min-rounds is large (it takes precedence). "
        "Default: %(default)r",
    )
    group.addoption(
        "--benchmark-min-rounds",
        metavar="NUM",
        type=parse_rounds,
        default=5,
        help="Minimum rounds, even if total time would exceed `--max-time`. Default: %(default)r",
    )
    group.addoption(
        "--benchmark-timer",
        metavar="FUNC",
        type=parse_timer,
        default=str(NameWrapper(default_timer)),
        help="Timer to use when measuring time. Default: %(default)r",
    )
    group.addoption(
        "--benchmark-calibration-precision",
        metavar="NUM",
        type=int,
        default=10,
        help="Precision to use when calibrating number of iterations. Precision of 10 will make the timer look 10 times"
        " more accurate, at a cost of less precise measure of deviations. Default: %(default)r",
    )
    group.addoption(
        "--benchmark-warmup",
        metavar="KIND",
        nargs="?",
        default=parse_warmup("auto"),
        type=parse_warmup,
        help="Activates warmup. Will run the test function up to number of times in the calibration phase. "
        "See `--benchmark-warmup-iterations`. Note: Even the warmup phase obeys --benchmark-max-time. "
        "Available KIND: 'auto', 'off', 'on'. Default: 'auto' (automatically activate on PyPy).",
    )
    group.addoption(
        "--benchmark-warmup-iterations",
        metavar="NUM",
        type=int,
        default=100000,
        help="Max number of iterations to run in the warmup phase. Default: %(default)r",
    )
    group.addoption("--benchmark-disable-gc", action="store_true", default=False, help="Disable GC during benchmarks.")
    group.addoption("--benchmark-skip", action="store_true", default=False, help="Skip running any tests that contain benchmarks.")
    group.addoption(
        "--benchmark-disable",
        action="store_true",
        default=False,
        help="Disable benchmarks. Benchmarked functions are only ran once and no stats are reported. Use this is you "
        "want to run the test but don't do any benchmarking.",
    )
    group.addoption(
        "--benchmark-enable",
        action="store_true",
        default=False,
        help="Forcibly enable benchmarks. Use this option to override --benchmark-disable (in case you have it in pytest configuration).",
    )
    group.addoption("--benchmark-only", action="store_true", default=False, help="Only run benchmarks. This overrides --benchmark-skip.")
    group.addoption("--benchmark-save", metavar="NAME", type=parse_save, help="Save the current run into 'STORAGE-PATH/counter_NAME.json'.")
    tag = get_tag()
    group.addoption(
        "--benchmark-autosave",
        action="store_const",
        const=tag,
        help=f"Autosave the current run into 'STORAGE-PATH/counter_{tag}.json",
    )
    group.addoption(
        "--benchmark-save-data",
        action="store_true",
        help="Use this to make --benchmark-save and --benchmark-autosave include all the timing data, not just the stats.",
    )
    group.addoption(
        "--benchmark-json",
        metavar="PATH",
        type=argparse.FileType("wb"),
        help="Dump a JSON report into PATH. Note that this will include the complete data (all the timings, not just the stats).",
    )
    group.addoption(
        "--benchmark-compare",
        metavar="NUM|_ID",
        nargs="?",
        default=[],
        const=True,
        help="Compare the current run against run NUM (or prefix of _id in elasticsearch) or the latest saved run if unspecified.",
    )
    group.addoption(
        "--benchmark-compare-fail",
        metavar="EXPR",
        nargs="+",
        type=parse_compare_fail,
        help="Fail test if performance regresses according to given EXPR"
        " (eg: min:5%% or mean:0.001 for number of seconds). Can be used multiple times.",
    )
    group.addoption(
        "--benchmark-cprofile",
        metavar="COLUMN",
        default=None,
        choices=["ncalls_recursion", "ncalls", "tottime", "tottime_per", "cumtime", "cumtime_per", "function_name"],
        help="If specified cProfile will be enabled. Top functions will be stored for the given column. Available columns: "
        "'ncalls_recursion', 'ncalls', 'tottime', 'tottime_per', 'cumtime', 'cumtime_per', 'function_name'.",
    )
    group.addoption(
        "--benchmark-cprofile-loops",
        metavar="LOOPS",
        default=1,
        type=parse_cprofile_loops,
        help="How many times to run the function in cprofile. Available options: 'auto', or an integer. ",
    )
    group.addoption(
        "--benchmark-cprofile-top",
        metavar="COUNT",
        default=25,
        type=int,
        help="How many rows to display.",
    )
    cprofile_dump_prefix = f"benchmark_{get_current_time()}"
    group.addoption(
        "--benchmark-cprofile-dump",
        action="append",
        metavar="FILENAME-PREFIX",
        nargs="?",
        default=[],
        const=cprofile_dump_prefix,
        help="Save cprofile dumps as FILENAME-PREFIX-test_name.prof. If FILENAME-PREFIX contains"
        f" slashes ('/') then directories will be created. Default: {cprofile_dump_prefix!r}",
    )
    add_global_options(group.addoption)
    add_display_options(group.addoption)
    add_histogram_options(group.addoption)


def pytest_addhooks(pluginmanager):
    from . import hookspec

    method = getattr(pluginmanager, "add_hookspecs", None)
    if method is None:
        method = pluginmanager.addhooks
    method(hookspec)


def pytest_benchmark_compare_machine_info(config, benchmarksession, machine_info, compared_benchmark):
    machine_info = consistent_dumps(machine_info)
    compared_machine_info = consistent_dumps(compared_benchmark["machine_info"])

    if compared_machine_info != machine_info:
        benchmarksession.logger.warning(
            f"Benchmark machine_info is different. Current: {machine_info} VS saved: {compared_machine_info} (location: {benchmarksession.storage.location})."
        )


def pytest_collection_modifyitems(config, items):
    bs = config._benchmarksession
    skip_bench = pytest.mark.skip(reason="Skipping benchmark (--benchmark-skip active).")
    skip_other = pytest.mark.skip(reason="Skipping non-benchmark (--benchmark-only active).")
    for item in items:
        has_benchmark = hasattr(item, "fixturenames") and "benchmark" in item.fixturenames
        if has_benchmark:
            if bs.skip:
                item.add_marker(skip_bench)
        else:
            if bs.only:
                item.add_marker(skip_other)


def pytest_benchmark_group_stats(config, benchmarks, group_by):
    groups = defaultdict(list)
    for bench in benchmarks:
        key = ()
        for grouping in group_by.split(","):
            if grouping == "group":
                key += (bench["group"],)
            elif grouping == "name":
                key += (bench["name"],)
            elif grouping == "func":
                key += (bench["name"].split("[")[0],)
            elif grouping == "fullname":
                key += (bench["fullname"],)
            elif grouping == "fullfunc":
                key += (bench["fullname"].split("[")[0],)
            elif grouping == "param":
                key += (bench["param"],)
            elif grouping.startswith("param:"):
                param_name = grouping[len("param:") :]
                key += ("{}={}".format(param_name, bench["params"][param_name]),)
            else:
                raise NotImplementedError(f"Unsupported grouping {group_by!r}.")
        groups[" ".join(str(p) for p in key if p) or None].append(bench)

    for grouped_benchmarks in groups.values():
        grouped_benchmarks.sort(key=operator.itemgetter("fullname" if "full" in group_by else "name"))
    return sorted(groups.items(), key=lambda pair: pair[0] or "")


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    session.config._benchmarksession.finish()
    yield


def pytest_terminal_summary(terminalreporter):
    try:
        terminalreporter.config._benchmarksession.display(terminalreporter)
    except PerformanceRegression:
        raise
    except Exception:
        terminalreporter.config._benchmarksession.logger.error(f"\n{traceback.format_exc()}")
        raise


def get_cpu_info():
    import cpuinfo

    return cpuinfo.get_cpu_info() or {}


def pytest_benchmark_scale_unit(config, unit, benchmarks, best, worst, sort):
    config_time_unit = config.getoption("benchmark_time_unit", None) if config else None
    if config_time_unit == "ns":
        return "n", 1e9
    elif config_time_unit == "us":
        return "u", 1e6
    elif config_time_unit == "ms":
        return "m", 1e3
    elif config_time_unit == "s":
        return "", 1.0
    assert config_time_unit in ("auto", None)
    if unit == "seconds":
        time_unit_key = sort
        if sort in ("name", "fullname"):
            time_unit_key = "min"
        return time_unit(best.get(sort, benchmarks[0][time_unit_key]))
    elif unit == "operations":
        return operations_unit(worst.get("ops", benchmarks[0]["ops"]))
    else:
        raise RuntimeError(f"Unexpected measurement unit {unit!r}")


def pytest_benchmark_generate_machine_info():
    python_implementation = platform.python_implementation()
    python_implementation_version = platform.python_version()
    if python_implementation == "PyPy":
        python_implementation_version = "%d.%d.%d" % sys.pypy_version_info[:3]
        if sys.pypy_version_info.releaselevel != "final":
            python_implementation_version += "-%s%d" % sys.pypy_version_info[3:]
    return {
        "node": platform.node(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "python_compiler": platform.python_compiler(),
        "python_implementation": python_implementation,
        "python_implementation_version": python_implementation_version,
        "python_version": platform.python_version(),
        "python_build": platform.python_build(),
        "release": platform.release(),
        "system": platform.system(),
        "cpu": get_cpu_info(),
    }


def pytest_benchmark_generate_commit_info(config):
    return get_commit_info(config.getoption("benchmark_project_name", None))


def pytest_benchmark_generate_json(config, benchmarks, include_data, machine_info, commit_info):
    benchmarks_json = []
    output_json = {
        "machine_info": machine_info,
        "commit_info": commit_info,
        "benchmarks": benchmarks_json,
        "datetime": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
    }
    for bench in benchmarks:
        if not bench.has_error:
            benchmarks_json.append(bench.as_dict(include_data=include_data))
    return output_json


import os


def _win32_longpath(path):
    """
    Helper function to add the long path prefix for Windows, so that shutil.copytree
     won't fail while working with paths with 255+ chars.
    TODO move this to the utils module.
    From https://github.com/gabrielcnr/pytest-datadir/blob/master/src/pytest_datadir/plugin.py
    """
    if sys.platform == "win32":
        # The use of os.path.normpath here is necessary since "the "\\?\" prefix
        # to a path string tells the Windows APIs to disable all string parsing
        # and to send the string that follows it straight to the file system".
        # (See https://docs.microsoft.com/pt-br/windows/desktop/FileIO/naming-a-file)
        normalized = os.path.normpath(path)
        if not normalized.startswith("\\\\?\\"):
            is_unc = normalized.startswith("\\\\")
            # see https://en.wikipedia.org/wiki/Path_(computing)#Universal_Naming_Convention
            if is_unc:  # then we need to insert an additional "UNC\" to the longpath prefix
                normalized = normalized.replace("\\\\", "\\\\?\\UNC\\")
            else:
                normalized = "\\\\?\\" + normalized
        return normalized
    else:
        return path


@pytest.fixture
def benchmark_weave(benchmark):
    return benchmark.weave


def pytest_runtest_setup(item):
    marker = item.get_closest_marker("benchmark")
    if marker:
        if marker.args:
            raise ValueError("benchmark mark can't have positional arguments.")
        for name in marker.kwargs:
            if name not in (
                "max_time",
                "min_rounds",
                "min_time",
                "timer",
                "group",
                "disable_gc",
                "warmup",
                "warmup_iterations",
                "calibration_precision",
                "cprofile",
            ):
                raise ValueError(f"benchmark mark can't have {name!r} keyword argument.")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    fixture = None
    if hasattr(item, "funcargs"):
        fixture = item.funcargs.get("benchmark")
    if fixture is not None and not isinstance(fixture, BenchmarkFixture):
        pass
        # raise TypeError(
        #     f"unexpected type for `benchmark` in funcargs, {fixture!r} must be a BenchmarkFixture instance. "
        #     "You should not use other plugins that define a `benchmark` fixture, or return and unexpected value if you do redefine it."
        # )
    # if fixture:
    #     fixture.skipped = outcome.get_result().outcome == "skipped"


@pytest.hookimpl(trylast=True)  # force the other plugins to initialise, fixes issue with capture not being properly initialised
def pytest_configure(config):
    config.addinivalue_line("markers", "benchmark: mark a test with custom benchmark settings.")
    bs = config._benchmarksession = BenchmarkSession(config)
    bs.handle_loading()
    config.pluginmanager.register(bs, "pytest-benchmark")
