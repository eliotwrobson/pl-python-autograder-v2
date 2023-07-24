import typing as t
import unittest as ut


# Modeled after this: https://github.com/PrairieLearn/PrairieLearn/blob/master/graders/python/python_autograder/pl_unit_test.py
class PLTestCase(ut.TestCase):
    # Legacy variable names
    st: t.NamedTuple
    ref: t.NamedTuple

    # TODO pass in safe executor class for student code here.
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

    # TODO actually, we want these values to be passed in by the test runner instead
    # of the constructor (so, a collection of test cases can be run against different student code).
    def callStudentCode(self) -> None:
        """
        Call student code and load student and answer tuples.
        Called during the setUp phase during each test.
        """

        ref_result: t.Dict = {}
        student_result: t.Dict = {}

        # TODO these variable names suck, support them for legacy cases but redefine as something better.
        answerTuple = t.NamedTuple("answerTuple", ref_result.keys())  # type: ignore
        self.ref = answerTuple(**ref_result)
        studentTuple = t.NamedTuple("studentTuple", student_result.keys())  # type: ignore
        self.st = studentTuple(**student_result)

    def _callSetUp(self) -> None:
        self.callStudentCode()
        # Overriding function so client code can still call setup, but we
        # can execute and store results of student code here.
        self.setUp()
