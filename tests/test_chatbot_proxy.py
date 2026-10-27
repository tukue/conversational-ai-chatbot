"""Exercise the chat entry point through the real gateway with a mocked provider."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from src import chatbot
from src.llm_proxy import Settings, create_app


@pytest.fixture
def integration(monkeypatch):
    for name, value in {
        "ENABLE_GENERATIVE_FALLBACK": True, "USE_LLM_PROXY": True,
        "ENABLE_RATE_LIMITING": False, "PROXY_CLIENT_KEY": "client",
        "PROXY_MODEL": "test-model", "PROXY_BASE_URL": "http://proxy.test/",
    }.items():
        monkeypatch.setattr(chatbot.config, name, value)
    monkeypatch.setattr(chatbot, "classify_intent", lambda _: "general")
    monkeypatch.setattr(chatbot, "is_on_topic", lambda _: True)
    monkeypatch.setattr(chatbot, "respond_with_dialogpt",
                        lambda *args: pytest.fail("must not bypass proxy"))
    calls = []
    output = {"choices": [{"message": {"role": "assistant", "content": "Please use Help on your order."}}],
              "usage": {"prompt_tokens": 10, "completion_tokens": 7}}

    def upstream(request):
        calls.append(request)
        return httpx.Response(200, json=output)

    settings = Settings("client", "admin", "provider", "https://provider.test/chat", ("test-model",))
    with TestClient(create_app(settings, httpx.MockTransport(upstream))) as client:
        def forward(url, **kwargs):
            assert url == "http://proxy.test/v1/chat/completions"
            assert kwargs.pop("trust_env") is False
            return client.post("/v1/chat/completions", **kwargs)
        monkeypatch.setattr(httpx, "post", forward)
        yield client, calls, output


def test_chat_forwards_history_and_counts_usage(integration):
    client, calls, _ = integration
    history = [{"role": "user", "content": "Hello"},
               {"role": "assistant", "content": "How can I help?"}]
    assert "Help on your order" in chatbot.chat("I need support", history)
    payload = json.loads(calls[0].content)
    assert payload["messages"][:2] == history
    assert "I need support" in payload["messages"][-1]["content"]
    assert payload["model"] == "test-model"
    assert calls[0].headers["authorization"] == "Bearer provider"
    metrics = client.get("/analytics", headers={"Authorization": "Bearer admin"}).json()
    assert metrics["completion_tokens"] == 7


def test_history_denial_never_calls_provider(integration):
    _, calls, _ = integration
    response = chatbot.chat("I need support", [("My SSN is 123-45-6789", "Hello")])
    assert "policy restriction" in response
    assert not calls


def test_blocked_generation_is_not_delivered(integration):
    client, calls, output = integration
    output["choices"][0]["message"]["content"] = "SSN: 123-45-6789"
    response = chatbot.chat("I need support", [])
    assert "policy restriction" in response
    assert "123-45-6789" not in response
    assert len(calls) == 1
    assert client.get("/analytics", headers={"Authorization": "Bearer admin"}).json()["completion_tokens"] == 7


@pytest.mark.parametrize("status, expected", [(401, "unavailable"), (403, "policy restriction"),
    (413, "policy restriction"), (429, "Too many requests"), (408, "timed out"),
    (504, "timed out"), (503, "busy"), (502, "trouble connecting"), (302, "unavailable")])
def test_safe_status_responses(integration, monkeypatch, status, expected):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(status, text="private provider error"))
    response = chatbot.chat("I need support", [])
    assert expected in response
    assert "private" not in response


@pytest.mark.parametrize("payload", [None, {}, {"choices": []}, {"choices": [None]},
    {"choices": [{"message": {"role": "user", "content": "private"}}]},
    {"choices": [{"message": {"role": "assistant", "content": 42}}]},
    {"choices": [{"message": {"role": "assistant", "content": " "}}]},
    {"choices": [{"message": {"role": "assistant", "content": "private", "tool_calls": [{}]}}]}])
def test_malformed_response_fails_closed(integration, monkeypatch, payload):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json=payload))
    assert "unavailable" in chatbot.chat("I need support", [])


@pytest.mark.parametrize("error, expected", [(httpx.ReadTimeout, "timed out"),
                                           (httpx.ConnectError, "unavailable")])
def test_transport_failure(integration, monkeypatch, caplog, error, expected):
    def fail(*args, **kwargs):
        raise error("private conversation")
    monkeypatch.setattr(httpx, "post", fail)
    assert expected in chatbot.chat("I need support", [])
    assert "private conversation" not in caplog.text


def test_local_model_remains_explicit_opt_in(integration, monkeypatch):
    monkeypatch.setattr(chatbot.config, "USE_LLM_PROXY", False)
    monkeypatch.setattr(chatbot, "respond_with_dialogpt", lambda *a: "Local model answer")
    assert chatbot.chat("I need support", []) == "Local model answer"
