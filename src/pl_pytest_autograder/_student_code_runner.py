import asyncio
import concurrent.futures
import io
import json
import linecache
import sys
import traceback
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from typing import Any
from typing import NamedTuple

from utils import ProcessStartResponse
from utils import StudentFunctionResponse
from utils import StudentQueryResponse

from pl_pytest_autograder.json_utils import to_json
from pl_pytest_autograder.utils import deserialize_object_unsafe

HOST = "127.0.0.1"  # Loopback address, means "this computer only"
TIMEOUT = 1  # Default timeout for student code execution in seconds

# Global ThreadPoolExecutor for CPU-bound tasks
# It's good practice to create this once and reuse it.
# The number of workers should ideally be around the number of CPU cores.
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


class StudentFunctionResult(NamedTuple):
    """
    A named tuple to hold the result of the student function.
    """

    result: Any
    captured_stdout: str
    captured_stderr: str
    execution_error: Exception | None
    execution_traceback: str | None = None


def populate_linecache(contents: str, fname: str) -> None:
    """
    TODO do what's in this file here
    https://github.com/PrairieLearn/PrairieLearn/commit/28c1f0bfb3792c950e5df30061469bfaf0ca199f
    """
    linecache.cache[fname] = (
        len(contents),
        None,
        [line + "\n" for line in contents.splitlines()],
        fname,
    )


async def student_function_runner(
    student_code_vars: dict[str, Any], func_name: str, timeout: int, args_tup: Any, kwargs_dict: Any
) -> StudentFunctionResponse:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error = None
    exception_traceback = None
    result = None

    try:
        student_function = student_code_vars[func_name]
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(executor, student_function, *args_tup, **kwargs_dict), timeout=timeout
            )
    except Exception as e:
        execution_error = e
        exception_traceback = traceback.format_exc()

    function_response: StudentFunctionResponse = {
        "status": "success" if execution_error is None else "exception",
        "value": result,
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "exception_name": type(execution_error).__name__,
        "exception_message": str(execution_error) if execution_error else None,
        "traceback": exception_traceback,
    }

    return function_response


async def student_code_runner(student_code: str, student_file_name: str, timeout: int) -> tuple[dict[str, Any], ProcessStartResponse]:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error = None
    exception_traceback = None
    student_code_vars: dict[str, Any] = {}

    try:
        # First, compile student code. Make sure to handle errors in this later
        # TODO have a better filename
        code_setup = compile(student_code, student_file_name, "exec")
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(executor, exec, code_setup, student_code_vars, student_code_vars), timeout=timeout
            )

    except Exception as e:
        execution_error = e
        # TODO this traceback is not very useful
        exception_traceback = traceback.format_exc()

    result_dict: ProcessStartResponse = {
        "status": "success" if execution_error is None else "exception",
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "execution_error": type(execution_error).__name__ if execution_error else None,
        "execution_traceback": str(exception_traceback),
    }

    return student_code_vars, result_dict


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """
    Reads lines from stdin asynchronously and responds on stdout.
    Mimics a simple server handling requests.
    """
    # try:
    #     json_message = json.loads(message)
    #     result = await asyncio.wait_for(
    #         asyncio.get_event_loop().run_in_executor(executor, _run_blocking_task, task_payload), timeout=timeout_seconds
    #     )
    #     # Example: send an acknowledgement back
    #     response_message = {"status": "received", "data": json_message}
    #     writer.write(json.dumps(response_message).encode("utf-8") + b"\n")  # Add newline for stream parsing
    #     await writer.drain()
    #     # ------------------------------------

    # except json.JSONDecodeError as e:
    #     error_response = {"status": "error", "message": f"Invalid JSON: {e}"}
    #     writer.write(json.dumps(error_response).encode("utf-8") + b"\n")
    #     await writer.drain()
    # except UnicodeDecodeError as e:
    #     error_response = {"status": "error", "message": f"Invalid UTF-8 encoding: {e}"}
    #     writer.write(json.dumps(error_response).encode("utf-8") + b"\n")
    #     await writer.drain()

    try:
        student_code_vars: None | dict = None
        async for line_bytes in reader:
            line = line_bytes.decode().strip()
            if not line:  # Handle empty lines
                continue

            json_message = json.loads(line)

            msg_type = json_message.get("type")
            if msg_type == "start":
                # Execute the student code for the first time and load
                # variables into the student_code_vars dictionary
                student_code = json_message["student_code"]
                student_file_name = json_message.get("student_file_name")

                populate_linecache(student_code, student_file_name)

                student_code_vars, start_response = await student_code_runner(student_code, student_file_name, TIMEOUT)

                writer.write(json.dumps(start_response).encode())

            elif msg_type == "query":
                assert student_code_vars is not None
                var_to_query = json_message["var"]

                # Check if the variable exists in the student_code_vars
                if var_to_query in student_code_vars:
                    query_response: StudentQueryResponse = {"status": "success", "value": to_json(student_code_vars[var_to_query])}
                else:
                    query_response = {"status": "not_found", "value": ""}

                writer.write(json.dumps(query_response).encode())

            elif msg_type == "query_function":
                assert student_code_vars is not None
                func_name = json_message["function_name"]
                args = deserialize_object_unsafe(json_message["args_encoded"])
                kwargs = deserialize_object_unsafe(json_message["kwargs_encoded"])

                function_response = await student_function_runner(student_code_vars, func_name, TIMEOUT, args, kwargs)

                writer.write(json.dumps(function_response).encode())

            # TODO handle cases of different payloads
            # The first payload should be student code
            if line.lower() == "exit":
                writer.write(b"Goodbye!")
                await writer.drain()
                break  # Exit the loop and terminate the server

            # Simulate processing a request
            # response = f"Server processed: '{line.upper()}'\n"

            await writer.drain()  # Ensure the response is written to stdout

    except asyncio.CancelledError:
        writer.write(json.dumps({"status": "failure", "message": "Server was cancelled."}).encode())
    except asyncio.TimeoutError:
        writer.write(json.dumps({"status": "failure", "message": "Student code timed out."}).encode())
    except Exception as e:
        writer.write(json.dumps({"status": "failure", "message": f"An error occurred: {e}"}).encode())
    finally:
        # It's good practice to close transports and writers
        # print("Closing server connections...")
        await writer.drain()  # Ensure all data is sent before closing
        writer.close()
        await writer.wait_closed()  # Wait for the writer to finish closing


async def main():
    """
    Starts the asynchronous socket server.
    """
    # Ensure ProactorEventLoop is used on Windows for robust socket operations
    if sys.platform == "win32":
        try:
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            print("Using ProactorEventLoop on Windows.", file=sys.stderr)
        except NotImplementedError:
            print("ProactorEventLoop not available, continuing with default loop.", file=sys.stderr)

    # Start the server, binding to the specified host and port
    server = await asyncio.start_server(handle_client, HOST, 0)
    addr = server.sockets[0].getsockname()
    print(f"{addr[0]}, {addr[1]}", flush=True)

    async with server:
        # Run forever, or until the server is explicitly stopped
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
