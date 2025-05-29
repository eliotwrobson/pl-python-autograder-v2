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
from .utils import serialize_object_unsafe

DataFixture = dict[str, Any]

SCRIPT_PATH = str(files("pl_pytest_autograder").joinpath("_student_code_runner.py"))
BUFFSIZE = 4096


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
            "messages": self.messages,
            "score": self.score,
        }


class StudentFiles(NamedTuple):
    leading_file: Path
    trailing_file: Path
    student_code_file: Path


class StudentFixture:
    process: subprocess.Popen | None

    def __init__(self, file_names: StudentFiles) -> None:
        self.leading_file = file_names.leading_file
        self.trailing_file = file_names.trailing_file
        self.student_code_file = file_names.student_code_file

        self._start_student_code_server()

    def _start_student_code_server(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, SCRIPT_PATH], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        student_code = ""
        if self.leading_file.is_file():
            with open(self.leading_file) as f:
                student_code += f.read()
                student_code += "\n"

        if self.student_code_file.is_file():
            with open(self.student_code_file) as f:
                student_code += f.read()

        if self.trailing_file.is_file():
            with open(self.trailing_file) as f:
                student_code += "\n"
                student_code += f.read()

        json_message = {
            "type": "start",
            "student_code": student_code,
        }

        line = self.process.stdout.readline().decode()  # Read the initial output from the process to ensure it's ready
        host, port = line.strip().split(",")

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, int(port)))

        self.socket.sendall(json.dumps(json_message).encode("utf-8") + os.linesep.encode("utf-8"))

        data = self.socket.recv(BUFFSIZE).decode()  # Adjust the buffer size as needed
        res = json.loads(data)
        assert res["status"] == "success"

    def query(self, var_to_query: str) -> str:
        json_message = {
            "type": "query",
            "var": var_to_query,
        }

        assert self.process is not None, "Student code server process is not running."

        self.socket.sendall(json.dumps(json_message).encode("utf-8") + os.linesep.encode("utf-8"))
        data = self.socket.recv(BUFFSIZE).decode()

        # print(self.process.stdout.read())
        # print(self.process.stderr.read())
        json_val = json.loads(data)["value"]

        res = from_json(json_val)
        return res

    def query_function(self, function_name: str, *args, **kwargs) -> str:
        json_message = {
            "type": "query_function",
            "function_name": function_name,
            "args_encoded": serialize_object_unsafe(args),
            "kwargs_encoded": serialize_object_unsafe(kwargs),
        }

        self.socket.sendall(json.dumps(json_message).encode("utf-8") + os.linesep.encode("utf-8"))

        data = self.socket.recv(BUFFSIZE).decode()
        # print(json.loads(data)["traceback"])
        res = json.loads(data)["value"]
        return res

    # TODO add functions that let instructors use the student fixture
    # use the stuff pete set up here: https://github.com/reteps/pytest-autograder-prototype
    def _cleanup(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

    def __repr__(self) -> str:
        return f"StudentFixture(leading_file={self.leading_file}, trailing_file={self.trailing_file}, student_code_file={self.student_code_file})"
