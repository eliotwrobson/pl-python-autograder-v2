import unittest

# Define custom test loader that schedules tests concurrently (by default) or in parallel.
class PLTestLoader(unittest.TestLoader):

    # Allow passing in desired suite class
    def __init__(self, suite_class):
        super().__init__()
        self.suiteClass = suite_class
