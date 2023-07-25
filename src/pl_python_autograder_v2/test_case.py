import typing as t
import unittest as ut
from collections import namedtuple

from .restricted_execution import RestrictedExecutor


# Modeled after this: https://github.com/PrairieLearn/PrairieLearn/blob/master/graders/python/python_autograder/pl_unit_test.py
class PLTestCase(ut.TestCase):
    # Legacy variable names
    # TODO if not set in init, are these like default constructed or something?
    st: t.Any
    ref: t.Any

    # TODO replace these dicts with executor objects once those are written
    ref_result: t.Optional[RestrictedExecutor]
    student_result: t.Optional[RestrictedExecutor]

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self.ref_result = None
        self.student_result = None
        super().__init__(*args, **kwargs)

    def setTestCaseCode(self, ref_result: RestrictedExecutor, student_result: RestrictedExecutor) -> None:
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

        self.ref_result.execute()
        ref_result_symbols = self.ref_result.get_defined_symbols()

        # TODO these variable names suck, support them for legacy cases but redefine as something better.
        answerTuple = namedtuple("answerTuple", ref_result_symbols.keys())  # type: ignore
        self.ref = answerTuple(**ref_result_symbols)

        self.student_result.execute()
        student_result_symbols = self.student_result.get_defined_symbols()
        studentTuple = namedtuple("studentTuple", student_result_symbols.keys())  # type: ignore
        self.st = studentTuple(**student_result_symbols)

    def _callSetUp(self) -> None:
        self.callStudentCode()
        # Overriding function so client code can still call setup, but we
        # can execute and store results of student code here.
        self.setUp()
