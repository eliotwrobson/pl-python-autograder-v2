import json
import os
import socket
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any
from typing import NamedTuple

from .json_utils import from_json
from .utils import ProcessStartRequest
from .utils import ProcessStartResponse
from .utils import StudentFunctionRequest
from .utils import StudentFunctionResponse
from .utils import StudentQueryRequest
from .utils import StudentQueryResponse
from .utils import serialize_object_unsafe

DataFixture = dict[str, Any]

SCRIPT_PATH = str(files("pl_pytest_autograder").joinpath("_student_code_runner.py"))
BUFFSIZE = 4096
DEFAULT_TIMEOUT = 1.0


class StudentFiles(NamedTuple):
    leading_file: Path
    trailing_file: Path
    student_code_file: Path


class FeedbackFixture:
    """
    A fixture to handle feedback from the student code.
    """

    test_id: str
    messages: list[str]
    score: float | None

    def __init__(self, test_id: str) -> None:
        self.test_id = test_id
        self.messages = []
        self.score = None

    def add_message(self, message: str) -> None:
        self.messages.append(message)

    def set_score(self, score: float) -> None:
        self.score = score

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "message": "".join(self.messages),
            "points": self.score,
        }


class StudentFixture:
    process: subprocess.Popen | None
    leading_file: Path
    trailing_file: Path
    student_code_file: Path
    student_socket: socket.socket | None

    def __init__(self, file_names: StudentFiles) -> None:
        self.leading_file = file_names.leading_file
        self.trailing_file = file_names.trailing_file
        self.student_code_file = file_names.student_code_file

        # Initialize the process and socket to None
        self.process = None
        self.student_socket = None

    def _assert_process_running(self) -> None:
        """
        TODO make the type of this a typeguard for process and socket
        """

        if self.process is None:
            raise RuntimeError("Student code server process is not running. Please start it first.")

        process_return_code = self.process.poll()
        if process_return_code is not None:
            raise RuntimeError(f"Student code server process terminated with code {process_return_code}.")

    def start_student_code_server(self, *, initialization_timeout: float = DEFAULT_TIMEOUT) -> ProcessStartResponse:
        self.process = subprocess.Popen(
            [sys.executable, SCRIPT_PATH], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
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

        # TODO make this a shared type
        json_message: ProcessStartRequest = {
            "message_type": "start",
            "student_code": student_code,
            "student_file_name": str(self.student_code_file),
            "initialization_timeout": initialization_timeout,
        }

        line = self.process.stdout.readline().decode()  # Read the initial output from the process to ensure it's ready
        host, port = line.strip().split(",")

        self.student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.student_socket.settimeout(initialization_timeout)
        self.student_socket.connect((host, int(port)))

        self.student_socket.sendall(json.dumps(json_message).encode("utf-8") + os.linesep.encode("utf-8"))

        try:
            data = self.student_socket.recv(BUFFSIZE).decode()  # Adjust the buffer size as needed
            res: ProcessStartResponse = json.loads(data)
        except Exception as e:
            res = {
                "status": "no_response",
                "execution_error": type(e).__name__,
                "execution_traceback": "",
                "stdout": "",
                "stderr": "",
            }

        return res

    def query_raw(self, var_to_query: str, *, query_timeout: float = DEFAULT_TIMEOUT) -> StudentQueryResponse:
        self._assert_process_running()

        json_message: StudentQueryRequest = {"message_type": "query", "var": var_to_query, "query_timeout": query_timeout}

        assert self.student_socket is not None
        self.student_socket.sendall(json.dumps(json_message).encode("utf-8") + os.linesep.encode("utf-8"))
        self.student_socket.settimeout(query_timeout)
        data: StudentQueryResponse = json.loads(self.student_socket.recv(BUFFSIZE).decode())

        return data

    def query(self, var_to_query: str, *, query_timeout: float = DEFAULT_TIMEOUT) -> Any:
        """
        Queries a variable from the student code and returns its value.
        """
        response = self.query_raw(var_to_query, query_timeout=query_timeout)

        assert response["status"] == "success", f"Query for '{var_to_query}' failed"

        return from_json(response["value"])

    def query_function_raw(self, function_name: str, *args, **kwargs) -> StudentFunctionResponse:
        """
        TODO add query timeout keyword only argument
        """
        self._assert_process_running()

        json_message: StudentFunctionRequest = {
            "message_type": "query_function",
            "function_name": function_name,
            "args_encoded": serialize_object_unsafe(args),
            "kwargs_encoded": serialize_object_unsafe(kwargs),
        }

        self.student_socket.sendall(json.dumps(json_message).encode("utf-8") + os.linesep.encode("utf-8"))

        data: StudentFunctionResponse = json.loads(self.student_socket.recv(BUFFSIZE).decode())

        return data

    def query_function(self, function_name: str, *args, **kwargs) -> Any:
        """
        Queries a function from the student code and returns its return value.
        """
        response = self.query_function_raw(function_name, *args, **kwargs)
        assert response["status"] == "success", f"Query for function {function_name} failed: {response['exception_message']}"

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
