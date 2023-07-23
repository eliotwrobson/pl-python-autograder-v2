import typing as t
import unittest


# https://stackoverflow.com/questions/4710142/can-pythons-unittest-test-in-parallel-like-nose-can/17059844#17059844
# https://stackoverflow.com/questions/13605669/python-unittest-can-we-repeat-unit-test-case-execution-for-a-configurable-numbe/13606054#13606054
# https://github.com/testing-cabal/testtools/blob/master/testtools/testsuite.py
class PLTestSuite(unittest.TestSuite):
    pass


# Define custom test loader that schedules tests concurrently (by default)
# or in parallel.
class PLTestLoader(unittest.TestLoader):
    # Allow passing in desired suite class
    # TODO define suite_class as base class,
    # inherited classes will change how tests are run
    def __init__(self, suite_class: t.Type[PLTestSuite]) -> None:
        super().__init__()
        self.suiteClass = suite_class
