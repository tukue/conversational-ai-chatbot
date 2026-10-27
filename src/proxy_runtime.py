"""Lifecycle for an optional loopback-only gateway bundled with Gradio."""
from contextlib import contextmanager
import math
import socket
import signal
import threading
from time import monotonic, sleep
from urllib.parse import urlsplit


def _port(base_url):
    url = urlsplit(base_url)
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or url.username
            or url.password or url.path not in ("", "/") or url.query or url.fragment):
        raise ValueError("Bundled proxy requires an HTTP 127.0.0.1 base URL without a path")
    port = url.port if url.port is not None else 80
    if not 1 <= port <= 65535:
        raise ValueError("Bundled proxy requires a valid port")
    return port


def _bind_listener(port):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
    except BaseException:
        listener.close()
        raise
    return listener


@contextmanager
def bundled_proxy():
    """Start only when requested, and always stop when the application exits."""
    import config

    if not config.START_INTERNAL_LLM_PROXY:
        yield
        return

    if not config.USE_LLM_PROXY:
        raise ValueError("Internal proxy startup requires USE_LLM_PROXY=true")
    timeout = config.PROXY_STARTUP_TIMEOUT_SECONDS
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Proxy startup timeout must be positive and finite")
    port = _port(config.PROXY_BASE_URL)

    import uvicorn
    from src.llm_proxy import app_from_config

    if config.PROXY_MODEL not in config.PROXY_MODELS:
        raise ValueError("Chatbot model must be in the proxy allowlist")
    app = app_from_config()
    # Bind before starting the thread: a port collision must never let another
    # service satisfy readiness or receive this application's credentials.
    with _bind_listener(port) as listener:
        server = uvicorn.Server(uvicorn.Config(
            app, host="127.0.0.1", port=port, lifespan="on", workers=1,
            access_log=False, log_config=None, log_level="critical",
            proxy_headers=False, timeout_graceful_shutdown=5,
        ))
        failed = threading.Event()

        def run():
            try:
                server.run(sockets=[listener])
            except BaseException:
                # Never print startup exception text; it can contain secrets.
                failed.set()

        thread = threading.Thread(target=run, name="llm-proxy", daemon=True)
        thread.start()
        try:
            deadline = monotonic() + timeout
            while not server.started:
                if failed.is_set() or not thread.is_alive():
                    raise RuntimeError("Internal proxy failed to start")
                if monotonic() >= deadline:
                    raise RuntimeError("Internal proxy startup timed out")
                sleep(0.01)
            if not app.state.ready:
                raise RuntimeError("Internal proxy is not ready")
            previous = None
            if threading.current_thread() is threading.main_thread():
                def terminate(signum, frame):
                    raise SystemExit(0)
                previous = signal.signal(signal.SIGTERM, terminate)
            try:
                yield
            finally:
                if previous is not None:
                    signal.signal(signal.SIGTERM, previous)
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Internal proxy shutdown timed out")
