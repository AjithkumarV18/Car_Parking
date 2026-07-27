import socket
import threading
import time

import uvicorn
import webview

from app.main import app


SERVER_HOST = "0.0.0.0"
LOCAL_HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{LOCAL_HOST}:{PORT}"


def wait_for_server(timeout: int = 30) -> bool:
    """Wait until the FastAPI server is ready."""

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((LOCAL_HOST, PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)

    return False


if __name__ == "__main__":
    config = uvicorn.Config(
        app=app,
        host=SERVER_HOST,
        port=PORT,
        reload=False,
        log_config=None,
        access_log=False,
    )

    server = uvicorn.Server(config)

    server_thread = threading.Thread(
        target=server.run,
        daemon=True,
    )
    server_thread.start()

    if not wait_for_server():
        server.should_exit = True
        raise RuntimeError("ParkingApp server failed to start.")

    webview.create_window(
        title="Parking Management System",
        url=APP_URL,
        width=1400,
        height=850,
        min_size=(1000, 650),
        resizable=True,
        confirm_close=True,
    )

    webview.start()

    server.should_exit = True
    server_thread.join(timeout=5)