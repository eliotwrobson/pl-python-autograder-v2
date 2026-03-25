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
from .utils import ProcessStartRequest
from .utils import ProcessStartResponse
from .utils import ProcessStatusCode
from .utils import SetupQueryRequest
from .utils import SetupQueryResponse
from .utils import StudentFunctionRequest
from .utils import StudentFunctionResponse
from .utils import StudentQueryRequest
from .utils import StudentQueryResponse
from .utils import WorkspaceStartRequest
from .utils import deserialize_object_unsafe
from .utils import drop_privileges
from .utils import serialize_object_unsafe

DataFixture = dict[str, Any]

SCRIPT_PATH = str(files("pytest_prairielearn_grader").joinpath("_student_code_runner.py"))
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


class _SandboxBase:
    """
    Shared subprocess/socket plumbing used by StudentFixture and WorkspaceFixture.
    Not intended to be instantiated directly.
    """

    process: subprocess.Popen | None
    student_socket: socket.socket | None
    import_whitelist: list[str] | None
    import_blacklist: list[str] | None
    starting_vars: dict[str, Any] | None
    builtin_whitelist: list[str] | None
    names_for_user_list: list[str] | None
    worker_username: str | None
    _accumulated_stdout: list[str]

    def __init__(
        self,
        import_whitelist: list[str] | None,
        import_blacklist: list[str] | None,
        starting_vars: dict[str, Any] | None,
        builtin_whitelist: list[str] | None,
        names_for_user_list: list[str] | None,
        worker_username: str | None,
    ) -> None:
        self.import_whitelist = import_whitelist
        self.import_blacklist = import_blacklist
        self.starting_vars = starting_vars
        self.builtin_whitelist = builtin_whitelist
        self.names_for_user_list = names_for_user_list
        self.worker_username = worker_username
        self.process = None
        self.student_socket = None
        self._accumulated_stdout = []

    def _assert_process_running(self) -> None:
        assert self.process is not None, "Sandbox process is not running. Please start it first."
        process_return_code = self.process.poll()
        if process_return_code is not None:
            raise RuntimeError(f"Sandbox process terminated with code {process_return_code}.")

    def _send_json_object(self, json_object: Any) -> None:
        assert self.student_socket is not None, "Socket is not connected. Please start the sandbox server first."
        self.student_socket.sendall((json.dumps(json_object) + os.linesep).encode("utf-8"))

    def _read_from_socket(self) -> bytes:
        """Read from the socket until a line terminator is found."""
        buffer = bytearray()
        terminator = os.linesep.encode("utf-8")
        max_len: int | None = None  # TODO add max length parameter?
        assert self.student_socket is not None, "Socket is not connected. Please start the sandbox server first."
        chunk_size = 4096
        chunk: bytes = b""
        # TODO maybe set a hard iteration limit to avoid infinite loops?
        while (idx := chunk.rfind(terminator)) == -1:
            try:
                chunk = self.student_socket.recv(chunk_size)
            except TimeoutError as e:
                raise TimeoutError("Socket read timed out.") from e
            if not chunk:
                raise Exception("Connection closed by peer before termination character was found.")
            buffer.extend(chunk)
            if max_len is not None and len(buffer) >= max_len:
                raise Exception(f"Maximum read length of {max_len} exceeded.")
        loc = len(buffer) - len(chunk) + idx + len(terminator)
        return buffer[:loc]

    def _start_subprocess(self) -> None:
        """Spawn the runner subprocess and store it in ``self.process``."""

        def try_drop_privileges() -> None:
            if self.worker_username is not None:
                drop_privileges(self.worker_username)

        self.process = subprocess.Popen(
            args=(sys.executable, SCRIPT_PATH),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=None if sys.platform == "win32" else try_drop_privileges,
        )
        self._assert_process_running()

    def _connect_to_server(self, timeout: float) -> None:
        """Read the host/port printed by the subprocess and connect the socket."""
        assert self.process is not None and self.process.stdout is not None
        host, port = self.process.stdout.readline().decode().strip().split(",")
        self.student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.student_socket.settimeout(timeout)
        self.student_socket.connect((host, int(port)))

    def _read_start_response(self) -> ProcessStartResponse:
        """Read and return the ProcessStartResponse sent after the start message."""
        try:
            data = self._read_from_socket().decode()
            res: ProcessStartResponse = json.loads(data)
            if res.get("stdout"):
                self._accumulated_stdout.append(res["stdout"])
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

    def query_raw(self, var_to_query: str, *, query_timeout: float = DEFAULT_TIMEOUT) -> StudentQueryResponse:
        self._assert_process_running()
        json_message = StudentQueryRequest(message_type="query", var=var_to_query, query_timeout=query_timeout)
        assert self.student_socket is not None
        self.student_socket.settimeout(query_timeout)
        self._send_json_object(json_message)
        data: StudentQueryResponse = json.loads(self._read_from_socket().decode())
        return data

    def query(self, var_to_query: str, *, query_timeout: float = DEFAULT_TIMEOUT) -> Any:
        """Query a variable from the student sandbox by name."""
        response = self.query_raw(var_to_query, query_timeout=query_timeout)
        if response["status"] == "not_found":
            raise NameError(f"Query for '{var_to_query}' failed")
        return from_json(response["value"])

    def query_function_raw(
        self, function_name: str, *args: Any, query_timeout: float = DEFAULT_TIMEOUT, **kwargs: Any
    ) -> StudentFunctionResponse:
        json_message = StudentFunctionRequest(
            message_type="query_function",
            function_name=function_name,
            args_encoded=serialize_object_unsafe(args),
            kwargs_encoded=serialize_object_unsafe(kwargs),
            query_timeout=query_timeout,
        )
        assert self.student_socket is not None
        self.student_socket.settimeout(query_timeout)
        self.student_socket.sendall((json.dumps(json_message) + os.linesep).encode("utf-8"))
        data: StudentFunctionResponse = json.loads(self._read_from_socket().decode())
        if data.get("stdout"):
            self._accumulated_stdout.append(data["stdout"])
        return data

    def query_function(self, function_name: str, *args: Any, query_timeout: float = DEFAULT_TIMEOUT, **kwargs: Any) -> Any:
        """Call a function in the student sandbox and return its value."""
        response = self.query_function_raw(function_name, *args, query_timeout=query_timeout, **kwargs)
        match response["status"]:
            case "exception":
                raise RuntimeError(
                    f"Function '{function_name}' raised an exception "
                    f"{response['exception_name']}: {response['exception_message']}\n{response['traceback']}"
                )
            case "timeout":
                raise TimeoutError(f"Query for function '{function_name}' timed out after {query_timeout} seconds.")
            case "not_found":
                raise NameError(f"Query for function '{function_name}' failed: {response['exception_message']}")
        return from_json(response["value"])

    def get_accumulated_stdout(self) -> str:
        """Return all stdout captured from function calls made through this fixture."""
        return "".join(self._accumulated_stdout)

    def _cleanup(self) -> None:
        if self.student_socket is not None:
            self.student_socket.close()
            self.student_socket = None
        if self.process is not None:
            self.process.terminate()
            self.process.wait()
            self.process = None


class StudentFixture(_SandboxBase):
    leading_file: Path
    trailing_file: Path
    student_code_file: Path
    setup_code_file: Path

    def __init__(
        self,
        file_names: StudentFiles,
        import_whitelist: list[str] | None,
        import_blacklist: list[str] | None,
        starting_vars: dict[str, Any] | None,
        builtin_whitelist: list[str] | None,
        names_for_user_list: list[str] | None,
        worker_username: str | None,
    ) -> None:
        super().__init__(import_whitelist, import_blacklist, starting_vars, builtin_whitelist, names_for_user_list, worker_username)
        self.leading_file = file_names.leading_file
        self.trailing_file = file_names.trailing_file
        self.student_code_file = file_names.student_code_file
        self.setup_code_file = file_names.setup_code_file

    def start_student_code_server(self, *, initialization_timeout: float = DEFAULT_TIMEOUT) -> ProcessStartResponse:
        if self.worker_username is not None:
            logger.debug(f"Starting student code server with worker username: {self.worker_username}")
        else:
            logger.debug("Starting student code server without dropping privileges.")

        self._start_subprocess()

        student_code = ""
        if self.leading_file.is_file():
            student_code += self.leading_file.read_text(encoding="utf-8")
            student_code += os.linesep
        if self.student_code_file.is_file():
            student_code += self.student_code_file.read_text(encoding="utf-8")
        if self.trailing_file.is_file():
            student_code += os.linesep
            student_code += self.trailing_file.read_text(encoding="utf-8")

        setup_code = None
        if self.setup_code_file.is_file():
            setup_code = self.setup_code_file.read_text(encoding="utf-8")

        self._connect_to_server(initialization_timeout)

        # TODO make this a shared type
        json_message = ProcessStartRequest(
            message_type="start",
            student_code=student_code,
            student_file_name=str(self.student_code_file),
            setup_code=setup_code,
            initialization_timeout=initialization_timeout,
            import_whitelist=self.import_whitelist,
            import_blacklist=self.import_blacklist,
            starting_vars=self.starting_vars,
            builtin_whitelist=self.builtin_whitelist,
            names_for_user_list=self.names_for_user_list,
        )
        self._send_json_object(json_message)
        return self._read_start_response()

    def query_setup_raw(self, var_to_query: str) -> SetupQueryResponse:
        self._assert_process_running()
        json_message: SetupQueryRequest = {"message_type": "query_setup", "var": var_to_query}
        assert self.student_socket is not None, "Student socket is not connected. Please start the student code server first."
        self._send_json_object(json_message)
        data: SetupQueryResponse = json.loads(self._read_from_socket().decode())
        return data

    def query_setup(self, var_to_query: str) -> Any:
        """Queries a variable from the setup code and returns its value."""
        response = self.query_setup_raw(var_to_query)
        if response["status"] == "not_found":
            raise NameError(f"Query for setup variable '{var_to_query}' failed")
        return deserialize_object_unsafe(response["value_encoded"])

    # TODO add functions that let instructors use the student fixture
    # use the stuff pete set up here: https://github.com/reteps/pytest-autograder-prototype
    def __repr__(self) -> str:
        return f"StudentFixture(leading_file={self.leading_file}, trailing_file={self.trailing_file}, student_code_file={self.student_code_file})"


class WorkspaceFixture(_SandboxBase):
    """
    Fixture for grading workspace-based student projects.

    In workspace mode the student submission is a multi-file Python project
    rooted at *workspace_dir*.  That directory is added to ``sys.path`` inside
    the sandbox subprocess so that standard Python import machinery works
    transparently.

    Tests interact with the student's project using dotted module paths:

    .. code-block:: python

        result = workspace_sandbox.query_function("models.classifier.predict", X)
        value  = workspace_sandbox.query("utils.EPSILON")

    Flat (non-dotted) names fall back to variables injected via ``setup_code``
    or ``names_for_user``, exactly as in the regular :class:`StudentFixture`.
    """

    workspace_dir: Path
    setup_code_file: Path
    exec_entry: str | None

    def __init__(
        self,
        workspace_dir: Path,
        setup_code_file: Path,
        import_whitelist: list[str] | None,
        import_blacklist: list[str] | None,
        starting_vars: dict[str, Any] | None,
        builtin_whitelist: list[str] | None,
        names_for_user_list: list[str] | None,
        worker_username: str | None,
        exec_entry: str | None = None,
    ) -> None:
        super().__init__(import_whitelist, import_blacklist, starting_vars, builtin_whitelist, names_for_user_list, worker_username)
        self.workspace_dir = workspace_dir
        self.setup_code_file = setup_code_file
        self.exec_entry = exec_entry

    def start_workspace_server(self, *, initialization_timeout: float = DEFAULT_TIMEOUT) -> ProcessStartResponse:
        """Start the sandbox subprocess and initialise the workspace."""
        self._start_subprocess()

        setup_code: str | None = None
        if self.setup_code_file.is_file():
            setup_code = self.setup_code_file.read_text(encoding="utf-8")

        self._connect_to_server(initialization_timeout)

        json_message = WorkspaceStartRequest(
            message_type="start_workspace",
            workspace_dir=str(self.workspace_dir),
            exec_entry=self.exec_entry,
            setup_code=setup_code,
            initialization_timeout=initialization_timeout,
            import_whitelist=self.import_whitelist,
            import_blacklist=self.import_blacklist,
            starting_vars=self.starting_vars,
            builtin_whitelist=self.builtin_whitelist,
            names_for_user_list=self.names_for_user_list,
        )
        self._send_json_object(json_message)
        return self._read_start_response()

    def __repr__(self) -> str:
        return f"WorkspaceFixture(workspace_dir={self.workspace_dir})"
