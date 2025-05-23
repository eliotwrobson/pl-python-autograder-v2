import asyncio
import concurrent.futures
import io
import json
import sys
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from typing import Any
from typing import NamedTuple

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


async def main() -> None:
    """
    Reads lines from stdin asynchronously and responds on stdout.
    Mimics a simple server handling requests.
    """
    loop = asyncio.get_running_loop()

    # Create StreamReader for stdin
    # We use a protocol to handle the stream, then get the reader/writer from it
    # This is a bit more involved than direct pipe connections, but more robust
    # for full duplex interactive streams like stdin/stdout.
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    # connect_read_pipe connects a pipe to an asyncio transport and protocol
    transport, _ = await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    # Create StreamWriter for stdout
    writer_transport, writer_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, loop)

    print("Server started. Type your message and press Enter. Type 'exit' to quit.", file=sys.stderr)
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

                writer.write(json.dumps(response).encode() + b"\n")

            elif msg_type == "query":
                var_to_query = json_message["var"]
                # Check if the variable exists in the student_code_vars
                if var_to_query in student_code_vars:
                    response = json.dumps({"status": "success", "value": student_code_vars[var_to_query]})
                else:
                    response = json.dumps({"status": "error", "message": f"Variable '{var_to_query}' not found."})

                writer.write(response.encode() + b"\n")  # Add newline for stream parsing

            # TODO handle cases of different payloads
            # The first payload should be student code
            if line.lower() == "exit":
                response = "Goodbye!\n"
                writer.write(response.encode())
                await writer.drain()
                break  # Exit the loop and terminate the server

            # Simulate processing a request
            # response = f"Server processed: '{line.upper()}'\n"

            await writer.drain()  # Ensure the response is written to stdout

    except asyncio.CancelledError:
        print("Server was cancelled.")
    except asyncio.TimeoutError:
        writer.write(json.dumps({"status": "failurue", "message": "Student code timed out."}).encode() + b"\n")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # It's good practice to close transports and writers
        print("Closing server connections...")
        if transport:
            transport.close()
        if writer:
            writer.close()
            await writer.wait_closed()  # Wait for the writer to finish closing


if __name__ == "__main__":
    asyncio.run(main())
