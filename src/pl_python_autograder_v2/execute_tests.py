import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from types import ModuleType


def get_test_module(test_file_path: Path) -> ModuleType:
    """
    Import test file located at test_file_path as a module. This is so we can use the
    unittest test loader function loadTestsFromModule.
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

    loader = unittest.TestLoader()
    tests = loader.loadTestsFromModule(test_module)
    result = unittest.TestResult()
    tests.run(result)
    print(result)
