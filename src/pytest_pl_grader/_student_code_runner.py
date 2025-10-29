import asyncio
import concurrent.futures
import io
import json
import linecache
import os
import sys
import traceback
import types
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from copy import deepcopy
from typing import Any

from pytest_pl_grader.json_utils import from_server_json

# TODO make it so that other files in this package cannot import from this one
# ask Gemini how to do it
from pytest_pl_grader.json_utils import to_json
from pytest_pl_grader.utils import NamesForUserInfo
from pytest_pl_grader.utils import ProcessStartRequest
from pytest_pl_grader.utils import ProcessStartResponse
from pytest_pl_grader.utils import SetupQueryRequest
from pytest_pl_grader.utils import SetupQueryResponse
from pytest_pl_grader.utils import StudentFunctionRequest
from pytest_pl_grader.utils import StudentFunctionResponse
from pytest_pl_grader.utils import StudentQueryRequest
from pytest_pl_grader.utils import StudentQueryResponse
from pytest_pl_grader.utils import deserialize_object_unsafe
from pytest_pl_grader.utils import get_builtins
from pytest_pl_grader.utils import serialize_object_unsafe

ImportFunction = Callable[[str, Mapping[str, object] | None, Mapping[str, object] | None, Sequence[str], int], types.ModuleType]

HOST = "127.0.0.1"  # Loopback address, means "this computer only"


# Global ThreadPoolExecutor for CPU-bound tasks
# It's good practice to create this once and reuse it.
# The number of workers should ideally be around the number of CPU cores.
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


def populate_linecache(contents: str, fname: str) -> None:
    """
    TODO do what's in this file here
    https://github.com/PrairieLearn/PrairieLearn/commit/28c1f0bfb3792c950e5df30061469bfaf0ca199f
    """
    linecache.cache[fname] = (
        len(contents),
        None,
        [line + os.linesep for line in contents.splitlines()],
        fname,
    )


async def student_function_runner(
    student_code_vars: dict[str, Any], func_name: str, timeout: float, args_tup: Any, kwargs_dict: Any
) -> StudentFunctionResponse:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error = None
    exception_traceback = None
    result = None

    try:

        def student_function_temp() -> Any:
            student_function = student_code_vars[func_name]
            return student_function(*args_tup, **kwargs_dict)

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(executor, student_function_temp), timeout=timeout)
    except Exception as e:
        execution_error = e
        exception_traceback = traceback.format_exc(limit=-1)

    function_response: StudentFunctionResponse = {
        "status": "success" if execution_error is None else "exception",
        "value": to_json(result),
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "exception_name": type(execution_error).__name__,
        "exception_message": str(execution_error) if execution_error else None,
        "traceback": exception_traceback,
    }

    return function_response


def get_custom_importer(import_whitelist: list[str] | None, import_blacklist: list[str] | None) -> ImportFunction:
    """
    Returns a custom import function that restricts imports based on the provided whitelist and blacklist.
    If a whitelist is provided, only those modules can be imported.
    """

    original_import = __import__

    def custom_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> types.ModuleType:
        # Allow specific modules to be imported
        if import_blacklist is not None and name in import_blacklist:
            raise ImportError(f"Module '{name}' is blacklisted and cannot be imported.")
        elif (
            (import_whitelist is not None and name in import_whitelist)
            or name.startswith("__")  # Allow internal dunder imports if necessary for basic functionality
            or import_whitelist is None
        ):
            return original_import(name, globals, locals, fromlist, level)
        else:
            # Forbid other imports
            raise ImportError(f"Module '{name}' is not allowed to be imported.")

    return custom_import


async def student_code_runner(
    setup_code: str | None,
    student_code: str,
    student_file_name: str,
    timeout: float,
    import_whitelist: list[str] | None,
    import_blacklist: list[str] | None,
    starting_vars: dict[str, Any] | None,
    builtin_whitelist: list[str] | None,
    names_for_user_list: list[NamesForUserInfo] | None,
) -> tuple[dict[str, Any], dict[str, Any], ProcessStartResponse]:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error = None
    exception_traceback = None
    local_vars = deepcopy(starting_vars) if starting_vars else {}
    local_vars["__from_server_json"] = from_server_json  # Add the deserialization function to the local variables for setup code to use

    student_code_vars: dict[str, Any] = {}
    student_code_vars["__builtins__"] = get_builtins(builtin_whitelist)

    student_code_vars["__builtins__"]["__name__"] = "__main__"  # Set __name__ to "__main__" to mimic the main module
    student_code_vars["__builtins__"]["__import__"] = get_custom_importer(import_whitelist, import_blacklist)

    # TODO the data object is not passed into the setup code. Add this if needed.

    try:
        # First, execute the setup code if provided
        if setup_code:
            # Compile the setup code
            code_setup = compile(setup_code, "<setup>", "exec")
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(executor, exec, code_setup, student_code_vars, local_vars),
                    timeout=timeout,
                )

    except Exception as e:
        execution_error = e
        # TODO need to create a different message for setup code errors. This should result
        # in a different error message reported from the test case.

    if names_for_user_list is not None:
        for name_info in names_for_user_list:
            var_name = name_info["name"]

            if var_name in local_vars:
                # NOTE I think there might be issues with security with deepcopying certain
                # objects. If needed, we can prevent leaks here through serialization.
                student_code_vars[var_name] = deepcopy(local_vars[var_name])

    if execution_error is None:
        try:
            # Next, compile student code. Make sure to handle errors in this later
            # TODO have a better filename
            code_setup = compile(student_code, student_file_name, "exec")
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(executor, exec, code_setup, student_code_vars, student_code_vars),
                    timeout=timeout,
                )

        except Exception as e:
            execution_error = e
            # TODO this traceback only shows the last line with the exception.
            # Would be better if we could give the full traceback within the student code
            # for example, if the student code calls a function that raises an exception,
            # we should show the full self-contained traceback including the function call.
            exception_traceback = traceback.format_exc(limit=-1)

    result_dict: ProcessStartResponse = {
        "status": "success" if execution_error is None else "exception",
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "execution_error": type(execution_error).__name__ if execution_error else None,
        "execution_message": str(execution_error) if execution_error else None,
        "execution_traceback": str(exception_traceback),
    }

    return local_vars, student_code_vars, result_dict


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
        local_vars: None | dict = None

        async for line_bytes in reader:
            line = line_bytes.decode().strip()
            if not line:  # Handle empty lines
                continue

            json_message = json.loads(line)

            msg_type = json_message.get("message_type")
            if msg_type == "start":
                start_json_message: ProcessStartRequest = json_message
                # Execute the student code for the first time and load
                # variables into the student_code_vars dictionary
                student_code = start_json_message["student_code"]
                student_file_name = start_json_message["student_file_name"]
                setup_code = start_json_message["setup_code"]
                initialization_timeout = start_json_message["initialization_timeout"]
                import_whitelist = start_json_message["import_whitelist"]
                import_blacklist = start_json_message["import_blacklist"]
                starting_vars = start_json_message["starting_vars"]
                builtin_whitelist = start_json_message["builtin_whitelist"]
                names_for_user_list = start_json_message["names_for_user_list"]

                populate_linecache(student_code, student_file_name)

                local_vars, student_code_vars, start_response = await student_code_runner(
                    setup_code=setup_code,
                    student_code=student_code,
                    student_file_name=student_file_name,
                    timeout=initialization_timeout,
                    import_whitelist=import_whitelist,
                    import_blacklist=import_blacklist,
                    starting_vars=starting_vars,
                    builtin_whitelist=builtin_whitelist,
                    names_for_user_list=names_for_user_list,
                )

                writer.write((json.dumps(start_response) + os.linesep).encode())

            elif msg_type == "query_setup":
                assert local_vars is not None
                query_setup_json_message: SetupQueryRequest = json_message

                var_to_query = query_setup_json_message["var"]
                if var_to_query in local_vars:
                    setup_query_response: SetupQueryResponse = {
                        "status": "success",
                        "value_encoded": serialize_object_unsafe(local_vars[var_to_query]),
                    }
                else:
                    setup_query_response = {"status": "not_found", "value_encoded": ""}

                writer.write((json.dumps(setup_query_response) + os.linesep).encode())

            elif msg_type == "query":
                assert student_code_vars is not None
                query_json_message: StudentQueryRequest = json_message

                var_to_query = query_json_message["var"]

                # Check if the variable exists in the student_code_vars
                if var_to_query in student_code_vars:
                    query_response: StudentQueryResponse = {"status": "success", "value": to_json(student_code_vars[var_to_query])}
                else:
                    query_response = {"status": "not_found", "value": ""}

                writer.write((json.dumps(query_response) + os.linesep).encode())

            elif msg_type == "query_function":
                assert student_code_vars is not None
                query_function_json_message: StudentFunctionRequest = json_message

                func_name = query_function_json_message["function_name"]
                args = deserialize_object_unsafe(query_function_json_message["args_encoded"])
                kwargs = deserialize_object_unsafe(query_function_json_message["kwargs_encoded"])
                query_timeout = query_function_json_message["query_timeout"]

                function_response = await student_function_runner(student_code_vars, func_name, query_timeout, args, kwargs)

                writer.write((json.dumps(function_response) + os.linesep).encode())

            # TODO handle cases of different payloads
            # The first payload should be student code
            if line.lower() == "exit":
                writer.write(("Goodbye!" + os.linesep).encode())
                await writer.drain()
                break  # Exit the loop and terminate the server

            # Simulate processing a request
            # response = f"Server processed: '{line.upper()}'\n"

            await writer.drain()  # Ensure the response is written to stdout

    except asyncio.CancelledError:
        writer.write((json.dumps({"status": "failure", "message": "Server was cancelled."}) + os.linesep).encode())
    except asyncio.TimeoutError:
        writer.write((json.dumps({"status": "failure", "message": "Student code timed out."}) + os.linesep).encode())
    except Exception as e:
        writer.write((json.dumps({"status": "failure", "message": f"An error occurred: {e}"}) + os.linesep).encode())
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
