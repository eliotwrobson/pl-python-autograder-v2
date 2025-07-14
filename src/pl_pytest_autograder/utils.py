import base64
from typing import Any
from typing import Literal
from typing import TypedDict

import dill

QueryStatusCode = Literal["success", "not_found"]
FunctionStatusCode = Literal["success", "exception", "timeout", "not_found"]
ProcessStatusCode = Literal["success", "exception", "timeout", "no_response"]

# TODO use some inheritance on the query and response types


# Variable query dict types
class StudentQueryRequest(TypedDict):
    message_type: Literal["query"]
    var: str
    query_timeout: float


class StudentQueryResponse(TypedDict):
    # This is meant to be deserialized into a Python object
    status: QueryStatusCode
    value: Any


# Function query dict types
class StudentFunctionRequest(TypedDict):
    message_type: Literal["query_function"]
    function_name: str
    args_encoded: str  # TODO add a stronger type for the input/output of the serialized function
    kwargs_encoded: str
    query_timeout: float


class StudentFunctionResponse(TypedDict):
    # This is meant to be deserialized into a Python object
    status: FunctionStatusCode
    value: Any
    stdout: str
    stderr: str
    exception_name: str | None
    exception_message: str | None
    traceback: str | None


# Process start dict types


class ProcessStartRequest(TypedDict):
    message_type: Literal["start"]
    student_code: str
    student_file_name: str
    initialization_timeout: float
    import_whitelist: list[str] | None
    import_blacklist: list[str] | None


class ProcessStartResponse(TypedDict):
    status: ProcessStatusCode
    stdout: str
    stderr: str
    execution_error: str | None
    execution_traceback: str


def serialize_object_unsafe(obj: object) -> str:
    """
    Serializes an arbitrary Python object to a JSON string.
    The object is first serialized using dill, then base64 encoded.

    Returns:
        A JSON string representing the serialized object.
    """
    # 1. Serialize the object using dill
    dilled_bytes = dill.dumps(obj)

    # 2. Base64 encode the byte stream
    base64_encoded_bytes = base64.b64encode(dilled_bytes)

    # 3. Decode base64 bytes to a UTF-8 string for JSON storage
    return base64_encoded_bytes.decode("utf-8")


def deserialize_object_unsafe(base64_string: str) -> object:
    """
    Deserializes a Python object from a JSON string.

    The string is expected to contain a base64-encoded, dill-serialized
    object.

    Returns:
        The deserialized Python object.
    """

    # 1. Encode the base64 string back to bytes
    base64_encoded_bytes = base64_string.encode("utf-8")

    # 2. Base64 decode the bytes
    dilled_bytes = base64.b64decode(base64_encoded_bytes)

    # 3. Deserialize the object using dill
    return dill.loads(dilled_bytes)
