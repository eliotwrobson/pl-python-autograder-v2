import importlib.machinery
import importlib.util
from pathlib import Path
from types import ModuleType

from .loader import PLTestLoader, PLTestSuite
from .restricted_execution import RestrictedExecutor
from .test_result import PLTestResult


def get_test_module(test_file_path: Path) -> ModuleType:
    """
    Import test file located at test_file_path as a module. This is so we can use the
    unittest test loader function loadTestsFromModule.

    Modeled after code here: https://stackoverflow.com/a/41595552/2923069
    TODO use cleaned up version given there.
    """
    import_loader = importlib.machinery.SourceFileLoader("test", str(test_file_path))
    spec = importlib.util.spec_from_loader("test", import_loader)

    if spec is None:
        raise ImportError(f"Module spec not found for file in path {test_file_path}")

    test_module = importlib.util.module_from_spec(spec)
    import_loader.exec_module(test_module)
    return test_module


def execute_tests(
    test_file_path: Path,
    student_code_path: Path,
) -> None:
    test_module = get_test_module(test_file_path)
    # test_code = test_file_path.read_text()
    # test_module = import_module(str(test_file_path))

    restricted_student_code = RestrictedExecutor(student_code_path.read_text())
    restricted_student_code.execute()
    print(restricted_student_code.get_defined_symbols())

    loader = PLTestLoader(PLTestSuite)
    suite = loader.loadTestsFromModule(test_module)
    result = PLTestResult()
    suite.runWithCode(result, restricted_student_code)

    print(result)
    print(result.successes)
    print(result.errors)
    # print(result.successes[0], type(result.successes[0]))
