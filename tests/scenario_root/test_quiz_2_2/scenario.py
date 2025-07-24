import numpy as np
import pytest

from pl_pytest_autograder.fixture import DataFixture
from pl_pytest_autograder.fixture import FeedbackFixture
from pl_pytest_autograder.fixture import StudentFixture


def compute_fp_list(L: float, n: int, start: float, end: float) -> tuple[float, float, list[float]]:
    """
    Given:

    - L: the logarithm base 2 of the smallest positive floating point number
    - n: the number of bits in the mantissa
    - start: the smallest fp number to find (inclusive)
    - end: the largest fp number to find (inclusive)

    We assume base == 2

    Computes:

    - largest_fp: the largest positive floating point number
    - machine_epsilon: the machine epsilon
    - fp_lst: a list of all possible normalized floating point numbers in the range [start, end]
    """
    # L = np.log2(smallest_fp)

    # 1) largest fp
    U = -L
    largest_fp = 2 ** (U + 1) * (1 - 2 ** (-(n + 1)))

    # 2) machine epsilon
    machine_epsilon = 2 ** (-n)

    fp_lst = []

    # determine the exp range that covers [start, end]
    exp_start = np.floor(np.log2(start)).astype(int)
    exp_end = np.floor(np.log2(end)).astype(int)
    exp_min = L
    exp_max = -L

    # we only look through what is necessary, a simpler solution would be to loop through all possible exponents
    for exp in range(max(exp_start, exp_min), min(exp_end, exp_max) + 1):
        # find the first and last possible mantissas that fall in range
        mantissa_start = (start / (2**exp)) - 1
        mantissa_end = (end / (2**exp)) - 1
        mantissa_start_bits = max(0, np.ceil(mantissa_start * (2**n)).astype(int))
        mantissa_end_bits = min((2**n) - 1, np.floor(mantissa_end * (2**n)).astype(int))

        # loop through the possible mantissas
        for mantissa_bits in range(mantissa_start_bits, mantissa_end_bits + 1):
            mantissa = 1 + (mantissa_bits / (2**n))  # normalized mantissa
            value = mantissa * (2**exp)  # floating point value
            fp_lst.append(value)

    return largest_fp, machine_epsilon, sorted(fp_lst)


# TODO add a sandbox at the module level and use it in these tests


@pytest.mark.grading_data(name="largest_fp", points=1)
def test_0(sandbox: StudentFixture, feedback: FeedbackFixture, data_json: DataFixture) -> None:
    largest_fp_st = sandbox.query("largest_fp")

    assert largest_fp_st is not None, "largest_fp should not be None"

    assert isinstance(largest_fp_st, float), "largest_fp is not of correct type. It should be a float."

    largest_fp_ref, _, _ = compute_fp_list(
        data_json["params"]["L"],
        data_json["params"]["n"],
        data_json["params"]["start"],
        data_json["params"]["end"],
    )

    assert largest_fp_st == largest_fp_ref, "largest_fp has incorrect value."

    feedback.add_message("Good Job!")
    # feedback.set_score(1)

    # if self.ref.largest_fp == self.st.largest_fp:
    #     feedback.add_feedback("Good Job!")
    #     feedback.set_score(1)
    # else:
    #     feedback.add_feedback("largest_fp has incorrect value.")
    #     feedback.set_score(0)


@pytest.mark.grading_data(name="machine_epsilon", points=1)
def test_1(sandbox: StudentFixture, data_json: DataFixture, feedback: FeedbackFixture) -> None:
    machine_epsilon_st = sandbox.query("machine_epsilon")

    assert machine_epsilon_st is not None, "machine_epsilon should not be None"

    assert isinstance(machine_epsilon_st, float), "machine_epsilon is not of correct type. It should be a float."

    _, machine_epsilon_ref, _ = compute_fp_list(
        data_json["params"]["L"],
        data_json["params"]["n"],
        data_json["params"]["start"],
        data_json["params"]["end"],
    )

    assert machine_epsilon_st == machine_epsilon_ref, "machine_epsilon has incorrect value."

    feedback.add_message("Good Job!")

    # if self.ref.machine_epsilon == self.st.machine_epsilon:
    #     feedback.add_feedback("Good Job!")
    #     feedback.set_score(1)
    # else:
    #     feedback.add_feedback("machine_epsilon has incorrect value.")
    #     feedback.set_score(0)


@pytest.mark.grading_data(name="fp_lst", points=8)
def test_2(sandbox: StudentFixture, data_json: DataFixture, feedback: FeedbackFixture) -> None:
    fp_lst_st = sandbox.query("fp_lst")

    assert fp_lst_st is not None, "fp_lst should not be None"

    assert isinstance(fp_lst_st, list), "fp_lst is not of correct type. It should be a list."

    assert len(fp_lst_st) > 0, "fp_lst should not be empty"

    _, _, fp_lst_ref = compute_fp_list(
        data_json["params"]["L"],
        data_json["params"]["n"],
        data_json["params"]["start"],
        data_json["params"]["end"],
    )

    assert len(fp_lst_st) == len(fp_lst_ref), "fp_lst has incorrect length."

    # feedback.add_message("Good Job!")

    # if self.ref.fp_lst == self.st.fp_lst:
    #     feedback.add_feedback("Good Job!")
    #     feedback.set_score(1)

    # check length of list
    # if not feedback.check_list("fp_lst", fp_lst_ref, fp_lst_st):
    #     feedback.set_score(0)
    #     return

    # check list content within range
    start = fp_lst_ref[0]
    end = fp_lst_ref[-1]
    for st_val in fp_lst_st:
        assert start <= st_val <= end, "found value in fp_lst not within range"

    assert fp_lst_st == fp_lst_ref, "fp_lst has incorrect value."

    # # check list contents
    # for st_val, ref_val in zip(fp_lst_st, fp_lst_ref):
    #     if st_val != ref_val:
    #         feedback.add_feedback("inaccurate value found in fp_lst")
    #         feedback.set_score(0)
    #         return

    feedback.add_message("Good Job!")
