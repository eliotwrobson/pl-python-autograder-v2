from pathlib import Path

from pl_python_autograder_v2.execute_tests import execute_tests


def verify_thing() -> None:
    test_file_path = Path("tests/data/test.py")
    student_code_path = Path("tests/data/student_code.py")
    execute_tests(test_file_path, student_code_path)
