from typing import Any
from typing import cast

import numpy as np
import pandas as pd
import pytest

from pytest_prairielearn_grader.json_utils import from_json
from pytest_prairielearn_grader.json_utils import from_server_json
from pytest_prairielearn_grader.json_utils import to_json
from pytest_prairielearn_grader.utils import deserialize_object_unsafe
from pytest_prairielearn_grader.utils import serialize_object_unsafe


def test_serialize_numpy_array() -> None:
    # Create a numpy array
    arr = np.array([1, 2, 3, 4, 5])

    # Serialize the numpy array
    serialized = serialize_object_unsafe(arr)

    # Deserialize the numpy array
    deserialized = cast(np.typing.ArrayLike, deserialize_object_unsafe(serialized))

    # Check if the original and deserialized arrays are equal
    assert np.array_equal(arr, deserialized)


@pytest.mark.parametrize("obj", [np.bool(True), np.int32(42), np.float64(3.14), complex(1, 2), True])
def test_serialize_json(obj: Any) -> None:
    # Serialize the object to JSON-compatible format
    json_compatible = to_json(obj)

    # Deserialize back to original object
    deserialized = from_json(json_compatible)

    np.testing.assert_equal(obj, deserialized)


@pytest.mark.parametrize(
    ("obj", "expected_result"),
    [
        (
            {
                "_type": "ndarray",
                "_value": [
                    [0.6838187162381367, 0.9687669728013233, 0.8739536562117622],
                    [0.6863101440077359, 0.18857604228294678, 0.036780253047014266],
                    [0.3518597494339264, 0.5156619713512136, 0.1474092805728887],
                ],
                "_dtype": "float64",
            },
            np.array([[0.68381872, 0.96876697, 0.87395366], [0.68631014, 0.18857604, 0.03678025], [0.35185975, 0.51566197, 0.14740928]]),
        ),
        (
            {"_type": "ndarray", "_value": [[64, 41, 40], [93, 75, 87], [27, 91, 27]], "_dtype": "int64"},
            np.array([[64, 41, 40], [93, 75, 87], [27, 91, 27]]),
        ),
    ],
)
def test_from_server_json_numpy(obj: dict, expected_result: np.ndarray) -> None:
    # Deserialize back to original object
    deserialized = from_server_json(obj)

    # Check if the original and deserialized arrays are equal
    np.testing.assert_allclose(deserialized, expected_result)


@pytest.mark.parametrize(
    ("obj", "expected_result"),
    [
        (
            {
                "_type": "dataframe",
                "_value": {
                    "index": [0, 1, 2, 3, 4],
                    "columns": ["ColA", "ColB", "ColC"],
                    "data": [[6, 98, 76], [91, 43, 6], [89, 46, 81], [48, 3, 19], [43, 31, 73]],
                },
            },
            pd.DataFrame(np.array([[6, 98, 76], [91, 43, 6], [89, 46, 81], [48, 3, 19], [43, 31, 73]]), columns=["ColA", "ColB", "ColC"]),
        )
    ],
)
def test_from_server_json(obj: dict, expected_result: pd.DataFrame) -> None:
    # Deserialize back to original object
    deserialized = from_server_json(obj)

    # Check if the original and deserialized arrays are equal
    pd.testing.assert_frame_equal(deserialized, expected_result)
