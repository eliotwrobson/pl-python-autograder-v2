import asyncio
import concurrent.futures
import json
import sys

# Global ThreadPoolExecutor for CPU-bound tasks
# It's good practice to create this once and reuse it.
# The number of workers should ideally be around the number of CPU cores.
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


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
        async for line_bytes in reader:
            line = line_bytes.decode().strip()
            if not line:  # Handle empty lines
                continue

            json_message = json.loads(line)

            # TODO handle cases of different payloads
            # The first payload should be student code
            if line.lower() == "exit":
                response = "Goodbye!\n"
                writer.write(response.encode())
                await writer.drain()
                break  # Exit the loop and terminate the server

            # Simulate processing a request
            response = f"Server processed: '{line.upper()}'\n"
            writer.write(response.encode())
            await writer.drain()  # Ensure the response is written to stdout

    except asyncio.CancelledError:
        print("Server was cancelled.", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        # It's good practice to close transports and writers
        print("Closing server connections...", file=sys.stderr)
        if transport:
            transport.close()
        if writer:
            writer.close()
            await writer.wait_closed()  # Wait for the writer to finish closing


if __name__ == "__main__":
    asyncio.run(main())
