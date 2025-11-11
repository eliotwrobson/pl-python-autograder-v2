import json
import logging
import os
import sys
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any
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
from .utils import ProcessStatusCode
from .utils import get_output_level_marker

logger = logging.getLogger(__name__)


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


# TODO maybe change to the module scope??
@pytest.fixture
def sandbox(request: pytest.FixtureRequest, data_json: dict[str, Any] | None) -> Iterable[StudentFixture]:
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

    # TODO maybe make it possible to add custom generators for starting variables?
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

    # Check for the custom mark
    marker = request.node.get_closest_marker("sandbox_timeout")
    if marker:
        # Markers can have positional arguments (args) or keyword arguments (kwargs)
        # We'll assume the timeout is the first positional argument
        if marker.args:
            initialization_timeout = marker.args[0]

    fixture = StudentFixture(
        file_names=request.param,
        import_whitelist=import_whitelist,
        import_blacklist=import_blacklist,
        starting_vars=starting_vars,
        builtin_whitelist=builtin_whitelist,
        names_for_user_list=names_for_user_list,
        worker_username=request.config.getoption("--worker-username"),
    )

    try:
        # TODO make sure to read student output and include in the exception message
        # TODO also get this configuration by reading from the marker
        response = fixture.start_student_code_server(initialization_timeout=initialization_timeout)
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

            # TODO make this not an assert?
            assert output_level == GradingOutputLevel.FullTraceback

            if exception_traceback := response.get("execution_traceback", ""):
                fail_message += f"{os.linesep * 2}{exception_traceback}"

            pytest.fail(fail_message, pytrace=False)

        elif response_status == ProcessStatusCode.TIMEOUT:
            # Don't get the exception message since there usually isn't one for timeouts
            pytest.fail("Student code initialization timed out", pytrace=False)

        elif response_status == ProcessStatusCode.NO_RESPONSE:
            # Don't get the exception message since there usually isn't one for timeouts
            pytest.fail(f"No response from initialization with timeout {initialization_timeout}", pytrace=False)

        elif response_status != ProcessStatusCode.SUCCESS:
            logger.warning(f"Unexpected status in response from student code server: {response}")
            pytest.fail(f"Unexpected status from student code server: {response_status}", pytrace=False)

        yield fixture
    finally:
        fixture._cleanup()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """
    TODO this is where the parameterization inside the folder is happening
    """

    # # Let's assume you have a 'data' directory next to your test file
    data_dir = get_datadir(metafunc.module)

    if data_dir is None:
        raise ValueError

    if "sandbox" in metafunc.fixturenames:
        if data_dir.is_dir():
            student_code_pattern = metafunc.module.__dict__.get("student_code_pattern", "student_code*.py")

            # print("IN THE DATA DIR")
            # Find a specific data file, e.g., 'test_data.txt'
            leading_file = data_dir / "leading_code.py"
            trailing_file = data_dir / "trailing_code.py"
            setup_code_file = data_dir / "setup_code.py"

            student_code_files = list(data_dir.glob(student_code_pattern))

            file_tups = [
                StudentFiles(leading_file, trailing_file, student_code_file, setup_code_file) for student_code_file in student_code_files
            ]
            file_stems = [file_tup.student_code_file.stem for file_tup in file_tups]

            metafunc.parametrize("sandbox", file_tups, indirect=True, ids=file_stems)
            # else:
            #    pass
            # pytest.skip(f"Data file '{data_file.name}' not found in '{data_dir}'")
        else:
            pass
            # pytest.skip(f"Data directory '{data_dir}' not found.")


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
    collected_results: dict[str, tuple[_pytest.reports.TestReport, pytest.CallInfo]]
    student_feedback_data: dict[str, FeedbackFixture]
    grading_data: dict[str, Any]
    student_fixtures: dict[str, StudentFixture]

    def __init__(self) -> None:
        self.collected_results = {}
        self.student_feedback_data = {}
        self.grading_data = {}
        self.student_fixtures = {}

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
            self.collected_results[report.nodeid] = (report, call)
            # Add a default outcome if not already set

        elif report.when == "call":
            self.collected_results[report.nodeid] = (report, call)
            # Store the student fixture if available for later stdout feedback
            try:
                # Use getattr with a fallback to avoid the typing issue
                funcargs = getattr(item, "funcargs", None)
                if funcargs and "sandbox" in funcargs:
                    student_fixture = funcargs["sandbox"]
                    if isinstance(student_fixture, StudentFixture):
                        self.student_fixtures[report.nodeid] = student_fixture
            except (AttributeError, KeyError):
                pass  # Fixture not available, which is fine
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
        """
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

            report, call = self.collected_results[nodeid]
            outcome = report.outcome

            if nodeid in self.student_feedback_data:
                feedback_obj = self.student_feedback_data[nodeid]
            else:
                # Create an empty feedback object if none was created during the test
                feedback_obj = FeedbackFixture(test_id=nodeid)

            # If the test failed, we can add the exception message to the feedback
            if report.outcome == "failed" and call.excinfo is not None:
                output_level: GradingOutputLevel = get_output_level_marker(item.get_closest_marker("output"))

                logger.debug(f"Grading output level set to: {output_level}")

                if output_level == GradingOutputLevel.ExceptionName:
                    exception_name = call.excinfo.type.__name__
                    fail_message = f"Student code grading failed with an exception: {exception_name}"
                    feedback_obj.add_message(fail_message)

                elif output_level == GradingOutputLevel.ExceptionMessage:
                    exception_name = call.excinfo.type.__name__
                    # TODO make this work with multiline messages somehow?
                    exception_message = str(call.excinfo.value).split(os.linesep)[0]
                    fail_message = (
                        f"Student code grading failed with an exception: {exception_name}{os.linesep}Exception Message: {exception_message}"
                    )
                    feedback_obj.add_message(fail_message)

                # If showing more than the exception name, show the message + full traceback
                else:
                    feedback_obj.add_message(str(call.excinfo.getrepr(style="no")))

            # Check if stdout feedback should be included (default True)
            include_stdout_feedback = grading_data.get("include_stdout_feedback", True)
            if include_stdout_feedback and nodeid in self.student_fixtures:
                student_fixture = self.student_fixtures[nodeid]
                accumulated_stdout = student_fixture.get_accumulated_stdout()
                if accumulated_stdout.strip():  # Only add if there's actual content
                    feedback_obj.add_message(f"Student code output:\n{accumulated_stdout}")

            res_obj = feedback_obj.to_dict()
            res_obj["name"] = grading_data.get("name", nodeid)
            res_obj["max_points"] = grading_data.get("points", 1)

            if report.when in ["setup", "teardown"] and report.outcome == "failed":
                res_obj["outcome"] = "error"
            else:
                res_obj["outcome"] = outcome

            if outcome == "passed":
                if not feedback_obj.final_score_override:
                    res_obj["points_frac"] = 1.0
                # Otherwise, we just use the set points value

            elif res_obj["points_frac"] is None:
                if outcome == "failed":
                    res_obj["points_frac"] = 0.0
                else:
                    # TODO fill in logic for other outcomes
                    # e.g., "skipped", "xpassed", etc.
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
            # TODO figure out something useful to put here (maybe single source of compilation failure??)
            # "output": "Overall feedback for the autograder session.",
            "tests": final_results,
        }

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
