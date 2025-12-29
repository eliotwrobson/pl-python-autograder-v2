import json
import logging
import os
import sys
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import NamedTuple
from typing import cast

import _pytest
import _pytest.reports
import _pytest.terminal
import pytest
from _pytest.config import Config
from prettytable import PrettyTable

from .fixture import FeedbackFixture
from .fixture import StudentFiles
from .fixture import StudentFixture
from .utils import GradingOutputLevel
from .utils import NamesForUserInfo
from .utils import ProcessStartResponse
from .utils import ProcessStatusCode
from .utils import get_output_level_marker

logger = logging.getLogger(__name__)


class TestResult(NamedTuple):
    """Container for test execution results."""

    report: _pytest.reports.TestReport
    call: pytest.CallInfo
    stdout: str


def get_datadir(test_module: ModuleType) -> Path | None:
    """
    Get the data directory for the current test module.
    """

    if test_module is None:
        # In case the test is not in a module (e.g., it is a class method)
        # or a standalone function, you can skip this step
        return None

    # Access the __file__ attribute of the module
    module_filepath_str = test_module.__file__

    if module_filepath_str is None:
        return None

    # Convert it to a pathlib.Path object for easier manipulation
    module_path = Path(module_filepath_str)

    # Let's assume you have a 'data' directory next to your test file
    data_dir = module_path.parent / module_path.stem

    return data_dir


@pytest.fixture(scope="module")
def data_json(request: pytest.FixtureRequest) -> dict[str, Any] | None:
    try:
        datadir = get_datadir(request.module)
        assert datadir is not None
        data_file = datadir / "data.json"
        return json.loads(data_file.read_text(encoding="utf-8"))
    except Exception:
        pass  # TODO add logging

    # If the data file is not found or cannot be read, return None
    return None

    # if datadir is None or not datadir.is_dir():
    #     raise ValueError(f"Data directory '{datadir}' not found or is not a directory.")

    # if not data_file.is_file():
    #     raise ValueError(f"Data file '{data_file.name}' not found in '{datadir}'.")


def _initialize_sandbox_fixture(
    request: pytest.FixtureRequest,
    data_json: dict[str, Any] | None,
    file_names: StudentFiles,
) -> tuple[StudentFixture, int]:
    """
    Common initialization logic for both sandbox and module_sandbox fixtures.
    Handles parameter parsing, timeout configuration, and StudentFixture creation.
    Returns the fixture and the initialization timeout.
    """
    # Default timeout TODO make this a command line option?
    initialization_timeout = 1

    if data_json is None:
        params_dict = {}
    else:
        params_dict = data_json.get("params", {})

    import_whitelist = params_dict.get("import_whitelist")
    import_blacklist = params_dict.get("import_blacklist")

    # TODO make sure this contains only valid builtins
    builtin_whitelist = params_dict.get("builtin_whitelist")
    names_for_user_list = cast(list[NamesForUserInfo] | None, params_dict.get("names_for_user"))

    starting_vars: dict[str, Any] = {
        "__data_params": deepcopy(params_dict) if data_json is not None else {},
    }

    if names_for_user_list is not None:
        for names_dict in names_for_user_list:
            name = names_dict["name"]
            value = params_dict.get(name, None)

            variable_type = type(value).__name__.strip()
            expected_variable_type = names_dict["type"].strip()

            if variable_type != expected_variable_type and value is not None:
                logger.warning(f"Variable type mismatch for starting var {name}: expected {expected_variable_type}, got {variable_type}")

            starting_vars[name] = value

    # Check for module-level timeout variable (works for module-scoped fixtures)
    # This allows setting: sandbox_timeout = 0.5 at module level
    if hasattr(request, "module") and hasattr(request.module, "sandbox_timeout"):
        initialization_timeout = request.module.sandbox_timeout

    # Check for the custom mark (overrides module-level setting)
    marker = request.node.get_closest_marker("sandbox_timeout")
    if marker and marker.args:
        initialization_timeout = marker.args[0]

    fixture = StudentFixture(
        file_names=file_names,
        import_whitelist=import_whitelist,
        import_blacklist=import_blacklist,
        starting_vars=starting_vars,
        builtin_whitelist=builtin_whitelist,
        names_for_user_list=names_for_user_list,
        worker_username=request.config.getoption("--worker-username"),
    )

    return fixture, initialization_timeout


def _handle_sandbox_startup_errors(
    request: pytest.FixtureRequest,
    response: ProcessStartResponse,
    initialization_timeout: int,
) -> None:
    """
    Common error handling logic for sandbox fixture startup failures.
    Handles exceptions, timeouts, and other error conditions.
    """
    response_status = response["status"]

    if response_status == ProcessStatusCode.EXCEPTION:
        output_level: GradingOutputLevel = get_output_level_marker(request.node.get_closest_marker("output"))

        logger.debug(f"Grading output level set to: {output_level}")
        exception_name = response.get("execution_error", "Unknown error")
        fail_message = f"Student code execution failed with an exception: {exception_name}"

        if output_level == GradingOutputLevel.ExceptionName:
            pytest.fail(fail_message, pytrace=False)

        exception_message = response.get("execution_message", "")
        fail_message += f"{os.linesep}Exception Message: {exception_message}"

        if output_level == GradingOutputLevel.ExceptionMessage:
            pytest.fail(fail_message, pytrace=False)

        assert output_level == GradingOutputLevel.FullTraceback

        if exception_traceback := response.get("execution_traceback", ""):
            fail_message += f"{os.linesep * 2}{exception_traceback}"

        pytest.fail(fail_message, pytrace=False)

    elif response_status == ProcessStatusCode.TIMEOUT:
        pytest.fail("Student code initialization timed out", pytrace=False)

    elif response_status == ProcessStatusCode.NO_RESPONSE:
        pytest.fail(f"No response from initialization with timeout {initialization_timeout}", pytrace=False)

    elif response_status != ProcessStatusCode.SUCCESS:
        logger.warning(f"Unexpected status in response from student code server: {response}")
        pytest.fail(f"Unexpected status from student code server: {response_status}", pytrace=False)


@pytest.fixture
def sandbox(request: pytest.FixtureRequest, data_json: dict[str, Any] | None) -> Iterable[StudentFixture]:
    fixture, initialization_timeout = _initialize_sandbox_fixture(request, data_json, request.param)

    try:
        # TODO make sure to read student output and include in the exception message
        # TODO also get this configuration by reading from the marker
        response = fixture.start_student_code_server(initialization_timeout=initialization_timeout)
        _handle_sandbox_startup_errors(request, response, initialization_timeout)

        yield fixture
    finally:
        fixture._cleanup()


@pytest.fixture
def module_sandbox(request: pytest.FixtureRequest, data_json: dict[str, Any] | None) -> Iterable[StudentFixture]:
    """
    Module-scoped sandbox fixture that shares the same student code server across all tests in a module.
    This fixture automatically handles both single and multiple student code files:
    - Single file: State persists across all tests in the module
    - Multiple files: Each file gets its own cached sandbox with independent state

    This fixture combines the benefits of:
    - Module-level caching (sandbox created once per student file per module)
    - Automatic parameterization across multiple student code files
    - Proper test isolation per student code file

    Use this when tests need to share state or when you want to test stateful behavior.
    This fixture is more efficient for scenarios where setup is expensive.
    """
    plugin = request.config.result_collector_plugin  # type: ignore[attr-defined]
    module_name = request.module.__name__

    # Get the student code file from parameterization (if multiple files) or find the single file
    if hasattr(request, "param"):
        # Parameterized case - multiple student files
        student_files: StudentFiles = request.param
    else:
        # Non-parameterized case - single student file, need to find it manually
        data_dir = get_datadir(request.module)
        if data_dir is None or not data_dir.is_dir():
            pytest.fail("Data directory not found for module sandbox")

        student_code_pattern = getattr(request.module, "student_code_pattern", "student_code*.py")
        student_code_files_list = list(data_dir.glob(student_code_pattern))

        if not student_code_files_list:
            pytest.fail(f"No student code files found matching pattern '{student_code_pattern}'")

        if len(student_code_files_list) > 1:
            pytest.fail(
                f"Multiple student code files found: {[f.name for f in student_code_files_list]}. "
                f"This should have been parameterized. Please check pytest_generate_tests."
            )

        # Set up file paths
        leading_file = data_dir / "leading_code.py"
        trailing_file = data_dir / "trailing_code.py"
        setup_code_file = data_dir / "setup_code.py"
        student_files = StudentFiles(leading_file, trailing_file, student_code_files_list[0], setup_code_file)

    student_code_file = student_files.student_code_file

    # Create cache key
    cache_key = (module_name, str(student_code_file))

    # Check if we already have a cached sandbox for this module/student code combination
    if cache_key not in plugin.module_sandbox_cache:
        # Check if we already recorded an initialization error for this module/file
        if cache_key in plugin.module_init_errors:
            # Re-raise the stored error for this test
            pytest.fail(plugin.module_init_errors[cache_key], pytrace=False)

        # Create new sandbox and cache it
        fixture, initialization_timeout = _initialize_sandbox_fixture(request, data_json, student_files)

        try:
            response = fixture.start_student_code_server(initialization_timeout=initialization_timeout)
            _handle_sandbox_startup_errors(request, response, initialization_timeout)

            # Cache the fixture for reuse within this module
            plugin.module_sandbox_cache[cache_key] = fixture
        except BaseException as e:
            # If initialization fails, store the error message and cleanup
            # Note: We catch BaseException because pytest.fail() raises Failed which inherits from BaseException, not Exception
            error_message = f"Module sandbox initialization failed for {student_code_file.name}: {e!s}"
            plugin.module_init_errors[cache_key] = error_message
            fixture._cleanup()
            # Re-raise for this test
            raise

    # Return the cached sandbox (shared across all tests for this student file)
    return plugin.module_sandbox_cache[cache_key]
    # Note: We don't cleanup here - cleanup happens at module teardown via pytest_sessionfinish


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """
    Generate parameterized tests for sandbox and parameterized_module_sandbox fixtures.
    This is where the parameterization for multiple student code files happens.
    """

    # Get the data directory next to the test file
    data_dir = get_datadir(metafunc.module)

    if data_dir is None:
        raise ValueError

    # Check if we need to parametrize sandbox or module_sandbox
    if "sandbox" in metafunc.fixturenames or "module_sandbox" in metafunc.fixturenames:
        if data_dir.is_dir():
            student_code_pattern = metafunc.module.__dict__.get("student_code_pattern", "student_code*.py")

            # Find student code files
            leading_file = data_dir / "leading_code.py"
            trailing_file = data_dir / "trailing_code.py"
            setup_code_file = data_dir / "setup_code.py"

            student_code_files = list(data_dir.glob(student_code_pattern))

            file_tups = [
                StudentFiles(leading_file, trailing_file, student_code_file, setup_code_file) for student_code_file in student_code_files
            ]
            file_stems = [file_tup.student_code_file.stem for file_tup in file_tups]

            # Parametrize the appropriate fixture
            if "sandbox" in metafunc.fixturenames:
                metafunc.parametrize("sandbox", file_tups, indirect=True, ids=file_stems)
            elif "module_sandbox" in metafunc.fixturenames:
                metafunc.parametrize("module_sandbox", file_tups, indirect=True, ids=file_stems)
        else:
            pass


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Registers command-line options for the plugin.
    """
    group = parser.getgroup("pytest_pl_autograder", "Prairielearn Python Autograder Options")

    group.addoption(
        "--worker-username",
        action="store",
        default=None,
        help="The username for the user of the worker process.",
    )


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


def pytest_runtest_setup(item):
    # TODO clean up this function
    marker = item.get_closest_marker("sandbox")
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


@pytest.hookimpl(trylast=True)  # force the other plugins to initialise, fixes issue with capture not being properly initialized
def pytest_configure(config: Config) -> None:
    # config.addinivalue_line("markers", "benchmark: mark a test with custom benchmark settings.")
    # bs = config._benchmarksession = BenchmarkSession(config)
    # bs.handle_loading()
    # config.pluginmanager.register(bs, "pytest-benchmark")

    # Add a marker for the sandbox fixture to set the initialization timeout
    config.addinivalue_line("markers", "sandbox_timeout(timeout_value): sets a timeout for initialization of the sandbox fixture")

    # Only register our plugin if it hasn't been already (e.g., in case of multiple conftests)
    if not hasattr(config, "result_collector_plugin"):
        config.result_collector_plugin = ResultCollectorPlugin()  # type: ignore[attr-defined]
        config.pluginmanager.register(config.result_collector_plugin)  # type: ignore[attr-defined]


class ResultCollectorPlugin:
    collected_results: dict[str, TestResult]
    student_feedback_data: dict[str, FeedbackFixture]
    grading_data: dict[str, Any]
    module_sandbox_cache: dict[tuple[str, str], StudentFixture]
    module_init_errors: dict[tuple[str, str], str]  # Stores initialization errors by (module_name, file_path)

    def __init__(self) -> None:
        self.collected_results = {}
        self.student_feedback_data = {}
        self.grading_data = {}
        self.module_sandbox_cache = {}
        self.module_init_errors = {}

    def pytest_configure(self, config: Config) -> None:
        """
        Register our custom marker to avoid warnings.
        """
        config.addinivalue_line(
            "markers", "grading_data(name, points, include_stdout_feedback=True): Mark a test with custom data that can be injected."
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo) -> Iterable[None]:
        """
        Hook wrapper to capture test outcomes.
        """
        outcome = yield
        report: _pytest.reports.TestReport = outcome.get_result()  # type: ignore[attr-defined]
        marker = item.get_closest_marker("grading_data")  # Ensure the marker is registered

        if marker:
            self.grading_data[item.nodeid] = marker.kwargs

        # Make a report for the setup phase, replace with the call phase if it happens later
        if report.when == "setup":
            self.collected_results[report.nodeid] = TestResult(report=report, call=call, stdout="")
            # Add a default outcome if not already set

        elif report.when == "call":
            # Get accumulated stdout from the student fixture if available
            accumulated_stdout = ""
            funcargs = getattr(item, "funcargs", None)
            if funcargs and "sandbox" in funcargs:
                student_fixture = funcargs.get("sandbox")
                if student_fixture and hasattr(student_fixture, "get_accumulated_stdout"):
                    stdout_content = student_fixture.get_accumulated_stdout()
                    if stdout_content.strip():  # Only store if there's actual content
                        accumulated_stdout = stdout_content

            self.collected_results[report.nodeid] = TestResult(report=report, call=call, stdout=accumulated_stdout)
            # You could store more details here if needed
            # item.config.my_test_results[report.nodeid] = {
            #     "outcome": report.outcome,
            #     "duration": report.duration,
            # }

        fixture = None
        # This code section appears to be unused legacy code
        # The actual fixture storage is now handled in the "call" phase above

        if fixture is not None and not isinstance(fixture, StudentFixture):
            pass
            # raise TypeError(
            #     f"unexpected type for `benchmark` in funcargs, {fixture!r} must be a BenchmarkFixture instance. "
            #     "You should not use other plugins that define a `benchmark` fixture, or return and unexpected value if you do redefine it."
            # )
        # if fixture:
        #     fixture.skipped = outcome.get_result().outcome == "skipped"

    @pytest.fixture
    def feedback(self, request: pytest.FixtureRequest) -> FeedbackFixture:
        """
        A fixture that allows tests to add feedback messages and scores.
        """
        nodeid = request.node.nodeid

        # Initialize feedback for this test if it doesn't exist
        if nodeid not in self.student_feedback_data:
            self.student_feedback_data[nodeid] = FeedbackFixture(test_id=nodeid)

        return self.student_feedback_data[nodeid]

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> Iterable[None]:
        """
        Hook wrapper to process test results after the session finishes.
        Also cleans up any cached module sandboxes.
        """
        # Clean up all cached module sandboxes before processing results
        for cache_key, fixture in list(self.module_sandbox_cache.items()):
            try:
                fixture._cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up module sandbox for {cache_key}: {e}")
        self.module_sandbox_cache.clear()

        yield  # Let other sessionfinish hooks run

        # print("\n--- Custom Test Results Summary (via Plugin Class) ---")
        # for nodeid, outcome in self.collected_results.items():
        #     print(f"Test: {nodeid} -> Outcome: {outcome}")
        # print("--------------------------------------------------")

        # # Example: Check the result of a specific test by its nodeid
        # target_nodeid = "test_example.py::test_passing_example" # Replace with a test you have
        # if target_nodeid in self.collected_results:
        #     print(f"\nResult for '{target_nodeid}': {self.collected_results[target_nodeid]}")
        # else:
        #     print(f"\n'{target_nodeid}' not found or no results collected.")

        # Collect all student feedback and generate the final report.
        final_results = []

        for item in session.items:
            nodeid = item.nodeid

            # for nodeid, feedback_obj in self.student_feedback_data.items():
            grading_data = self.grading_data.setdefault(nodeid, {"name": nodeid, "points": 1})

            if nodeid not in self.collected_results:
                continue  # Skip if no results collected for this test

            test_result = self.collected_results[nodeid]
            report = test_result.report
            call = test_result.call
            outcome = report.outcome

            if nodeid in self.student_feedback_data:
                feedback_obj = self.student_feedback_data[nodeid]
            else:
                # Create an empty feedback object if none was created during the test
                feedback_obj = FeedbackFixture(test_id=nodeid)

            # If the test failed (in any phase), add the exception message to the feedback
            if report.outcome == "failed" and call.excinfo is not None:
                output_level: GradingOutputLevel = get_output_level_marker(item.get_closest_marker("output"))

                logger.debug(f"Grading output level set to: {output_level}")

                # Customize the message based on the failure phase
                if report.when == "setup":
                    phase_message = "Student code execution failed with an exception"
                elif report.when == "teardown":
                    phase_message = "Student code teardown failed with an exception"
                else:
                    phase_message = "Student code grading failed with an exception"

                if output_level == GradingOutputLevel.ExceptionName:
                    exception_name = call.excinfo.type.__name__
                    fail_message = f"{phase_message}: {exception_name}"
                    feedback_obj.add_message(fail_message)

                elif output_level == GradingOutputLevel.ExceptionMessage:
                    exception_name = call.excinfo.type.__name__
                    # TODO make this work with multiline messages somehow?
                    exception_message = str(call.excinfo.value).split(os.linesep)[0]
                    fail_message = f"{phase_message}: {exception_name}{os.linesep}Exception Message: {exception_message}"
                    feedback_obj.add_message(fail_message)

                # If showing more than the exception name, show the message + full traceback
                else:
                    feedback_obj.add_message(str(call.excinfo.getrepr(style="no")))

            # Check if stdout feedback should be included (default True)
            include_stdout_feedback = grading_data.get("include_stdout_feedback", True)
            if include_stdout_feedback and test_result.stdout:
                feedback_obj.add_message(f"Student code output:{os.linesep}{test_result.stdout}")

            res_obj = feedback_obj.to_dict()
            res_obj["name"] = grading_data.get("name", nodeid)
            res_obj["max_points"] = grading_data.get("points", 1)

            if report.when in ["setup", "teardown"] and report.outcome == "failed":
                res_obj["outcome"] = "error"
            else:
                res_obj["outcome"] = outcome

            # Check if this test failed due to a module initialization error
            # If so, clear the message since it will be shown in the top-level output
            for (module_name, file_path), error_msg in self.module_init_errors.items():
                if nodeid.startswith(module_name.split(".")[-1]):
                    # This test is from a module with an init error, clear the repetitive message
                    res_obj["message"] = ""

            if outcome == "passed":
                if not feedback_obj.final_score_override:
                    res_obj["points_frac"] = 1.0
                # Otherwise, we just use the set points value

            elif res_obj["points_frac"] is None:
                if outcome == "failed":
                    res_obj["points_frac"] = 0.0
                elif outcome == "skipped":
                    # Skipped tests don't contribute to the score
                    # but also don't count as failures
                    res_obj["points_frac"] = 0.0
                    res_obj["outcome"] = "skipped"
                else:
                    # TODO fill in logic for other outcomes
                    # e.g., "xpassed", "xfailed", etc.
                    # For now, we raise an error for unexpected outcomes
                    raise ValueError(f"Unexpected outcome '{outcome}' for test '{nodeid}'.")

            res_obj["points"] = res_obj["points_frac"] * res_obj["max_points"]
            final_results.append(res_obj)
        # TODO add gradable property
        # https://prairielearn.readthedocs.io/en/latest/externalGrading/#grading-results

        total_score = sum(res["points_frac"] * res["max_points"] for res in final_results)

        # TODO should probably just raise an exception if this is zero bc it's almost certainly a mistake
        total_possible_score = sum(res["max_points"] for res in final_results)

        res_dict = {
            "score": total_score / total_possible_score if total_possible_score > 0 else 0,
            "tests": final_results,
        }

        # Add top-level output message if there were any module initialization errors
        if self.module_init_errors:
            error_messages = []
            for (module_name, file_path), error_msg in self.module_init_errors.items():
                error_messages.append(error_msg)
            res_dict["output"] = "Module initialization errors:\n" + "\n".join(error_messages)

        print_autograder_summary(session, final_results)

        # Example: Save to a JSON file
        # TODO make this configurable via command line options
        output_path = session.config.rootpath / "autograder_results.json"
        with open(output_path, "w") as f:
            json.dump(res_dict, f, indent=4, sort_keys=True)
        print(f"\nAutograder results saved to {output_path}")

        # For autograding platforms like Gradescope, you might format
        # it according to their specific JSON format.
        # Example Gradescope format:
        # {
        #   "score": 0,
        #   "output": "Overall feedback",
        #   "tests": [
        #     {"name": "Test Case 1", "score": 2, "max_score": 5, "output": "Feedback for test 1"},
        #     ...
        #   ]
        # }


def print_autograder_summary(session: pytest.Session, test_results: list[dict[str, Any]]) -> None:
    """
    Print a summary of the autograder results in a formatted table.
    This function is called at the end of the test session to display
    the results in a readable format.
    """
    if not session.config.pluginmanager.hasplugin("terminalreporter"):
        print("Terminal reporter plugin not found. Cannot print autograder summary.")
        return

    # Get the terminal reporter and its writer
    reporter_plugin = session.config.pluginmanager.getplugin("terminalreporter")
    if reporter_plugin is None:
        print("Terminal reporter plugin not found. Cannot print autograder summary.")
        return
    reporter: _pytest.terminal.TerminalReporter = cast(_pytest.terminal.TerminalReporter, reporter_plugin)
    writer = reporter._tw  # Access the internal TerminalWriter instance

    if not test_results:
        writer.line("No tests were run or no results collected.")
        return

    # Create a PrettyTable instance
    table = PrettyTable()
    table_headers = ["Test Name", "Score", "Feedback"]
    table.field_names = table_headers

    # Set alignment for columns
    table.align["Test Name"] = "l"
    table.align["Score"] = "c"
    table.align["Feedback"] = "l"

    # Add data rows
    for result in test_results:
        table.add_row([result["test_id"], result["points"], result["message"]])

    # TODO this is incorrect as the fractions were changed in the display shown to PL.
    # Can fix this later since most people will just see the output shown in PL.

    # Calculate total score
    total_score = sum(result["points"] for result in test_results)
    max_score = len(test_results)

    # Add total score row
    table.add_row(["Total Score", f"{total_score}/{max_score}", ""])

    # Set table style (optional, but 'grid' is similar to previous tabulate output)
    # You can experiment with other styles like:
    # table.set_style(MARKDOWN)
    # table.set_style(SINGLE_BORDER)
    # table.set_style(DOUBLE_BORDER)
    # For a grid-like appearance, PrettyTable's default is quite good,
    # or you can explicitly set it to something like:
    # from prettytable import MSWORD_FRIENDLY, PLAIN_COLUMNS, ORGMODE
    # table.set_style(MSWORD_FRIENDLY)

    # Try to make the table fit the terminal width
    # PrettyTable's get_string method has a 'max_width' parameter for columns
    # We distribute the available width among the columns.
    terminal_width = writer.fullwidth

    # Estimate average column width, subtracting for borders and padding
    # This is a heuristic, PrettyTable will adjust
    num_columns = len(table_headers)
    estimated_col_width = (terminal_width // num_columns) - 4  # Subtract for borders/padding

    # Set max_width for each column to attempt fitting
    # PrettyTable will wrap text if it exceeds max_width
    for field in table.field_names:
        table.max_width[field] = estimated_col_width

    # Generate the table string
    # prettytable's get_string() will automatically handle column width adjustments
    # and wrapping based on max_width and terminal size.
    table_string = table.get_string()

    # Get the width of the generated table from the first line
    # Prettytable's output includes the borders, so this should be accurate.
    table_width = len(table_string.splitlines()[0])

    # Print the autograder summary as a centered header above the table
    summary_title = "Autograder Summary"
    # Calculate padding for centering. Subtract 2 for the outer '+' characters.
    # If the title is longer than the table width, just print it without centering.
    if table_width > len(summary_title) + 2:
        padding_left = (table_width - len(summary_title) - 2) // 2
        padding_right = (table_width - len(summary_title) - 2) - padding_left
        header_line = f"+{'=' * padding_left} {summary_title} {'=' * padding_right}+"
    else:
        # Fallback if the table is very narrow
        header_line = f"+{summary_title.center(table_width - 2)}+"

    writer.line(os.linesep)  # Add a newline before the custom header
    writer.line(header_line, bold=True)

    # Print the generated table using the TerminalWriter
    for line in table_string.splitlines():
        writer.line(line)

    writer.write(f"{os.linesep}Final Grade: {total_score}/{max_score}{os.linesep}", bold=True)
