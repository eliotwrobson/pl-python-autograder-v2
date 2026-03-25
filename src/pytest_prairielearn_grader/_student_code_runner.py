import asyncio
import builtins
import concurrent.futures
import importlib
import io
import json
import linecache
import os
import pathlib
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

from pytest_prairielearn_grader.json_utils import from_server_json

# TODO make it so that other files in this package cannot import from this one
# ask Gemini how to do it
from pytest_prairielearn_grader.json_utils import to_json
from pytest_prairielearn_grader.utils import FunctionStatusCode
from pytest_prairielearn_grader.utils import ProcessStartRequest
from pytest_prairielearn_grader.utils import ProcessStartResponse
from pytest_prairielearn_grader.utils import ProcessStatusCode
from pytest_prairielearn_grader.utils import QueryStatusCode
from pytest_prairielearn_grader.utils import SetupQueryRequest
from pytest_prairielearn_grader.utils import SetupQueryResponse
from pytest_prairielearn_grader.utils import StudentFunctionRequest
from pytest_prairielearn_grader.utils import StudentFunctionResponse
from pytest_prairielearn_grader.utils import StudentQueryRequest
from pytest_prairielearn_grader.utils import StudentQueryResponse
from pytest_prairielearn_grader.utils import WorkspaceStartRequest
from pytest_prairielearn_grader.utils import deserialize_object_unsafe
from pytest_prairielearn_grader.utils import get_builtins
from pytest_prairielearn_grader.utils import serialize_object_unsafe

ImportFunction = Callable[[str, Mapping[str, object] | None, Mapping[str, object] | None, Sequence[str] | None, int], types.ModuleType]

# Capture the real built-in import once at module load time, before any patching.
# get_custom_importer must delegate to this to avoid recursion when builtins.__import__
# is later replaced by a workspace_importer in workspace_runner.
_REAL_IMPORT: ImportFunction = builtins.__import__  # type: ignore[assignment]

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


def _resolve_dotted_name(name: str, student_code_vars: dict[str, Any]) -> Any:
    """
    Resolves a name that may be a dotted module path (e.g. 'models.classifier.predict').

    For dotted names, splits on the last '.' to get a module path and attribute name,
    then imports the module and retrieves the attribute.  This uses the normal Python
    import machinery, so relative imports, __init__.py, and package structure all work
    as expected.

    For flat names, falls back to looking up the name in student_code_vars (the
    namespace populated by setup_code and direct exec).
    """
    if "." in name:
        module_path, attr_name = name.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, attr_name)
    return student_code_vars[name]


async def student_function_runner(
    student_code_vars: dict[str, Any],
    func_name: str,
    timeout: float,
    args_tup: Any,
    kwargs_dict: Any,
    workspace_mode: bool = False,
) -> StudentFunctionResponse:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error = None
    exception_traceback = None
    result = None

    try:

        def student_function_temp() -> Any:
            if workspace_mode:
                student_function = _resolve_dotted_name(func_name, student_code_vars)
            else:
                student_function = student_code_vars[func_name]
            return student_function(*args_tup, **kwargs_dict)

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(executor, student_function_temp), timeout=timeout)
    except Exception as e:
        execution_error = e
        exception_traceback = traceback.format_exc(limit=-1)

    function_response: StudentFunctionResponse = {
        "status": FunctionStatusCode.SUCCESS if execution_error is None else FunctionStatusCode.EXCEPTION,
        "value": to_json(result),
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "exception_name": type(execution_error).__name__,
        "exception_message": str(execution_error) if execution_error else None,
        "traceback": exception_traceback,
    }

    return function_response


def get_custom_importer(
    import_whitelist: list[str] | None,
    import_blacklist: list[str] | None,
    workspace_dir: str | None = None,
) -> ImportFunction:
    """
    Returns a custom import function that restricts imports based on the provided whitelist and
    blacklist.  If a whitelist is provided, only those modules can be imported.

    When *workspace_dir* is given, any module whose top-level package name resolves to a file or
    directory inside that directory is unconditionally allowed, so that student modules can import
    each other without instructors needing to maintain a manual whitelist of their own files.
    Relative imports (level > 0) are always permitted for the same reason.
    """

    original_import = _REAL_IMPORT

    # Pre-compute the workspace directory string at factory time (before this importer is
    # installed into builtins.__import__).  Doing pathlib.Path() or os.path operations
    # inside custom_import itself would trigger re-entrant calls: Python 3.12 pathlib
    # lazy-imports ntpath/posixpath on first use, which would call custom_import again
    # and cause infinite RecursionError.  Using a plain str and os.path functions (which
    # are loaded as part of the 'os' module and never need to re-import anything) is safe.
    _ws_str: str | None = str(pathlib.Path(workspace_dir)) if workspace_dir is not None else None

    def custom_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = None,
        level: int = 0,
    ) -> types.ModuleType:
        fl = fromlist or ()
        # Relative imports are always intra-package and allowed.
        if level > 0:
            return original_import(name, globals, locals, fl, level)

        # Workspace-local modules are always importable regardless of whitelist/blacklist.
        # A module is considered local if its top-level package maps to a file or directory
        # directly inside workspace_dir.
        if _ws_str is not None:
            top_level = name.split(".")[0]
            if os.path.isfile(os.path.join(_ws_str, top_level + ".py")) or os.path.isdir(os.path.join(_ws_str, top_level)):
                return original_import(name, globals, locals, fl, level)

        # Apply blacklist / whitelist to external imports.
        if import_blacklist is not None and name in import_blacklist:
            raise ImportError(f"Module '{name}' is blacklisted and cannot be imported.")
        elif (
            (import_whitelist is not None and name in import_whitelist)
            or name.startswith("_")  # Allow Python internal/private modules (_io, _abc, _collections, etc.)
            or import_whitelist is None
        ):
            return original_import(name, globals, locals, fl, level)
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
    names_for_user_list: list[str] | None,
) -> tuple[dict[str, Any], dict[str, Any], ProcessStartResponse]:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error: Exception | None = None
    exception_traceback = None
    local_vars = deepcopy(starting_vars) if starting_vars else {}
    local_vars["__from_server_json"] = from_server_json  # Add the deserialization function to the local variables for setup code to use

    student_code_vars: dict[str, Any] = {}
    student_code_vars["__builtins__"] = get_builtins(builtin_whitelist)

    student_code_vars["__builtins__"]["__name__"] = "__main__"  # Set __name__ to "__main__" to mimic the main module
    student_code_vars["__builtins__"]["__import__"] = get_custom_importer(import_whitelist, import_blacklist)

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

    except asyncio.TimeoutError:
        execution_error = asyncio.TimeoutError("Setup code execution timed out")
        # TODO need to create a different message for setup code errors. This should result
        # in a different error message reported from the test case.
    except Exception as e:
        execution_error = e
        # TODO need to create a different message for setup code errors. This should result
        # in a different error message reported from the test case.

    # Only inject variables that are explicitly listed in names_for_user_list
    # This prevents accidental variable leaking from setup_code or starting_vars
    if names_for_user_list is not None:
        for var_name in names_for_user_list:
            if var_name in local_vars:
                # NOTE I think there might be issues with security with deepcopying certain
                # objects. If needed, we can prevent leaks here through serialization.
                student_code_vars[var_name] = deepcopy(local_vars[var_name])
            elif starting_vars is not None and var_name in starting_vars:
                # If not in local_vars (setup_code), try getting from starting_vars
                student_code_vars[var_name] = deepcopy(starting_vars[var_name])

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

        except asyncio.TimeoutError:
            execution_error = asyncio.TimeoutError("Student code execution timed out")
        except Exception as e:
            execution_error = e
            # TODO this traceback only shows the last line with the exception.
            # Would be better if we could give the full traceback within the student code
            # for example, if the student code calls a function that raises an exception,
            # we should show the full self-contained traceback including the function call.
            exception_traceback = traceback.format_exc(limit=-1)

    # Determine the status based on the type of error
    if execution_error is None:
        status = ProcessStatusCode.SUCCESS
    elif isinstance(execution_error, asyncio.TimeoutError):
        status = ProcessStatusCode.TIMEOUT
    else:
        status = ProcessStatusCode.EXCEPTION

    result_dict: ProcessStartResponse = {
        "status": status,
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "execution_error": type(execution_error).__name__ if execution_error else None,
        "execution_message": str(execution_error) if execution_error else None,
        "execution_traceback": str(exception_traceback),
    }

    return local_vars, student_code_vars, result_dict


async def workspace_runner(
    workspace_dir: str,
    exec_entry: str | None,
    setup_code: str | None,
    timeout: float,
    import_whitelist: list[str] | None,
    import_blacklist: list[str] | None,
    starting_vars: dict[str, Any] | None,
    builtin_whitelist: list[str] | None,
    names_for_user_list: list[str] | None,
) -> tuple[dict[str, Any], dict[str, Any], ProcessStartResponse]:
    """
    Sets up a workspace sandbox by inserting workspace_dir at the front of sys.path
    so that student modules can be imported via their dotted names.  Optionally
    executes an entry-point file (exec_entry) and runs setup_code exactly as the
    regular student_code_runner does.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error: Exception | None = None
    exception_traceback = None
    local_vars = deepcopy(starting_vars) if starting_vars else {}
    local_vars["__from_server_json"] = from_server_json

    student_code_vars: dict[str, Any] = {}
    student_code_vars["__builtins__"] = get_builtins(builtin_whitelist)
    student_code_vars["__builtins__"]["__name__"] = "__main__"
    workspace_importer = get_custom_importer(import_whitelist, import_blacklist, workspace_dir)
    student_code_vars["__builtins__"]["__import__"] = workspace_importer
    # Patch the real builtins.__import__ so that workspace modules loaded via
    # importlib.import_module() (which use the real builtins, not student_code_vars)
    # also go through the same restrictions.  The subprocess is dedicated to one
    # grading session so this global patch is safe.
    builtins.__import__ = workspace_importer  # type: ignore[assignment]

    # Insert workspace_dir at the front of sys.path so imports resolve against it.
    # Use insert(0, ...) to take precedence over any previously added paths.
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)

    try:
        if setup_code:
            code_setup = compile(setup_code, "<setup>", "exec")
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(executor, exec, code_setup, student_code_vars, local_vars),
                    timeout=timeout,
                )
    except asyncio.TimeoutError:
        execution_error = asyncio.TimeoutError("Setup code execution timed out")
    except Exception as e:
        execution_error = e

    if names_for_user_list is not None:
        for var_name in names_for_user_list:
            if var_name in local_vars:
                student_code_vars[var_name] = deepcopy(local_vars[var_name])
            elif starting_vars is not None and var_name in starting_vars:
                student_code_vars[var_name] = deepcopy(starting_vars[var_name])

    # Optionally exec an entry-point file at startup (e.g. "main.py") so that
    # module-level side effects in the student's root script are applied.
    if execution_error is None and exec_entry is not None:
        entry_path = pathlib.Path(workspace_dir) / exec_entry
        try:
            entry_source = entry_path.read_text(encoding="utf-8")
            entry_code = compile(entry_source, str(entry_path), "exec")
            populate_linecache(entry_source, str(entry_path))
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(executor, exec, entry_code, student_code_vars, student_code_vars),
                    timeout=timeout,
                )
        except asyncio.TimeoutError:
            execution_error = asyncio.TimeoutError("Entry-point file execution timed out")
        except Exception as e:
            execution_error = e
            exception_traceback = traceback.format_exc(limit=-1)

    if execution_error is None:
        status = ProcessStatusCode.SUCCESS
    elif isinstance(execution_error, asyncio.TimeoutError):
        status = ProcessStatusCode.TIMEOUT
    else:
        status = ProcessStatusCode.EXCEPTION

    result_dict: ProcessStartResponse = {
        "status": status,
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
        workspace_mode: bool = False

        async for line_bytes in reader:
            line = line_bytes.decode().strip()
            if not line:  # Handle empty lines
                continue

            json_message = json.loads(line)

            msg_type = json_message.get("message_type")
            if msg_type == "start_workspace":
                ws_json_message: WorkspaceStartRequest = json_message
                workspace_mode = True

                local_vars, student_code_vars, start_response = await workspace_runner(
                    workspace_dir=ws_json_message["workspace_dir"],
                    exec_entry=ws_json_message["exec_entry"],
                    setup_code=ws_json_message["setup_code"],
                    timeout=ws_json_message["initialization_timeout"],
                    import_whitelist=ws_json_message["import_whitelist"],
                    import_blacklist=ws_json_message["import_blacklist"],
                    starting_vars=ws_json_message["starting_vars"],
                    builtin_whitelist=ws_json_message["builtin_whitelist"],
                    names_for_user_list=ws_json_message["names_for_user_list"],
                )

                writer.write((json.dumps(start_response) + os.linesep).encode())

            elif msg_type == "start":
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
                        "status": QueryStatusCode.SUCCESS,
                        "value_encoded": serialize_object_unsafe(local_vars[var_to_query]),
                    }
                else:
                    setup_query_response = {"status": QueryStatusCode.NOT_FOUND, "value_encoded": ""}

                writer.write((json.dumps(setup_query_response) + os.linesep).encode())

            elif msg_type == "query":
                assert student_code_vars is not None
                query_json_message: StudentQueryRequest = json_message

                var_to_query = query_json_message["var"]

                try:
                    if workspace_mode and "." in var_to_query:
                        value = _resolve_dotted_name(var_to_query, student_code_vars)
                    elif var_to_query in student_code_vars:
                        value = student_code_vars[var_to_query]
                    else:
                        raise KeyError(var_to_query)

                    query_response: StudentQueryResponse = {
                        "status": QueryStatusCode.SUCCESS,
                        "value": to_json(value),
                    }
                except (KeyError, AttributeError, ImportError):
                    query_response = {"status": QueryStatusCode.NOT_FOUND, "value": ""}

                writer.write((json.dumps(query_response) + os.linesep).encode())

            elif msg_type == "query_function":
                assert student_code_vars is not None
                query_function_json_message: StudentFunctionRequest = json_message

                func_name = query_function_json_message["function_name"]
                args = deserialize_object_unsafe(query_function_json_message["args_encoded"])
                kwargs = deserialize_object_unsafe(query_function_json_message["kwargs_encoded"])
                query_timeout = query_function_json_message["query_timeout"]

                function_response = await student_function_runner(
                    student_code_vars, func_name, query_timeout, args, kwargs, workspace_mode=workspace_mode
                )

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

    line_limit = 10 * 1024 * 1024  # 10 MB line limit to handle large messages

    # Start the server, binding to the specified host and port
    server = await asyncio.start_server(handle_client, HOST, 0, limit=line_limit)
    addr = server.sockets[0].getsockname()
    print(f"{addr[0]}, {addr[1]}", flush=True)

    async with server:
        # Run forever, or until the server is explicitly stopped
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
