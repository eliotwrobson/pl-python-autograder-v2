import numpy as np
import numpy.linalg as la
import pytest

from pl_pytest_autograder.fixture import FeedbackFixture
from pl_pytest_autograder.fixture import StudentFixture


def compute_starting_parameters() -> tuple[list[str], list[dict]]:
    overall_members = ["Alex", "Jordan", "Taylor", "Casey", "Riley", "Chris", "Avery", "Sam", "Devon", "Morgan"]

    rng = np.random.default_rng()

    members = list(rng.choice(overall_members, size=5, replace=False))
    N_sales = len(members)

    hours_set = set()
    sale_metadata = []

    # Avoid edge case where two lists of hours are the same, causing a singularity
    while len(sale_metadata) < N_sales:
        hours = tuple(rng.integers(10, 101, size=N_sales))
        if hours in hours_set:
            continue
        hours_set.add(hours)
        rng.shuffle(members)
        sale_metadata.append({"hours": list(zip(members, hours)), "units_sold": rng.integers(100, 2001)})

    return members, sale_metadata


def compute_answers(members: list[str], sale_metadata: list[dict]) -> tuple[dict[str, float], str, str]:
    member_id = {member: i for i, member in enumerate(members)}
    A = np.zeros((len(sale_metadata), len(members)))
    sales = np.zeros(len(sale_metadata))

    for i, sale_md in enumerate(sale_metadata):
        for v, t in sale_md["hours"]:
            A[i, member_id[v]] = t
        sales[i] = sale_md["units_sold"]

    contribs = la.solve(A, sales)
    member_ratings = {members[i]: contribs[i] for i in range(len(members))}
    highest_performing = members[np.argmax(contribs)]
    lowest_performing = members[np.argmin(contribs)]

    return member_ratings, highest_performing, lowest_performing


@pytest.mark.grading_data(name="ratings", points=4)
def test_0(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    score = 0
    members, sale_metadata = compute_starting_parameters()

    student_member_ratings, _, _ = sandbox.query_function("solve_ratings", members, sale_metadata)

    ref_member_ratings, _, _ = compute_answers(members, sale_metadata)

    if student_member_ratings is not None:
        if type(student_member_ratings) != dict:
            feedback.add_message("member_ratings is not a dictionary")
        else:
            for member, rating in student_member_ratings.items():
                if member not in ref_member_ratings:
                    feedback.add_message(f"{member} is not a known team member")
                    continue
                if ref_member_ratings[member] != rating:
                    feedback.add_message(f"{member} has an incorrect rating")
                else:
                    score += 1
    else:
        feedback.add_message("member_ratings is not defined")

    feedback.set_score_final(score / len(ref_member_ratings))


@pytest.mark.grading_data(name="highest_performing", points=1)
def test_1(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    members, sale_metadata = compute_starting_parameters()

    _, student_highest_performing, _ = sandbox.query_function("solve_ratings", members, sale_metadata)

    _, ref_highest_performing, _ = compute_answers(members, sale_metadata)

    assert ref_highest_performing == student_highest_performing, "highest_performing is not correct"


@pytest.mark.grading_data(name="lowest_performing", points=1)
def test_2(sandbox: StudentFixture, feedback: FeedbackFixture) -> None:
    members, sale_metadata = compute_starting_parameters()

    _, _, student_lowest_performing = sandbox.query_function("solve_ratings", members, sale_metadata)

    _, _, ref_lowest_performing = compute_answers(members, sale_metadata)

    assert ref_lowest_performing == student_lowest_performing, "lowest_performing is not correct"
