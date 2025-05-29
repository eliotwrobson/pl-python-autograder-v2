import pytest

from pl_pytest_autograder.fixture import DataFixture
from pl_pytest_autograder.fixture import FeedbackFixture
from pl_pytest_autograder.fixture import StudentFixture

# @pytest.mark.grading_data(name="test_query_func", points=2)
# def test_query_func(sandbox: StudentFixture) -> None:
#     assert sandbox.query_function("fib", 3) == 5


@pytest.mark.grading_data(name="Test expected inputs", points=4)
def test_input(sandbox: StudentFixture, data_json: DataFixture, feedback: FeedbackFixture) -> None:
    function_name = data_json["params"]["function_name"]
    # student_function = getattr(self.st, function_name)

    num_correct = 0
    pairs_dicts = data_json["params"]["pairs"]

    for pair_dict in pairs_dicts:
        func_input = pair_dict["input"]
        expected_output = pair_dict["output"]
        student_output = sandbox.query_function(function_name, func_input)

        if student_output == expected_output:
            feedback.add_message(f'Function "{function_name}" returned "{student_output}" on input "{func_input}".')
            num_correct += 1

        else:
            feedback.add_message(
                f'Function "{function_name}" returned "{student_output}" on input "{func_input}", not "{expected_output}".'
            )

    percentage_score = num_correct / len(pairs_dicts)
    feedback.set_score(percentage_score)


@pytest.mark.grading_data(name="Test default output", points=1)
def test_default_output(sandbox: StudentFixture, data_json: DataFixture, feedback: FeedbackFixture) -> None:
    function_name = data_json["params"]["function_name"]
    invalid_input = data_json["params"]["invalid_input"]
    default_output = data_json["params"]["default_output"]

    student_output = sandbox.query_function(function_name, invalid_input)

    if student_output == default_output:
        feedback.add_message(f'Function "{function_name}" returned "{student_output}" on input "{invalid_input}".')
        feedback.set_score(1)

    else:
        feedback.add_message(f'Function "{function_name}" returned "{student_output}" on input "{invalid_input}", not "{default_output}".')
        feedback.set_score(0)
