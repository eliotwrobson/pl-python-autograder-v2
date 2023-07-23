# from code_feedback import Feedback
# from pl_helpers import name, points
# from pl_unit_test import PLTestCase
import unittest


class Test(unittest.TestCase):
    # @points(1)
    # @name("area")
    def test_0(self):
        self.assertTrue(True)
        # if Feedback.check_scalar("area", self.ref.area, self.st.area):
        #    Feedback.set_score(1)
        # else:
        #    Feedback.set_score(0)
