import typing as t
import unittest as ut
from collections import namedtuple


# Modeled after this: https://github.com/PrairieLearn/PrairieLearn/blob/master/graders/python/python_autograder/pl_unit_test.py
class PLTestCase(ut.TestCase):
    # Legacy variable names
    # TODO if not set in init, are these like default constructed or something?
    st: t.NamedTuple
    ref: t.NamedTuple

    # TODO replace these dicts with executor objects once those are written
    ref_result: t.Optional[t.Dict]
    student_result: t.Optional[t.Dict]

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self.ref_result = None
        self.student_result = None
        super().__init__(*args, **kwargs)

    def setTestCaseCode(self, ref_result: t.Dict, student_result: t.Dict) -> None:
        self.ref_result = ref_result
        self.student_result = student_result

    # TODO actually, we want these values to be passed in by the test runner instead
    # of the constructor (so, a collection of test cases can be run against different student code).
    def callStudentCode(self) -> None:
        """
        Call student code and load student and answer tuples.
        Called during the setUp phase during each test.
        """

        if self.ref_result is None or self.student_result is None:
            raise ValueError("Executor objects are None. Did you forget to call setTestCaseCode?")

        # TODO these variable names suck, support them for legacy cases but redefine as something better.
        answerTuple = namedtuple("answerTuple", self.ref_result.keys())  # type: ignore
        self.ref = answerTuple(**self.ref_result)
        studentTuple = namedtuple("studentTuple", self.student_result.keys())  # type: ignore
        self.st = studentTuple(**self.student_result)

    def _callSetUp(self) -> None:
        self.callStudentCode()
        # Overriding function so client code can still call setup, but we
        # can execute and store results of student code here.
        self.setUp()
