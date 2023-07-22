import unittest

# Define custom test loader that schedules tests concurrently (by default) or in parallel.
class PLTestLoader(unittest.TestLoader):

    def __init__(self):
        pass
