import typing as t
import unittest as ut


class PLTestResult(ut.TestResult):
    successes: t.List[ut.TestCase] = []

    def addSuccess(self, test: ut.TestCase) -> None:
        self.successes.append(test)
        # print("heereo")
        # print(test)
