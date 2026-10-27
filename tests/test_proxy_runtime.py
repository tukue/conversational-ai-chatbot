"""Real loopback startup/restart checks; all model traffic uses a fake provider."""
import signal
import socket
from types import SimpleNamespace

import httpx
import pytest

import config
from src import llm_proxy, proxy_runtime


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    state = SimpleNamespace(port=None, calls=[], apps=[])
    values = {
        "START_INTERNAL_LLM_PROXY": True, "USE_LLM_PROXY": True,
        "PROXY_BASE_URL": "http://127.0.0.1:8080", "PROXY_MODEL": "test-model",
        "PROXY_MODELS": ("test-model",), "PROXY_STARTUP_TIMEOUT_SECONDS": 2,
    }
    for name, value in values.items():
        monkeypatch.setattr(config, name, value)
    calls = state.calls
    apps = state.apps
    bind_listener = proxy_runtime._bind_listener

    def allocate_listener(port):
        # Let the OS allocate the actual server socket; never release a probe
        # socket between choosing a port and starting the gateway.
        listener = bind_listener(0)
        state.port = listener.getsockname()[1]
        monkeypatch.setattr(config, "PROXY_BASE_URL", f"http://127.0.0.1:{state.port}")
        return listener

    monkeypatch.setattr(proxy_runtime, "_bind_listener", allocate_listener)
    state.bind_listener = bind_listener

    def upstream(request):
        calls.append(request)
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "Open Help for support."}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3},
        })

    def factory():
        app = llm_proxy.create_app(llm_proxy.Settings(
            "client", "admin", "provider", "https://provider.test/chat", ("test-model",),
            analytics_db=str(tmp_path / "usage.db")), httpx.MockTransport(upstream))
        apps.append(app)
        return app
    monkeypatch.setattr(llm_proxy, "app_from_config", factory)
    return state


def test_restart_readiness_generation_persistence_and_cleanup(runtime, monkeypatch):
    previous = signal.getsignal(signal.SIGTERM)
    for count in (1, 2):
        if count == 2:
            # Exercise the real bind on rapid restart of the previous port.
            monkeypatch.setattr(proxy_runtime, "_bind_listener", runtime.bind_listener)
        with proxy_runtime.bundled_proxy():
            with httpx.Client(base_url=config.PROXY_BASE_URL, trust_env=False) as client:
                assert client.get("/health/ready").status_code == 200
                assert client.get("/analytics").status_code == 401
                response = client.post("/v1/chat/completions",
                    headers={"Authorization": "Bearer client"}, json={
                        "model": "test-model", "messages": [{"role": "user", "content": "Help"}]})
                assert response.status_code == 200
                history = client.get("/analytics/history?days=1",
                                     headers={"Authorization": "Bearer admin"}).json()
                assert history["totals"]["completion_tokens"] == count * 3
        assert not runtime.apps[-1].state.ready
        assert runtime.apps[-1].state.upstream.is_closed
        assert signal.getsignal(signal.SIGTERM) == previous
    assert len(runtime.calls) == 2
    assert runtime.calls[0].headers["authorization"] == "Bearer provider"
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", runtime.port)) != 0


def test_disabled_runtime_never_builds_gateway(monkeypatch):
    monkeypatch.setattr(config, "START_INTERNAL_LLM_PROXY", False)
    monkeypatch.setattr(llm_proxy, "app_from_config", lambda: pytest.fail("must not start"))
    with proxy_runtime.bundled_proxy():
        pass


@pytest.mark.parametrize("name,value", [
    ("USE_LLM_PROXY", False), ("PROXY_STARTUP_TIMEOUT_SECONDS", 0),
    ("PROXY_STARTUP_TIMEOUT_SECONDS", float("nan")),
    ("PROXY_BASE_URL", "https://127.0.0.1:8080"),
    ("PROXY_BASE_URL", "http://0.0.0.0:8080"),
    ("PROXY_BASE_URL", "http://127.0.0.1:8080/path"),
    ("PROXY_BASE_URL", "http://127.0.0.1:0"),
    ("PROXY_MODEL", "unapproved"),
])
def test_invalid_configuration_fails_before_ui(runtime, monkeypatch, name, value):
    monkeypatch.setattr(config, name, value)
    with pytest.raises(ValueError):
        with proxy_runtime.bundled_proxy():
            pytest.fail("UI must not start")


def test_port_collision_fails_before_ui(runtime, monkeypatch):
    monkeypatch.setattr(proxy_runtime, "_bind_listener", runtime.bind_listener)
    with socket.socket() as occupied:
        occupied.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        monkeypatch.setattr(config, "PROXY_BASE_URL", f"http://127.0.0.1:{port}")
        with pytest.raises(OSError):
            with proxy_runtime.bundled_proxy():
                pytest.fail("must not contact existing listener")


def test_ui_error_still_stops_gateway(runtime):
    with pytest.raises(RuntimeError, match="UI failed"):
        with proxy_runtime.bundled_proxy():
            raise RuntimeError("UI failed")
    assert not runtime.apps[0].state.ready


def test_sigterm_stops_gateway(runtime):
    with pytest.raises(SystemExit):
        with proxy_runtime.bundled_proxy():
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
    assert not runtime.apps[0].state.ready


@pytest.mark.parametrize("mode", ["failed", "timeout", "not_ready", "stuck"])
def test_startup_and_shutdown_failures(runtime, monkeypatch, mode):
    import uvicorn

    class Server:
        def __init__(self, settings):
            self.started = mode in {"not_ready", "stuck"}
            self.should_exit = False

        def run(self, sockets):
            raise RuntimeError("private startup data")

    class Thread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            if mode == "failed":
                self.target()
            if mode == "stuck":
                runtime.apps[0].state.ready = True

        def is_alive(self):
            return mode != "failed"

        def join(self, timeout):
            pass

    monkeypatch.setattr(uvicorn, "Server", Server)
    monkeypatch.setattr(proxy_runtime.threading, "Thread", Thread)
    if mode == "timeout":
        monkeypatch.setattr(config, "PROXY_STARTUP_TIMEOUT_SECONDS", 0.001)
    with pytest.raises(RuntimeError, match="Internal proxy") as exc:
        with proxy_runtime.bundled_proxy():
            pass
    assert "private startup data" not in str(exc.value)


def test_app_launch_runs_inside_gateway_lifecycle(monkeypatch):
    from contextlib import contextmanager
    import importlib.util
    from pathlib import Path
    import sys

    monkeypatch.setitem(sys.modules, "gradio", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "spaces", SimpleNamespace(GPU=lambda fn: fn))
    spec = importlib.util.spec_from_file_location("bundled_app_test", Path(__file__).parents[1] / "app.py")
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    events = []

    @contextmanager
    def gateway():
        events.append("ready")
        try:
            yield
        finally:
            events.append("stopped")

    monkeypatch.setattr(proxy_runtime, "bundled_proxy", gateway)
    monkeypatch.setattr(app, "_launch_chatbot", lambda: events.append("launch"))
    app.main()
    assert events == ["ready", "launch", "stopped"]


def test_invalid_model_never_constructs_gateway(runtime, monkeypatch):
    monkeypatch.setattr(config, "PROXY_MODEL", "unapproved")
    monkeypatch.setattr(llm_proxy, "app_from_config", lambda: pytest.fail("must validate model first"))
    with pytest.raises(ValueError, match="allowlist"):
        with proxy_runtime.bundled_proxy():
            pytest.fail("must not launch")


def test_listener_supports_reuse_and_reserves_port():
    with proxy_runtime._bind_listener(0) as listener:
        assert listener.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 1
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(OSError):
            proxy_runtime._bind_listener(port)
