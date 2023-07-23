# from code_feedback import Feedback
# from pl_helpers import name, points
# from pl_unit_test import PLTestCase
from pl_python_autograder_v2 import loader, test_case


class Test(test_case.PLTestCase):
    # @points(1)
    # @name("area")
    def test_0(self) -> None:
        loader.PLTestLoader(loader.PLTestSuite)
        self.assertTrue(True)
        # if Feedback.check_scalar("area", self.ref.area, self.st.area):
        #    Feedback.set_score(1)
        # else:
        #    Feedback.set_score(0)
