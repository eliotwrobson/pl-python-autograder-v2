import math
import platform
from collections import defaultdict
from pathlib import Path

import pytest

pytest_plugins = ("pytester",)
platform  # noqa: B018
import json

# --- Configuration ---
# The root directory where your scenario folders are located
SCENARIO_ROOT = Path(__file__).parent / "scenario_root"

# The file you want to copy into each scenario directory.
# This could be your autograder's conftest.py, or a specific test file.
# FILE_TO_COPY = Path(__file__).parent / "scenario_root" / "scenario.py"

CONVERSION_DICT = {
    "error": "errors",
    "passed": "passed",
    "failed": "failed",
    "skipped": "skipped",
}


# --- Helper Functions ---
def print_file_structure(path: Path, indent: str = "") -> None:
    """Recursively prints the file structure of a given directory."""
    print("-" * 100)

    for item in path.iterdir():
        print(indent + item.name)
        if item.is_dir():
            print_file_structure(item, indent + "  ")


def get_scenario_dirs(root_dir: Path):
    """
    Discovers all scenario directories within the given root_dir
    that start with 'test_'.
    """
    scenario_dirs = []
    for item in root_dir.iterdir():
        if item.is_dir() and item.name.startswith("test_"):
            scenario_dirs.append(item)

    return scenario_dirs


# --- Test Function with pytester ---
@pytest.mark.parametrize("scenario_dir", get_scenario_dirs(SCENARIO_ROOT), ids=lambda d: d.name)
def test_autograder_scenario_with_pytester(pytester: pytest.Pytester, scenario_dir: Path) -> None:
    """
    Tests each autograder scenario using the pytester fixture:
    1. Copies all files from the scenario directory (and the common testing file)
       into pytester's isolated test directory.
    2. Runs pytest within that isolated environment.
    3. Asserts on the pytest outcome (passed, failed, etc.) and captured stdout/stderr.
    """
    print(f"\n--- Running scenario: {scenario_dir.name} with pytester ---")

    # Ensure the common file to copy exists
    # if not FILE_TO_COPY.exists():
    #     pytest.fail(f"Error: FILE_TO_COPY '{FILE_TO_COPY}' does not exist.")

    # 1. Copy all files from the scenario directory into pytester's test directory
    # pytester.makepyfile() is for creating files with content,
    # pytester.copy_example() is good for copying directories or specific files.
    # We will iterate and copy all files from the scenario_dir and the common file.
    pytester_scenario_dir = pytester.mkdir(scenario_dir.name)

    new_file_name = scenario_dir.name + ".py"
    expected_outcome_file_name = "expected_outcome.json"
    expected_outcome_dict = None

    # Copy files from the specific scenario directory
    for item in scenario_dir.iterdir():
        if item.is_file():
            if item.name == "scenario.py":
                print("in the scenario.py branch", scenario_dir.name)
                pytester.path.joinpath(new_file_name).write_text(item.read_text())  # Copy the file content
            elif item.name == "expected_outcome.json":
                expected_outcome_dict = json.loads(item.read_text())
            elif item.name != "__init__.py":  # Ignore __init__.py files
                pytester_scenario_dir.joinpath(item.name).write_text(item.read_text())  # Copy the file content
                print(f"Copied '{item.name}' to pytester's testdir.")
        elif item.is_dir():
            raise ValueError("Scenario directories should not contain subdirectories. Please flatten the structure.")

    if expected_outcome_dict is None:
        pytest.fail(f"Error: expected_outcome.json not found in scenario directory '{scenario_dir.name}'.")

    # You can pass additional arguments to pytest here, e.g., '-s' for print statements
    result = pytester.runpytest("-v", new_file_name)

    results_obj = json.loads((pytester.path / "autograder_results.json").read_text())

    """
    #NOTE uncomment this to save the results object to a file
    output_path = scenario_dir / "autograder_output.json"
    print(output_path)
    with open(output_path, "w") as f:
        json.dump(results_obj, f, indent=4, sort_keys=True)
    """

    expected_data_obj = expected_outcome_dict["expected_data_object"]

    assert math.isclose(expected_data_obj["score"], results_obj["score"])

    outcome_dict = defaultdict(int)

    # TODO add tests for the tests object
    test_results_obj = {test_result["test_id"]: test_result for test_result in results_obj["tests"]}
    for expected_test in expected_data_obj["tests"]:
        test_id = expected_test["test_id"]

        # TODO make this not depend on the file name
        assert test_id in test_results_obj, f"Test '{test_id}' not found in results."
        actual_test = test_results_obj[test_id]

        # assert actual_test["message"] == expected_test["message"], f"Message mismatch for test '{test_id}'."
        assert actual_test["max_points"] == expected_test["max_points"], f"Max points mismatch for test '{test_id}'."
        assert math.isclose(expected_test["points"], actual_test["points"]), f"Points mismatch for test '{test_id}'."
        assert actual_test["outcome"] == expected_test["outcome"], f"Outcome mismatch for test '{test_id}'."
        outcome_dict[CONVERSION_DICT[actual_test["outcome"]]] += 1

    result.assert_outcomes(**outcome_dict)

    # For a scenario where student code is expected to fail:
    # result.assert_outcomes(failed=1, passed=1) # If one test fails and one passes

    # You can also inspect stdout and stderr if your plugin prints output
    # result.stdout.fnmatch_lines(
