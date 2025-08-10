from typing import cast

import numpy as np

from pl_pytest_autograder.utils import deserialize_object_unsafe
from pl_pytest_autograder.utils import serialize_object_unsafe


def test_serialize_numpy_array() -> None:
    # Create a numpy array
    arr = np.array([1, 2, 3, 4, 5])

    # Serialize the numpy array
    serialized = serialize_object_unsafe(arr)

    # Deserialize the numpy array
    deserialized = cast(np.typing.ArrayLike, deserialize_object_unsafe(serialized))

    # Check if the original and deserialized arrays are equal
    assert np.array_equal(arr, deserialized)
