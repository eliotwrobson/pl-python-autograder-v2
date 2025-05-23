import asyncio
import concurrent.futures
import io
import json
import sys
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from typing import Any
from typing import NamedTuple

# Define the server's address and port
HOST = "127.0.0.1"  # Loopback address, means "this computer only"
PORT = 1111

# Global ThreadPoolExecutor for CPU-bound tasks
# It's good practice to create this once and reuse it.
# The number of workers should ideally be around the number of CPU cores.
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


class StudentCodeResult(NamedTuple):
    """
    A named tuple to hold the result of the student code execution.
    """

    student_local_vars: dict
    captured_stdout: str
    captured_stderr: str
    execution_error: Exception | None


def student_code_runner(student_code: str) -> StudentCodeResult:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    execution_error = None
    student_code_vars: dict[str, Any] = {}

    try:
        # First, compile student code. Make sure to handle errors in this later
        # TODO have a better filename
        code_setup = compile(student_code, "StudentCodeFile", "exec")
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code_setup, {}, student_code_vars)  # noqa: S102
    except Exception as e:
        execution_error = e

    return StudentCodeResult(
        student_local_vars=student_code_vars,
        captured_stdout=stdout_capture.getvalue(),
        captured_stderr=stderr_capture.getvalue(),
        execution_error=execution_error,
    )


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

                student_code_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(executor, student_code_runner, student_code), timeout=1
                )

                student_code_vars = student_code_result.student_local_vars

                response = {
                    "status": "success",
                    "stdout": student_code_result.captured_stdout,
                    "stderr": student_code_result.captured_stderr,
                    "execution_error": str(student_code_result.execution_error),
                }

                writer.write(json.dumps(response).encode())  # Add newline for stream parsing

            elif msg_type == "query":
                var_to_query = json_message["var"]
                # Check if the variable exists in the student_code_vars
                if var_to_query in student_code_vars:
                    response = json.dumps({"status": "success", "value": student_code_vars[var_to_query]})
                else:
                    response = json.dumps({"status": "error", "message": f"Variable '{var_to_query}' not found."})

                writer.write(response.encode())  # Add newline for stream parsing

            # TODO handle cases of different payloads
            # The first payload should be student code
            if line.lower() == "exit":
                response = "Goodbye!"
                writer.write(response.encode())
                await writer.drain()
                break  # Exit the loop and terminate the server

            # Simulate processing a request
            # response = f"Server processed: '{line.upper()}'\n"

            await writer.drain()  # Ensure the response is written to stdout

    except asyncio.CancelledError:
        print("Server was cancelled.")
    except asyncio.TimeoutError:
        writer.write(json.dumps({"status": "failurue", "message": "Student code timed out."}).encode())
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # It's good practice to close transports and writers
        print("Closing server connections...")

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
    server = await asyncio.start_server(handle_client, HOST, PORT)

    async with server:
        # Run forever, or until the server is explicitly stopped
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
