from typing import Any
from typing import cast

import numpy as np
import pytest

from pytest_pl_grader.json_utils import from_json
from pytest_pl_grader.json_utils import to_json
from pytest_pl_grader.utils import deserialize_object_unsafe
from pytest_pl_grader.utils import serialize_object_unsafe


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
