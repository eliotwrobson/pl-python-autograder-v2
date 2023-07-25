import typing as t
import unittest as ut
from types import ModuleType

from .restricted_execution import RestrictedExecutor
from .test_case import PLTestCase


# https://stackoverflow.com/questions/4710142/can-pythons-unittest-test-in-parallel-like-nose-can/17059844#17059844
# https://stackoverflow.com/questions/13605669/python-unittest-can-we-repeat-unit-test-case-execution-for-a-configurable-numbe/13606054#13606054
# https://github.com/testing-cabal/testtools/blob/master/testtools/testsuite.py
class PLTestSuite(ut.TestSuite):
    # TODO change the type signature of this class so it can only take in PLTestSuites and PLTestCases
    def runWithCode(self, result: ut.TestResult, student_code_executor: RestrictedExecutor) -> ut.TestResult:
        """
        Call run() for each test, but first set executor objects on each one.
        """

        work_stack: t.List = list(self)

        while work_stack:
            test_suite_or_case = work_stack.pop()

            if isinstance(test_suite_or_case, PLTestCase):
                test_suite_or_case.setTestCaseCode(RestrictedExecutor(""), student_code_executor)
            elif isinstance(test_suite_or_case, PLTestSuite):
                work_stack.extend(test_suite_or_case)

        return super().run(result)


# Define custom test loader that schedules tests concurrently (by default)
# or in parallel.
class PLTestLoader(ut.TestLoader):
    suiteClass: t.Type[PLTestSuite]

    # Allow passing in desired suite class
    # TODO define suite_class as base class,
    # inherited classes will change how tests are run
    def __init__(self, suite_class: t.Type[PLTestSuite]) -> None:
        super().__init__()
        self.suiteClass = suite_class

    # TODO see if there's a way to override this type annotation without rewriting the function.
    # maybe do this in a .pyi file.
    def loadTestsFromModule(self, module: ModuleType, *args: t.Any, pattern: t.Any = None) -> PLTestSuite:
        return t.cast(PLTestSuite, super().loadTestsFromModule(module, *args, pattern=pattern))
