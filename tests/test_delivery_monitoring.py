import logging
from concurrent.futures import ThreadPoolExecutor

import pytest

from src import chatbot
from src.monitoring import get_monitoring_metrics, reset_monitoring_metrics


@pytest.fixture(autouse=True)
def clean_metrics(monkeypatch):
    reset_monitoring_metrics()
    monkeypatch.setattr(chatbot.config, "ENABLE_RATE_LIMITING", False)
    yield
    reset_monitoring_metrics()


@pytest.mark.parametrize("message, expected", [
    ("My delivery is late", "latest estimate"),
    ("Items are missing from my order", "affected items"),
    ("How do I contact the courier?", "contact option"),
    ("What is the delivery fee?", "checkout"),
    ("Do you deliver to my area?", "secure checkout"),
    ("How can I update my delivery address?", "secure form"),
    ("I want a refund", "store policy"),
])
def test_delivery_guidance(message, expected):
    assert expected in chatbot.chat(message, []).lower()
    metrics = get_monitoring_metrics()
    assert metrics["requests"] == 1
    assert metrics["input_allowed"] == 1
    assert metrics["outcome_completed"] == 1


def test_order_status_does_not_invent_backend_data():
    response = chatbot.chat("Track order AB-12345", [])
    assert "AB-12345" in response
    assert "cannot access live" in response
    assert "2 business days" not in response


def test_blocked_input_metrics_do_not_retain_content(caplog):
    caplog.set_level(logging.INFO)
    secret = "123-45-6789"
    chatbot.chat("My SSN is " + secret, [])
    metrics = get_monitoring_metrics()
    assert metrics["requests"] == 1
    assert metrics["input_blocked"] == 1
    assert secret not in str(metrics) + caplog.text


def test_complete_output_is_screened_once(monkeypatch):
    monkeypatch.setattr(chatbot, "_chat", lambda message, history: "SSN: 123-45-6789")
    response = chatbot.chat("Help", [])
    assert "123-45-6789" not in response
    assert get_monitoring_metrics()["outcome_output_blocked"] == 1


def test_errors_are_counted_without_exception_text(monkeypatch, caplog):
    def fail(message, history):
        raise RuntimeError("private payload")
    monkeypatch.setattr(chatbot, "_chat", fail)
    with pytest.raises(RuntimeError):
        chatbot.chat("Help", [])
    assert get_monitoring_metrics()["outcome_error"] == 1
    assert "private payload" not in caplog.text


def test_concurrent_metrics_are_consistent():
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: chatbot.chat("My delivery is late", []), range(40)))
    metrics = get_monitoring_metrics()
    assert metrics["requests"] == metrics["outcome_completed"] == 40
    assert metrics["route_late_delivery"] == 40
    assert metrics["latency_ms_mean"] >= 0


def test_unconfigured_proxy_never_sends_request(monkeypatch):
    monkeypatch.setattr(chatbot.config, "PROXY_CLIENT_KEY", "  ")
    import httpx
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("must not send credentials"))
    assert "unavailable" in chatbot.respond_via_proxy("Help", [])
