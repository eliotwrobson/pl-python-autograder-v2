import asyncio
import concurrent.futures
import json

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 8888  # Port to listen on (non-privileged ports are > 1023)
BUFFER_SIZE = 4096  # Standard buffer size for receiving data

# Global ThreadPoolExecutor for CPU-bound tasks
# It's good practice to create this once and reuse it.
# The number of workers should ideally be around the number of CPU cores.
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Handles a single client connection, receiving and processing JSON messages.
    """
    addr = writer.get_extra_info("peername")

    while True:
        try:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break

            message = data.decode("utf-8")

            try:
                json_message = json.loads(message)
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(executor, _run_blocking_task, task_payload), timeout=timeout_seconds
                )
                # Example: send an acknowledgement back
                response_message = {"status": "received", "data": json_message}
                writer.write(json.dumps(response_message).encode("utf-8") + b"\n")  # Add newline for stream parsing
                await writer.drain()
                # ------------------------------------

            except json.JSONDecodeError as e:
                error_response = {"status": "error", "message": f"Invalid JSON: {e}"}
                writer.write(json.dumps(error_response).encode("utf-8") + b"\n")
                await writer.drain()
            except UnicodeDecodeError as e:
                error_response = {"status": "error", "message": f"Invalid UTF-8 encoding: {e}"}
                writer.write(json.dumps(error_response).encode("utf-8") + b"\n")
                await writer.drain()

        except ConnectionResetError:
            break
        except Exception:
            break

    writer.close()
    await writer.wait_closed()  # Ensure the writer is truly closed


async def main():
    """
    Main function to start the asyncio TCP server.
    """
    server = await asyncio.start_server(handle_client, HOST, PORT)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
