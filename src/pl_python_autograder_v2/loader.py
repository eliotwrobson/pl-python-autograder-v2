import unittest
import typing as t

class PLTestSuite(unittest.TestSuite):
    pass

# Define custom test loader that schedules tests concurrently (by default) or in parallel.
class PLTestLoader(unittest.TestLoader):

    # Allow passing in desired suite class
    # TODO define suite_class as base class,
    # inherited classes will change how tests are run
    def __init__(self, suite_class: t.Type[PLTestSuite]) -> None:
        super().__init__()
        self.suiteClass = suite_class
