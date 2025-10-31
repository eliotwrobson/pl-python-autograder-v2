import base64
import builtins
import os
import pwd
from enum import StrEnum
from typing import Any
from typing import Literal
from typing import TypedDict

import dill


class QueryStatusCode(StrEnum):
    """
    Status codes for a query operation.
    """

    SUCCESS = "success"
    NOT_FOUND = "not_found"


class FunctionStatusCode(StrEnum):
    """
    Status codes for a function execution.
    """

    SUCCESS = "success"
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"


class ProcessStatusCode(StrEnum):
    """
    Status codes for a process execution.
    """

    SUCCESS = "success"
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    NO_RESPONSE = "no_response"


# TODO use some inheritance on the query and response types


class NamesForUserInfo(TypedDict):
    name: str
    description: str
    type: str


class SetupQueryRequest(TypedDict):
    message_type: Literal["query_setup"]
    var: str


class SetupQueryResponse(TypedDict):
    status: QueryStatusCode
    value_encoded: str


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
    setup_code: str | None
    initialization_timeout: float
    import_whitelist: list[str] | None
    import_blacklist: list[str] | None
    starting_vars: dict[str, Any] | None
    builtin_whitelist: list[str] | None
    names_for_user_list: list[NamesForUserInfo] | None


class ProcessStartResponse(TypedDict):
    status: ProcessStatusCode
    stdout: str
    stderr: str
    execution_error: str | None
    execution_message: str | None
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


def get_builtins(builtin_whitelist: list[str] | None) -> dict[str, Any]:
    """
    Returns a dictionary of safe built-in functions and exceptions.
    This is used to restrict the built-ins available in the student code execution environment.
    From https://github.com/zopefoundation/RestrictedPython/blob/master/src/RestrictedPython/Guards.py
    """
    final_builtins = {}

    _safe_names = (
        "__build_class__",
        "None",
        "False",
        "True",
        "abs",
        "bool",
        "bytes",
        "callable",
        "chr",
        "complex",
        "divmod",
        "float",
        "hash",
        "hex",
        "id",
        "int",
        "isinstance",
        "issubclass",
        "len",
        "oct",
        "ord",
        "pow",
        "print",
        "range",
        "repr",
        "round",
        "slice",
        "sorted",
        "str",
        "set",
        "list",
        "dict",
        "tuple",
        "zip",
        "enumerate",
        "min",
        "max",
    )

    _safe_exceptions = (
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BaseException",
        "BufferError",
        "BytesWarning",
        "DeprecationWarning",
        "EOFError",
        "EnvironmentError",
        "Exception",
        "FloatingPointError",
        "FutureWarning",
        "GeneratorExit",
        "IOError",
        "ImportError",
        "ImportWarning",
        "IndentationError",
        "IndexError",
        "KeyError",
        "KeyboardInterrupt",
        "LookupError",
        "MemoryError",
        "NameError",
        "NotImplementedError",
        "OSError",
        "OverflowError",
        "PendingDeprecationWarning",
        "ReferenceError",
        "RuntimeError",
        "RuntimeWarning",
        "StopIteration",
        "SyntaxError",
        "SyntaxWarning",
        "SystemError",
        "SystemExit",
        "TabError",
        "TypeError",
        "UnboundLocalError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeError",
        "UnicodeTranslateError",
        "UnicodeWarning",
        "UserWarning",
        "ValueError",
        "Warning",
        "ZeroDivisionError",
    )

    for name in _safe_names:
        final_builtins[name] = getattr(builtins, name)

    for name in _safe_exceptions:
        final_builtins[name] = getattr(builtins, name)

    # TODO raise exception if the name is not in the built-ins?
    if builtin_whitelist is not None:
        # Filter the built-ins based on the whitelist
        for name in builtin_whitelist:
            if name not in final_builtins:
                final_builtins[name] = getattr(builtins, name)

    return final_builtins


def drop_privileges(user_name: str) -> None:
    """Sets the process user and group to the specified non-root user."""
    try:
        # Get the UID and GID for the target user (e.g., 'nobody')
        pwnam = pwd.getpwnam(user_name)
        target_uid = pwnam.pw_uid
        target_gid = pwnam.pw_gid
    except KeyError:
        raise ValueError(f"User '{user_name}' not found.")

    # 1. Set the real and effective GID
    # NOTE: Set GID before UID, as changing UID may restrict GID changes
    os.setgid(target_gid)
    os.setegid(target_gid)

    # 2. Set the real and effective UID
    os.setuid(target_uid)
    os.seteuid(target_uid)
