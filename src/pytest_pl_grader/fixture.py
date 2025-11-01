import json
import logging
import os
import socket
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any
from typing import NamedTuple

from .json_utils import from_json
from .utils import NamesForUserInfo
from .utils import ProcessStartRequest
from .utils import ProcessStartResponse
from .utils import ProcessStatusCode
from .utils import SetupQueryRequest
from .utils import SetupQueryResponse
from .utils import StudentFunctionRequest
from .utils import StudentFunctionResponse
from .utils import StudentQueryRequest
from .utils import StudentQueryResponse
from .utils import deserialize_object_unsafe
from .utils import drop_privileges
from .utils import serialize_object_unsafe

DataFixture = dict[str, Any]

SCRIPT_PATH = str(files("pytest_pl_grader").joinpath("_student_code_runner.py"))
DEFAULT_TIMEOUT = 1.0

logger = logging.getLogger(__name__)


class StudentFiles(NamedTuple):
    leading_file: Path
    trailing_file: Path
    student_code_file: Path
    setup_code_file: Path


class FeedbackFixture:
    """
    A fixture to handle feedback from the student code.
    """

    test_id: str
    messages: list[str]
    score: float | None
    final_score_override: bool

    def __init__(self, test_id: str) -> None:
        self.test_id = test_id
        self.messages = []
        self.score = None
        self.final_score_override = False

    def add_message(self, message: str) -> None:
        self.messages.append(message)

    def set_score(self, score: float) -> None:
        self.score = score

    def set_score_final(self, score: float) -> None:
        """
        Sets the final score for the test. This should be called at the end of the test.
        """
        if self.score is not None:
            raise RuntimeError("Final score has already been set.")

        # TODO maybe change this to assert the score is 1? Then it will fail if the score is not 1.
        # Will maintain invariant that score should be 1 if all tests pass.
        self.score = score
        self.final_score_override = True

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "message": os.linesep.join(self.messages),
            "points_frac": self.score,
        }


class StudentFixture:
    process: subprocess.Popen | None
    leading_file: Path
    trailing_file: Path
    student_code_file: Path
    student_socket: socket.socket | None
    import_whitelist: list[str] | None
    import_blacklist: list[str] | None
    starting_vars: dict[str, Any] | None
    builtin_whitelist: list[str] | None
    names_for_user_list: list[NamesForUserInfo] | None
    worker_username: str | None

    def __init__(
        self,
        file_names: StudentFiles,
        import_whitelist: list[str] | None,
        import_blacklist: list[str] | None,
        starting_vars: dict[str, Any] | None,
        builtin_whitelist: list[str] | None,
        names_for_user_list: list[NamesForUserInfo] | None,
        worker_username: str | None,
    ) -> None:
        self.leading_file = file_names.leading_file
        self.trailing_file = file_names.trailing_file
        self.student_code_file = file_names.student_code_file
        self.setup_code_file = file_names.setup_code_file

        self.import_whitelist = import_whitelist
        self.import_blacklist = import_blacklist
        self.starting_vars = starting_vars
        self.builtin_whitelist = builtin_whitelist
        self.names_for_user_list = names_for_user_list
        self.worker_username = worker_username

        # Initialize the process and socket to None
        self.process = None
        self.student_socket = None

    def _assert_process_running(self) -> None:
        """
        TODO make the type of this a typeguard for process and socket
        """

        assert self.process is not None, "Student code server process is not running. Please start it first."

        process_return_code = self.process.poll()
        if process_return_code is not None:
            raise RuntimeError(f"Student code server process terminated with code {process_return_code}.")

    def _send_json_object(
        self, json_object: StudentQueryRequest | ProcessStartRequest | StudentFunctionRequest | SetupQueryRequest
    ) -> None:
        """
        Sends a JSON object to the student code server.
        """
        assert self.student_socket is not None, "Student socket is not connected. Please start the student code server first."
        self.student_socket.sendall((json.dumps(json_object) + os.linesep).encode("utf-8"))

    def _read_from_socket(self) -> bytes:
        """
        Reads data from a socket until a termination character is found.
        """
        buffer = bytearray()

        terminator = os.linesep.encode("utf-8")
        max_len: int | None = None  # TODO add max length parameter?

        assert self.student_socket is not None, "Student socket is not connected. Please start the student code server first."

        # Define a small chunk size for reading
        chunk_size = 4096
        chunk: bytes = b""

        # TODO maybe set a hard iteration limit to avoid infinite loops?
        while (idx := chunk.rfind(terminator)) == -1:
            try:
                # Read a chunk of data
                chunk = self.student_socket.recv(chunk_size)
            except TimeoutError as e:
                # Re-raise the timeout error
                raise TimeoutError("Socket read timed out.") from e

            # Check if the connection was closed
            if not chunk:
                # Connection closed before terminator was found
                raise Exception("Connection closed by peer before termination character was found.")

            # Append the new chunk to the buffer
            buffer.extend(chunk)

            # Check for maximum length constraint
            if max_len is not None and len(buffer) >= max_len:
                # Raise an error or return buffer depending on desired behavior
                raise Exception(f"Maximum read length of {max_len} exceeded.")

        loc = len(buffer) - len(chunk) + idx + len(terminator)

        # Return the buffer content up to and including the terminator
        # to only return the necessary data if more data was read
        return buffer[:loc]

    def start_student_code_server(self, *, initialization_timeout: float = DEFAULT_TIMEOUT) -> ProcessStartResponse:
        if self.worker_username is not None:
            logger.debug(f"Starting student code server with worker username: {self.worker_username}")
        else:
            logger.debug("Starting student code server without dropping privileges.")

        def try_drop_privileges() -> None:
            if self.worker_username is not None:
                drop_privileges(self.worker_username)

        self.process = subprocess.Popen(
            args=(sys.executable, SCRIPT_PATH),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=try_drop_privileges,
        )

        # Assert process is running after popen call
        self._assert_process_running()

        student_code = ""
        if self.leading_file.is_file():
            student_code += self.leading_file.read_text(encoding="utf-8")
            student_code += os.linesep

        if self.student_code_file.is_file():
            student_code += self.student_code_file.read_text(encoding="utf-8")

        if self.trailing_file.is_file():
            student_code += os.linesep
            student_code += self.trailing_file.read_text(encoding="utf-8")

        # TODO maybe add an error message for this?
        setup_code = None
        if self.setup_code_file.is_file():
            setup_code = self.setup_code_file.read_text(encoding="utf-8")

        # TODO make this a shared type
        json_message: ProcessStartRequest = {
            "message_type": "start",
            "student_code": student_code,
            "student_file_name": str(self.student_code_file),
            "setup_code": setup_code,
            "initialization_timeout": initialization_timeout,
            "import_whitelist": self.import_whitelist,
            "import_blacklist": self.import_blacklist,
            "starting_vars": self.starting_vars,
            "builtin_whitelist": self.builtin_whitelist,
            "names_for_user_list": self.names_for_user_list,
        }

        assert self.process.stdout is not None, "Process stdout is None. Ensure the process is started correctly."

        line = self.process.stdout.readline().decode()  # Read the initial output from the process to ensure it's ready
        host, port = line.strip().split(",")

        self.student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.student_socket.settimeout(initialization_timeout)
        self.student_socket.connect((host, int(port)))

        self._send_json_object(json_message)

        try:
            data = self._read_from_socket().decode()
            res: ProcessStartResponse = json.loads(data)
        except Exception as e:
            res = {
                "status": ProcessStatusCode.NO_RESPONSE,
                "execution_error": type(e).__name__,
                "execution_message": str(e),
                "execution_traceback": "",
                "stdout": "",
                "stderr": "",
            }

        return res

    def query_setup_raw(self, var_to_query: str) -> SetupQueryResponse:
        self._assert_process_running()

        json_message: SetupQueryRequest = {"message_type": "query_setup", "var": var_to_query}

        assert self.student_socket is not None, "Student socket is not connected. Please start the student code server first."
        self._send_json_object(json_message)
        data: SetupQueryResponse = json.loads(self._read_from_socket().decode())

        return data

    def query_setup(self, var_to_query: str) -> Any:
        """
        Queries a variable from the setup code and returns its value.
        """
        response = self.query_setup_raw(var_to_query)

        if response["status"] == "not_found":
            raise NameError(f"Query for setup variable '{var_to_query}' failed")

        return deserialize_object_unsafe(response["value_encoded"])

    def query_raw(self, var_to_query: str, *, query_timeout: float = DEFAULT_TIMEOUT) -> StudentQueryResponse:
        self._assert_process_running()

        json_message: StudentQueryRequest = {"message_type": "query", "var": var_to_query, "query_timeout": query_timeout}

        assert self.student_socket is not None, "Student socket is not connected. Please start the student code server first."
        self.student_socket.settimeout(query_timeout)
        self._send_json_object(json_message)
        data: StudentQueryResponse = json.loads(self._read_from_socket().decode())

        return data

    def query(self, var_to_query: str, *, query_timeout: float = DEFAULT_TIMEOUT) -> Any:
        """
        Queries a variable from the student code and returns its value.
        """
        response = self.query_raw(var_to_query, query_timeout=query_timeout)

        if response["status"] == "not_found":
            raise NameError(f"Query for '{var_to_query}' failed")

        return from_json(response["value"])

    def query_function_raw(self, function_name: str, *args, query_timeout: float = DEFAULT_TIMEOUT, **kwargs) -> StudentFunctionResponse:
        """
        TODO add query timeout keyword only argument
        """

        json_message: StudentFunctionRequest = {
            "message_type": "query_function",
            "function_name": function_name,
            "args_encoded": serialize_object_unsafe(args),
            "kwargs_encoded": serialize_object_unsafe(kwargs),
            "query_timeout": query_timeout,
        }

        assert self.student_socket is not None, "Student socket is not connected. Please start the student code server first."
        self.student_socket.settimeout(query_timeout)
        self.student_socket.sendall((json.dumps(json_message) + os.linesep).encode("utf-8"))
        data: StudentFunctionResponse = json.loads(self._read_from_socket().decode())

        return data

    def query_function(self, function_name: str, *args, query_timeout: float = DEFAULT_TIMEOUT, **kwargs) -> Any:
        """
        Queries a function from the student code and returns its return value.
        """
        response = self.query_function_raw(function_name, *args, query_timeout=query_timeout, **kwargs)

        match response["status"]:
            case "exception":
                raise RuntimeError(
                    f"Function '{function_name}' raised an exception {response['exception_name']}: {response['exception_message']}\n{response['traceback']}"
                )
            case "timeout":
                raise TimeoutError(f"Query for function '{function_name}' timed out after {query_timeout} seconds.")
            case "not_found":
                raise NameError(f"Query for function '{function_name}' failed: {response['exception_message']}")

        return from_json(response["value"])

    # TODO add functions that let instructors use the student fixture
    # use the stuff pete set up here: https://github.com/reteps/pytest-autograder-prototype
    def _cleanup(self) -> None:
        if self.student_socket is not None:
            self.student_socket.close()
            self.student_socket = None

        if self.process is not None:
            self.process.terminate()
            self.process.wait()
            self.process = None

    def __repr__(self) -> str:
        return f"StudentFixture(leading_file={self.leading_file}, trailing_file={self.trailing_file}, student_code_file={self.student_code_file})"
