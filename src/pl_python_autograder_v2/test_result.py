import typing as t
import unittest as ut

# Use this for IO capture:
# https://docs.python.org/3/library/contextlib.html#contextlib.redirect_stdout
# Will be important when trying to get threading to work.


# https://github.com/gradescope/gradescope-utils/blob/master/gradescope_utils/autograder_utils/json_test_runner.py
class PLTestResult(ut.TestResult):
    successes: t.List[ut.TestCase] = []

    def addSuccess(self, test: ut.TestCase) -> None:
        self.successes.append(test)
        # print("heereo")
        # print(test)
